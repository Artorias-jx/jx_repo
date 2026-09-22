/**
 * 诊断：打印指定知乎文章的原始 HTML 片段（定位公式/排版异常）
 *
 * 用法: node probe_zhihu.js <url> <关键词> [关键词2 ...]
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const CHROME_PATHS = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
];
function findChrome() {
  for (const p of CHROME_PATHS) if (fs.existsSync(p)) return p;
  throw new Error('找不到 Chrome/Edge');
}

async function main() {
  const url = process.argv[2];
  const keys = process.argv.slice(3);
  if (!url) { console.log('用法: node probe_zhihu.js <url> [关键词...]'); process.exit(1); }

  const browser = await chromium.launch({
    executablePath: findChrome(), headless: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 }, locale: 'zh-CN',
  });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(3000);

  const html = await page.evaluate(() => {
    const sel = ['.Post-RichTextContainer', '.RichText.ztext', '.Post-RichText', 'article'];
    let node = null;
    for (const s of sel) { node = document.querySelector(s); if (node) break; }
    return node ? node.innerHTML : '';
  });
  await browser.close();

  fs.writeFileSync('probe_raw.html', html, 'utf-8');
  console.log(`正文 HTML ${html.length} 字符 -> probe_raw.html`);

  if (!keys.length) return;
  for (const k of keys) {
    const idx = html.indexOf(k);
    console.log(`\n===== 关键词「${k}」${idx === -1 ? '未找到' : '位置 ' + idx} =====`);
    if (idx !== -1) {
      console.log(html.slice(Math.max(0, idx - 1200), idx + 2500));
    }
  }
}
main().catch(e => { console.error(e); process.exit(1); });
