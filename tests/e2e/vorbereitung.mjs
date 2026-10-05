// Meldet jedes Musterkonto einmal je Lauf an und legt die Sitzung ab.
// Die Tests übernehmen sie mit anmelden(); so bleibt es bei einer Anmeldung je Konto und Lauf.
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { daten, mitPasswortAnmelden, sitzungen, sitzungsDatei } from './hilfen.mjs';

export default async function vorbereitung(config) {
  const { baseURL, channel } = config.projects[0].use;
  mkdirSync(sitzungen, { recursive: true });
  const browser = await chromium.launch({ channel });
  try {
    for (const wer of Object.keys(daten.nutzer)) {
      const kontext = await browser.newContext({ baseURL });
      const page = await kontext.newPage();
      await mitPasswortAnmelden(page, wer);
      await kontext.storageState({ path: sitzungsDatei(wer) });
      await kontext.close();
    }
  } finally {
    await browser.close();
  }
}
