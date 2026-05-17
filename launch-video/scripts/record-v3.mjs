// Records 6 tour clips at the new (longer) durations for the 2:20 video.
// Slower scrolling, more dwell time, richer content per clip.

import {chromium} from 'playwright';
import {mkdir, rename, writeFile, readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const OUT = 'public/recordings';
const PDF_PATH = '/home/sortmon/UPV_EARTH_PROYECTOIII/docs/A study of aerosol liquid water content based on hygroscopicity measurements at high relative humidity in the North China Plain.pdf';

async function setup(browser, slug) {
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
  page.__events = [];
  page.__t0 = null;
  page.startClock = () => {
    page.__t0 = Date.now();
  };
  page.recordEvent = (action, x, y, extra = {}) => {
    if (page.__t0 === null) page.__t0 = Date.now();
    page.__events.push({tMs: Date.now() - page.__t0, action, x, y, ...extra});
  };
  page.moveSlow = async (x, y, steps = 24) => {
    await page.mouse.move(x, y, {steps});
    page.recordEvent('move', x, y);
  };
  page.clickAt = async (x, y) => {
    await page.moveSlow(x, y);
    await page.waitForTimeout(220);
    page.recordEvent('click_down', x, y);
    await page.mouse.down();
    await page.waitForTimeout(80);
    await page.mouse.up();
    page.recordEvent('click_up', x, y);
  };
  page.pause = (ms) => page.waitForTimeout(ms);

  page.smoothScrollTo = async (targetY, durationMs) => {
    await page.evaluate(
      ([target, dur]) =>
        new Promise((resolve) => {
          const start = window.scrollY;
          const delta = target - start;
          const startTime = performance.now();
          const ease = (t) => 0.5 - Math.cos(Math.PI * t) / 2;
          const step = (now) => {
            const t = Math.min(1, (now - startTime) / dur);
            window.scrollTo(0, start + delta * ease(t));
            if (t < 1) requestAnimationFrame(step);
            else resolve();
          };
          requestAnimationFrame(step);
        }),
      [targetY, durationMs],
    );
  };
  return {ctx, page, slug};
}

async function finalize({ctx, page, slug}) {
  const videoHandle = page.video();
  const events = page.__events;
  await page.close();
  await ctx.close();
  if (videoHandle) {
    const tempPath = await videoHandle.path();
    const finalPath = join(OUT, `${slug}.webm`);
    if (existsSync(tempPath)) {
      await rename(tempPath, finalPath);
      console.log(`  ✓ ${finalPath}`);
    }
  }
  await writeFile(join(OUT, `${slug}.cursor.json`), JSON.stringify({slug, events}, null, 2));
}

// ─── 1. DASHBOARD ── 17s, slow scroll through every chart ─────────────
async function clipDashboard(browser) {
  console.log('→ 01-dashboard (17s)');
  const env = await setup(browser, '01-dashboard');
  const {page} = env;
  await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(700);
  page.startClock();

  // 0-2s: hover on KPI hero
  await page.moveSlow(280, 240);
  await page.pause(400);
  await page.moveSlow(1280, 540);
  await page.pause(1100);

  // 2-5s: scroll to area chart "Papers per año"
  await page.smoothScrollTo(900, 2500);
  page.recordEvent('scroll', 960, 540, {to: 900});
  await page.moveSlow(960, 700);
  await page.pause(700);

  // 5-9s: scroll further to bar chart + donut
  await page.smoothScrollTo(1750, 3000);
  page.recordEvent('scroll', 960, 540, {to: 1750});
  await page.moveSlow(1450, 620);
  await page.pause(700);
  await page.moveSlow(1450, 700);
  await page.pause(800);

  // 9-13s: scroll to boundaries breakdown
  await page.smoothScrollTo(2700, 2500);
  page.recordEvent('scroll', 960, 540, {to: 2700});
  await page.moveSlow(700, 800);
  await page.pause(900);

  // 13-17s: scroll to bottom (last KPI bars)
  await page.smoothScrollTo(3500, 2200);
  page.recordEvent('scroll', 960, 540, {to: 3500});
  await page.moveSlow(900, 700);
  await page.pause(1000);

  await finalize(env);
}

// ─── 2. ANALYSIS ── 15s, hits methodology + bar charts + stacked area + UMAP ──
async function clipAnalysis(browser) {
  console.log('→ 02-analysis (15s)');
  const env = await setup(browser, '02-analysis');
  const {page} = env;
  await page.goto(`${BASE}/analysis`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(700);
  page.startClock();

  // 0-2s: top with methodology
  await page.moveSlow(320, 260);
  await page.pause(800);

  // 2-5s: scroll to histograms + KPIs
  await page.smoothScrollTo(2800, 2500);
  page.recordEvent('scroll', 960, 540, {to: 2800});
  await page.moveSlow(1100, 700);
  await page.pause(700);

  // 5-8s: scroll to bar charts + donut (rich visuals)
  await page.smoothScrollTo(5300, 2400);
  page.recordEvent('scroll', 960, 540, {to: 5300});
  await page.moveSlow(1300, 600);
  await page.pause(700);

  // 8-11s: scroll to stacked area chart per boundary
  await page.smoothScrollTo(8500, 2500);
  page.recordEvent('scroll', 960, 540, {to: 8500});
  await page.moveSlow(960, 700);
  await page.pause(900);

  // 11-15s: scroll to UMAP embedding map (the visual finale)
  await page.smoothScrollTo(13200, 2500);
  page.recordEvent('scroll', 960, 540, {to: 13200});
  await page.moveSlow(960, 600);
  await page.pause(1000);

  await finalize(env);
}

// ─── 3. PAPERS ── 11s, search + scroll the table ─────────────────────
async function clipPapers(browser) {
  console.log('→ 03-papers (11s)');
  const env = await setup(browser, '03-papers');
  const {page} = env;
  await page.goto(`${BASE}/papers`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(700);
  page.startClock();

  // 0-2s: arrival
  await page.moveSlow(280, 280);
  await page.pause(700);

  // 2-4s: type in search
  await page.moveSlow(420, 320);
  await page.clickAt(420, 320);
  await page.keyboard.type('freshwater', {delay: 80});
  page.recordEvent('type', 420, 320, {text: 'freshwater'});
  await page.pause(700);

  // 4-7s: scroll table
  await page.smoothScrollTo(700, 2000);
  page.recordEvent('scroll', 960, 540, {to: 700});
  await page.moveSlow(960, 700);
  await page.pause(800);

  // 7-11s: scroll further + hover row
  await page.smoothScrollTo(1500, 2000);
  page.recordEvent('scroll', 960, 540, {to: 1500});
  await page.moveSlow(900, 600);
  await page.pause(700);
  await page.moveSlow(900, 800);
  await page.pause(800);

  await finalize(env);
}

// ─── 4. PAPER DETAIL ── 15s, scroll through everything a paper has ──
async function clipPaperDetail(browser, paperId) {
  console.log('→ 04-paper-detail (15s)');
  const env = await setup(browser, '04-paper-detail');
  const {page} = env;
  await page.goto(`${BASE}/papers/${encodeURIComponent(paperId)}`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(700);
  page.startClock();

  // 0-2s: hover on title + boundary chip
  await page.moveSlow(960, 380);
  await page.pause(500);
  await page.moveSlow(1500, 380);
  await page.pause(700);

  // 2-5s: scroll to validation cards
  await page.smoothScrollTo(900, 2200);
  page.recordEvent('scroll', 960, 540, {to: 900});
  await page.moveSlow(900, 600);
  await page.pause(800);

  // 5-9s: scroll to similar papers list
  await page.smoothScrollTo(2200, 2800);
  page.recordEvent('scroll', 960, 540, {to: 2200});
  await page.moveSlow(900, 600);
  await page.pause(800);
  await page.moveSlow(900, 800);
  await page.pause(600);

  // 9-12s: scroll to keywords bar charts
  await page.smoothScrollTo(3800, 2500);
  page.recordEvent('scroll', 960, 540, {to: 3800});
  await page.moveSlow(700, 600);
  await page.pause(700);

  // 12-15s: scroll to UMAP of this paper in embedding space
  await page.smoothScrollTo(5000, 2200);
  page.recordEvent('scroll', 960, 540, {to: 5000});
  await page.moveSlow(960, 700);
  await page.pause(800);

  await finalize(env);
}

// ─── 5. UPLOAD PDF ── 15s, drag + wait for pipeline ──────────────────
async function clipUpload(browser) {
  console.log('→ 05-upload-pdf (15s)');
  const env = await setup(browser, '05-upload-pdf');
  const {page} = env;
  await page.goto(`${BASE}/upload`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(700);
  page.startClock();

  // 0-2s: hover on dropzone
  await page.moveSlow(420, 460);
  await page.pause(900);

  // 2-3s: drop file
  const input = page.locator('#pdf-input');
  await input.setInputFiles(PDF_PATH);
  page.recordEvent('upload', 420, 460, {file: 'aerosol_liquid_water_north_china.pdf'});
  await page.pause(800);

  // 3-7s: hover over pipeline stages (one by one)
  await page.moveSlow(1200, 460);
  await page.pause(700);
  await page.moveSlow(1200, 560);
  await page.pause(700);
  await page.moveSlow(1200, 660);
  await page.pause(700);
  await page.moveSlow(1200, 760);
  await page.pause(700);

  // 7-10s: click "Procesar PDF" if visible, else just dwell
  try {
    const btn = page.getByRole('button', {name: /procesar pdf/i}).first();
    const bb = await btn.boundingBox({timeout: 1500});
    if (bb) {
      await page.moveSlow(bb.x + bb.width / 2, bb.y + bb.height / 2);
      await page.pause(300);
      await page.clickAt(bb.x + bb.width / 2, bb.y + bb.height / 2);
      page.recordEvent('process', bb.x + bb.width / 2, bb.y + bb.height / 2);
    }
  } catch (e) {
    // ignore — keep showing pipeline
  }
  await page.pause(900);

  // 10-15s: dwell + scroll through stages
  await page.smoothScrollTo(300, 2000);
  page.recordEvent('scroll', 960, 540, {to: 300});
  await page.moveSlow(1100, 700);
  await page.pause(1200);
  await page.moveSlow(900, 800);
  await page.pause(1200);

  await finalize(env);
}

// ─── 6. CHAT RAG ── 19s, send question + watch streaming response ───
async function clipChat(browser) {
  console.log('→ 06-chat-rag (19s)');
  const RAG_QUESTION = 'What does the corpus say about freshwater use and aerosol-water interactions across the planetary boundaries?';
  const env = await setup(browser, '06-chat-rag');
  const {page} = env;
  await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(700);
  page.startClock();

  // 0-2s: hover to chatbot launcher
  await page.moveSlow(1864, 1024);
  await page.pause(700);
  await page.clickAt(1864, 1024);
  await page.pause(900);

  // 2-6s: type question
  const textarea = page.locator('div[aria-label="Chatbot UPV-EARTH"] textarea').first();
  await textarea.waitFor({state: 'visible', timeout: 6000});
  const box = await textarea.boundingBox();
  if (box) {
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    await page.moveSlow(cx, cy);
    await page.pause(300);
    await page.clickAt(cx, cy);
  }
  await page.keyboard.type(RAG_QUESTION, {delay: 28});
  page.recordEvent('type', 0, 0, {text: RAG_QUESTION});
  await page.pause(500);

  // 6-7s: submit
  const submitBtn = page.locator('div[aria-label="Chatbot UPV-EARTH"] button[type="submit"]').first();
  const sb = await submitBtn.boundingBox();
  if (sb) {
    await page.moveSlow(sb.x + sb.width / 2, sb.y + sb.height / 2);
    await page.pause(200);
    await page.clickAt(sb.x + sb.width / 2, sb.y + sb.height / 2);
    page.recordEvent('submit', sb.x + sb.width / 2, sb.y + sb.height / 2);
  } else {
    await page.keyboard.press('Enter');
  }

  // 7-19s: wait for response to stream in
  await page.pause(11500);

  await finalize(env);
}

async function main() {
  await mkdir(OUT, {recursive: true});
  const report = JSON.parse(await readFile('public/recon/report.json', 'utf-8'));
  const paperId = report.paperIds[0];
  console.log('Paper for detail clip:', paperId);

  const browser = await chromium.launch({headless: true});

  await clipDashboard(browser);
  await clipAnalysis(browser);
  await clipPapers(browser);
  await clipPaperDetail(browser, paperId);
  await clipUpload(browser);
  await clipChat(browser);

  await browser.close();
  console.log('\nALL DONE.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
