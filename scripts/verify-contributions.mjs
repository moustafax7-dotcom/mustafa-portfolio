// Compares the calendar served by YOUR function with the public contribution graph on github.com.
//   node scripts/verify-contributions.mjs https://mustafa-portfolio-lyart.vercel.app [username]
//   node scripts/verify-contributions.mjs http://localhost:3000            (with `vercel dev`)
// Exit code 0 = identical totals and identical per-day counts/levels.
const base = (process.argv[2] || '').replace(/\/$/, '');
const user = process.argv[3] || 'moustafax7-dotcom';
if (!base) {
  console.error('Usage: node scripts/verify-contributions.mjs <site-base-url> [username]');
  process.exit(2);
}

const decode = (s) => s.replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"');

// 1) what the function returns
const apiRes = await fetch(`${base}/api/github-contributions`);
if (!apiRes.ok) {
  console.error(`Function responded ${apiRes.status}:`, await apiRes.text());
  process.exit(1);
}
const api = await apiRes.json();
const apiDays = new Map(api.weeks.flat().map(([date, count, level]) => [date, { count, level }]));

// 2) what github.com shows publicly
const html = await (await fetch(`https://github.com/users/${user}/contributions`)).text();
const headerTotal = Number((html.match(/([\d,]+)\s+contributions?\s+in\s+(?:the\s+last\s+year|\d{4})/) || [])[1]?.replace(/,/g, ''));
const cells = new Map();
for (const td of html.match(/<td[^>]*data-date="[^"]+"[^>]*>/g) || []) {
  const id = td.match(/\bid="([^"]+)"/)?.[1];
  cells.set(id, { date: td.match(/data-date="([^"]+)"/)[1], level: Number(td.match(/data-level="(\d)"/)[1]) });
}
const profileDays = new Map();
for (const [id, { date, level }] of cells) {
  const tip = html.match(new RegExp(`<tool-tip[^>]*for="${id}"[^>]*>([^<]+)</tool-tip>`));
  const m = tip && decode(tip[1]).match(/^(\d+) contributions?/);
  profileDays.set(date, { count: m ? Number(m[1]) : 0, level });
}

// 3) compare
const diffs = [];
for (const [date, p] of profileDays) {
  const a = apiDays.get(date);
  if (!a) diffs.push(`${date}: missing in function output`);
  else if (a.count !== p.count || a.level !== p.level) diffs.push(`${date}: function ${a.count}/L${a.level} vs profile ${p.count}/L${p.level}`);
}
const profileSum = [...profileDays.values()].reduce((s, d) => s + d.count, 0);
console.log(`Function total : ${api.total}   (days: ${apiDays.size}, range ${api.from} → ${api.to})`);
console.log(`Profile header : ${headerTotal}   (sum of ${profileDays.size} public cells: ${profileSum})`);
console.log(diffs.length ? `\n${diffs.length} differing day(s):\n  ${diffs.slice(0, 15).join('\n  ')}` : '\nEvery day matches (count and intensity level).');
if (api.total !== headerTotal) console.log('\nTotals differ. Possible reasons: private-contribution visibility (profile setting vs token), a different date window, or a contribution made between the two requests.');
process.exit(diffs.length || api.total !== headerTotal ? 1 : 0);
