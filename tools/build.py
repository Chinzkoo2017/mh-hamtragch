"""Download product images and certificates from Marine Health, render certificate
previews, and compose background music for the reels. Runs in GitHub Actions."""
import asyncio, hashlib, io, json, os, subprocess, sys, tempfile, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets"
UA = {"User-Agent": "Mozilla/5.0 (partner-site build)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def save_img(data, out, maxside):
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
    im.thumbnail((maxside, maxside), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "WEBP", quality=82, method=6)

def images(cfg):
    base = cfg["base"]
    for pid, f in cfg["main"].items():
        out = A / "img" / f"{pid}.webp"
        if out.exists(): continue
        try: save_img(get(base + f), out, 1000); print("img", pid)
        except Exception as e: print("img FAIL", pid, e)
    for pid, lst in cfg["media"].items():
        for i, p in enumerate(lst, 1):
            out = A / "img" / f"{pid}-m{i}.webp"
            if out.exists(): continue
            try: save_img(get(base + p), out, 1100); print("media", pid, i)
            except Exception as e: print("media FAIL", pid, i, e)

def certs(cfg):
    idx = []
    d = A / "certs"; d.mkdir(parents=True, exist_ok=True)
    for c in cfg["certs"]:
        pdf = d / f"{c['key']}.pdf"
        if not pdf.exists():
            try: pdf.write_bytes(get(cfg["base"] + c["path"])); print("cert", c["key"])
            except Exception as e: print("cert FAIL", c["key"], e); continue
        pages = []
        with tempfile.TemporaryDirectory() as t:
            subprocess.run(["pdftoppm", "-r", "120", "-l", "4", "-png", str(pdf), f"{t}/p"], check=True)
            for i, png in enumerate(sorted(Path(t).glob("p*.png")), 1):
                out = d / f"{c['key']}-p{i}.webp"
                im = Image.open(png).convert("RGB"); im.thumbnail((1400, 1400), Image.LANCZOS)
                im.save(out, "WEBP", quality=80, method=6); pages.append(out.name)
        idx.append({**{k: c[k] for k in ("key", "pid", "title")}, "pdf": pdf.name, "pages": pages})
    (d / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")

CUT_KEYS = ["154","121","214","104","106","282","2028","2301","2302","2303","2304","2305","2306",
            "2279","2275","2127","2102","154-m5","121-m1","214-m4","104-m1","106-m1","282-m6","2028-m4"]

def cutouts():
    """Remove photo backgrounds so products can sit on new animated scenes."""
    import numpy as np
    from rembg import remove, new_session
    from scipy import ndimage
    sess = new_session("isnet-general-use")
    d = A / "cut"; d.mkdir(parents=True, exist_ok=True)
    for k in CUT_KEYS:
        out = d / f"{k}.webp"; src = A / "img" / f"{k}.webp"
        if out.exists() or not src.exists(): continue
        im = Image.open(src).convert("RGB")
        rgba = remove(im, session=sess, post_process_mask=True)
        a = np.array(rgba.split()[-1])
        lab, n = ndimage.label(a > 40)
        if n > 1:  # drop small detached bits such as promo lettering
            sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1))
            keep = [i + 1 for i, v in enumerate(sizes) if v >= 0.08 * sizes.max()]
            mask = np.isin(lab, keep)
            mask = ndimage.binary_dilation(mask, iterations=3)
            a = (a * mask).astype("uint8")
        rgba.putalpha(Image.fromarray(a))
        bb = rgba.getbbox()
        if bb: rgba = rgba.crop(bb)
        rgba.thumbnail((900, 900), Image.LANCZOS)
        rgba.save(out, "WEBP", quality=86, method=6)
        print("cut", k, rgba.size)

def music():
    sys.path.insert(0, str(ROOT / "tools"))
    import music as M
    spec = json.loads((ROOT / "data" / "reels.json").read_text(encoding="utf-8"))
    bpm = spec.get("bpm", 120); bar = 240 / bpm
    d = A / "music"; d.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(spec["reels"]):
        bars = sum(b["bars"] for b in r["beats"]); mu = r["music"]
        h = hashlib.sha1(json.dumps([bars, mu, bpm, 3]).encode()).hexdigest()[:12]
        meta = d / f"{r['id']}.json"
        if meta.exists() and json.loads(meta.read_text())["hash"] == h: continue
        mid = M.compose(bars, mu["key"], tuple(mu["prog"]), mu["lead"], mu["mood"], bpm, seed=i + 7)
        secs = bars * bar + 1.4
        M.render(mid, d / f"{r['id']}.mp3", secs)
        meta.write_text(json.dumps({"id": r["id"], "hash": h, "bpm": bpm, "dur": round(secs, 2)}))
        print("music", r["id"], round(secs, 1), "s")

if __name__ == "__main__":
    cfg = json.loads((ROOT / "data" / "assets.json").read_text(encoding="utf-8"))
    steps = sys.argv[1:] or ["images", "cutouts", "certs", "music"]
    if "images" in steps: images(cfg)
    if "cutouts" in steps: cutouts()
    if "certs" in steps: certs(cfg)
    if "music" in steps: music()
