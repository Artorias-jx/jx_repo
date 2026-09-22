/**
 * 知乎 408 真题解析 —— 一键抓取 + 转换
 *
 * 用法:
 *   node crawl_zhihu.js <url> <输出目录> [文件名前缀] [--headed]
 *   node crawl_zhihu.js --batch <清单文件> [--headed]
 *
 * 清单文件格式（每行）:
 *   <年份>|<科目>|<url>
 *   例: 2010|计算机组成原理|https://zhuanlan.zhihu.com/p/655158544
 *
 * 输出: <输出目录>/<年份年408真题><科目>篇.md
 *   （图片保留知乎图床外链）
 */
const { chromium } = require('playwright-core');
const TurndownService = require('turndown');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const CHROME_PATHS = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
];

function findChrome() {
  for (const p of CHROME_PATHS) if (fs.existsSync(p)) return p;
  throw new Error('找不到 Chrome/Edge');
}

function decodeTex(t) {
  return t.replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
/**
 * 判定是否「多行块公式」→ 输出 $$...$$
 *
 * 只有真正的 LaTeX 环境才算块公式。**不能因为含 `\\` 就判为块公式** ——
 * 知乎作者常在行内公式末尾多写一个 `\\`（LaTeX 换行残留），
 * 若据此提为块公式，会把一整句劈成三段（2026-09-22 踩坑：2010/2022 数据结构
 * 的「根据贪心策略，若 G 一定连通，则需要 [公式] 即先分成…」）。
 */
function isBlockMath(t) {
  return /\\begin\{(array|aligned|matrix|cases|bmatrix|pmatrix|vmatrix|split|gather|align)\}/.test(t);
}
/** 清行内公式末尾多余的 `\\`（知乎常见笔误） */
function tidyInlineTex(t) {
  return t.trim().replace(/\\{1,2}$/, '').trim();
}

/** HTML -> Markdown（图文位置完整还原） */
function html2md(html, title) {
  const texStore = {}, imgStore = {};

  // 1. 公式
  (function () {
    const out = [];
    let i = 0;
    while (i < html.length) {
      const idx = html.indexOf('ztext-math', i);
      if (idx === -1) { out.push(html.slice(i)); break; }
      const start = html.lastIndexOf('<span', idx);
      if (start === -1) { out.push(html.slice(i)); break; }
      let j = start, depth = 0;
      while (j < html.length) {
        const no = html.indexOf('<span', j);
        const nc = html.indexOf('</span>', j);
        if (nc === -1) break;
        if (no !== -1 && no < nc) { depth++; j = no + 5; }
        else { depth--; j = nc + 7; if (depth === 0) break; }
      }
      const whole = html.slice(start, j);
      const m = whole.match(/data-tex="([^"]*)"/);
      const tex = m ? decodeTex(m[1]) : '';
      out.push(html.slice(i, start));
      if (tex) {
        const block = isBlockMath(tex);
        const ph = (block ? 'ZZMATHB' : 'ZZMATHI') + out.length + 'ZZ';
        out.push(block ? `\n\n${ph}\n\n` : ph);
        texStore[ph] = block ? `\n\n$$${tex}$$\n\n` : `$${tidyInlineTex(tex)}$`;
      }
      i = j;
    }
    html = out.join('');
  })();

  // 2. 噪声
  html = html.replace(/<div[^>]*class="[^"]*\bCatalog\b[^"]*"[^>]*>[\s\S]*?<\/div>/g, '');
  html = html.replace(/<div[^>]*class="[^"]*\b(ContentItem-actions|Reward|Post-SideActions)\b[^"]*"[^>]*>[\s\S]*?<\/div>/g, '');
  html = html.replace(/<figcaption[\s\S]*?<\/figcaption>/g, '');
  html = html.replace(/<br\s*\/?>/g, '\n');

  // 3. 图片
  let n = 0;
  html = html.replace(/<img[^>]*>/g, (tag) => {
    let u = (tag.match(/data-original="([^"]+)"/) || [])[1]
         || (tag.match(/src="([^"]+)"/) || [])[1] || '';
    u = u.replace(/&amp;/g, '&');
    if (!u || u.startsWith('data:')) return '';
    const ph = `ZZIMGPZ${n}ZZ`;
    imgStore[ph] = `![](${u})`;
    n++;
    return `\n\n${ph}\n\n`;
  });

  // 4. turndown
  const td = new TurndownService({
    headingStyle: 'atx', codeBlockStyle: 'fenced',
    bulletListMarker: '-', emDelimiter: '*',
  });
  td.addRule('fencedCode', {
    filter: (node) => node.nodeName === 'PRE' && node.firstChild && node.firstChild.nodeName === 'CODE',
    replacement: (content, node) => {
      const code = node.firstChild;
      const lang = ((code.getAttribute('class') || '').match(/language-(\w+)/) || [])[1] || '';
      return `\n\n\`\`\`${lang}\n${code.textContent.replace(/\n$/, '')}\n\`\`\`\n\n`;
    },
  });
  td.keep(['table', 'thead', 'tbody', 'tr', 'th', 'td']);

  let md = td.turndown(html);

  // 5. 还原占位符
  for (const [p, v] of Object.entries(texStore)) md = md.split(p).join(v);
  for (const [p, v] of Object.entries(imgStore)) md = md.split(p).join(v);

  // 6. 收尾
  md = md.replace(/\u200b/g, '')
    .replace(/^<div[^>]*>\s*$/gm, '')
    .replace(/^<\/div>\s*$/gm, '')
    .replace(/^\s*收起\s*$/gm, '')
    // 删「第XX~40小题…最符合题目要求的。」单选题说明句（用户 2026-09-22 要求）
    .replace(/^第\s*\d+\s*~\s*40\s*小题[^\n]*最符合题目要求的。\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return { md: `# ${title}\n\n${md}\n`, imgCount: n,
           mathCount: (md.match(/\$/g) || []).length / 2 };
}

/** 清理知乎跳转污染（含 keep 保留的原始 HTML 表格内的残留 —— 2026-09-22 补） */
function cleanLinks(text) {
  const n1 = (text.match(/\[([^\]]+)\]\(https:\/\/zhida\.zhihu\.com\/[^)]+\)/g) || []).length;
  text = text.replace(/\[([^\]]+)\]\(https:\/\/zhida\.zhihu\.com\/[^)]+\)/g, '$1');
  let n2 = 0;
  text = text.replace(/\[([^\]]+)\]\(https:\/\/link\.zhihu\.com\/\?target=([^)&]+)[^)]*\)/g,
    (m, label, enc) => { n2++; return `[${label}](${decodeURIComponent(enc)})`; });

  // 表格是 td.keep 保留的原始 HTML，里面的 <a href="zhida..."> 不会被上面的 markdown 正则命中
  // 处理：把 <a ...href="zhida.zhihu.com/...">文字 [+内嵌 <svg>]</a> 整体替换成纯文字
  let n3 = 0;
  text = text.replace(/<a\b[^>]*href="https:\/\/zhida\.zhihu\.com\/[^"]*"[^>]*>([\s\S]*?)<\/a>/g,
    (m, inner) => { n3++; return inner.replace(/<svg[\s\S]*?<\/svg>/g, '').trim(); });
  // link.zhihu.com 的 HTML 版：还原真实目标
  text = text.replace(/<a\b[^>]*href="https:\/\/link\.zhihu\.com\/\?target=([^&"]+)[^"]*"[^>]*>([\s\S]*?)<\/a>/g,
    (m, enc, inner) => { n3++; return `[${inner.replace(/<svg[\s\S]*?<\/svg>/g, '').trim()}](${decodeURIComponent(enc)})`; });

  return { text, n1, n2, n3 };
}

