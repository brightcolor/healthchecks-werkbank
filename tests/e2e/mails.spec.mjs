// Mails im Hausdesign: jede gerenderte Mail bei drei Breiten, ohne Querscrollen, Kontrast geprüft.
// tools/dev.py mails bzw. tools/ci/testinstanz.sh legt die Dateien an (tests/mails/rendern.py).
import { test, expect } from '@playwright/test';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { bilder, katalogStand, kontrast } from './hilfen.mjs';

const ordner = process.env.WB_MAILS || 'tests/e2e/ergebnisse/mails';
const breiten = (process.env.WB_MAIL_BREITEN || '360,390,760').split(',').map(Number);
const mails = existsSync(ordner) ? readdirSync(ordner).filter((d) => d.endsWith('.html')).map((d) => d.slice(0, -5)).sort() : [];
// Wörter, die in einem deutschen Betreff nicht vorkommen.
const englisch = /\b(the|is|your|you|has|been|log in|please)\b/i;

test('Alle Mails sind gerendert', () => {
  expect(mails.length, `Mails in ${ordner}; tools/dev.py mails legt sie an`).toBeGreaterThanOrEqual(15);
});

for (const name of mails) {
  test(`Mail ${name}`, async ({ page }) => {
    const html = readFileSync(path.join(ordner, `${name}.html`), 'utf8');
    // Über die Adresse der Instanz ausliefern: Logo und Schriften kommen dann aus derselben Quelle.
    await page.route('**/__werkbank-mail', (route) => route.fulfill({ contentType: 'text/html; charset=utf-8', body: html }));
    const befunde = [];
    for (const breite of breiten) {
      await page.setViewportSize({ width: breite, height: 900 });
      await page.goto('/__werkbank-mail');
      await page.evaluate(() => document.fonts.ready);
      const ueber = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (ueber > 0) befunde.push(`bei ${breite} px ${ueber} px zu breit`);
      await page.screenshot({ path: `${bilder}/mail-${name}-${breite}.png`, fullPage: true });
    }
    const k = await kontrast(page);
    if (k.findings.length) befunde.push(`Kontrast: ${k.summary}`);
    const logo = page.locator('img[alt="bright color"]');
    if ((await logo.count()) === 1) {
      expect(await logo.evaluate((img) => img.naturalWidth), 'Logo geladen').toBeGreaterThan(0);
    } else {
      befunde.push('steht nicht im Werkbank-Layout');
    }
    // Die deutschen Mails gelten für die Version aus katalog.toml. Ändert Healthchecks eine Vorlage,
    // bleibt sie englisch im Original; das ist ein Hinweis (Issue „uebersetzung“), kein Halt.
    if (!katalogStand) {
      if (befunde.length) test.info().annotations.push({ type: 'Hinweis', description: `${name}: ${befunde.join('; ')}` });
      return;
    }
    expect(befunde, `Mail ${name}`).toEqual([]);
    const betreff = readFileSync(path.join(ordner, `${name}-betreff.txt`), 'utf8');
    expect(betreff, `Betreff von ${name}`).not.toMatch(englisch);
    // Nur-Text-Fassung: Zeilen bis 78 Zeichen; Adressen ohne Leerzeichen und Tabellenzeilen dürfen länger sein.
    const zeilen = readFileSync(path.join(ordner, `${name}.txt`), 'utf8').split('\n');
    const lang = zeilen.filter((z) => z.length > 78 && z.trim().includes(' ') && !/^[+|]/.test(z));
    expect(lang, `Zeilen über 78 Zeichen in ${name}.txt`).toEqual([]);
    expect(zeilen.filter((z) => z === '--'), `Signaturtrenner in ${name}.txt ohne Leerzeichen`).toEqual([]);
  });
}
