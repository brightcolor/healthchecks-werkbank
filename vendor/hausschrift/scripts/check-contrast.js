/*
 * check-contrast.js: WCAG AA contrast of every visible text on a rendered page.
 *
 * Paste into the browser console, or run through a browser tool's JavaScript
 * call; the last expression returns the result object.
 *
 * It scores the text against the background a reader actually sees: it walks
 * up the ancestors, composites every translucent layer, and reads
 * -webkit-text-fill-color first, because that property paints over `color`
 * (Elementor and Raven set it). Text over a background image or gradient
 * cannot be scored; those land in `unscored`.
 *
 * Single characters count (a white "4" on cyan fails like a word does).
 * Text inside inline SVG is scored by its `fill` against the shapes painted
 * beneath it, found with elementsFromPoint; that needs the text inside the
 * viewport, so run it on a full-height render (shoot.mjs --full). SVG text
 * outside the viewport lands in `unscored`.
 * Counter-test: scripts/gegenprobe-kontrast.html must give 6 findings.
 *
 * Thresholds: 4.5:1 for body text, 3:1 for large text (24 px, or 18.66 px bold).
 * Hover and focus states are not measured; check them with bc_check.py
 * contrast FG BG1 BG2 against every ground the text can sit on.
 *
 * Based on tools/check-contrast.js of ispconfig-brightcolor.
 */
