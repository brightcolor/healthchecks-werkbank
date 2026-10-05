// Browserprüfung der Werkbank. Einstellungen über Umgebungsvariablen:
// WB_BASIS_URL (Vorgabe http://localhost:8000), WB_BROWSER_KANAL (chrome, msedge oder chromium),
// WB_TEST_FRIST (Frist je Test in Millisekunden, Vorgabe 120000).
import { defineConfig } from '@playwright/test';

const kanal = process.env.WB_BROWSER_KANAL || 'chrome';

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './tests/e2e/ergebnisse/playwright',
  fullyParallel: false,
  workers: 1,
  timeout: Number(process.env.WB_TEST_FRIST || 120000),
  reporter: [['list'], ['html', { outputFolder: 'tests/e2e/ergebnisse/bericht', open: 'never' }]],
  use: {
    baseURL: process.env.WB_BASIS_URL || 'http://localhost:8000',
    channel: kanal === 'chromium' ? undefined : kanal,
    viewport: { width: 1280, height: 900 },
    screenshot: 'only-on-failure',
  },
});
