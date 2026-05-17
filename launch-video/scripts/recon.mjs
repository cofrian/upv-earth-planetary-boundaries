import {chromium} from 'playwright';
import {mkdir, writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const OUT = 'public/recon';

const ROUTES = [
  {path: '/dashboard', slug: '01-dashboard', label: 'Dashboard'},
  {path: '/analysis', slug: '02-analysis', label: 'Análisis exploratorio'},
  {path: '/papers', slug: '03-papers', label: 'Explorar corpus'},
  {path: '/upload', slug: '04-upload', label: 'Subir paper'},
];

async function extractTokens(page) {
  return await page.evaluate(() => {
    const body = document.body;
    const cs = getComputedStyle(body);
    const root = getComputedStyle(document.documentElement);

    const headings = [...document.querySelectorAll('h1, h2, [class*="font-semibold"]')]
      .slice(0, 5)
      .map((el) => {
        const s = getComputedStyle(el);
        return {tag: el.tagName, fontFamily: s.fontFamily, fontWeight: s.fontWeight, color: s.color};
      });

    const accents = [...document.querySelectorAll('[class*="emerald"], [class*="accent"], [class*="primary"], button')]
      .slice(0, 10)
      .map((el) => {
        const s = getComputedStyle(el);
        return {bg: s.backgroundColor, color: s.color};
      });

    const cssVars = {};
    const sheet = root.cssText || '';
    for (const k of ['--bg', '--surface-1', '--surface-2', '--line', '--text-main', '--text-muted', '--accent']) {
      const v = root.getPropertyValue(k).trim();
      if (v) cssVars[k] = v;
    }

    const themeAttr = document.documentElement.getAttribute('data-theme') || document.documentElement.className;

    return {
      bodyBg: cs.backgroundColor,
      bodyColor: cs.color,
      bodyFont: cs.fontFamily,
      htmlClass: document.documentElement.className,
      theme: themeAttr,
      cssVars,
      headings,
      accents,
    };
  });
}

async function getPaperIds(page) {
  await page.goto(`${BASE}/papers`, {waitUntil: 'networkidle', timeout: 30000});
  await page.waitForTimeout(800);
  return await page.evaluate(() => {
    const links = [...document.querySelectorAll('a[href^="/papers/"]')]
      .map((a) => a.getAttribute('href'))
      .filter((h) => h && h !== '/papers' && !h.includes('?'))
      .map((h) => h.replace(/^\/papers\//, ''))
      .filter((id) => id.length > 0 && id.length < 200);
    return [...new Set(links)].slice(0, 5);
  });
}

async function discoverChatbot(page) {
  await page.goto(`${BASE}/dashboard`, {waitUntil: 'networkidle', timeout: 30000});
  await page.waitForTimeout(800);
  return await page.evaluate(() => {
    const candidates = [...document.querySelectorAll('button, [role="button"]')]
      .filter((el) => {
        const t = (el.textContent || '').toLowerCase();
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        return /chat|assist|pregunt|bot/.test(t + ' ' + aria);
      })
      .map((el) => ({
        text: (el.textContent || '').trim().slice(0, 60),
        aria: el.getAttribute('aria-label'),
        rect: el.getBoundingClientRect().toJSON(),
      }));
    return candidates.slice(0, 5);
  });
}

async function main() {
  await mkdir(OUT, {recursive: true});

  const browser = await chromium.launch({headless: true});
  const ctx = await browser.newContext({viewport: {width: 1920, height: 1080}, deviceScaleFactor: 1});
  const page = await ctx.newPage();

  const report = {base: BASE, pages: [], paperIds: [], chatbot: [], tokens: null};

  for (const r of ROUTES) {
    console.log(`→ ${r.path}`);
    await page.goto(`${BASE}${r.path}`, {waitUntil: 'networkidle', timeout: 45000});
    await page.waitForTimeout(1200);
    await page.screenshot({path: join(OUT, `${r.slug}.png`), fullPage: false});
    const tokens = await extractTokens(page);
    if (!report.tokens) report.tokens = tokens;
    report.pages.push({...r, tokens: {bodyBg: tokens.bodyBg, bodyColor: tokens.bodyColor, theme: tokens.theme}});
  }

  console.log('→ discover paper IDs');
  report.paperIds = await getPaperIds(page);

  if (report.paperIds.length > 0) {
    const pid = report.paperIds[0];
    console.log(`→ /papers/${pid}`);
    await page.goto(`${BASE}/papers/${encodeURIComponent(pid)}`, {waitUntil: 'networkidle', timeout: 45000});
    await page.waitForTimeout(1500);
    await page.screenshot({path: join(OUT, `05-paper-detail.png`), fullPage: false});
    report.pages.push({path: `/papers/${pid}`, slug: '05-paper-detail', label: 'Detalle de paper'});
  }

  console.log('→ chatbot probe');
  report.chatbot = await discoverChatbot(page);

  await writeFile(join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log('\nDONE. Report at', join(OUT, 'report.json'));

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