(function () {
	'use strict';

	// rgb() is read directly. Everything else Chrome may report (color(srgb …)
	// from color-mix(), oklch(), lab()) goes through a 1 x 1 canvas, which
	// converts any valid CSS colour to sRGB bytes. A value the canvas rejects
	// returns null and is reported, never skipped in silence.
	var canvas = document.createElement('canvas');
	canvas.width = canvas.height = 1;
	var ctx = canvas.getContext('2d', { willReadFrequently: true });

	function parse(color) {
		var s = String(color || '').trim();
		if (!s || s === 'transparent') return { r: 0, g: 0, b: 0, a: 0 };
		var m = s.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?\s*\)$/);
		if (m) {
			var a = m[4] === undefined ? 1 : (m[4].slice(-1) === '%' ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
			return { r: +m[1], g: +m[2], b: +m[3], a: a };
		}
		ctx.clearRect(0, 0, 1, 1);
		ctx.fillStyle = '#010203';
		ctx.fillStyle = s;
		if (ctx.fillStyle === '#010203') return null;
		ctx.fillRect(0, 0, 1, 1);
		var d = ctx.getImageData(0, 0, 1, 1).data;
		return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 };
	}

	function composite(top, bottom) {
		var a = top.a + bottom.a * (1 - top.a);
		if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
		return {
			r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
			g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
			b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
			a: a
		};
	}

	function background(el) {
		var layers = [], node = el, image = false, unread = null;
		while (node && node.nodeType === 1) {
			var s = getComputedStyle(node);
			if (s.backgroundImage && s.backgroundImage !== 'none') image = true;
			var bg = parse(s.backgroundColor);
			if (!bg) { unread = s.backgroundColor; image = true; }
			if (bg && bg.a > 0) {
				layers.push(bg);
				if (bg.a === 1) break;
			}
			node = node.parentElement;
		}
		var out = layers.length ? layers[layers.length - 1] : { r: 255, g: 255, b: 255, a: 1 };
		for (var i = layers.length - 2; i >= 0; i--) out = composite(layers[i], out);
		if (out.a < 1) out = composite(out, { r: 255, g: 255, b: 255, a: 1 });
		return { color: out, image: image, unread: unread };
	}

	function luminance(c) {
		function lin(v) { v = v / 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }
		return .2126 * lin(c.r) + .7152 * lin(c.g) + .0722 * lin(c.b);
	}

	function ratio(fg, bg) {
		var a = luminance(fg), b = luminance(bg);
		return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
	}

	function hex(c) {
		function h(v) { return ('0' + Math.round(v).toString(16)).slice(-2); }
		return '#' + h(c.r) + h(c.g) + h(c.b);
	}

	function describe(el) {
		// getAttribute: on SVG elements className is an object, not a string.
		var raw = (el.getAttribute && el.getAttribute('class')) || '';
		var cls = raw.trim() ? '.' + raw.trim().split(/\s+/).slice(0, 2).join('.') : '';
		return el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + cls;
	}

	function ownText(el) {
		for (var i = 0; i < el.childNodes.length; i++) {
			var n = el.childNodes[i];
			if (n.nodeType === 3 && n.textContent.trim().length > 0) return true;
		}
		return false;
	}

	function num(value, fallback) {
		var f = parseFloat(value);
		return isNaN(f) ? fallback : f;
	}

	var SVG_TEXT = /^(text|tspan|textpath)$/i;
	var SVG_SHAPE = /^(rect|circle|ellipse|path|polygon|polyline|line)$/i;

	// The ground under SVG text: the shapes painted beneath its centre, then
	// the HTML element the drawing sits on.
	function centre(el) {
		var box = el.getBoundingClientRect();
		var x = box.left + box.width / 2, y = box.top + box.height / 2;
		var inside = x >= 0 && y >= 0 && x < window.innerWidth && y < window.innerHeight;
		return { x: x, y: y, inside: inside };
	}

	function svgBackground(el) {
		var at = centre(el);
		// Hit-testing needs the text on screen. "instant" beats a smooth
		// scroll-behavior that would still be moving when we measure; the
		// centre keeps it clear of a sticky header.
		if (!at.inside) {
			el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' });
			at = centre(el);
		}
		if (!at.inside) return { outside: true };
		var x = at.x, y = at.y;
		var stack = document.elementsFromPoint(x, y), layers = [], image = false, base = null;
		for (var i = 0; i < stack.length; i++) {
			var n = stack[i];
			if (n === el || el.contains(n)) continue;
			if (!(n instanceof SVGElement)) { base = n; break; }
			if (n.contains(el)) continue;
			var tag = n.tagName.toLowerCase();
			if (tag === 'image' || tag === 'foreignobject') { image = true; continue; }
			if (!SVG_SHAPE.test(tag)) continue;
			var s = getComputedStyle(n);
			if (/url\(/.test(s.fill)) { image = true; continue; }
			var c = parse(s.fill);
			if (!c) { image = true; continue; }
			c.a *= num(s.fillOpacity, 1) * num(s.opacity, 1);
			if (c.a > 0) {
				layers.push(c);
				if (c.a >= 1) break;
			}
		}
		var ground = base ? background(base) : { color: { r: 255, g: 255, b: 255, a: 1 }, image: false, unread: null };
		var out = ground.color;
		for (var j = layers.length - 1; j >= 0; j--) out = composite(layers[j], out);
		return { color: out, image: image || ground.image, unread: ground.unread };
	}

	function hidden(el) {
		for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
			var s = getComputedStyle(n);
			if (s.visibility === 'hidden' || s.display === 'none' || parseFloat(s.opacity) === 0) return true;
		}
		return false;
	}

	var findings = [], unscored = [], seen = {}, checked = 0;
	var nodes = document.querySelectorAll('body *');

	for (var i = 0; i < nodes.length; i++) {
		var el = nodes[i];
		if (!ownText(el)) continue;
		var box = el.getBoundingClientRect();
		if (!box.width || !box.height || hidden(el)) continue;
		if (el.closest('.bc-sr, .sr-only, .visually-hidden')) continue;

		var style = getComputedStyle(el);
		var svg = el instanceof SVGElement && SVG_TEXT.test(el.tagName);
		var fg, bg, size = parseFloat(style.fontSize);
		if (svg) {
			if (/url\(/.test(style.fill)) {
				unscored.push({ where: describe(el), text: el.textContent.trim().slice(0, 40), fg: style.fill, background: 'SVG-Text mit Verlauf oder Muster' });
				continue;
			}
			fg = parse(style.fill);
			if (!fg || fg.a === 0) continue;
			fg.a *= num(style.fillOpacity, 1) * num(style.opacity, 1);
			bg = svgBackground(el);
			if (bg.outside) {
				unscored.push({ where: describe(el), text: el.textContent.trim().slice(0, 40), fg: hex(fg), background: 'SVG-Text außerhalb des Fensters, mit --full messen' });
				continue;
			}
			// Font size in user units; the drawing may be scaled on screen.
			var ctm = el.getScreenCTM && el.getScreenCTM();
			if (ctm) size *= Math.sqrt(ctm.a * ctm.a + ctm.b * ctm.b);
		} else {
			fg = parse(style.webkitTextFillColor) || parse(style.color);
			if (!fg || fg.a === 0) continue;
			bg = background(el);
		}
		if (fg.a < 1) fg = composite(fg, bg.color);

		var weight = parseInt(style.fontWeight, 10) || 400;
		var large = size >= 24 || (size >= 18.66 && weight >= 700);
		var need = large ? 3 : 4.5;
		var got = ratio(fg, bg.color);
		checked++;

		if (bg.image) {
			unscored.push({ where: describe(el), text: el.textContent.trim().slice(0, 40), fg: hex(fg),
				background: bg.unread ? 'unlesbar: ' + bg.unread : 'Bild oder Verlauf' });
			continue;
		}
		if (got < need) {
			var key = describe(el) + '|' + hex(fg) + '|' + hex(bg.color);
			if (seen[key]) { seen[key].count++; continue; }
			seen[key] = { where: describe(el), text: el.textContent.trim().slice(0, 40), fg: hex(fg), bg: hex(bg.color),
				ratio: Math.round(got * 100) / 100, needs: need, count: 1 };
			findings.push(seen[key]);
		}
	}

	findings.sort(function (a, b) { return a.ratio - b.ratio; });
	if (typeof console !== 'undefined' && console.table && findings.length) console.table(findings);

	return {
		summary: checked + ' Texte geprüft, ' + findings.length + ' unter AA, ' + unscored.length + ' nicht messbar (Bild, Verlauf oder unlesbare Farbe)',
		findings: findings,
		unscored: unscored.slice(0, 20)
	};
})()
