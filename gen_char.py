#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate ONLY the character + crushed sprites as an original design."""
import base64, json, os, urllib.request, concurrent.futures, io
from PIL import Image

API = os.environ.get("IMAGE_API_URL", "")  # OpenAI-compatible /images/generations endpoint; set via env
KEY = os.environ.get("IMAGE_API_KEY", "")  # set via env / .env, never commit
PROJ = "/Users/tal/Desktop/海龟汤游戏/assets"
POOL = "/Users/tal/Desktop/资源管理"
CHROMA = ("solid pure magenta background color hex #FF00FF, the subject fully "
          "isolated with clean edges, no shadow on the background")

JOBS = {
    "character": (
        "16-bit pixel art sprite of an original cute round chibi mole-like creature "
        "character, plump brown furry body, big round belly, tiny arms raised over the "
        "shoulders ready to carry weight, small round ears, big friendly eyes, a little "
        "red bandana around the neck, standing facing forward, full body, centered, "
        "original mascot design, retro SNES style, crisp pixels, " + CHROMA),
    "crushed": (
        "16-bit pixel art sprite of the same original plump brown furry chibi mole "
        "creature with a red bandana, now flattened and squished flat like a pancake "
        "under a big heavy pile of grey boulders, dizzy spiral eyes, comical defeated, "
        "tiny arms sticking out, retro SNES style, crisp pixels, centered, " + CHROMA),
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
    return name, img.size

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    futs = {ex.submit(gen, n, p): n for n, p in JOBS.items()}
    for fut in concurrent.futures.as_completed(futs):
        try:
            print("OK", *fut.result(), flush=True)
        except Exception as e:
            print("FAIL", futs[fut], e, flush=True)
