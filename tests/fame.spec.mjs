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

section('persistence across a reload');
await openFame();
check('ticks restored', await ticked() === '6', await ticked());
check('First Steps still done',
  await page.locator('.fame-collection[data-collection="First Steps"]')
    .evaluate(el => el.classList.contains('done')));

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
check('no item checked', await page.locator('.fame-item .fame-check:checked').count() === 0);
await page.click('#fameSearch');
check('no picker row checked',
  await page.locator('.fame-result .fame-result-check:checked').count() === 0);

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
