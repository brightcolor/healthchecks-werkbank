// Markenname: Namen aus WB_MARKEN erscheinen so, wie sie geschrieben sind, auch dort,
// wo die Werkbank Versalien setzt. Die Instanz läuft dafür mit einem SITE_NAME, der
// einen dieser Namen enthält (tools/dev.py und tools/ci/testinstanz.sh, Vorgabe „bright color | health“).
import { test, expect } from '@playwright/test';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { anmelden, angemeldeteSeiten, daten, marken, markenVerstoesse } from './hilfen.mjs';

const mailOrdner = process.env.WB_MAILS || 'tests/e2e/ergebnisse/mails';

test('Anmeldeseite', async ({ page }) => {
  await page.goto(daten.seiten.anmeldung);
  const text = (await page.evaluate(() => document.body.textContent)).toLowerCase();
  test.skip(!marken.some((m) => text.includes(m.toLowerCase())),
    'SITE_NAME der Instanz enthält keinen Namen aus WB_MARKEN; die Prüfung braucht einen solchen Namen.');
  expect(await markenVerstoesse(page), 'Anmeldeseite').toEqual([]);
});

for (const [name, pfad] of angemeldeteSeiten) {
  test(`Seite ${name}`, async ({ page }) => {
    await anmelden(page, 'hell');
    await page.goto(pfad);
    expect(await markenVerstoesse(page), name).toEqual([]);
  });
}

test('Doku-Überschrift trägt den Namen der Instanz', async ({ page }) => {
  await page.goto(daten.seiten.docs);
  expect(await page.locator('h1').first().textContent()).not.toMatch(/WERKBANK_NAME|SITE_NAME/);
});

test('Mails', async ({ page }) => {
  const dateien = existsSync(mailOrdner) ? readdirSync(mailOrdner).filter((d) => d.endsWith('.html')).sort() : [];
  expect(dateien.length, `Mails in ${mailOrdner}; tools/dev.py mails legt sie an`).toBeGreaterThan(0);
  const befunde = [];
  for (const datei of dateien) {
    await page.setContent(readFileSync(path.join(mailOrdner, datei), 'utf8'));
    for (const befund of await markenVerstoesse(page)) befunde.push(`${datei}: ${befund}`);
  }
  expect(befunde).toEqual([]);
});
