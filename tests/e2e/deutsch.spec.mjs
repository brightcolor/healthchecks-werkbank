// Deutsche Oberfläche: Zahlen, die Skripte lesen, bleiben maschinenlesbar; Zustände, Dauern und
// Datumsangaben erscheinen deutsch. Texte von Healthchecks prüft der Test nur gegen die Version,
// für die der Katalog vollständig ist (katalogStand); sonst übernimmt der Hinweis-Issue.
import { test, expect } from '@playwright/test';
import { anmelden, daten, katalogStand } from './hilfen.mjs';

test('Log: Zeitstempel mit Punkt, Live-Updates antworten', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.log);
  const stempel = (await page.locator('#last-event-timestamp').textContent()).trim();
  expect(stempel, 'Zeitstempel als Zahl mit Dezimalpunkt').toMatch(/^\d+(\.\d+)?$/);
  const pfad = await page.locator('#log').getAttribute('data-refresh-url');
  const antwort = await page.waitForResponse((r) => new URL(r.url()).pathname === pfad, { timeout: 20000 });
  expect(antwort.status(), `Live-Update ${pfad}`).toBe(200);
});

test('Zustände, Dauern und Datumsangaben deutsch', async ({ page }) => {
  test.skip(!katalogStand, 'nur gegen die Healthchecks-Version aus werkbank/deutsch/katalog.toml');
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  const liste = page.locator('#checks-table');
  await expect(liste).toContainText(/vor \d+/);
  await expect(liste).toContainText(/\d+ (Minuten?|Stunden?|Tage?|Wochen?)/);
  await expect(liste).not.toContainText(/\b(ago|minutes?|hours?|days?|weeks?|never)\b/i);

  await page.goto(daten.seiten.details);
  const details = page.locator('body');
  await expect(details).toContainText(/Intervall|Zeitplan/);
  await expect(details).not.toContainText(/\bPeriod\b|\bGrace Time\b/);
  const ausfaelle = page.locator('#downtimes');
  if (await ausfaelle.count()) {
    await expect(ausfaelle).toContainText(/(Jan|Feb|März|Apr|Mai|Juni|Juli|Aug|Sept|Okt|Nov|Dez)\.?\s+\d{4}/);
    await expect(ausfaelle).toContainText(/verfügbar/);
  }
});
