#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One sprite per stone count (0..10). Reuse existing art for the counts the
user already approved, generate the missing tiers 3,4,6,7,8 with a matching
rounded-boulder pile and progressively more exhausted expression."""
import base64, json, os, shutil, urllib.request, concurrent.futures, io
from PIL import Image

API = os.environ.get("IMAGE_API_URL", "")  # OpenAI-compatible /images/generations endpoint; set via env
KEY = os.environ.get("IMAGE_API_KEY", "")  # set via env / .env, never commit
PROJ = "/Users/tal/Desktop/海龟汤游戏/assets"
POOL = "/Users/tal/Desktop/资源管理"
CHROMA = ("solid pure magenta background color hex #FF00FF, the subject fully "
          "isolated with clean edges, no shadow on the background")
BASE = ("16-bit pixel art sprite of the SAME original plump brown furry chibi "
        "mole creature with a big round belly, small round ears, a little red "
        "bandana around the neck, both short arms raised straight up over the "
        "head holding boulders, standing facing forward, full body, centered, "
        "original mascot, retro SNES style, crisp pixels, grey rounded boulders "
        "in a neat pile balanced above the head, ")

# Map an existing approved sprite to a stone count -> hero{N}.png
REUSE = {
    0:  "character.png",   # 0 stones (character_v2)
    1:  "carry0.png",      # 1 stone
    2:  "carry1.png",      # 2 stones (carry1_v2)
    5:  "carry3.png",      # 5 stones
    9:  "carry2.png",      # 9 stones (carry2_v2)
    10: "crushed.png",     # 10 stones, final round
}

# Counts to generate, with count-specific strain wording
GEN = {
    3: (BASE + "exactly THREE boulders stacked overhead, weight becoming real, "
        "eyebrows pushed together, mouth tight with effort, one or two sweat "
        "drops, still holding steady, " + CHROMA),
    4: (BASE + "exactly FOUR boulders stacked overhead, clearly heavier now, "
        "brow furrowed hard, teeth beginning to show, several sweat drops, arms "
        "tensing, " + CHROMA),
    6: (BASE + "a pile of SIX boulders overhead, straining hard, gritted teeth "
        "grimace, eyes squinting, face flushing red, lots of sweat, arms "
        "trembling under the weight, " + CHROMA),
    7: (BASE + "a big pile of SEVEN boulders overhead, straining very hard, "
        "clenched teeth, eyes squeezed, face red and puffed, sweat flying, legs "
        "starting to bend under the load, " + CHROMA),
    8: (BASE + "a huge heavy pile of EIGHT boulders overhead nearly crushing "
        "the mole, exhausted desperate face, teeth gritted hard, eyes screwed "
        "shut, tongue starting to show, whole body shaking, knees buckling, "
        + CHROMA),
}

def keyed(raw):
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    px = img.load(); w, h = img.size
    for y in range(h):
        for x in range(w):
            r_, g_, b_, a_ = px[x, y]
            if r_ > 180 and g_ < 90 and b_ > 180:
                px[x, y] = (r_, g_, b_, 0)
    return img

def gen(n, prompt):
    body = json.dumps({"model": "gpt-image-2", "prompt": prompt}).encode()
    req = urllib.request.Request(API, data=body, method="POST",
        headers={"api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.load(r)
    raw = base64.b64decode(data["data"][0]["b64_json"])
    with open(os.path.join(POOL, f"海龟汤_hero{n}石_gpt-image-2.png"), "wb") as f:
        f.write(raw)
    keyed(raw).save(os.path.join(PROJ, f"hero{n}.png"))
    return n

if __name__ == "__main__":
    # 1) reuse approved art
    for n, src in REUSE.items():
        shutil.copyfile(os.path.join(PROJ, src), os.path.join(PROJ, f"hero{n}.png"))
        print(f"REUSE hero{n} <- {src}", flush=True)
    # 2) generate the missing tiers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(gen, n, p): n for n, p in GEN.items()}
        for fut in concurrent.futures.as_completed(futs):
            try:
                print(f"OK hero{fut.result()}", flush=True)
            except Exception as e:
                print(f"FAIL hero{futs[fut]}: {e}", flush=True)
