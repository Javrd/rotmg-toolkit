/* Browser tests for the Fame Checklist tab.
 *
 * These run in a real Chromium because the bug they exist to prevent is a CSS
 * cascade bug: an author rule like `.fame-result { display:flex }` outranks the
 * UA stylesheet's `[hidden] { display:none }`, so `el.hidden = true` silently
 * does nothing. jsdom does not model that cascade -- it reported the filtered
 * rows as `display:none` while the real page showed all 65. Assert on what the
 * user can see (`:visible`), never on the attribute. See docs/decisions/0010.
 *
 *   npm install
 *   npx playwright install chromium     # ~110 MB, once
 *   npm test
 *
 * On this NUC there is no sudo for Chromium's system libs, so they are unpacked
 * locally and pointed at with env vars -- see docs/decisions/0010.
 */
import { chromium } from 'playwright-core';
import { fileURLToPath } from 'url';
import path from 'path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PAGE = 'file://' + path.join(root, 'index.html');

let failures = 0;
const check = (name, cond, extra = '') => {
  console.log((cond ? '  PASS ' : '  FAIL ') + name + (cond ? '' : '  <- ' + extra));
  if (!cond) failures++;
};
const section = name => console.log('\n== ' + name + ' ==');

const browser = await chromium.launch({
  executablePath: process.env.PW_EXE || undefined,
  args: ['--no-sandbox'],
});
const ctx = await browser.newContext();
const page = await ctx.newPage();
page.on('dialog', d => d.accept());

const openFame = async () => {
  await page.goto(PAGE);
  await page.click('.pagetab[data-page="fame"]');
};
const visibleRows = () => page.locator('.fame-result:visible');
const ticked = () => page.locator('#fameDone').textContent();

await openFame();

section('structure');
check('13 collection sections', await page.locator('.fame-collection').count() === 13);
check('fame page is shown', await page.locator('#page-fame').isVisible());
check('picker is closed until focused', !(await page.locator('#fameResults').isVisible()));

section('difficulty order');
// [{collection, difficulties:[...]}] in page order; unrated dungeons count as 0.
const order = await page.locator('.fame-collection').evaluateAll(secs => secs.map(sec => ({
  collection: sec.dataset.collection,
  difficulties: Array.from(sec.querySelectorAll('.fame-item')).map(it => {
    const t = it.querySelector('.difficulty')?.title;
    return t ? parseFloat(t.replace('Difficulty: ', '')) : 0;
  }),
})));
check('every dungeon but the seasonal three shows a rating',
  order.flatMap(o => o.difficulties).filter(d => d === 0).length === 3);
check('dungeons go easiest to hardest inside each collection, unrated first',
  order.every(o => o.difficulties.every((d, i, a) => i === 0 || a[i - 1] <= d)));
// Hardest first, then second hardest, ...; a collection out of dungeons counts 0.
const desc = order.map(o => [...o.difficulties].sort((a, b) => b - a));
const cmpDesc = (a, b) => {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] || 0) - (b[i] || 0);
    if (d) return d;
  }
  return 0;
};
check('collections compare hardest dungeon, then next hardest, and so on',
  desc.every((k, i) => i === 0 || cmpDesc(desc[i - 1], k) <= 0),
  order.map(o => o.collection).join(' > '));
check('First Steps comes first', order[0].collection === 'First Steps');

section('icons');
check('no dungeon falls back to the grey placeholder',
  await page.locator('.fame-icon[src^="data:"]').count() === 0,
  await page.locator('.fame-icon[src^="data:"]').count() + ' placeholder(s)');
check('every icon points at realmeye',
  (await page.locator('.fame-icon').evaluateAll(
    els => els.filter(e => !e.getAttribute('src').startsWith('https://www.realmeye.com/')).length)) === 0);

section('picker opens with every dungeon, A-Z');
await page.click('#fameSearch');
check('dropdown visible', await page.locator('#fameResults').isVisible());
const names = await page.locator('.fame-result:visible .fame-name').allTextContents();
check('65 rows visible', names.length === 65, names.length);
check('alphabetical',
  JSON.stringify(names) === JSON.stringify([...names].sort((a, b) => a.localeCompare(b, 'en'))),
  names.slice(0, 3).join(' | '));

section('typing filters the list');
await page.fill('#fameSearch', 'snake');
check('only Snake Pit visible',
  JSON.stringify(await visibleRows().locator('.fame-name').allTextContents()) === '["Snake Pit"]',
  JSON.stringify(await visibleRows().locator('.fame-name').allTextContents()));
