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

A dye code is what RealmEye's data-dye1/data-dye2 carry: 0x01RRGGBB is a plain
colour, anything else names a cloth texture at sheetOffsets[code][:4]. The
skin id is data-skin. Keeping those exact ids lets a later RealmEye sync
(TASK-008) import a character's look as-is. See docs/decisions/0012.

Writes data/outfits.json and data/outfits.png (the sheet, decoded).
"""
import base64
import colorsys
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


def parse_dyes(sheet_js, definition_js):
    offsets = json.loads(js_object_to_json(SHEET_OFFSETS_RE.search(sheet_js).group(1)))
    names = {int(i): n for i, n in ITEM_NAME_RE.findall(definition_js)}
    colours, cloths = [], []
    for code_s, entry in offsets.items():
        code = int(code_s)
        item_ids = entry[4:]
        name = next((dye_name(names[i]) for i in item_ids if i in names), None)
        if not name:
            continue
        if code >> 24 == PLAIN_DYE:
            colours.append({"code": code, "name": name})
        else:
            cloths.append({"code": code, "name": name, "tex": entry[:4]})
    colours.sort(key=lambda d: hue_key(d["code"]))
    cloths.sort(key=lambda d: d["name"])
    return colours + cloths


def run(out_json, out_png):
    urls = script_urls()
    classinfo, sheet, definition = (fetch(urls[k]) for k in ("classinfo", "sheet", "definition"))
    png = base64.b64decode(SHEET_SRC_RE.search(sheet).group(1))
    outfits = {"classes": parse_classes(classinfo), "dyes": parse_dyes(sheet, definition)}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(outfits, f, ensure_ascii=False, separators=(",", ":"))
    with open(out_png, "wb") as f:
        f.write(png)
    n_skins = sum(len(c["skins"]) for c in outfits["classes"].values())
    n_cloth = sum(1 for d in outfits["dyes"] if "tex" in d)
    print(f"Saved {len(outfits['classes'])} classes with {n_skins} skins and "
          f"{len(outfits['dyes'])} dyes ({n_cloth} cloths) to {out_json}; "
          f"sheet {len(png) // 1024} KB to {out_png}", file=sys.stderr)
    return outfits


if __name__ == "__main__":
    out_json = sys.argv[1] if len(sys.argv) > 1 else "data/outfits.json"
    out_png = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(out_json)[0] + ".png"
    run(out_json, out_png)
