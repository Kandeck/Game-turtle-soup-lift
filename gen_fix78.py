#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate ONLY hero7 (7 boulders) and hero8 (8 boulders). The model
miscounts loose piles, so describe the pile as explicit stacked ROWS."""
import base64, json, os, urllib.request, concurrent.futures, io
from PIL import Image

API = "http://ai-service.tal.com/openai-compatible/v1/images/generations"
KEY = os.environ.get("TAL_IMAGE_API_KEY", "")  # set via env, never commit the real key
PROJ = "/Users/tal/Desktop/海龟汤游戏/assets"
POOL = "/Users/tal/Desktop/资源管理"
CHROMA = ("solid pure magenta background color hex #FF00FF, the subject fully "
          "isolated with clean edges, no shadow on the background")
BASE = ("16-bit pixel art sprite of the SAME original plump brown furry chibi "
        "mole creature with a big round belly, small round ears, a little red "
        "bandana around the neck, both short arms raised straight up over the "
        "head, standing facing forward, full body, centered, original mascot, "
        "retro SNES style, crisp pixels, ")

JOBS = {
    # 8 = two clean rows of four boulders each (4 + 4)
    "hero8": (BASE + "balancing a big pile of exactly EIGHT grey rounded "
        "boulders above the head, arranged as just TWO rows: a bottom row of "
        "four boulders and a top row of four boulders, four plus four equals "
        "eight boulders total, no other boulders, exhausted desperate face, "
        "teeth gritted hard, eyes screwed shut, whole body shaking, knees "
        "buckling, " + CHROMA),
}

def gen(name, prompt):
    body = json.dumps({"model": "gpt-image-2", "prompt": prompt}).encode()
    req = urllib.request.Request(API, data=body, method="POST",
        headers={"api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.load(r)
    raw = base64.b64decode(data["data"][0]["b64_json"])
    with open(os.path.join(POOL, f"海龟汤_{name}_v2_gpt-image-2.png"), "wb") as f:
        f.write(raw)
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    px = img.load(); w, h = img.size
    for y in range(h):
        for x in range(w):
            r_, g_, b_, a_ = px[x, y]
            if r_ > 180 and g_ < 90 and b_ > 180:
                px[x, y] = (r_, g_, b_, 0)
    img.save(os.path.join(PROJ, f"{name}.png"))
    return name

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    futs = {ex.submit(gen, n, p): n for n, p in JOBS.items()}
    for fut in concurrent.futures.as_completed(futs):
        try:
            print("OK", fut.result(), flush=True)
        except Exception as e:
            print("FAIL", futs[fut], e, flush=True)
