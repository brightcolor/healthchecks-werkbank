// Jede Seite hell und dunkel, Kontrast, Breiten ohne Querscrollen, Listen auf dem Handy.
import { test, expect } from '@playwright/test';
import { anmelden, angemeldeteSeiten, bilder, breiten, daten, konsolenfehler, kontrast, ueberdeckungen, werkbankGeladen } from './hilfen.mjs';

for (const wer of ['hell', 'dunkel']) {
  for (const [name, pfad] of angemeldeteSeiten) {
    test(`${name} ${wer}`, async ({ page }) => {
      const fehler = konsolenfehler(page);
      await anmelden(page, wer);
      const antwort = await page.goto(pfad);
      expect(antwort.status(), `${pfad} antwortet`).toBe(200);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('#wb-leiste')).toBeVisible();
      await expect(page.locator('body > nav.navbar')).toBeHidden();
      expect(await werkbankGeladen(page), 'werkbank.css ist geladen').toBe(true);
      expect(await page.evaluate(() => document.body.classList.contains('dark'))).toBe(wer === 'dunkel');
      await page.screenshot({ path: `${bilder}/${name}-${wer}.png`, fullPage: true });
      const k = await kontrast(page);
      expect(k.findings, `Kontrast ${name} ${wer}: ${k.summary}`).toEqual([]);
      expect(fehler, 'Konsole ohne Fehler').toEqual([]);
    });
  }
}

for (const breite of breiten) {
  test(`Breite ${breite} px ohne Querscrollen`, async ({ page }) => {
    await anmelden(page, 'hell');
    await page.setViewportSize({ width: breite, height: 900 });
    const zuBreit = [];
    for (const [name, pfad] of angemeldeteSeiten) {
      await page.goto(pfad);
      await page.waitForLoadState('networkidle');
      const ueber = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (ueber > 0) zuBreit.push(`${name}: ${ueber} px zu breit`);
      if (breite <= 390) await page.screenshot({ path: `${bilder}/${name}-${breite}.png`, fullPage: true });
    }
    expect(zuBreit).toEqual([]);
  });
}

test('Check-Liste auf dem Handy zweizeilig', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.checks);
  const zeile = page.locator('#checks-table tr.checks-row').first();
  const name = await zeile.locator('td').nth(1).boundingBox();
  const ping = await zeile.locator('td').nth(5).boundingBox();
  expect(ping, 'letzter Ping ist sichtbar').not.toBeNull();
  expect(ping.width).toBeGreaterThan(0);
  expect(ping.y, 'letzter Ping steht unter dem Namen').toBeGreaterThanOrEqual(name.y + name.height - 2);
});

test('Integrationen auf dem Handy zweizeilig', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.integrations);
  const zeile = page.locator('.channels-table tr.channel-row').first();
  const name = await zeile.locator('td').nth(1).boundingBox();
  const status = await zeile.locator('td').nth(3).boundingBox();
  expect(status, 'Status ist sichtbar').not.toBeNull();
  expect(status.y, 'Status steht unter dem Namen').toBeGreaterThanOrEqual(name.y + name.height - 2);
});

test('Log auf dem Handy zweizeilig', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.log);
  const zeile = page.locator('#log tr.ok').first();
  const rahmen = await zeile.boundingBox();
  const etikett = await zeile.locator('.label').first().boundingBox();
  const details = await zeile.locator('td').nth(4).boundingBox();
  expect(details.width, 'Details nutzen die Zeilenbreite').toBeGreaterThan(rahmen.width / 2);
  expect(details.y, 'Details stehen unter dem Etikett').toBeGreaterThanOrEqual(etikett.y + etikett.height - 2);
  expect(await ueberdeckungen(page, '#log tr', 'td:nth-child(-n+3), .label, td:nth-child(5)')).toEqual([]);
});

test('Integrationen: Text, Symbole und Knöpfe stehen frei', async ({ page }) => {
  await anmelden(page, 'hell');
  const befunde = [];
  for (const breite of breiten) {
    await page.setViewportSize({ width: breite, height: 900 });
    await page.goto(daten.seiten.integrations);
    const zeilen = '.add-integration li, .channels-table tr.channel-row';
    const teile = '.icon, .icon-cell img, h2, p, a.btn, td:nth-child(2)';
    for (const befund of await ueberdeckungen(page, zeilen, teile)) befunde.push(`${breite} px, ${befund}`);
  }
  expect(befunde).toEqual([]);
});
