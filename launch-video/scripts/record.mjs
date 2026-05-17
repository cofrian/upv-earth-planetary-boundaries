import {chromium} from 'playwright';
import {mkdir, rename, writeFile, readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {join} from 'node:path';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const OUT = 'public/recordings';
const PDF_PATH = '/home/sortmon/UPV_EARTH_PROYECTOIII/docs/A study of aerosol liquid water content based on hygroscopicity measurements at high relative humidity in the North China Plain.pdf';

const HIDE_CURSOR_CSS = `*, *::before, *::after { cursor: none !important; } html, body { cursor: none !important; }`;

const RAG_QUESTION = 'What does the corpus say about freshwater use and aerosol-water interactions across the planetary boundaries?';

async function setup(browser, slug, durationSec) {
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
  page.pause = async (ms) => {
    await page.waitForTimeout(ms);
  };

  return {ctx, page, slug, durationSec};
}

async function finalize({ctx, page, slug, durationSec}, startedAt) {
  const elapsed = Date.now() - startedAt;
  const remaining = Math.max(0, durationSec * 1000 - elapsed);
  if (remaining > 0) await page.waitForTimeout(remaining);
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
  await writeFile(join(OUT, `${slug}.cursor.json`), JSON.stringify({slug, durationSec, events}, null, 2));
}

async function clip01_dashboard(browser) {
  const slug = '01-dashboard';
  console.log(`→ ${slug}`);
  const env = await setup(browser, slug, 7);
  const {page} = env;
  await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(500);
  page.startClock();
  // Bring cursor in from off-screen-ish toward the big KPI numbers
  await page.moveSlow(300, 200);
  await page.pause(450);
  // KPI "Indexado en SPECTER2" sits in the second row. Approximate coords.
  await page.moveSlow(1280, 540);
  await page.pause(700);
  await page.moveSlow(960, 700);
  await page.pause(500);
  await page.mouse.wheel(0, 600);
  page.recordEvent('scroll', 960, 700, {dy: 600});
  await page.pause(900);
  await page.moveSlow(700, 800);
  return finalize(env, Date.now() - 4000); // fallback compute, will be replaced below
}

async function clipRunner(name, durationSec, body, browser) {
  const env = await setup(browser, name, durationSec);
  const startedAt = Date.now();
  env.page.startClock();
  await body(env);
  await finalize(env, startedAt);
}

async function clip02_analysis(env) {
  const {page} = env;
  await page.goto(`${BASE}/analysis`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(400);
  await page.moveSlow(280, 220);
  await page.pause(500);
  await page.moveSlow(1180, 500);
  await page.pause(600);
  await page.mouse.wheel(0, 500);
  page.recordEvent('scroll', 960, 540, {dy: 500});
  await page.pause(700);
  await page.moveSlow(720, 760);
  await page.pause(500);
}

async function clip03_papers(env) {
  const {page} = env;
  await page.goto(`${BASE}/papers`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(400);
  // Move to search input near top of papers page
  await page.moveSlow(420, 320);
  await page.pause(350);
  await page.clickAt(420, 320);
  // Type slowly
  await page.keyboard.type('freshwater', {delay: 65});
  page.recordEvent('type', 420, 320, {text: 'freshwater'});
  await page.pause(600);
  // Scroll the table area
  await page.moveSlow(960, 700);
  await page.mouse.wheel(0, 500);
  page.recordEvent('scroll', 960, 700, {dy: 500});
  await page.pause(700);
  await page.moveSlow(900, 820);
}

async function clip04_paperDetail(env, paperId) {
  const {page} = env;
  await page.goto(`${BASE}/papers/${encodeURIComponent(paperId)}`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(500);
  await page.moveSlow(960, 380);
  await page.pause(500);
  await page.moveSlow(1300, 420);
  await page.pause(500);
  await page.mouse.wheel(0, 600);
  page.recordEvent('scroll', 960, 600, {dy: 600});
  await page.pause(800);
  await page.moveSlow(700, 760);
  await page.pause(400);
}

async function clip05_upload(env) {
  const {page} = env;
  await page.goto(`${BASE}/upload`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(400);
  // Move cursor near the dropzone label first
  await page.moveSlow(420, 460);
  await page.pause(450);
  // Set file directly into the hidden input
  const input = page.locator('#pdf-input');
  await input.setInputFiles(PDF_PATH);
  page.recordEvent('upload', 420, 460, {file: 'aerosol_liquid_water_north_china.pdf'});
  // The page should now switch to pipeline view; move cursor toward stage timeline
  await page.pause(900);
  await page.moveSlow(1200, 500);
  await page.pause(700);
  await page.moveSlow(1200, 620);
  await page.pause(900);
  await page.moveSlow(1200, 740);
  await page.pause(900);
  await page.moveSlow(900, 800);
  await page.pause(500);
}

async function clip06_chat(env) {
  const {page} = env;
  await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
  await page.pause(400);
  // Floating chatbot button is around (1840, 1000) from recon
  await page.moveSlow(1864, 1024);
  await page.pause(350);
  await page.clickAt(1864, 1024);
  await page.pause(700);
  // After open, textarea appears inside the floating panel. Find it.
  const textarea = page.locator('div[aria-label="Chatbot UPV-EARTH"] textarea').first();
  await textarea.waitFor({state: 'visible', timeout: 6000});
  const box = await textarea.boundingBox();
  if (box) {
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    await page.moveSlow(cx, cy);
    await page.pause(250);
    await page.clickAt(cx, cy);
  }
  await page.keyboard.type(RAG_QUESTION, {delay: 22});
  page.recordEvent('type', 0, 0, {text: RAG_QUESTION});
  await page.pause(350);
  // Submit by pressing Enter (form will catch onSubmit on enter? safer: click submit)
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
  // Stream usually starts in <1s; keep recording until total 10s
  await page.pause(6500);
}

async function main() {
  await mkdir(OUT, {recursive: true});
  const report = JSON.parse(await readFile('public/recon/report.json', 'utf-8'));
  const paperId = report.paperIds[0];
  console.log('Paper for detail clip:', paperId);

  const browser = await chromium.launch({headless: true, args: ['--disable-blink-features=AutomationControlled']});

  console.log('→ 01-dashboard'); await clipRunner('01-dashboard', 7, async ({page}) => {
    await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
    await page.pause(400);
    await page.moveSlow(300, 220);
    await page.pause(450);
    await page.moveSlow(1280, 540);
    await page.pause(700);
    await page.mouse.wheel(0, 500);
    page.recordEvent('scroll', 960, 540, {dy: 500});
    await page.pause(800);
    await page.moveSlow(700, 760);
    await page.pause(400);
  }, browser);

  console.log('→ 02-analysis'); await clipRunner('02-analysis', 6, clip02_analysis, browser);
  console.log('→ 03-papers'); await clipRunner('03-papers', 6, clip03_papers, browser);
  console.log('→ 04-paper-detail'); await clipRunner('04-paper-detail', 6, (env) => clip04_paperDetail(env, paperId), browser);
  console.log('→ 05-upload-pdf'); await clipRunner('05-upload-pdf', 9, clip05_upload, browser);
  console.log('→ 06-chat-rag'); await clipRunner('06-chat-rag', 10, clip06_chat, browser);

  await browser.close();
  console.log('\nALL DONE.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
