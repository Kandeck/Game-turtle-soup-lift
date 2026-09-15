#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate pixel-art assets for the 海龟汤 (lateral-thinking) game via gpt-image-2.
Fires all requests concurrently, saves to project assets/ and Desktop/资源管理/,
and chroma-keys the magenta background of sprites into transparency."""
import base64, json, os, urllib.request, concurrent.futures
from PIL import Image
import io

API = os.environ.get("IMAGE_API_URL", "")  # OpenAI-compatible /images/generations endpoint; set via env
KEY = os.environ.get("IMAGE_API_KEY", "")  # set via env / .env, never commit
PROJ = "/Users/tal/Desktop/海龟汤游戏/assets"
POOL = "/Users/tal/Desktop/资源管理"

# Magenta backdrop makes chroma-keying reliable for sprites.
CHROMA = ("solid pure magenta background color hex #FF00FF, "
          "the subject fully isolated with clean edges, no shadow on the background")

JOBS = {
    "character": (
        "16-bit pixel art sprite of a cute chibi adventurer standing facing forward, "
        "brave small explorer with a green tunic, brown boots, determined happy face, "
        "arms slightly raised as if ready to carry something heavy on the shoulders, "
        "full body, centered, retro SNES JRPG style, crisp pixels, "
        + CHROMA),
    "stone": (
        "16-bit pixel art of a single grey rounded boulder rock, chunky retro game style, "
        "clear outline, top-down-ish lighting, small enough to be stacked, centered, "
        + CHROMA),
    "crushed": (
        "16-bit pixel art sprite of a cartoon adventurer flattened and squished under a "
        "big pile of grey boulders, dizzy spiral eyes, comical defeated pose, "
        "retro SNES JRPG style, crisp pixels, centered, "
        + CHROMA),
    "bg": (
        "16-bit pixel art background scene of a mysterious dim stone dungeon chamber "
        "with torches on the walls, cracked stone floor, moody purple and blue palette, "
        "empty center area for a character to stand, retro SNES JRPG parallax style, "
        "no characters, no text"),
}

def gen(name, prompt):
    body = json.dumps({"model": "gpt-image-2", "prompt": prompt}).encode()
    req = urllib.request.Request(API, data=body, method="POST",
        headers={"api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.load(r)
    raw = base64.b64decode(data["data"][0]["b64_json"])
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    pool_path = os.path.join(POOL, f"海龟汤_{name}_gpt-image-2.png")
    with open(pool_path, "wb") as f:
        f.write(raw)
    # Chroma-key magenta -> transparent for sprites (not the bg scene)
    if name != "bg":
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r_, g_, b_, a_ = px[x, y]
                if r_ > 180 and g_ < 90 and b_ > 180:
                    px[x, y] = (r_, g_, b_, 0)
    out = os.path.join(PROJ, f"{name}.png")
    img.save(out)
    return name, img.size

if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(gen, n, p): n for n, p in JOBS.items()}
        for fut in concurrent.futures.as_completed(futs):
            try:
                n, size = fut.result()
                print(f"OK {n} {size}", flush=True)
            except Exception as e:
                print(f"FAIL {futs[fut]}: {e}", flush=True)