/** 生成 frontmatter（与 Obsidian Clipper 剪藏格式一致；不含 description —— 用户 2026-09-22 要求删掉） */
function buildFrontmatter(title, url) {
  const created = new Date().toISOString().slice(0, 10);
  return [
    '---',
    `title: ${title}`,
    `source: ${url}`,
    'author:',
    '  - "[[千葉原]]"',
    `created: ${created}`,
    '---',
    '',
  ].join('\n');
}

async function fetchOne(ctx, url, outDir, title, opts = {}) {
  const page = await ctx.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(3000);
    const r = await page.evaluate(() => {
      const sel = ['.Post-RichTextContainer', '.RichText.ztext', '.Post-RichText', 'article'];
      let node = null;
      for (const s of sel) { node = document.querySelector(s); if (node) break; }
      const h1 = document.querySelector('.Post-Title, h1');
      return { title: h1 ? h1.innerText.trim() : document.title,
               html: node ? node.innerHTML : null };
    });
    if (!r.html) throw new Error('未找到正文容器');
    const { md, imgCount, mathCount } = html2md(r.html, title || r.title);
    const { text, n1, n2, n3 } = cleanLinks(md);
    const full = buildFrontmatter(title || r.title, url) + text;
    fs.mkdirSync(outDir, { recursive: true });
    const outFile = path.join(outDir, `${title}.md`);
    fs.writeFileSync(outFile, full, 'utf-8');
    return { ok: true, file: outFile, imgCount, mathCount, n1, n2, n3, len: full.length };
  } finally {
    await page.close();
  }
}

