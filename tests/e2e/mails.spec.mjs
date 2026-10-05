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
    for (const breite of breiten) {
      await page.setViewportSize({ width: breite, height: 900 });
      await page.goto('/__werkbank-mail');
      await page.evaluate(() => document.fonts.ready);
      const ueber = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(ueber, `${name} ist bei ${breite} px ${ueber} px zu breit`).toBeLessThanOrEqual(0);
      await page.screenshot({ path: `${bilder}/mail-${name}-${breite}.png`, fullPage: true });
    }
    const k = await kontrast(page);
    expect(k.findings, `Kontrast ${name}: ${k.summary}`).toEqual([]);
    const logo = page.locator('img[alt="bright color"]');
    await expect(logo, `${name} steht im Werkbank-Layout`).toHaveCount(1, { timeout: 5000 });
    expect(await logo.evaluate((img) => img.naturalWidth), 'Logo geladen').toBeGreaterThan(0);
    if (katalogStand) {
      const betreff = readFileSync(path.join(ordner, `${name}-betreff.txt`), 'utf8');
      expect(betreff, `Betreff von ${name}`).not.toMatch(englisch);
    }
  });
}
