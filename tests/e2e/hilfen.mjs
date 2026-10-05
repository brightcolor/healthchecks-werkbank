// Gemeinsame Hilfen der Browserprüfung.
import { mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

export const daten = JSON.parse(readFileSync(process.env.WB_MUSTERDATEN || 'tests/e2e/ergebnisse/musterdaten.json', 'utf8'));
export const passwort = process.env.WB_TEST_PASSWORT || '';
export const bilder = process.env.WB_BILDER || 'tests/e2e/ergebnisse/bilder';
export const breiten = (process.env.WB_BREITEN || '320,390,768,1024,1280,1440').split(',').map(Number);
export const angemeldeteSeiten = Object.entries(daten.seiten).filter(([name]) => name !== 'anmeldung');
// Sitzungen der Musterkonten; liegen außerhalb von ergebnisse/, damit sie nicht mit den Bildern hochgeladen werden.
export const sitzungen = process.env.WB_SITZUNGEN || 'tests/e2e/.sitzungen';

const erlaubt = process.env.WB_KONSOLE_ERLAUBT ? new RegExp(process.env.WB_KONSOLE_ERLAUBT) : null;
const kontrastSkript = readFileSync('vendor/hausschrift/scripts/check-contrast.js', 'utf8');
mkdirSync(bilder, { recursive: true });

export function sitzungsDatei(wer) {
  return path.join(sitzungen, `${wer}.json`);
}

// Meldet ein Konto über das Formular an. Healthchecks erlaubt je Konto 20 Anmeldungen
// mit Passwort am Tag; deshalb ruft nur vorbereitung.mjs diese Funktion auf.
export async function mitPasswortAnmelden(page, wer) {
  if (!passwort) {
    throw new Error('WB_TEST_PASSWORT fehlt. Die Prüfung über tools/dev.py pruefen starten oder tools/ci/testinstanz.sh vorher laufen lassen.');
  }
  await page.goto(daten.seiten.anmeldung);
  await page.fill('#login-form input[name="email"]', daten.nutzer[wer]);
  await page.fill('#login-form input[name="password"]', passwort);
  await page.click('#login-form button[type="submit"]');
  await page.waitForLoadState('load');
  if (new URL(page.url()).pathname === daten.seiten.anmeldung) {
    const grund = (await page.locator('#login-form .text-danger').allTextContents()).join(' ').trim();
    throw new Error(`Die Anmeldung von ${daten.nutzer[wer]} ist gescheitert: ${grund || 'Healthchecks nennt keinen Grund'}. `
      + 'Bei „Too many attempts“ ist das Tageskontingent verbraucht; tools/dev.py pruefen löst die Sperre in der lokalen Testdatenbank.');
  }
}

// Übernimmt die Sitzung, die vorbereitung.mjs für das Konto abgelegt hat.
export async function anmelden(page, wer) {
  const zustand = JSON.parse(readFileSync(sitzungsDatei(wer), 'utf8'));
  await page.context().addCookies(zustand.cookies);
}

export function konsolenfehler(page) {
  const fehler = [];
  page.on('console', (meldung) => {
    if (meldung.type() === 'error' && !(erlaubt && erlaubt.test(meldung.text()))) fehler.push(meldung.text());
  });
  page.on('pageerror', (fehlerObjekt) => fehler.push(String(fehlerObjekt)));
  return fehler;
}

export async function kontrast(page) {
  return page.evaluate(kontrastSkript);
}

export async function werkbankGeladen(page) {
  return page.evaluate(() => [...document.styleSheets].some((blatt) => (blatt.href || '').includes('/bc/werkbank.css')));
}

// Sucht in jeder Zeile Teile, die einander überdecken. Bei Text zählen die Textzeilen,
// denn Blockkästen reichen immer bis zum rechten Rand; Bilder, Knöpfe und Etiketten
// zählen mit ihrem ganzen Kasten.
export async function ueberdeckungen(page, zeilen, teile) {
  return page.evaluate(([zeilen, teile]) => {
    const flaechen = (el) => {
      if (el.tagName === 'IMG' || el.matches('.btn, .label')) return [el.getBoundingClientRect()];
      const bereich = document.createRange();
      bereich.selectNodeContents(el);
      return [...bereich.getClientRects()].filter((r) => r.width > 1 && r.height > 1);
    };
    const schneiden = (a, b) => a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
    const befunde = [];
    for (const zeile of document.querySelectorAll(zeilen)) {
      const sichtbar = [...zeile.querySelectorAll(teile)].filter((el) => el.getBoundingClientRect().width > 0);
      for (let i = 0; i < sichtbar.length; i++) {
        for (let j = i + 1; j < sichtbar.length; j++) {
          const [a, b] = [sichtbar[i], sichtbar[j]];
          if (a.contains(b) || b.contains(a)) continue;
          if (flaechen(a).some((x) => flaechen(b).some((y) => schneiden(x, y)))) {
            befunde.push(`„${zeile.textContent.trim().split(/\s+/)[0]}“: ${a.tagName.toLowerCase()} überdeckt ${b.tagName.toLowerCase()}`);
          }
        }
      }
    }
    return befunde;
  }, [zeilen, teile]);
}

// Healthchecks-Version, für die der Katalog vollständig ist, und die geprüfte Version.
// Tests, die bestimmte deutsche Texte von Healthchecks erwarten, laufen nur, wenn beide gleich sind.
export const stand = (readFileSync('werkbank/deutsch/katalog.toml', 'utf8').match(/^stand\s*=\s*"([^"]+)"/m) || [])[1] || '';
export const hcVersion = process.env.WB_HC_VERSION || '';
export const katalogStand = hcVersion !== '' && hcVersion === stand;
