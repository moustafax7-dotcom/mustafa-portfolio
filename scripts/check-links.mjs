// Run locally (Node 18+):  node scripts/check-links.mjs
// Checks every external link in index.html and reports its HTTP status.
// The audit sandbox could not reach vercel.app / github.io, so live demos were NOT verified there.
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const urls = [...new Set([...html.matchAll(/href="(https?:\/\/[^"]+)"/g)].map((m) => m[1]))]
  .filter((u) => !u.includes('wa.me') && !u.includes('linkedin.com') && !u.startsWith('https://mustafa-portfolio-lyart')); // these block bots

let bad = 0;
for (const url of urls) {
  try {
    const res = await fetch(url, { method: 'GET', redirect: 'follow', signal: AbortSignal.timeout(15000) });
    const ok = res.status >= 200 && res.status < 400;
    if (!ok) bad++;
    console.log(`${ok ? 'OK  ' : 'FAIL'} ${res.status}  ${url}`);
  } catch (e) {
    bad++;
    console.log(`FAIL ERR  ${url}  (${e.cause?.code || e.message})`);
  }
}
console.log(bad ? `\n${bad} link(s) need attention` : '\nAll checked links respond');
process.exit(bad ? 1 : 0);
