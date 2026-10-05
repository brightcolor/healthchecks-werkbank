// Gemeinsame Hilfen der Browserprüfung.
import { mkdirSync, readFileSync } from 'node:fs';

export const daten = JSON.parse(readFileSync(process.env.WB_MUSTERDATEN || 'tests/e2e/ergebnisse/musterdaten.json', 'utf8'));
export const passwort = process.env.WB_TEST_PASSWORT || '';
export const bilder = process.env.WB_BILDER || 'tests/e2e/ergebnisse/bilder';
export const breiten = (process.env.WB_BREITEN || '320,390,768,1024,1280,1440').split(',').map(Number);
export const angemeldeteSeiten = Object.entries(daten.seiten).filter(([name]) => name !== 'anmeldung');

const erlaubt = process.env.WB_KONSOLE_ERLAUBT ? new RegExp(process.env.WB_KONSOLE_ERLAUBT) : null;
const kontrastSkript = readFileSync('vendor/hausschrift/scripts/check-contrast.js', 'utf8');
mkdirSync(bilder, { recursive: true });

export async function anmelden(page, wer) {
  if (!passwort) {
    throw new Error('WB_TEST_PASSWORT fehlt. Die Prüfung über tools/dev.py pruefen starten oder tools/ci/testinstanz.sh vorher laufen lassen.');
  }
  await page.goto(daten.seiten.anmeldung);
  await page.fill('#login-form input[name="email"]', daten.nutzer[wer]);
  await page.fill('#login-form input[name="password"]', passwort);
  await Promise.all([
    page.waitForURL((url) => url.pathname !== daten.seiten.anmeldung),
    page.click('#login-form button[type="submit"]'),
  ]);
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
