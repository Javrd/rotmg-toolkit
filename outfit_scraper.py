#!/usr/bin/env python3
"""Scrape what the Fame Checklist needs to draw a character the way the game
does: every class's skins, every dye, and the sprite sheet both come from.

None of it is on the wiki. RealmEye draws the characters on its player pages
client-side from three scripts, and this reads the same three:

- classinfo.js:  window.classInfos = [[classId, name, plural, ..., skins], ...]
                 where skins = [[skinId, skinName, sheetIndex], ...].
- sheet.js:      sheetSrc = "data:image/png;base64,..." (one PNG holding every
                 skin and the dye cloth textures) and
                 sheetOffsets = {dyeCode: [w, h, x, y, clothingItemId, accessoryItemId]}.
- definition.js: items = {itemId: [name, ...], ...}; only the dye names are used.

Several dyes can share one code: an animated cloth and its still twin
(Running Heart / Heart) draw from the same texture, and Cyan/Magenta are
Aqua/Fuchsia under another name. So there is one entry per dye *name*, keyed
by its RealmEye item ids (data-clothing-dye-id / data-accessory-dye-id),
and the code only says how to paint it. Neither RealmEye nor the wiki has
the animation itself -- only one frame -- so animated cloths (the wiki's
/wiki/cloths "Animated" table) are flagged and drawn still.

A dye code is what RealmEye's data-dye1/data-dye2 carry: 0x01RRGGBB is a plain
colour, anything else names a cloth texture at sheetOffsets[code][:4]. The
skin id is data-skin. Keeping those exact ids lets a later RealmEye sync
(TASK-008) import a character's look as-is. See docs/decisions/0012.

Writes data/outfits.json and data/outfits.png (the sheet, decoded).
"""
import base64
import colorsys
import html as htmlmod
import json
import os
import re
import sys

from scraper import fetch, BASE

# Any page that draws characters links the three scripts; their path carries
# a version segment (/s/hu/js/...), so it is read from the page, not hardcoded.
SCRIPTS_PAGE = BASE + "/recent-deaths"
SCRIPT_RE = re.compile(r'src="(/s/[^"]+/js/(classinfo|sheet|definition)\.js)"')
SHEET_SRC_RE = re.compile(r'sheetSrc="data:image/png;base64,([^"]+)"')
SHEET_OFFSETS_RE = re.compile(r'sheetOffsets=(\{.*?\})', re.S)
ITEM_NAME_RE = re.compile(r'"?(-?\d+)"?:\["((?:[^"\\]|\\.)*)"')
CLOTHS_URL = BASE + "/wiki/cloths"
# Its <img> alts mislabel a few (Running Heart's is "Heart Cloth"); the
# caption cell next to each pair of images carries the in-game name.
CAPTION_RE = re.compile(r"<td>([^<]+)</td>")

PLAIN_DYE = 1  # code >> 24 of a plain-colour dye


def script_urls():
    urls = {kind: BASE + path for path, kind in SCRIPT_RE.findall(fetch(SCRIPTS_PAGE))}
    missing = {"classinfo", "sheet", "definition"} - urls.keys()
    if missing:
        raise RuntimeError(f"{SCRIPTS_PAGE} no longer links {', '.join(sorted(missing))}.js")
    return urls


def js_object_to_json(src):
    """classInfos/sheetOffsets are JS literals: bare numeric keys and numbers
    like .5 are valid JS but not JSON."""
    src = re.sub(r'([{,])(-?\d+):', r'\1"\2":', src)
    return re.sub(r'(?<=[\[,:\-])\.(\d)', r'0.\1', src)


def parse_classes(js):
    body = js[js.index("=") + 1:].strip().rstrip(";")
    classes = {}
    for info in json.loads(js_object_to_json(body)):
        skins = [[sid, name.strip(), idx] for sid, name, idx in info[6]]
        classes[info[1]] = {"id": info[0], "skins": skins}
    return classes


def dye_name(item_name):
    """'Alice Blue Clothing Dye' -> 'Alice Blue'; 'Large Blue Lace Cloth' -> 'Blue Lace Cloth'."""
    name = re.sub(r" (Clothing|Accessory) Dye$", "", item_name)
    return re.sub(r"^(Large|Small) ", "", name)


def hue_key(code):
    r, g, b = ((code >> 16) & 255) / 255, ((code >> 8) & 255) / 255, (code & 255) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    # Greys (no saturation) first, darkest to lightest; then round the wheel.
    return (0, l, 0) if s < 0.08 else (1, round(h * 24), l)


def animated_cloths():
    page = fetch(CLOTHS_URL)
    start = page.find(">Animated<")
    if start < 0:
        raise RuntimeError("no Animated table on " + CLOTHS_URL)
    end = page.find("<h", start + 20)
    return {htmlmod.unescape(c).strip() + " Cloth" for c in CAPTION_RE.findall(page[start:end])}


def parse_dyes(sheet_js, definition_js, animated):
    offsets = json.loads(js_object_to_json(SHEET_OFFSETS_RE.search(sheet_js).group(1)))
    names = {int(i): n for i, n in ITEM_NAME_RE.findall(definition_js)}
    colours, cloths = [], []
    for code_s, entry in offsets.items():
        code = int(code_s)
        by_name = {}   # dye name -> [clothing item id, accessory item id]
        for item_id in entry[4:]:
            if item_id not in names:
                continue
            slot = 1 if re.search(r"Accessory Dye$|^Small ", names[item_id]) else 0
            by_name.setdefault(dye_name(names[item_id]), [None, None])[slot] = item_id
        for name, items in by_name.items():
            dye = {"code": code, "name": name, "items": items}
            if code >> 24 == PLAIN_DYE:
                colours.append(dye)
            else:
                dye["tex"] = entry[:4]
                if name in animated:
                    dye["animated"] = True
                cloths.append(dye)
    colours.sort(key=lambda d: hue_key(d["code"]))
    cloths.sort(key=lambda d: d["name"])
    return colours + cloths


def run(out_json, out_png):
    urls = script_urls()
    classinfo, sheet, definition = (fetch(urls[k]) for k in ("classinfo", "sheet", "definition"))
    png = base64.b64decode(SHEET_SRC_RE.search(sheet).group(1))
    outfits = {"classes": parse_classes(classinfo),
               "dyes": parse_dyes(sheet, definition, animated_cloths())}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(outfits, f, ensure_ascii=False, separators=(",", ":"))
    with open(out_png, "wb") as f:
        f.write(png)
    n_skins = sum(len(c["skins"]) for c in outfits["classes"].values())
    n_cloth = sum(1 for d in outfits["dyes"] if "tex" in d)
    n_anim = sum(1 for d in outfits["dyes"] if d.get("animated"))
    print(f"Saved {len(outfits['classes'])} classes with {n_skins} skins and "
          f"{len(outfits['dyes'])} dyes ({n_cloth} cloths, {n_anim} animated) to {out_json}; "
          f"sheet {len(png) // 1024} KB to {out_png}", file=sys.stderr)
    return outfits


if __name__ == "__main__":
    out_json = sys.argv[1] if len(sys.argv) > 1 else "data/outfits.json"
    out_png = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(out_json)[0] + ".png"
    run(out_json, out_png)
