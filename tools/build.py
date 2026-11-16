"""Download product images and certificates from Marine Health, render certificate
previews, and compose background music for the reels. Runs in GitHub Actions."""
import asyncio, hashlib, io, json, math, os, subprocess, sys, tempfile, urllib.request
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

def brand():
    """Official Marine Health logos (permission to use: see project notes)."""
    d = A / "brand"; d.mkdir(parents=True, exist_ok=True)
    for name, url in (("mh-white.svg", "https://marinehealth.asia/assets/img/logo-white.svg"),
                      ("mh-dark.svg", "https://marinehealth.asia/assets/img/logo.svg")):
        out = d / name
        if out.exists(): continue
        try: out.write_bytes(get(url)); print("brand", name)
        except Exception as e: print("brand FAIL", name, e)

VOICE_EXT = (".mp3", ".wav", ".m4a", ".ogg")

def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())

def voice_files(rid, n):
    """assets/voice/<reel>/01.mp3 … one clip per beat. Returns list or None if any is missing."""
    d = A / "voice" / rid
    out = []
    for i in range(1, n + 1):
        f = next((d / f"{i:02d}{e}" for e in VOICE_EXT if (d / f"{i:02d}{e}").exists()), None)
        if not f: return None
        out.append(f)
    return out

def music():
    sys.path.insert(0, str(ROOT / "tools"))
    import music as M
    spec = json.loads((ROOT / "data" / "reels.json").read_text(encoding="utf-8"))
    bpm = spec.get("bpm", 120); bar = 240 / bpm
    d = A / "music"; d.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(spec["reels"]):
        mu = r["music"]; n = len(r["beats"])
        full = A / "voice" / f"{r['id']}.mp3"  # one dialogue recording for the whole reel → split per beat
        if full.exists():
            import split_voice as SV
            stamp = A / "voice" / r["id"] / ".source"
            sig = hashlib.sha1(full.read_bytes() + json.dumps([b["say"] for b in r["beats"]]).encode()).hexdigest()[:12]
            if not stamp.exists() or stamp.read_text().strip() != sig:
                print("split", r["id"])
                SV.split(full, [b["say"] for b in r["beats"]], A / "voice" / r["id"], [b["who"] for b in r["beats"]])
                stamp.write_text(sig)
        vf = voice_files(r["id"], n)
        vsig = [[f.name, f.stat().st_size] for f in vf] if vf else None
        h = hashlib.sha1(json.dumps([[b["bars"] for b in r["beats"]], mu, bpm, vsig, 5]).encode()).hexdigest()[:12]
        meta = d / f"{r['id']}.json"
        if meta.exists() and json.loads(meta.read_text())["hash"] == h: continue
        if not vf:
            bars = sum(b["bars"] for b in r["beats"])
            mid = M.compose(bars, mu["key"], tuple(mu["prog"]), mu["lead"], mu["mood"], bpm, seed=i + 7)
            secs = bars * bar + 1.4
            M.render(mid, d / f"{r['id']}.mp3", secs)
            meta.write_text(json.dumps({"id": r["id"], "hash": h, "bpm": bpm, "dur": round(secs, 2), "voice": False}))
            print("music", r["id"], round(secs, 1), "s"); continue
        # voice present: beat lengths follow the recordings, music is fitted underneath and ducked
        lead, gap = 0.35, 0.45
        beats, t = [], 0.0
        for k, f in enumerate(vf):
            dv = dur(f)
            v0 = t + (lead if k == 0 else 0.15)
            t1 = max(v0 + dv + gap, t + 1.6)
            beats.append({"t0": round(t, 3), "t1": round(t1, 3), "v0": round(v0, 3), "v1": round(v0 + dv, 3)})
            t = t1
        total = t + 1.2
        bars = max(2, math.ceil(total / bar))
        mid = M.compose(bars, mu["key"], tuple(mu["prog"]), mu["lead"], mu["mood"], bpm, seed=i + 7)
        with tempfile.TemporaryDirectory() as tmp:
            bed = Path(tmp) / "bed.mp3"
            M.render(mid, bed, total + 0.4)
            ins = ["-i", str(bed)]; fl = []
            for k, (f, b) in enumerate(zip(vf, beats), 1):
                ins += ["-i", str(f)]
                ms = int(b["v0"] * 1000)
                fl.append(f"[{k}]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{k}]")
            fl.append("".join(f"[v{k}]" for k in range(1, len(vf) + 1)) + f"amix=inputs={len(vf)}:normalize=0,apad=whole_dur={total + 0.4:.2f}[vo]")
            fl.append("[vo]asplit=2[vk][vm]")
            fl.append("[0]aresample=44100,aformat=channel_layouts=stereo,volume=0.55[bg]")
            fl.append("[bg][vk]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350:makeup=1[duck]")
            fl.append("[duck][vm]amix=inputs=2:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=9[out]")
            subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fl), "-map", "[out]", "-t", f"{total + 0.4:.2f}",
                            "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k", str(d / f"{r['id']}.mp3")], check=True)
        meta.write_text(json.dumps({"id": r["id"], "hash": h, "bpm": bpm, "dur": round(total + 0.4, 2), "voice": True, "beats": beats}))
        print("voice+music", r["id"], round(total, 1), "s")

if __name__ == "__main__":
    cfg = json.loads((ROOT / "data" / "assets.json").read_text(encoding="utf-8"))
    steps = sys.argv[1:] or ["brand", "images", "cutouts", "certs", "music"]
    if "brand" in steps: brand()
    if "images" in steps: images(cfg)
    if "cutouts" in steps: cutouts()
    if "certs" in steps: certs(cfg)
    if "music" in steps: music()
