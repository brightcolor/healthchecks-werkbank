// Grundlage: Healthchecks lädt werkbank.css, die Tokens der Hausschrift sind da.
import { test, expect } from '@playwright/test';
import { daten, konsolenfehler, werkbankGeladen } from './hilfen.mjs';

test('Anmeldeseite lädt werkbank.css mit den Tokens', async ({ page }) => {
  const fehler = konsolenfehler(page);
  const antwort = await page.goto(daten.seiten.anmeldung);
  expect(antwort.status()).toBe(200);
  expect(await werkbankGeladen(page)).toBe(true);
  const gelb = await page.evaluate(() => getComputedStyle(document.body).getPropertyValue('--bc-yellow').trim());
  expect(gelb).toBe('#fed329');
  expect(fehler).toEqual([]);
});
