// Leiste, Kopfzeile, Anmeldeseite und Umschalter für Hell und Dunkel.
import { test, expect } from '@playwright/test';
import { anmelden, bilder, daten, konsolenfehler, kontrast } from './hilfen.mjs';

test('Anmeldeseite mit Markenfläche', async ({ page }) => {
  const fehler = konsolenfehler(page);
  await page.goto(daten.seiten.anmeldung);
  await expect(page.locator('.wb-marke')).toBeVisible();
  await expect(page.locator('#wb-leiste')).toHaveCount(0);
  await expect(page.locator('body > nav.navbar')).toBeHidden();
  await page.screenshot({ path: `${bilder}/anmeldung.png`, fullPage: true });
  const k = await kontrast(page);
  expect(k.findings, k.summary).toEqual([]);
  expect(fehler).toEqual([]);
});

test('Leiste zeigt jedes Projekt als Modul, eines ist offen', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  const module = page.locator('.wb-projekt > .bc-rail__item');
  await expect(module).toHaveCount(daten.projekte.length);
  await expect(module.first()).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.bc-rail__link[aria-current="page"]')).toHaveText('Checks');
  await module.nth(1).click();
  await expect(module.nth(1)).toHaveAttribute('aria-expanded', 'true');
  await expect(module.first()).toHaveAttribute('aria-expanded', 'false');
  const ziel = await page.locator(`#wb-sub-${daten.projekte[1].code} a`).first().getAttribute('href');
  expect(ziel).toContain(daten.projekte[1].code);
  await module.nth(1).click();
  await expect(module.nth(1)).toHaveAttribute('aria-expanded', 'false');
});

test('Zustand des Projekts steht als Punkt und als Wort in der Leiste', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  const nord = page.locator(`.wb-projekt[data-code="${daten.projekte[0].code}"]`);
  await expect(nord.locator('.wb-zustand')).toHaveClass(/ic-down/);
  await expect(nord.locator('.wb-zustand__text')).toHaveText(/\(down\)/);
});

test('Brotkrumen nennen Projekt und Seite', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.log);
  const krumen = page.locator('.bc-crumbs');
  await expect(krumen).toContainText(daten.projekte[0].name);
  await expect(krumen.locator('[aria-current="page"]')).toHaveText('Log');
});

test('Sprunglink ist das erste Ziel der Tastatur', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  await page.keyboard.press('Tab');
  await expect(page.locator('.wb-sprung')).toBeFocused();
});

test('Leiste auf dem Handy: Menüknopf, Escape und Schleier', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.checks);
  const leiste = page.locator('#wb-leiste');
  const knopf = page.locator('.bc-burger');
  await expect(leiste).toBeHidden();
  await knopf.click();
  await expect(leiste).toBeVisible();
  await expect(knopf).toHaveAttribute('aria-expanded', 'true');
  await leiste.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)));
  await page.screenshot({ path: `${bilder}/leiste-handy.png` });
  await page.keyboard.press('Escape');
  await expect(leiste).toBeHidden();
  await expect(knopf).toBeFocused();
  await knopf.click();
  await page.locator('.bc-shade').click({ position: { x: 360, y: 420 } });
  await expect(leiste).toBeHidden();
});

test('Umschalter speichert die Darstellung', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  await page.click('.bc-mode [data-mode="dark"]');
  await expect(page.locator('body')).toHaveClass(/\bdark\b/);
  await page.reload();
  await expect(page.locator('body')).toHaveClass(/\bdark\b/);
  await page.click('.bc-mode [data-mode="light"]');
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
  await page.reload();
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
});

test('Umschalter: scheitert das Speichern, springt der Modus zurück und eine Meldung erscheint', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  await page.route((url) => url.pathname === daten.seiten.darstellung, (route) => route.abort());
  await page.click('.bc-mode [data-mode="dark"]');
  const meldung = page.locator('.wb-meldung');
  await expect(meldung).toBeVisible();
  await expect(meldung).toContainText(/reload the page/i);
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
});
