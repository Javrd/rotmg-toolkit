/* Browser tests for the Fame Checklist tab (and its character panel).
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
import { createServer } from 'http';
import { readFile } from 'fs/promises';
import path from 'path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/* Served over HTTP, not file://: the page fetch()es data/*.json, which
   Chromium refuses for file:// pages, and a canvas drawn from a file://
   image is tainted, so the outfit checks could not read its pixels. */
const TYPES = { '.html': 'text/html', '.json': 'application/json', '.png': 'image/png' };
const server = createServer(async (req, res) => {
  const file = path.join(root, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!file.startsWith(root)) { res.writeHead(403).end(); return; }
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' }).end(body);
  } catch { res.writeHead(404).end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const PAGE = `http://127.0.0.1:${server.address().port}/index.html`;

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
// Every confirm() is accepted unless a test sets dismissNext for the next one.
let dismissNext = false;
page.on('dialog', d => {
  if (dismissNext) { dismissNext = false; return d.dismiss(); }
  return d.accept();
});

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

section('characters');
const tiles = () => page.locator('.char');
const charNames = () => page.locator('.char-name').allTextContents();
const addChar = async cls => {
  await page.click('.char-add');
  await page.click(`.class-opt[data-cls="${cls}"]`);
  await page.click('.char-dialog-close');
};
const listCols = () => page.locator('#charList').evaluate(el =>
  getComputedStyle(el).gridTemplateColumns.split(' ').length);
await page.setViewportSize({ width: 1280, height: 800 });
await openFame();
await page.locator('.fame-item[data-dungeon="Snake Pit"] .fame-check').first().check();
check('no characters yet: only the + tile', await tiles().count() === 0
  && await page.locator('.char-add').isVisible());
check('a hint explains what it is for', await page.locator('#charHint').isVisible());
await page.click('.char-add');
check('+ opens the class picker', await page.locator('#charDialog').isVisible());
check('it offers all 19 classes, with portraits',
  await page.locator('.class-opt').count() === 19
  && await page.locator('.class-opt img[src^="https://www.realmeye.com/"]').count() === 19);
await page.keyboard.press('Escape');
check('Escape before picking a class adds nothing', !(await page.locator('#charDialog').isVisible())
  && await tiles().count() === 0);
await page.click('.char-add');
await page.mouse.click(5, 5);
check('a click on the backdrop closes it too', !(await page.locator('#charDialog').isVisible()));
await page.click('.char-add');
await page.click('.class-opt[data-cls="Wizard"]');
check('picking a class adds it straight away', await tiles().count() === 1);
check('and moves on to its look, with no Save button', await page.locator('#outfitStep').isVisible()
  && !(await page.locator('#classGrid').isVisible())
  && await page.locator('#charDialog button', { hasText: /^(Save|Create)$/ }).count() === 0);
await page.click('.char-dialog-close');
check('closing the look keeps the character', !(await page.locator('#charDialog').isVisible())
  && await tiles().count() === 1);
check('named after its class', JSON.stringify(await charNames()) === '["Wizard"]');
check('and selected', await page.locator('.char.active .char-name').textContent() === 'Wizard');
check('the first character takes over the ticks made before', await ticked() === '1'
  && await page.locator('.fame-item[data-dungeon="Snake Pit"] .fame-check').first().isChecked());
check('those loose ticks leave storage',
  await page.evaluate(() => localStorage.getItem('rotmg-toolkit:fame-dungeons')) === null);
check('hint gone once there is a character', !(await page.locator('#charHint').isVisible()));

await addChar('Wizard');
check('a second one of the same class is numbered',
  JSON.stringify(await charNames()) === '["Wizard","Wizard 2"]', JSON.stringify(await charNames()));
check('the new character is selected, with an empty checklist',
  await page.locator('.char.active .char-name').textContent() === 'Wizard 2' && await ticked() === '0');
const fs = page.locator('.fame-collection[data-collection="First Steps"] .fame-check');
for (let i = 0; i < await fs.count(); i++) await fs.nth(i).check();
check('ticks go to the selected character', await ticked() === '5');
check('its tile shows its progress',
  await page.locator('.char.active .char-meta').textContent() === '1/13 · 100 fame',
  await page.locator('.char.active .char-meta').textContent());
await page.locator('.char-pick').first().click();
check('switching back shows the other checklist', await ticked() === '1'
  && await page.locator('.fame-item[data-dungeon="Snake Pit"] .fame-check').first().isChecked()
  && !(await page.locator('.fame-collection[data-collection="First Steps"]')
    .evaluate(el => el.classList.contains('done'))));
check('each tile keeps its own numbers',
  JSON.stringify(await page.locator('.char-meta').allTextContents()) === '["0/13 · 0 fame","1/13 · 100 fame"]',
  JSON.stringify(await page.locator('.char-meta').allTextContents()));

await openFame();
check('characters survive a reload', JSON.stringify(await charNames()) === '["Wizard","Wizard 2"]');
check('and so does the selection and its ticks',
  await page.locator('.char.active .char-name').textContent() === 'Wizard' && await ticked() === '1');
await page.click('.pagetab[data-page="potions"]');
check('the panel only shows on the Fame Checklist', !(await page.locator('.char-panel').isVisible()));
await page.click('.pagetab[data-page="fame"]');

section('character look');
// Ids straight from data/outfits.json, which keeps RealmEye's own.
const ref = await page.evaluate(async () => {
  const o = await (await fetch('data/outfits.json')).json();
  const by = n => o.dyes.find(d => d.name === n).code;
  return { skins: o.classes.Wizard.skins.length, slime: o.classes.Wizard.skins.find(s => s[1] === 'Slime Wizard')[0],
           alice: by('Alice Blue'), lace: by('Blue Lace Cloth'), dyes: o.dyes.length };
});
const pixels = sel => page.locator(sel).evaluate(c =>
  c.getContext('2d').getImageData(0, 0, c.width, c.height).data.filter((v, i) => i % 4 === 3 && v).length);
const sprite = sel => page.locator(sel).evaluate(c => c.toDataURL());
await page.waitForSelector('.char canvas.char-icon');
check('tiles draw the character sprite', await pixels('.char:nth-child(1) canvas.char-icon') > 200);
check('an untouched character is the Classic skin, undyed',
  await page.evaluate(() => JSON.parse(localStorage.getItem('rotmg-toolkit:fame-characters')).list
    .every(c => c.skin === 0 && c.dye1 === 0 && c.dye2 === 0)));
const classic = await sprite('.char:nth-child(1) canvas.char-icon');
await page.locator('.char-edit').nth(1).click();
check('✎ opens the look of that character', await page.locator('#outfitStep').isVisible()
  && await page.locator('#charDialogTitle').textContent() === 'Wizard 2'
  && !(await page.locator('#classGrid').isVisible()));
check('every skin of the class is offered', await page.locator('.outfit-opt').count() === ref.skins,
  await page.locator('.outfit-opt').count() + ' vs ' + ref.skins);
await page.fill('#outfitSearch', 'slime');
check('the search narrows the skins',
  await page.locator('.outfit-opt:visible').count() === 1, await page.locator('.outfit-opt:visible').count());
await page.locator('.outfit-opt:visible').click();
check('picking one updates the summary', await page.locator('#outfitSkinName').textContent() === 'Slime Wizard');
const wiz2 = () => page.evaluate(() => JSON.parse(localStorage.getItem('rotmg-toolkit:fame-characters')).list
  .find(c => c.cls === 'Wizard' && c.n === 2));
check('and is saved at once', (await wiz2()).skin === ref.slime);
check('the tile behind updates too', await sprite('.char:nth-child(2) canvas.char-icon') !== classic);
await page.click('.outfit-tab[data-slot="dye1"]');
check('the dye tab lists every dye plus None',
  await page.locator('.outfit-opt').count() === ref.dyes + 1, await page.locator('.outfit-opt').count());
check('search box was cleared on the way', await page.inputValue('#outfitSearch') === '');
await page.locator('.outfit-opt[title="Alice Blue"]').click();
await page.click('.outfit-tab[data-slot="dye2"]');
await page.locator('.outfit-opt[title="Blue Lace Cloth"]').click();
check('the preview is drawn', await pixels('#outfitPreview') > 200);
check('both dyes named in the summary',
  await page.locator('#outfitDye1Name').textContent() === 'Alice Blue'
  && await page.locator('#outfitDye2Name').textContent() === 'Blue Lace Cloth');
await page.keyboard.press('Escape');
const saved = await wiz2();
check('RealmEye ids are stored', saved.skin === ref.slime && saved.dye1 === ref.alice && saved.dye2 === ref.lace,
  JSON.stringify(saved) + ' vs ' + JSON.stringify(ref));
check('its ticks are untouched', saved.done.length === 5);
check('editing a look does not change which character is selected',
  await page.locator('.char.active .char-name').textContent() === 'Wizard' && await ticked() === '1');
await page.locator('.char-edit').nth(1).click();
await page.click('.outfit-tab[data-slot="dye1"]');
await page.fill('#outfitSearch', 'heart cloth');
const hearts = await page.locator('.outfit-opt:visible').evaluateAll(els => els.map(e => e.title));
check('an animated cloth is offered next to its still twin',
  hearts.includes('Heart Cloth') && hearts.includes('Running Heart Cloth (animated in game, shown still)'),
  JSON.stringify(hearts));
check('and is marked as animated', await page.locator('.outfit-opt.animated[title^="Running Heart"]')
  .evaluate(el => getComputedStyle(el, '::after').content.includes('▶')));
await page.locator('.outfit-opt[title^="Running Heart"]').click();
check('the summary names the animated one', await page.locator('#outfitDye1Name').textContent()
  === 'Running Heart Cloth (animated)');
const heartRef = await page.evaluate(async () => (await (await fetch('data/outfits.json')).json())
  .dyes.filter(d => d.name === 'Heart Cloth' || d.name === 'Running Heart Cloth'));
check('the twins share a code but not an item id', heartRef.length === 2
  && heartRef[0].code === heartRef[1].code && heartRef[0].items[0] !== heartRef[1].items[0]);
const running = heartRef.find(d => d.name === 'Running Heart Cloth');
check('so the item id is what is stored', (await wiz2()).dye1 === running.code
  && (await wiz2()).dye1Item === running.items[0]);
await page.keyboard.press('Escape');
await page.locator('.char-edit').nth(1).click();
check('and reopening still shows Running Heart, not Heart',
  await page.locator('#outfitDye1Name').textContent() === 'Running Heart Cloth (animated)');
await page.click('.outfit-tab[data-slot="dye1"]');
await page.locator('.outfit-opt[title="Alice Blue"]').click();
await page.click('.outfit-tab[data-slot="dye2"]');
check('a tab opens scrolled to the picked option', await page.locator('.outfit-opt[aria-selected="true"]')
  .evaluate(el => { const r = el.getBoundingClientRect(), g = el.parentElement.getBoundingClientRect();
    return el.title === 'Blue Lace Cloth' && el.parentElement.scrollTop > 0 && r.top >= g.top && r.bottom <= g.bottom; }));
await page.keyboard.press('Escape');
check('the look tabs leave the potion page’s tabs alone', await page.evaluate(() =>
  document.querySelectorAll('#page-potions .view.active').length === 1
  && document.querySelectorAll('.tabs .tab.active').length === 1));
await openFame();
await page.waitForSelector('.char canvas.char-icon');
check('the look survives a reload', await sprite('.char:nth-child(2) canvas.char-icon') !== classic
  && (await wiz2()).skin === ref.slime);

section('character panel layout');
check('a few characters fit in one column', await listCols() === 1);
const panelFits = () => page.locator('.char-panel').evaluate(el =>
  el.getBoundingClientRect().bottom <= window.innerHeight + 1);
while (await tiles().count() < 14) await addChar('Rogue');
check('a full column spills into a second one', await listCols() === 2, await listCols());
check('without scrolling yet', await page.locator('#charList').evaluate(el => el.scrollHeight <= el.clientHeight + 1));
while (await tiles().count() < 30) await addChar('Priest');
check('then the list scrolls by itself', await page.locator('#charList').evaluate(el => el.scrollHeight > el.clientHeight + 1));
check('still in two columns', await listCols() === 2);
check('a new character scrolls into view', await page.locator('.char.active').evaluate(el => {
  const r = el.getBoundingClientRect(), l = el.parentElement.getBoundingClientRect();
  return r.top >= l.top - 1 && r.bottom <= l.bottom + 1; }));
await page.evaluate(() => window.scrollTo(0, 3000));
check('scrolled down, the panel sticks and fits the window', await panelFits()
  && await page.locator('.char-panel').evaluate(el =>
    el.getBoundingClientRect().top >= document.querySelector('header').getBoundingClientRect().bottom));
await page.evaluate(() => window.scrollTo(0, 0));
await openFame();
check('two columns again after a reload', await listCols() === 2);

section('deleting characters');
await page.locator('.char-pick').first().click();
dismissNext = true;
await page.locator('.char-del').first().click();
check('cancelling the confirmation keeps it', await tiles().count() === 30);
await page.locator('.char-del').first().click();
check('confirming deletes it', await tiles().count() === 29
  && (await charNames())[0] === 'Wizard 2');
check('the next character becomes the selected one',
  await page.locator('.char.active .char-name').textContent() === 'Wizard 2' && await ticked() === '5');
await addChar('Wizard');
check('a freed number is reused', (await charNames()).at(-1) === 'Wizard');
while (await tiles().count() > 6) await page.locator('.char-del').last().click();
check('back to one column when they fit', await listCols() === 1, await listCols());
while (await tiles().count()) await page.locator('.char-del').first().click();
check('deleting the last one leaves no character and an empty checklist',
  await ticked() === '0' && await page.locator('#charHint').isVisible());

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
await page.keyboard.press('Escape');
await page.keyboard.press('Escape');
for (const cls of ['Knight', 'Archer', 'Trickster', 'Druid', 'Assassin']) await addChar(cls);
check('the panel sits above the checklist', await page.locator('.char-panel').evaluate(el =>
  el.getBoundingClientRect().bottom <= document.querySelector('.fame-picker').getBoundingClientRect().top));
check('its tiles scroll sideways inside it', await page.locator('#charList').evaluate(el =>
  el.scrollWidth > el.clientWidth));
check('without widening the page',
  await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
await page.click('.char-add');
check('the class picker fits the screen', await page.locator('#charDialog').evaluate(el => {
  const r = el.getBoundingClientRect(); return r.left >= 0 && r.right <= window.innerWidth; }));
await page.keyboard.press('Escape');

await browser.close();
server.close();
console.log(failures ? `\n${failures} FAILURE(S)` : '\nALL PASS');
process.exit(failures ? 1 : 0);
