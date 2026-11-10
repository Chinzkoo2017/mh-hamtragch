"""Download product images and certificates from Marine Health, render certificate
previews, and synthesize Mongolian voice-overs for the reels. Runs in GitHub Actions."""
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

def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())

async def say(text, path, voice, rate):
    import edge_tts
    try:
        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:
        com = edge_tts.Communicate(text, voice, rate=rate)
    words = []
    with open(path, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"t": round(ch["offset"] / 1e7, 3), "w": ch["text"]})
    return words

def reels():
    spec = json.loads((ROOT / "data" / "reels.json").read_text(encoding="utf-8"))
    d = A / "reels"; d.mkdir(parents=True, exist_ok=True)
    for r in spec["reels"]:
        voice = r.get("voice", spec["voice"]); rate = r.get("rate", spec["rate"])
        h = hashlib.sha1(json.dumps([voice, rate, [b["say"] for b in r["beats"]]], ensure_ascii=False).encode()).hexdigest()[:12]
        meta = d / f"{r['id']}.json"
        if meta.exists() and json.loads(meta.read_text())["hash"] == h and (d / f"{r['id']}.mp3").exists():
            continue
        with tempfile.TemporaryDirectory() as t:
            parts, beats, t0 = [], [], 0.0
            for i, b in enumerate(r["beats"]):
                p = Path(t) / f"b{i}.mp3"
                words = asyncio.run(say(b["say"], p, voice, rate))
                n = Path(t) / f"n{i}.wav"
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(p), "-af", "apad=pad_dur=0.12", "-ar", "24000", "-ac", "1", str(n)], check=True)
                L = dur(n)
                beats.append({"t0": round(t0, 3), "t1": round(t0 + L, 3), "words": words})
                parts.append(n); t0 += L
            lst = Path(t) / "list.txt"
            lst.write_text("".join(f"file '{p}'\n" for p in parts))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                            "-c:a", "libmp3lame", "-b:a", "64k", str(d / f"{r['id']}.mp3")], check=True)
        meta.write_text(json.dumps({"id": r["id"], "hash": h, "voice": voice, "dur": round(t0, 3), "beats": beats},
                                   ensure_ascii=False), encoding="utf-8")
        print("reel", r["id"], round(t0, 1), "s")

if __name__ == "__main__":
    cfg = json.loads((ROOT / "data" / "assets.json").read_text(encoding="utf-8"))
    steps = sys.argv[1:] or ["images", "certs", "reels"]
    if "images" in steps: images(cfg)
    if "certs" in steps: certs(cfg)
    if "reels" in steps: reels()
