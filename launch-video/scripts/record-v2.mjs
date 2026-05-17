// Re-records 3 tour clips with cinematic scroll paths that showcase the
// full vertical richness of each page (charts, heatmaps, UMAP).
//
// Overwrites public/recordings/01-dashboard.webm, 02-analysis.webm,
// 04-paper-detail.webm and their .cursor.json files.

import {chromium} from 'playwright';
import {mkdir, rename, writeFile, readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const OUT = 'public/recordings';

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
  page.moveSlow = async (x, y, steps = 22) => {
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

  // Smooth scroll using requestAnimationFrame to a target Y, over a given duration.
  page.smoothScrollTo = async (targetY, durationMs) => {
    await page.evaluate(
      ([target, dur]) =>
        new Promise((resolve) => {
          const start = window.scrollY;
          const delta = target - start;
          const startTime = performance.now();
          const ease = (t) => 0.5 - Math.cos(Math.PI * t) / 2; // easeInOut
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

async function clipDashboard(browser) {
  console.log('→ 01-dashboard (10s, cinematic scroll)');
  const env = await setup(browser, '01-dashboard');
  const {page} = env;
  await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(600);
  page.startClock();

  // 0.0-1.2s: hover on the big KPI number (30,508)
  await page.moveSlow(280, 240);
  await page.pause(250);
  await page.moveSlow(1280, 540, 30);
  await page.pause(700);

  // 1.2-3.2s: scroll to area chart "Papers per año"
  await page.smoothScrollTo(900, 2000);
  page.recordEvent('scroll', 960, 540, {to: 900});
  await page.moveSlow(960, 700, 30);
  await page.pause(400);

  // 3.2-5.5s: scroll further to bar chart + donut
  await page.smoothScrollTo(1750, 2200);
  page.recordEvent('scroll', 960, 540, {to: 1750});

  // 5.5-7.5s: hover on donut chart area (right side)
  await page.moveSlow(1450, 620, 30);
  await page.pause(500);
  await page.moveSlow(1450, 700, 20);
  await page.pause(700);

  // 7.5-9s: scroll near bottom to show boundaries breakdown
  await page.smoothScrollTo(2700, 1500);
  page.recordEvent('scroll', 960, 540, {to: 2700});
  await page.moveSlow(700, 800, 25);
  await page.pause(800);

  await finalize(env);
}

async function clipAnalysis(browser) {
  console.log('→ 02-analysis (8s, jumps through key sections)');
  const env = await setup(browser, '02-analysis');
  const {page} = env;
  await page.goto(`${BASE}/analysis`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(600);
  page.startClock();

  // 0-1s: arrival, hover near top
  await page.moveSlow(320, 260, 25);
  await page.pause(500);

  // 1-3s: smooth scroll to bar charts / wordclouds area (~3000px)
  await page.smoothScrollTo(2800, 2000);
  page.recordEvent('scroll', 960, 540, {to: 2800});

  // 3-5s: hover on a chart, then continue scrolling
  await page.moveSlow(1300, 600, 30);
  await page.pause(700);
  await page.smoothScrollTo(7500, 2000);
  page.recordEvent('scroll', 960, 540, {to: 7500});

  // 5-7s: arrive at heatmap zone, hover
  await page.moveSlow(960, 700, 30);
  await page.pause(600);

  // 7-8s: jump-scroll to UMAP at the very bottom (the embedding map)
  await page.smoothScrollTo(13200, 1000);
  page.recordEvent('scroll', 960, 540, {to: 13200});
  await page.moveSlow(960, 600, 25);
  await page.pause(300);

  await finalize(env);
}

async function clipPaperDetail(browser, paperId) {
  console.log('→ 04-paper-detail (7s, scroll to similar papers + UMAP)');
  const env = await setup(browser, '04-paper-detail');
  const {page} = env;
  await page.goto(`${BASE}/papers/${encodeURIComponent(paperId)}`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(600);
  page.startClock();

  // 0-1.2s: hover on title + boundary chip
  await page.moveSlow(960, 380, 25);
  await page.pause(450);
  await page.moveSlow(1500, 380, 25);
  await page.pause(450);

  // 1.2-3s: scroll to similar papers list
  await page.smoothScrollTo(1300, 1500);
  page.recordEvent('scroll', 960, 540, {to: 1300});
  await page.moveSlow(900, 600, 25);
  await page.pause(500);

  // 3-5s: scroll to PB scoring bar chart
  await page.smoothScrollTo(3000, 1500);
  page.recordEvent('scroll', 960, 540, {to: 3000});
  await page.moveSlow(700, 700, 25);
  await page.pause(500);

  // 5-7s: scroll to UMAP visualization
  await page.smoothScrollTo(4500, 1500);
  page.recordEvent('scroll', 960, 540, {to: 4500});
  await page.moveSlow(960, 600, 25);
  await page.pause(500);

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
  await clipPaperDetail(browser, paperId);

  await browser.close();
  console.log('\nALL DONE.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