async function main() {
  const argv = process.argv.slice(2);
  const headed = argv.includes('--headed');
  const rest = argv.filter(a => !a.startsWith('--'));

  let targets = [];   // {year, subject, url}
  if (rest[0] === 'batch' || argv.includes('--batch')) {
    const listFile = rest[rest.includes('batch') ? rest.indexOf('batch') + 1 : 0];
    const lines = fs.readFileSync(listFile, 'utf-8').split(/\r?\n/).filter(Boolean);
    for (const ln of lines) {
      if (ln.startsWith('#')) continue;
      const [year, subject, url] = ln.split('|').map(s => s.trim());
      if (year && subject && url) targets.push({ year, subject, url });
    }
  } else {
    const [url, outDir, prefix] = rest;
    if (!url || !outDir) {
      console.log('用法: node crawl_zhihu.js <url> <输出目录> [文件名前缀] [--headed]');
      console.log('  或: node crawl_zhihu.js --batch <清单文件> [--headed]');
      process.exit(1);
    }
    targets.push({ year: '', subject: '', url, outDir, prefix: prefix || '' });
  }

  const browser = await chromium.launch({
    executablePath: findChrome(),
    headless: !headed,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 },
    locale: 'zh-CN',
  });

  let ok = 0, fail = 0;
  for (const t of targets) {
    const title = t.year ? `${t.year}年408真题${t.subject}篇` : (t.prefix || '');
    // 有年份时自动落到 <根>/<年份>/ 子目录
    const outDir = t.outDir || (t.year ? path.join(BASE_OUT, t.year) : BASE_OUT);
    process.stdout.write(`[${t.year || '?'}] ${title} ... `);
    try {
      const r = await fetchOne(ctx, t.url, outDir, title);
      console.log(`OK  图${r.imgCount} 公式${Math.round(r.mathCount)} 清跳转${r.n1 + r.n2 + (r.n3 || 0)} (${r.len}字符)`);
      ok++;
    } catch (e) {
      console.log(`FAIL  ${e.message}`);
      fail++;
    }
    await new Promise(r => setTimeout(r, 1500));   // 礼貌间隔
  }

  await browser.close();
  console.log(`\n完成: 成功 ${ok} / 失败 ${fail} / 共 ${targets.length}`);
}

const BASE_OUT = process.env.ZHIHU_OUT || 'D:\\Graduate school entrance exam\\jx_repo\\408\\真题解析';
main().catch(e => { console.error(e); process.exit(1); });
