/**
 * 从知乎目录页提取 408 真题解析各年各科 URL
 *
 * 用法: node extract_toc.js <目录页URL> [输出json]
 *   例: node extract_toc.js https://zhuanlan.zhihu.com/p/3484668199 toc.json
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
  const outJson = process.argv[3] || 'toc.json';
  if (!url) { console.log('用法: node extract_toc.js <目录页URL> [输出json]'); process.exit(1); }

  const browser = await chromium.launch({
    executablePath: findChrome(),
    headless: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
  });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(3000);

  // 滚动加载全部内容
  for (let k = 0; k < 30; k++) {
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 2));
    await page.waitForTimeout(400);
  }
  await page.waitForTimeout(1500);

  const links = await page.evaluate(() => {
    const root = document.querySelector('.Post-RichTextContainer, .RichText.ztext, article') || document.body;
    const out = [];
    root.querySelectorAll('a[href*="/p/"]').forEach(a => {
      const href = a.href || a.getAttribute('href') || '';
      const m = href.match(/zhuanlan\.zhihu\.com\/p\/(\d+)/);
      if (!m) return;
      out.push({
        id: m[1],
        text: (a.innerText || a.textContent || '').replace(/\s+/g, ' ').trim(),
        url: `https://zhuanlan.zhihu.com/p/${m[1]}`,
      });
    });
    return out;
  });

  await browser.close();
  fs.writeFileSync(outJson, JSON.stringify(links, null, 2), 'utf-8');
  console.log(`提取 ${links.length} 条链接 -> ${outJson}`);
  links.forEach(l => console.log(`${l.text}  |  ${l.url}`));
}
main().catch(e => { console.error(e); process.exit(1); });
