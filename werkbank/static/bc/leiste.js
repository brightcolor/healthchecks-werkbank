/* healthchecks-werkbank: Leiste, Kopfzeile und Umschalter für die Darstellung.
   Alle Adressen kommen aus data-Attributen von bc/leiste.html. */
(function () {
	'use strict';

	var app = document.querySelector('.wb-app');
	if (!app) return;
	var leiste = app.querySelector('.bc-rail');
	var schleier = app.querySelector('.bc-shade');
	var projekte = leiste.querySelector('.wb-projekte');
	var menueknopf = document.querySelector('.bc-burger');
	var meldung = document.querySelector('.wb-meldung');
	var UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
	var ZUSTAENDE = ['down', 'grace', 'up'];
	var UNTERPUNKTE = [
		['zielChecks', 'Checks'],
		['zielIntegrations', 'Integrations'],
		['zielBadges', 'Badges'],
		['zielSettings', 'Settings']
	];
	var TEXTE = {
		sitzung: 'Your appearance setting wasn’t saved because your session has expired or the page is outdated. Reload the page, log in if asked, and try again.',
		antwort: 'Your appearance setting wasn’t saved: Healthchecks answered with an error (HTTP {status}). Reload the page and try again; if it happens again, check the server log.',
		netz: 'Your appearance setting wasn’t saved because Healthchecks didn’t respond. Check your connection, reload the page and try again.'
	};

	/* Akkordeon: ein Modul offen; ein Klick auf das offene klappt es zu. */
	function klappe(modul) {
		var offen = modul.getAttribute('aria-expanded') === 'true';
		leiste.querySelectorAll('.wb-projekt > .bc-rail__item').forEach(function (anderes) {
			anderes.setAttribute('aria-expanded', 'false');
			var sub = document.getElementById(anderes.getAttribute('aria-controls'));
			if (sub) sub.hidden = true;
		});
		modul.setAttribute('aria-expanded', String(!offen));
		var meins = document.getElementById(modul.getAttribute('aria-controls'));
		if (meins) meins.hidden = offen;
	}

	leiste.addEventListener('click', function (ereignis) {
		var modul = ereignis.target.closest('.wb-projekt > .bc-rail__item');
		if (modul) klappe(modul);
	});

	/* Projekte aus dem Projektmenü von Healthchecks. */
	function winkel() {
		var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svg.setAttribute('class', 'bc-rail__chev');
		svg.setAttribute('viewBox', '0 0 24 24');
		svg.setAttribute('aria-hidden', 'true');
		var pfad = document.createElementNS('http://www.w3.org/2000/svg', 'path');
		pfad.setAttribute('d', 'M9 6l6 6-6 6');
		svg.appendChild(pfad);
		return svg;
	}

	function setzeZustand(punkt, zustand) {
		if (!punkt) return;
		ZUSTAENDE.forEach(function (z) { punkt.classList.remove('ic-' + z); });
		punkt.classList.add('ic-' + zustand);
		var text = punkt.parentElement.querySelector('.wb-zustand__text');
		// Das Wort kommt aus der Vorlage (Filter zustand), damit das Skript jede Sprache spricht.
		var wort = app.getAttribute('data-zustand-' + zustand) || zustand;
		if (text) text.textContent = ' (' + wort + ')';
	}

	function zustandAus(element) {
		for (var i = 0; i < ZUSTAENDE.length; i++) {
			if (element && element.classList.contains('ic-' + ZUSTAENDE[i])) return ZUSTAENDE[i];
		}
		return 'up';
	}

	function modul(code, name, zustand) {
		var eintrag = document.createElement('li');
		eintrag.className = 'wb-projekt';
		eintrag.dataset.code = code;
		var knopf = document.createElement('button');
		knopf.className = 'bc-rail__item';
		knopf.type = 'button';
		knopf.setAttribute('aria-expanded', 'false');
		knopf.setAttribute('aria-controls', 'wb-sub-' + code);
		var punkt = document.createElement('span');
		punkt.className = 'wb-zustand';
		punkt.setAttribute('aria-hidden', 'true');
		var titel = document.createElement('span');
		titel.className = 'wb-projekt__name';
		titel.textContent = name;
		var text = document.createElement('span');
		text.className = 'bc-sr wb-zustand__text';
		knopf.append(punkt, titel, text, winkel());
		var sub = document.createElement('ul');
		sub.className = 'bc-rail__sub';
		sub.id = 'wb-sub-' + code;
		sub.hidden = true;
		UNTERPUNKTE.forEach(function (punktDaten) {
			var li = document.createElement('li');
			var a = document.createElement('a');
			a.className = 'bc-rail__link';
			a.href = app.dataset[punktDaten[0]].split(app.dataset.muster).join(code);
			a.textContent = punktDaten[1];
			li.appendChild(a);
			sub.appendChild(li);
		});
		eintrag.append(knopf, sub);
		setzeZustand(punkt, zustand);
		return eintrag;
	}

	function ladeProjekte() {
		if (!app.dataset.projektmenue || !projekte) return;
		fetch(app.dataset.projektmenue, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
			.then(function (antwort) {
				if (!antwort.ok) throw new Error('HTTP ' + antwort.status);
				return antwort.text();
			})
			.then(function (html) {
				// DOMParser parst inert: keine Skripte, keine geladenen Bilder; gelesen werden nur Text und Attribute.
				var dokument = new DOMParser().parseFromString(html, 'text/html');
				dokument.querySelectorAll('li.project-item a').forEach(function (link) {
					var treffer = (link.getAttribute('href') || '').match(UUID);
					if (!treffer) return;
					var code = treffer[0];
					var zustand = zustandAus(link.querySelector('.status'));
					var vorhanden = projekte.querySelector('.wb-projekt[data-code="' + code + '"]');
					if (vorhanden) {
						setzeZustand(vorhanden.querySelector('.wb-zustand'), zustand);
						return;
					}
					var name = (link.querySelector('.name') || link).textContent.trim();
					projekte.appendChild(modul(code, name, zustand));
				});
			})
			.catch(function () {
				var hinweis = leiste.querySelector('.wb-leiste__hinweis');
				if (hinweis) hinweis.hidden = false;
			});
	}

	/* Neues Projekt: der Dialog von Healthchecks, wo die Seite ihn mitbringt. */
	var neu = leiste.querySelector('[data-wb-neues-projekt]');
	if (neu && document.getElementById('add-project-modal')) {
		neu.setAttribute('data-toggle', 'modal');
		neu.setAttribute('data-target', '#add-project-modal');
		neu.setAttribute('role', 'button');
	}

	/* Schmale Bildschirme: Menüknopf, Schleier, Escape. */
	function zeigeLeiste(offen) {
		app.setAttribute('data-rail', offen ? 'open' : 'closed');
		if (menueknopf) menueknopf.setAttribute('aria-expanded', String(offen));
		if (schleier) schleier.hidden = !offen;
		if (offen) {
			var erstes = leiste.querySelector('a[href], button');
			if (erstes) erstes.focus();
		} else if (menueknopf) {
			menueknopf.focus();
		}
	}

	if (menueknopf) {
		menueknopf.addEventListener('click', function () {
			zeigeLeiste(app.getAttribute('data-rail') !== 'open');
		});
	}
	if (schleier) schleier.addEventListener('click', function () { zeigeLeiste(false); });
	document.addEventListener('keydown', function (ereignis) {
		if (ereignis.key === 'Escape' && app.getAttribute('data-rail') === 'open') zeigeLeiste(false);
	});

	/* Hell und dunkel: dieselbe Einstellung wie im Profil von Healthchecks. */
	var modusKnoepfe = document.querySelectorAll('.bc-mode [data-mode]');

	function zeigeModus(dunkel) {
		document.body.classList.toggle('dark', dunkel);
		modusKnoepfe.forEach(function (knopf) {
			knopf.setAttribute('aria-pressed', String((knopf.dataset.mode === 'dark') === dunkel));
		});
	}

	function melde(text) {
		if (!meldung) return;
		meldung.textContent = text;
		meldung.hidden = false;
	}

	zeigeModus(document.body.classList.contains('dark'));
	modusKnoepfe.forEach(function (knopf) {
		knopf.addEventListener('click', function () {
			var vorher = document.body.classList.contains('dark');
			var dunkel = knopf.dataset.mode === 'dark';
			if (dunkel === vorher || !app.dataset.darstellung) return;
			zeigeModus(dunkel);
			var token = document.querySelector('.wb-kopf input[name="csrfmiddlewaretoken"]');
			var formular = new URLSearchParams();
			formular.set('csrfmiddlewaretoken', token ? token.value : '');
			formular.set('theme', dunkel ? 'dark' : '');
			fetch(app.dataset.darstellung, {
				method: 'POST',
				credentials: 'same-origin',
				headers: { 'X-Requested-With': 'XMLHttpRequest' },
				body: formular
			})
				.then(function (antwort) {
					if (antwort.status === 403) throw { art: 'sitzung' };
					if (!antwort.ok) throw { art: 'antwort', status: antwort.status };
					if (meldung) meldung.hidden = true;
				})
				.catch(function (fehler) {
					zeigeModus(vorher);
					var art = fehler && fehler.art ? fehler.art : 'netz';
					melde(TEXTE[art].replace('{status}', fehler && fehler.status ? fehler.status : ''));
				});
		});
	});

	ladeProjekte();
})();
