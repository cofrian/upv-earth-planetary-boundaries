// Records the upload flow, waits for ALL pipeline stages to complete.
// We record the full real-time wait (long); Remotion will crop out the middle.

import {chromium} from 'playwright';
import {mkdir, rename, writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const OUT = 'public/recordings';
const PDF_PATH = '/home/sortmon/UPV_EARTH_PROYECTOIII/docs/A study of aerosol liquid water content based on hygroscopicity measurements at high relative humidity in the North China Plain.pdf';

async function main() {
  await mkdir(OUT, {recursive: true});
  const browser = await chromium.launch({headless: true});
  const ctx = await browser.newContext({
    viewport: {width: 1920, height: 1080},
    deviceScaleFactor: 1,
    recordVideo: {dir: OUT, size: {width: 1920, height: 1080}},
  });
  await ctx.addInitScript(() => {
    const id = '__hide_cursor_style__';
    const apply = () => {
      if (document.getElementById(id)) return;
      const s = document.createElement('style');
      s.id = id;
      s.textContent = '*, *::before, *::after { cursor: none !important; }';
      (document.head || document.documentElement).appendChild(s);
    };
    if (document.readyState !== 'loading') apply();
    else document.addEventListener('DOMContentLoaded', apply);
  });
  const page = await ctx.newPage();
  const events = [];
  const t0 = {v: null};
  const startClock = () => {
    t0.v = Date.now();
  };
  const recordEvent = (action, x, y, extra = {}) => {
    if (t0.v === null) t0.v = Date.now();
    events.push({tMs: Date.now() - t0.v, action, x, y, ...extra});
  };
  const moveSlow = async (x, y, steps = 24) => {
    await page.mouse.move(x, y, {steps});
    recordEvent('move', x, y);
  };
  const clickAt = async (x, y) => {
    await moveSlow(x, y);
    await page.waitForTimeout(220);
    recordEvent('click_down', x, y);
    await page.mouse.down();
    await page.waitForTimeout(80);
    await page.mouse.up();
    recordEvent('click_up', x, y);
  };

  console.log('→ goto /upload');
  await page.goto(`${BASE}/upload`, {waitUntil: 'networkidle', timeout: 30000});
  await page.waitForTimeout(800);
  startClock();

  // 0-1.5s: hover dropzone
  await moveSlow(420, 460);
  await page.waitForTimeout(800);

  // 1.5-3s: drop file
  console.log('→ drop PDF');
  await page.locator('#pdf-input').setInputFiles(PDF_PATH);
  recordEvent('upload', 420, 460, {file: 'aerosol_liquid_water_north_china.pdf'});
  await page.waitForTimeout(1100);

  // Cursor moves towards "Procesar PDF" button
  await moveSlow(450, 700, 30);
  await page.waitForTimeout(400);

  // Click the "Procesar PDF" / Start button
  console.log('→ click Procesar PDF');
  try {
    const btn = page.getByRole('button', {name: /procesar pdf/i}).first();
    await btn.waitFor({state: 'visible', timeout: 5000});
    const bb = await btn.boundingBox();
    if (bb) {
      await moveSlow(bb.x + bb.width / 2, bb.y + bb.height / 2);
      await page.waitForTimeout(250);
      await clickAt(bb.x + bb.width / 2, bb.y + bb.height / 2);
    }
  } catch (e) {
    console.warn('No "Procesar PDF" button found, trying alternative...');
  }

  // Now we wait for processing. Poll the DOM until all stages show "completado"
  // (or up to 60s). The frontend updates as backend pushes SSE/poll events.
  console.log('→ waiting for pipeline to complete...');
  const completionStart = Date.now();
  let completed = false;
  while (Date.now() - completionStart < 60000) {
    completed = await page.evaluate(() => {
      // Look for any text suggesting completion: "completado", "complete", "done",
      // or "Resumen", "Inferencia Planetary Boundaries" results visible
      const text = document.body.innerText;
      // If we see "Persistencia" stage with "completado" or summary text, we're done.
      const persistenciaDone =
        /persistencia[\s\S]{0,200}completad/i.test(text) ||
        /resumen[\s\S]{0,200}generado/i.test(text);
      const summaryShown = /resumen extractivo/i.test(text) || /boundary principal/i.test(text);
      return persistenciaDone || summaryShown;
    });
    if (completed) {
      console.log('  ✓ pipeline reports completion');
      break;
    }
    await page.waitForTimeout(800);
  }
  if (!completed) {
    console.log('  (timed out at 60s — recording the current state anyway)');
  }

  // After completion, dwell heavily on results: scroll through validation,
  // similar papers, summary. Need ~18s of post-completion content.
  await page.waitForTimeout(1500);
  await moveSlow(1200, 600, 30);
  await page.waitForTimeout(1200);

  // Scroll 1: validation + abstract
  await page.evaluate(() => window.scrollTo({top: 500, behavior: 'smooth'}));
  recordEvent('scroll', 960, 540, {to: 500});
  await page.waitForTimeout(2400);
  await moveSlow(900, 700, 25);
  await page.waitForTimeout(1500);

  // Scroll 2: similar papers
  await page.evaluate(() => window.scrollTo({top: 1100, behavior: 'smooth'}));
  recordEvent('scroll', 960, 540, {to: 1100});
  await page.waitForTimeout(2400);
  await moveSlow(1000, 600, 25);
  await page.waitForTimeout(1500);

  // Scroll 3: deeper results
  await page.evaluate(() => window.scrollTo({top: 1700, behavior: 'smooth'}));
  recordEvent('scroll', 960, 540, {to: 1700});
  await page.waitForTimeout(2400);
  await moveSlow(900, 700, 25);
  await page.waitForTimeout(1500);

  // Scroll 4: even deeper
  await page.evaluate(() => window.scrollTo({top: 2400, behavior: 'smooth'}));
  recordEvent('scroll', 960, 540, {to: 2400});
  await page.waitForTimeout(2200);
  await moveSlow(960, 700, 25);
  await page.waitForTimeout(1500);

  const totalMs = Date.now() - t0.v;
  console.log(`  total scripted wallclock: ${totalMs}ms`);

  const videoHandle = page.video();
  await page.close();
  await ctx.close();
  if (videoHandle) {
    const tempPath = await videoHandle.path();
    const finalPath = join(OUT, '05-upload-pdf.webm');
    if (existsSync(tempPath)) {
      await rename(tempPath, finalPath);
      console.log(`  ✓ ${finalPath}`);
    }
  }
  await writeFile(join(OUT, '05-upload-pdf.cursor.json'), JSON.stringify({slug: '05-upload-pdf', events, totalMs}, null, 2));

  await browser.close();
  console.log('DONE.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
