#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 4 strain-tier variants of the original mole mascot, in a
raised-arms 'supporting weight overhead' pose, expression getting more
exhausted. Stones themselves are rendered separately on top in the frontend."""
import base64, json, os, urllib.request, concurrent.futures, io
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
        "head pressing upward as if holding a heavy weight overhead, standing "
        "facing forward, full body, centered, original mascot, retro SNES style, "
        "crisp pixels, ")

JOBS = {
    "carry0": BASE + "relaxed happy confident face, slight easy smile, this load "
        "is light and easy, " + CHROMA,
    "carry1": BASE + "starting to strain, mouth a little tight, eyebrows pushed "
        "together in effort, one tiny sweat drop, still determined, " + CHROMA,
    "carry2": BASE + "straining hard, gritted teeth grimace, eyes squinting, "
        "several sweat drops flying off, face flushed red from effort, arms "
        "trembling, " + CHROMA,
    "carry3": BASE + "utterly exhausted and about to be crushed, eyes squeezed "
        "shut with X or spiral strain, tongue out, whole body shaking, lots of "
        "sweat, legs buckling and bending under the weight, desperate, " + CHROMA,
}

def gen(name, prompt):
    body = json.dumps({"model": "gpt-image-2", "prompt": prompt}).encode()
    req = urllib.request.Request(API, data=body, method="POST",
        headers={"api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.load(r)
    raw = base64.b64decode(data["data"][0]["b64_json"])
    with open(os.path.join(POOL, f"海龟汤_{name}_gpt-image-2.png"), "wb") as f:
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

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    futs = {ex.submit(gen, n, p): n for n, p in JOBS.items()}
    for fut in concurrent.futures.as_completed(futs):
        try:
            print("OK", *fut.result(), flush=True)
        except Exception as e:
            print("FAIL", futs[fut], e, flush=True)
