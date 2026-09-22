/**
 * 全库体检（UTF-8 输出，避免控制台编码干扰）
 * 用法: node health_check2.js > result.txt
 */
const fs = require('fs');
const path = require('path');

const ROOT = 'D:\\Graduate school entrance exam\\jx_repo\\408\\真题解析';
const LOG = [];

function log(s) { LOG.push(s); }

function listMd() {
  const out = [];
  for (const d of fs.readdirSync(ROOT)) {
    const p = path.join(ROOT, d);
    if (!fs.statSync(p).isDirectory() || d.startsWith('_')) continue;
    for (const f of fs.readdirSync(p)) if (f.endsWith('.md')) out.push(path.join(p, f));
  }
  return out.sort();
}

const files = listMd();
const hits = {};
const KINDS = ['HTML实体未解码','占位符残留','裸HTML标签','块公式尾反斜杠','ZWJ零宽字符',
  '行内公式首位空格','行内公式尾空格','同行未闭合$','data/class属性残留','description残留',
  '单选题说明句','空markdown表','连续3+空行','图片空路径','知乎跳转'];
KINDS.forEach(k => hits[k] = []);

function rec(kind, f, ln, text) {
  hits[kind].push(`${path.basename(path.dirname(f))}\\${path.basename(f)}:${ln}  ${text.replace(/\n/g,' ').slice(0,120)}`);
}

for (const f of files) {
  const raw = fs.readFileSync(f, 'utf-8');
  const lines = raw.split('\n');
  lines.forEach((L, i) => {
    const ln = i + 1;
    if (/&(amp|lt|gt|quot|nbsp|#\d+);/.test(L)) rec('HTML实体未解码', f, ln, L.trim());
    if (/ZZ(?:MATH[BI]|IMGPZ)\d*ZZ/.test(L)) rec('占位符残留', f, ln, L.trim());
    if (/<\/?(p|div|span|a|font|strong|em|table|tr|td|th|img|figure)\b[^>]*>/.test(L)) rec('裸HTML标签', f, ln, L.trim());
    if (/\u200c|\u200d/.test(L)) rec('ZWJ零宽字符', f, ln, L.trim());
    if (/\bdata-(pid|tex|eeimg|original)="|class="[^"]*ztext/.test(L)) rec('data/class属性残留', f, ln, L.trim());
    if (/https:\/\/(zhida|link)\.zhihu\.com/.test(L)) rec('知乎跳转', f, ln, L.trim());
    if (/^\|[\s|]*\|\s*$/.test(L)) rec('空markdown表', f, ln, L.trim());
    if (/!\[\]\(\s*\)/.test(L)) rec('图片空路径', f, ln, L.trim());
    if (/^\s*description\s*:/.test(L)) rec('description残留', f, ln, L.trim());
    if (/第\s*\d+\s*~\s*40\s*小题/.test(L)) rec('单选题说明句', f, ln, L.trim());

    const stripped = L.replace(/\$\$/g, '');
    if ((stripped.match(/(?<!\\)\$/g) || []).length % 2 !== 0) rec('同行未闭合$', f, ln, L.trim());

    for (const m of L.matchAll(/\$([^$\n]+)\$/g)) {
      const body = m[1];
      if (/^\s/.test(body)) rec('行内公式首位空格', f, ln, m[0]);
      if (/\s$/.test(body)) rec('行内公式尾空格', f, ln, m[0]);
    }
  });

  // 块公式尾反斜杠（排除矩阵/对齐环境）
  let pos = 0;
  for (const m of raw.matchAll(/\$\$([\s\S]*?)\$\$/g)) {
    pos = raw.indexOf(m[0], pos);
    const inner = m[1];
    if (/\\\\\s*$/.test(inner) &&
        !/\\begin\{(aligned|array|cases|matrix|align|gather|split|bmatrix|pmatrix|vmatrix)\}/.test(inner)) {
      const ln = raw.slice(0, pos).split('\n').length;
      rec('块公式尾反斜杠', f, ln, m[0]);
    }
    pos += 1;
  }

  // 连续 3+ 空行
  for (let i = 2; i < lines.length; i++) {
    if (lines[i] === '' && lines[i-1] === '' && lines[i-2] === '') rec('连续3+空行', f, i+1, `(行 ${i+1})`);
  }
}

log(`扫描文件: ${files.length} 篇`);
let total = 0;
for (const k of KINDS) {
  const v = hits[k];
  total += v.length;
  log(`${v.length === 0 ? 'OK ' : '!! '} ${k}: ${v.length}`);
  for (const h of v.slice(0, 50)) log(`      ${h}`);
  if (v.length > 50) log(`      ...共 ${v.length} 处`);
}
log(`\n合计命中: ${total}`);

fs.writeFileSync('D:\\Graduate school entrance exam\\jx_repo\\408\\真题解析\\_tools\\hc_result.txt',
  '\ufeff' + LOG.join('\n'), 'utf-8');
console.log('done, hits=' + total);
