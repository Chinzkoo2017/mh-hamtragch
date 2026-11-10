"""Original background music for each reel: a short tropical-pop loop written as MIDI
and rendered with the FluidR3 General MIDI soundfont. Length is matched to the reel."""
import random, subprocess, tempfile
from pathlib import Path
import mido

SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
TPB = 480                      # ticks per quarter note
STEP = TPB // 4                # 16th note
BAR = STEP * 16
MAJOR = [0, 2, 4, 5, 7, 9, 11]

def triad(key, degree):
    """Diatonic triad (3 MIDI notes) for a 1-based scale degree in a major key."""
    i = degree - 1
    notes = []
    for k in (0, 2, 4):
        j = i + k
        notes.append(key + MAJOR[j % 7] + 12 * (j // 7))
    return notes

class Track:
    def __init__(self, ch, program, name, vol=100, pan=64, rev=60):
        self.ch, self.ev = ch, []
        self.meta = [mido.MetaMessage("track_name", name=name, time=0)]
        if ch != 9:
            self.meta.append(mido.Message("program_change", channel=ch, program=program, time=0))
        for cc, v in ((7, vol), (10, pan), (91, rev)):
            self.meta.append(mido.Message("control_change", channel=ch, control=cc, value=v, time=0))
    def note(self, t, n, dur, vel):
        vel = max(1, min(127, int(vel + random.randint(-6, 6))))
        self.ev.append((t, 1, mido.Message("note_on", channel=self.ch, note=int(n), velocity=vel)))
        self.ev.append((t + dur, 0, mido.Message("note_off", channel=self.ch, note=int(n), velocity=0)))
    def build(self):
        tr = mido.MidiTrack(self.meta)
        last = 0
        for t, _, m in sorted(self.ev, key=lambda e: (e[0], e[1])):
            tr.append(m.copy(time=t - last)); last = t
        return tr

MOODS = {  # (pad program, bass program, drum density)
    "bright": (89, 38, 2), "fresh": (88, 38, 2), "warm": (89, 33, 1),
    "ocean": (91, 38, 1), "drive": (90, 39, 3), "soft": (88, 33, 1),
}

def compose(bars, key=60, prog=(6, 4, 1, 5), lead=12, mood="bright", bpm=120, seed=1):
    random.seed(seed)
    pad_p, bass_p, dens = MOODS.get(mood, MOODS["bright"])
    drums = Track(9, 0, "drums", vol=104, rev=30)
    bass = Track(0, bass_p, "bass", vol=104, rev=10)
    pad = Track(1, pad_p, "pad", vol=70, rev=90)
    arp = Track(2, lead, "lead", vol=96, pan=72, rev=70)
    hook = Track(3, lead, "hook", vol=84, pan=52, rev=80)

    motif = random.choice([[0, 2, 1, 2, 0, 3, 2, 1], [0, 1, 2, 3, 2, 1, 2, 0], [2, 1, 0, 1, 2, 3, 4, 3]])
    hook_rhythm = random.choice([[0, 3, 6, 8, 10], [0, 2, 6, 10, 12], [0, 3, 6, 10, 14]])
    total = bars + 1                      # +1 bar for the ending hit
    for b in range(total):
        t0 = b * BAR
        ch = triad(key, prog[b % len(prog)])
        intro, last = b == 0, b == total - 1
        if last:
            tonic = triad(key, 1)
            for n in tonic: pad.note(t0, n, BAR * 2, 70); arp.note(t0, n + 12, BAR, 90)
            bass.note(t0, tonic[0] - 24, BAR, 100)
            drums.note(t0, 36, STEP, 115); drums.note(t0, 49, BAR, 100)
            continue
        # pad: whole-bar chord, gentle swell on the intro
        for n in ch: pad.note(t0, n, BAR - 10, 50 if intro else 62)
        # lead arpeggio in 16ths across two octaves
        pool = ch + [n + 12 for n in ch] + [ch[0] + 24]
        for s in range(16):
            if intro and s % 2: continue
            n = pool[motif[s % 8] + (3 if s >= 8 and b % 2 else 0)]
            arp.note(t0 + s * STEP, n + 12, STEP - 8, (88 if s % 4 == 0 else 66) - (14 if intro else 0))
        # hook: a short melodic phrase every second bar after the intro
        if not intro and b % 2 == 1:
            for i, s in enumerate(hook_rhythm):
                n = ch[i % 3] + 24 + (2 if i == 3 else 0)
                hook.note(t0 + s * STEP, n, STEP * 2, 92)
        if intro:
            drums.note(t0 + 12 * STEP, 39, STEP, 70); drums.note(t0 + 14 * STEP, 39, STEP, 80)
            continue
        # bass: syncopated tropical pattern
        root = ch[0] - 24
        for s, l, o in ((0, 3, 0), (3, 2, 0), (6, 2, 12), (8, 3, 0), (11, 2, 0), (14, 2, 7)):
            bass.note(t0 + s * STEP, root + o, l * STEP - 10, 98 if s in (0, 8) else 82)
        # drums
        fill = (b % 4 == 3) and dens >= 1
        for s in range(16):
            t = t0 + s * STEP
            if s % 4 == 0: drums.note(t, 36, STEP, 112)
            if s in (4, 12): drums.note(t, 39, STEP, 96)
            if s % 4 == 2: drums.note(t, 42, STEP, 74)
            if dens >= 2 and s % 2 == 1: drums.note(t, 82, STEP, 38)
            if dens >= 3 and s in (7, 15): drums.note(t, 42, STEP, 60)
            if s == 14 and b % 2: drums.note(t, 46, STEP * 2, 66)
            if fill and s >= 12: drums.note(t, 38, STEP, 70 + (s - 12) * 10)
        if b == 1: drums.note(t0, 49, BAR, 90)

    mid = mido.MidiFile(ticks_per_beat=TPB)
    tempo = mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0)])
    mid.tracks.append(tempo)
    for tr in (drums, bass, pad, arp, hook): mid.tracks.append(tr.build())
    return mid

def render(mid, out_mp3, seconds):
    with tempfile.TemporaryDirectory() as t:
        m, w = Path(t) / "a.mid", Path(t) / "a.wav"
        mid.save(m)
        subprocess.run(["fluidsynth", "-ni", "-g", "0.55", "-r", "44100", "-F", str(w), SF2, str(m)],
                       check=True, capture_output=True)
        fade_st = max(0.0, seconds - 1.6)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(w), "-t", f"{seconds:.2f}",
                        "-af", f"afade=t=in:d=0.04,afade=t=out:st={fade_st:.2f}:d=1.6,loudnorm=I=-15:TP=-1.5:LRA=9",
                        "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "112k", str(out_mp3)], check=True)