await page.fill('#fameSearch', 'the ');
const many = await visibleRows().count();
check('partial word matches several', many > 3 && many < 65, many);
await page.fill('#fameSearch', "oryx's");
check('straight apostrophe matches the wiki’s typographic one',
  await visibleRows().count() === 3, await visibleRows().count());
await page.fill('#fameSearch', 'zzzz');
check('no rows when nothing matches', await visibleRows().count() === 0);
check('empty state is shown', await page.locator('.fame-empty').isVisible());
await page.fill('#fameSearch', '');
check('clearing the box restores all 65', await visibleRows().count() === 65);

section('ticking from the picker');
await page.fill('#fameSearch', 'snake');
await visibleRows().first().locator('.fame-result-check').check();
check('row shows as checked', await page.locator('.fame-result[data-dungeon="Snake Pit"]')
  .evaluate(el => el.classList.contains('checked')));
check('dropdown stays open', await page.locator('#fameResults').isVisible());
check('summary counts it', await ticked() === '1', await ticked());
check('sections updated', await page.locator('.fame-item[data-dungeon="Snake Pit"] .fame-check')
  .first().isChecked());

section('cross-section sync');
await page.keyboard.press('Escape');
await page.keyboard.press('Escape');
await page.locator('.fame-item[data-dungeon="Pirate Cave"] .fame-check').first().check();
const pc = page.locator('.fame-item[data-dungeon="Pirate Cave"] .fame-check');
check('Pirate Cave is in 4 collections', await pc.count() === 4, await pc.count());
let allOn = true;
for (let i = 0; i < await pc.count(); i++) if (!(await pc.nth(i).isChecked())) allOn = false;
check('ticked in all 4', allOn);
await page.click('#fameSearch');
check('picker reflects a section tick',
  await page.locator('.fame-result[data-dungeon="Pirate Cave"] .fame-result-check').isChecked());

section('collection completion');
await page.keyboard.press('Escape');
await page.keyboard.press('Escape');
const first = page.locator('.fame-collection[data-collection="First Steps"]');
const boxes = first.locator('.fame-check');
for (let i = 0; i < await boxes.count(); i++) await boxes.nth(i).check();
check('marked done', await first.evaluate(el => el.classList.contains('done')));
check('count reads 5/5', (await first.locator('.fame-count').textContent()) === '5/5');
check('bar is full',
  (await first.locator('.fame-bar-fill').evaluate(el => el.style.width)) === '100%');
check('summary: 1 collection', (await page.locator('#fameCollections').textContent()) === '1');
check('summary: 100 fame', (await page.locator('#fameFame').textContent()) === '100');
const firstItems = first.locator('.fame-item:visible');
check('a completed collection folds away', await firstItems.count() === 0, await firstItems.count());
check('its header stays visible', await first.locator('.fame-count').isVisible());
check('aria-expanded follows the fold',
  (await first.locator('.fame-head').getAttribute('aria-expanded')) === 'false');
await first.locator('.fame-title').click();
check('clicking the header unfolds it', await firstItems.count() === 5, await firstItems.count());
await page.locator('.fame-item[data-dungeon="Snake Pit"] .fame-check').last().uncheck();
await page.locator('.fame-item[data-dungeon="Snake Pit"] .fame-check').last().check();
check('ticks elsewhere leave a hand-opened collection open', await firstItems.count() === 5);
await first.locator('.fame-count').click();
check('clicking the header again folds it', await firstItems.count() === 0);
await first.locator('.fame-head').focus();
await page.keyboard.press('Enter');
check('Enter on the header unfolds it', await firstItems.count() === 5);
await first.locator('.fame-check').first().uncheck();
check('unticking keeps it open', await firstItems.count() === 5);
await first.locator('.fame-head').click();
check('an incomplete collection can be folded too', await firstItems.count() === 0);
await first.locator('.fame-head').click();
await first.locator('.fame-check').first().check();
check('open collections are expanded by default',
  await page.locator('.fame-collection:not(.done) .fame-item:visible').count() > 0
  && await page.locator('.fame-collection:not(.done).collapsed').count() === 0);

section('persistence across a reload');
await openFame();
check('ticks restored', await ticked() === '6', await ticked());
check('First Steps still done',
  await page.locator('.fame-collection[data-collection="First Steps"]')
    .evaluate(el => el.classList.contains('done')));
check('and starts folded',
  await page.locator('.fame-collection[data-collection="First Steps"] .fame-item:visible').count() === 0);

