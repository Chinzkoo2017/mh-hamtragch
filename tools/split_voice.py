"""Split one full-reel dialogue recording (assets/voice/<reel>.mp3) into one clip per beat
(assets/voice/<reel>/01.mp3 …). Cut points are chosen among the pauses in the recording so that
the cumulative speaking time best matches the cumulative length of each beat's text."""
import json, subprocess, sys
from pathlib import Path
import numpy as np

SR = 16000
HOP = 0.01  # 10 ms frames


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def pauses(x):
    n = int(SR * HOP)
    fr = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    loud = np.percentile(db, 95)
    quiet = db < loud - 32
    # speech span
    idx = np.where(~quiet)[0]
    s0, s1 = idx[0] * HOP, (idx[-1] + 1) * HOP
    gaps, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            a, b = i * HOP, j * HOP
            if b - a >= 0.14 and a > s0 and b < s1:
                gaps.append((a, b))
            i = j
        else:
            i += 1
    return s0, s1, gaps


HIGH = {"Alimaa"}  # higher-pitched voices; used to place cuts on speaker changes


def f0_track(x):
    n = int(0.04 * SR); h = n // 2; lo, hi = int(SR / 350), int(SR / 70); out = []
    for i in range(0, len(x) - n, h):
        f = x[i:i + n]
        if np.sqrt((f ** 2).mean()) < 0.02: out.append(0.0); continue
        f = f - f.mean(); ac = np.correlate(f, f, "full")[n - 1:]
        k = lo + int(np.argmax(ac[lo:hi]))
        out.append(SR / k if ac[k] > 0.4 * ac[0] else 0.0)
    return np.array(out), h / SR


def side_pitch(tr, step, a, b):
    seg = tr[int(max(a, 0) / step): int(max(b, 0) / step)]
    seg = seg[seg > 0]
    return float(np.median(seg)) if len(seg) >= 4 else 0.0


def choose(gaps, s0, s1, texts, who=None, x=None):
    """DP: pick len(texts)-1 gaps in order; cost = timing error − bonus for long pauses
    + penalty when the pitch on either side does not fit the expected speaker change."""
    w = np.array([max(len(t), 1) for t in texts], float)
    target = s0 + (s1 - s0) * np.cumsum(w)[:-1] / w.sum()
    k, G = len(target), len(gaps)
    if G < k: raise ValueError(f"only {G} pauses for {k} cuts")
    mid = [(a + b) / 2 for a, b in gaps]
    ln = [b - a for a, b in gaps]
    pen = np.zeros((k, G))
    if who and x is not None:
        tr, step = f0_track(x)
        L = [side_pitch(tr, step, a - 1.0, a) for a, b in gaps]
        R = [side_pitch(tr, step, b, b + 1.0) for a, b in gaps]
        for c in range(k):
            if who[c] == who[c + 1]: continue
            hiL, hiR = who[c] in HIGH, who[c + 1] in HIGH
            for g in range(G):
                if L[g] and R[g]:
                    want = 1 if hiR else -1  # pitch should rise at the cut if the next speaker is the high voice
                    pen[c, g] = 0 if (R[g] - L[g]) * want > 25 else 2.5
    cost = lambda c, g: abs(mid[g] - target[c]) - 2.2 * min(ln[g], 0.8) + pen[c, g]
    INF = 1e18
    D = np.full((k, G), INF); P = np.zeros((k, G), int)
    for g in range(G): D[0, g] = cost(0, g)
    for c in range(1, k):
        best, bi = INF, -1
        for g in range(G):
            if g - 1 >= 0 and D[c - 1, g - 1] < best: best, bi = D[c - 1, g - 1], g - 1
            if bi >= 0: D[c, g] = best + cost(c, g); P[c, g] = bi
    g = int(np.argmin(D[k - 1])); out = [g]
    for c in range(k - 1, 0, -1):
        g = P[c, g]; out.append(g)
    return [gaps[g] for g in reversed(out)], target


def split(full, texts, outdir, who=None, verbose=True):
    x = load(full)
    s0, s1, gaps = pauses(x)
    cuts, target = choose(gaps, s0, s1, texts, who, x)
    edges = [max(0.0, s0 - 0.05)] + [(a + b) / 2 for a, b in cuts] + [s1 + 0.12]
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("[0-9][0-9].*"): old.unlink()
    for i in range(len(texts)):
        a, b = edges[i], edges[i + 1]
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(full), "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-af", "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,afade=t=in:d=0.02",
                        "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(outdir / f"{i + 1:02d}.mp3")], check=True)
        if verbose:
            print(f"  {i + 1:02d} {a:6.2f}-{b:6.2f}  {texts[i][:60]}")
    return edges


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    spec = json.loads((root / "data" / "reels.json").read_text(encoding="utf-8"))
    want = sys.argv[1:]
    for r in spec["reels"]:
        f = root / "assets" / "voice" / f"{r['id']}.mp3"
        if not f.exists() or (want and r["id"] not in want): continue
        print(r["id"])
        split(f, [b["say"] for b in r["beats"]], root / "assets" / "voice" / r["id"], [b["who"] for b in r["beats"]])