section('closing the picker');
await page.click('#fameSearch');
await page.fill('#fameSearch', 'snake');
await page.keyboard.press('Escape');
check('first Escape clears the query', (await page.inputValue('#fameSearch')) === '');
check('and keeps it open', await page.locator('#fameResults').isVisible());
await page.keyboard.press('Escape');
check('second Escape closes it', !(await page.locator('#fameResults').isVisible()));
await page.click('#fameSearch');
await page.click('h1');
check('a click outside closes it', !(await page.locator('#fameResults').isVisible()));

section('clear all');
await page.click('#fameClear');
check('summary reset', await ticked() === '0', await ticked());
check('no section marked done', await page.locator('.fame-collection.done').count() === 0);
check('no section left folded', await page.locator('.fame-collection.collapsed').count() === 0);
check('no item checked', await page.locator('.fame-item .fame-check:checked').count() === 0);
await page.click('#fameSearch');
check('no picker row checked',
  await page.locator('.fame-result .fame-result-check:checked').count() === 0);

section('"dropped by" tooltips');
await page.click('h1');
const tip = page.locator('#dropsTip');
check('tooltip hidden until asked', !(await tip.isVisible()));
const chip = page.locator('.fame-item[data-dungeon="Pirate Cave"] .drops-from').first();
check('fame items carry a chip', await chip.count() === 1);
check('chip previews up to 3 sprites and a count',
  await chip.locator('img').count() === 3 && (await chip.locator('.drops-more').textContent()) === '+7',
  await chip.innerHTML());
await chip.hover();
check('hover shows the tooltip', await tip.isVisible());
check('tooltip names the dungeon', (await tip.locator('.drops-tip-title b').textContent()) === 'Pirate Cave');
check('one sprite per source monster', await tip.locator('.drops-src').count() === 10,
  await tip.locator('.drops-src').count());
check('guaranteed sources are marked', await tip.locator('.drops-src.g').count() === 2,
  await tip.locator('.drops-src.g').count());
check('sprites link to the monster page',
  (await tip.locator('.drops-src').first().getAttribute('href')) === 'https://www.realmeye.com/wiki/pirate');
check('tooltip stays inside the viewport',
  await tip.evaluate(el => { const r = el.getBoundingClientRect();
    return r.left >= 0 && r.right <= window.innerWidth && r.top >= 0 && r.bottom <= window.innerHeight; }));
await page.mouse.move(0, 0);
await page.waitForTimeout(300);
check('leaving the chip hides it again', !(await tip.isVisible()));
await chip.click();
check('a click pins it', await tip.isVisible());
check('and does not tick the checkbox',
  !(await page.locator('.fame-item[data-dungeon="Pirate Cave"] .fame-check').first().isChecked()));
await page.mouse.move(0, 0);
await page.waitForTimeout(300);
check('pinned tooltip survives the mouse leaving', await tip.isVisible());
await page.keyboard.press('Escape');
check('Escape closes it', !(await tip.isVisible()));
await page.locator('.fame-item[data-dungeon="Oryx’s Castle"] .drops-from').first().hover();
check('a dungeon with no monsters shows its note instead',
  await tip.locator('.drops-src').count() === 0 && (await tip.locator('.drops-note').textContent()).includes('Realm closes'));
await page.mouse.move(0, 0);
await page.click('#fameSearch');
await page.fill('#fameSearch', 'snake');
const pickerChip = visibleRows().first().locator('.drops-from');
check('picker rows carry a chip too', await pickerChip.count() === 1);
await pickerChip.hover();
check('and it opens the same tooltip', await tip.isVisible()
  && (await tip.locator('.drops-tip-title b').textContent()) === 'Snake Pit');
await page.keyboard.press('Escape');
await page.keyboard.press('Escape');
await page.keyboard.press('Escape');
await page.click('.pagetab[data-page="potions"]');
const cardChip = page.locator('.card[data-name="snake pit"] .drops-from');
check('potion cards carry a chip', await cardChip.count() === 1);
await cardChip.hover();
check('card chip opens the tooltip', await tip.isVisible()
  && (await tip.locator('.drops-tip-title b').textContent()) === 'Snake Pit');
await page.mouse.move(0, 0);
await page.waitForTimeout(300);

section('narrow viewport (400px)');
await page.setViewportSize({ width: 400, height: 800 });
await openFame();
check('no horizontal overflow',
  await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
  await page.evaluate(() => document.documentElement.scrollWidth + ' > ' + window.innerWidth));
await page.click('#fameSearch');
check('picker usable on mobile', await page.locator('#fameResults').isVisible());
check('dropdown fits the screen',
  await page.locator('#fameResults').evaluate(el => el.getBoundingClientRect().right <= window.innerWidth + 1));

await browser.close();
console.log(failures ? `\n${failures} FAILURE(S)` : '\nALL PASS');
process.exit(failures ? 1 : 0);
