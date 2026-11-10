#!/usr/bin/env python3
"""Abnahme eines fertigen Masters: alle technischen Prüfungen in einem Lauf, mit Ampel (Schritt 6).

Prüft Format, Farbtags, Takt, Lautheit, Spitzen, Tonlöcher, falsche und eingefrorene
Frames zwischen den Takes, Grading-Sprünge, gleichmäßige Lautstärke und auf Wunsch
Sync gegen den Take und den Body gegen eine schon abgenommene Version.

    python abnahme.py <master.mp4> [--take take.mp4] [--referenz alt.mp4 --ab-frame 270] [--fix]

  --take      Take in der Zeitachse des Masters (z. B. remotion/public/video/v1-hd.mp4) → Sync + Grading-Vergleich
  --referenz  schon abgenommener Master derselben Fassung → Body ab --ab-frame muss bildgleich sein (≥ 40 dB)
  --gesicht   x,y,b,h des Gesichts für die Sync-Prüfung (Standard 420,920,240,240, Bildmitte)
  --fix       nur Technik reparieren (Lautheit, Spitzen, Farbtags), danach neu prüfen. Inhaltliches nur melden.
  --vollbild  Vollbild-Passagen 'a-b,c-d' (Master-Frames). Ohne Angabe aus remotion/src/reel.ts
              (VOLLBILD + HOOK/SATZ2 der Version): dort kein Einfrier-/Grading-Check.
  --reel-ts   Pfad zu reel.ts, falls der Master nicht in <projekt>/aus/ liegt
  --version   Version (v1, v2 ...), falls sie nicht im Dateinamen steht

Rückgabe 0 = grün, 2 = gelb (Befunde melden), 1 = rot (nicht freigeben).
Schreibt <master>-abnahme.md (Bericht) und <master>-abnahme.jpg (Kontaktbogen, selbst ansehen).
Braucht numpy (Python-Umgebung aus setup.py).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from naht_check import loecher  # noqa: E402

FPS = 30
# Take-Bereich unterhalb der Grafik-Zone
TAKE_CROP = (0, 1150, 1080, 700)
KLEIN = (108, 70)

# Grenzwerte
LUFS_MIN, LUFS_MAX = -15.0, -13.0  # master.sh zielt auf -14 LUFS
TP_MAX = -1.0  # dBTP, master.sh
FREEZE = 0.05  # mittlere Differenz auf 54×35
STANDBILD_AB = 8  # längere Stand-Läufe nur gelb (ruhender Screen, Standbild-Effekt)
SCHNITT = 6.0  # mittlere Differenz auf 108×70 ab der ein harter Bildwechsel zählt
YAVG_MIN, YAVG_MAX = 105, 135  # Take-Grading „hell + knackig“ ~118, gemessen am gegradeten Take, nicht am Master (Bühne ist dunkel)
HELL_SPRUNG = 4.0  # Luma-Stufe in den stillen Bildteilen (Hintergrund), Untertitel + Gestik fallen dort raus
MASTER_ZU_TAKE = 4.0  # Luma/Chroma-Abweichung Master gegen Take in den stillen Bildteilen (Render hat Farbe verschoben)
PEGEL_SPRUNG = 3.0  # dB Sprachpegel zwischen zwei Takes
PSNR_MIN = 40.0  # Body gegen Referenz


def lauf(cmd, check=False):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        sys.stderr.write(r.stderr[-2000:])  # sonst bricht probe() ohne Fehlertext ab
        r.check_returncode()
    return r


def probe(datei):
    r = lauf(["ffprobe", "-v", "error", "-show_entries",
              "stream=codec_type,codec_name,width,height,r_frame_rate,color_transfer,color_primaries,color_space,duration",
              "-show_entries", "format=duration", "-of", "json", datei], check=True)
    return json.loads(r.stdout)


def frames_lesen(datei, vf, b, h):
    """Graustufen-Frames (Luma) als Array [n, h, b]. Erst auf 1080x1920, damit Take (z. B. 1350x2400) und Master dieselben Koordinaten haben."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", datei, "-vf", f"scale=1080:1920,{vf},scale={b}:{h}:flags=area,format=gray",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, h, b).astype(np.float32)


def lautheit(datei):
    r = lauf(["ffmpeg", "-nostats", "-i", datei, "-af", "ebur128=peak=true", "-f", "null", "-"])
    zusammen = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", zusammen)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", zusammen)
    return float(i.group(1)), float(tp.group(1)) if tp and tp.group(1) != "-inf" else -99.0


def ton_samples(datei):
    with tempfile.NamedTemporaryFile(suffix=".raw") as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", datei, "-ac", "1", "-ar", "16000", "-f", "s16le", tmp.name], check=True)
        return np.fromfile(tmp.name, dtype=np.int16).astype(np.float32) / 32768


def sprachpegel(x, a, b, sr=16000):
    """Mittlerer Pegel (dBFS) der lauten 50-ms-Fenster zwischen Sekunde a und b, also ohne Pausen."""
    s = x[int(a * sr):int(b * sr)]
    n = int(0.05 * sr)
    if len(s) < n * 10:
        return None
    rms = np.sqrt(np.mean(s[: len(s) // n * n].reshape(-1, n) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    laut = db[db > -40]
    return float(10 * np.log10(np.mean(10 ** (laut / 10)))) if len(laut) >= 10 else None


def farbabstand(a, b):
    """Mittlere Chroma-Abweichung (U/V) zwischen Master und Take im unteren Bildstreifen links/rechts."""
    def uv(d):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", d, "-vf", "scale=1080:1920,crop=1080:300:0:1600,scale=36:10:flags=area,format=yuv444p",
                            "-frames:v", "600", "-f", "rawvideo", "-"], capture_output=True, check=True)
        x = np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, 3, 10, 36).astype(np.float32)
        return x[:, 1:, :, list(range(0, 6)) + list(range(30, 36))].mean(axis=(0, 2, 3))
    return float(np.abs(uv(a) - uv(b)).max())


def sync_messen(master, take, gesicht):
    """(bester Versatz in Frames, klares Minimum?) aus dem Gesichtsausschnitt von Master und Take."""
    gx, gy, gb, gh = (int(v) for v in gesicht.split(","))
    vf = f"crop={gb}:{gh}:{gx}:{gy}"
    m, tk = frames_lesen(master, vf, 48, 48), frames_lesen(take, vf, 48, 48)
    norm = lambda a: (a - a.mean(axis=(1, 2), keepdims=True)) / (a.std(axis=(1, 2), keepdims=True) + 1e-6)  # noqa: E731
    m, tk = norm(m), norm(tk)
    lang = min(len(m), len(tk)) - 8
    probe_i = np.linspace(8, lang, 120).astype(int)
    fehl = {o: float(np.mean([np.abs(m[i] - tk[i + o]).mean() for i in probe_i])) for o in range(-4, 5)}
    best = min(fehl, key=fehl.get)
    rest = np.mean([v for o, v in fehl.items() if o != best])
    return best, fehl[best] <= 0.8 * rest


def zeit(n):
    return f"{n / FPS:5.2f} s (Frame {n})"


VOLL_RAND = 3  # Frames um jede Vollbild-Passage mit auslassen (Übergang Grafik ↔ Take)


def reel_ts_finden(master, reel_ts=None, version=None):
    """(Pfad zu reel.ts, Version) oder (None, None). Standard: <projekt>/remotion/src/reel.ts zu <projekt>/aus/<master>."""
    m = re.search(r"(v\d+)", Path(master).stem)
    version = version or (m.group(1) if m else None)
    pfad = Path(reel_ts) if reel_ts else Path(master).resolve().parent.parent / "remotion" / "src" / "reel.ts"
    return (pfad, version) if pfad.is_file() and version else (None, None)


def vollbild_bereiche(master, angabe=None, reel_ts=None, version=None):
    """Vollbild-Passagen als Master-Frames [(von, bis)], bis exklusiv.

    In diesen Passagen liegt eine Grafik ohne Sprecher über dem Take-Bereich. Gerenderte Grafiken haben echte
    Standbild-Frames, die der Einfrier-Check sonst als Decoder-Fehler läse. Quelle ist reel.ts der Vorlage:
    `export const VOLLBILD` (Body-Frames) plus HOOK/SATZ2 je Version (Vollbild im Hook = SATZ2 bis HOOK).
    `angabe` = "a-b,c-d" überschreibt. Dazu das Ende des Hook-Zooms (Frame 0 bis SATZ2 zoomt weich rein, der
    Hintergrund wandert, das ist keine Grading-Stufe).
    Gibt (bereiche, quelle, zoom_ende) zurück, ([], None, 0) wenn nichts gefunden (dann prüft alles).
    """
    if angabe:
        return [tuple(int(x) for x in t.split("-")) for t in angabe.split(",") if t.strip()], "--vollbild", 0
    ts, version = reel_ts_finden(master, reel_ts, version)
    if not ts:
        return [], None, 0
    q = ts.read_text(encoding="utf-8")
    body = re.search(r"export const VOLLBILD\b[^=]*=\s*(\[.*?\]);", q, re.S)
    if not body:
        return [], None, 0

    def wert(name):
        # Record je Version ({"v1": 187, …}) oder eine Zahl
        r = re.search(rf"export const {name}\b[^=]*=\s*(\{{[^}}]*\}}|\d+)", q)
        if not r:
            return None
        v = json.loads(r.group(1))
        return v.get(version) if isinstance(v, dict) else v

    hook, satz2 = wert("HOOK"), wert("SATZ2")
    if hook is None:
        return [], None, 0
    bereiche = [(satz2, hook)] if satz2 is not None and satz2 < hook else []
    bereiche += [(hook + a, hook + e) for a, e in json.loads(body.group(1))]
    return bereiche, f"{ts} ({version})", satz2 or 0


class Bericht:
    def __init__(self):
        self.zeilen = []
        self.rot = self.gelb = 0
        self.fixbar = []

    def ok(self, was, detail=""):
        self.zeilen.append(f"✅ **{was}** {detail}")

    def warn(self, was, detail):
        self.gelb += 1
        self.zeilen.append(f"⚠️ **{was}** {detail}")

    def pruef(self, gut, was, detail, stufe="rot", fix=None):
        """gut → ✅, sonst ❌ (stufe rot) oder ⚠️ (stufe gelb)."""
        if gut:
            self.ok(was, detail)
        elif stufe == "gelb":
            self.warn(was, detail)
        else:
            self.fehler(was, detail, fix=fix)

    def fehler(self, was, detail, fix=None):
        self.rot += 1
        self.zeilen.append(f"❌ **{was}** {detail}" + (" → mit `--fix` reparierbar" if fix else ""))
        if fix:
            self.fixbar.append(fix)


def pruefen(master, args):
    b = Bericht()
    info = probe(master)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dauer = float(info["format"]["duration"])

    # ---- Format ----
    fmt_ok = video["width"] == 1080 and video["height"] == 1920 and video["r_frame_rate"] == "30/1" and video["codec_name"] == "h264"
    b.pruef(fmt_ok, "Format", f"{video['codec_name']} {video['width']}×{video['height']} @ {video['r_frame_rate']}")
    if audio is None:
        b.fehler("Ton", "keine Tonspur")
        return b, None
    abw = abs(float(audio.get("duration") or dauer) - float(video.get("duration") or dauer))
    # 1 cfr-Duplikat (33 ms) + AAC-Polster sind normal
    b.pruef(abw < 0.1, "Ton-/Bildlänge", f"Abweichung {abw * 1000:.0f} ms", stufe="gelb")

    # ---- Farbe: HDR-Reste färben die Haut rot ----
    trc, prim = video.get("color_transfer", "unknown"), video.get("color_primaries", "unknown")
    if trc in ("arib-std-b67", "smpte2084") or prim == "bt2020":
        b.fehler("Farbtags", f"HDR-Rest im Stream (transfer {trc}, primaries {prim}), Haut wird rot", fix="farbtags")
    elif trc != "bt709" or prim != "bt709":
        b.fehler("Farbtags", f"nicht als bt709 getaggt (transfer {trc}, primaries {prim}), Plattformen raten dann die Farben", fix="farbtags")
    else:
        b.ok("Farbtags", "bt709")

    # ---- Takt ----
    pts = lauf(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "packet=pts_time", "-of", "csv=p=0", master], check=True)
    t = np.sort(np.array([float(z.split(",")[0]) for z in pts.stdout.split() if z]))
    luecken = np.where(np.abs(np.diff(t) - 1 / FPS) > 0.0005)[0]
    if abs(t[0]) > 0.001:
        b.fehler("Takt", f"Bild startet bei {t[0]:.3f} s statt 0, Ton liegt daneben")
    elif len(luecken):
        b.fehler("Takt", f"{len(luecken)} unregelmäßige Frame-Abstände, erste bei {t[luecken[0]]:.3f} s")
    else:
        b.ok("Takt", f"{len(t)} Frames, alle 33,3 ms")

    # ---- Ton: Lautheit, Spitzen, Löcher ----
    lufs, tp = lautheit(master)
    if not (LUFS_MIN <= lufs <= LUFS_MAX):
        b.fehler("Lautheit", f"{lufs:.1f} LUFS (Soll −15 bis −13)", fix="ton")
    else:
        b.ok("Lautheit", f"{lufs:.1f} LUFS")
    b.pruef(tp <= TP_MAX, "Spitzen", f"{tp:.1f} dBTP (Soll ≤ −1)", fix="ton")
    loch = [(a, e) for a, e in loecher(master) if 0.1 < a < dauer - 0.1]
    if loch:
        b.fehler("Tonlöcher", ", ".join(f"{a:.2f} s ({(e - a) * 1000:.0f} ms)" for a, e in loch[:5]))
    else:
        b.ok("Tonlöcher", "keine")

    # ---- Bild: falsche Frames, Einfrierungen, Schnittkanten (Take-Bereich, Grafik-Zone ausgenommen) ----
    x0, y0, w0, h0 = TAKE_CROP
    f = frames_lesen(master, f"crop={w0}:{h0}:{x0}:{y0}", *KLEIN)
    n = len(f)
    d1 = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))  # d1[i] = Frame i → i+1
    blitzer = []
    for k in (1, 2):  # ein oder zwei fremde Frames zwischen zwei passenden
        for i in range(1, n - k):
            rein, raus = d1[i - 1], d1[i + k - 1]
            if rein > SCHNITT and raus > SCHNITT and np.abs(f[i - 1] - f[i + k]).mean() < 0.4 * min(rein, raus):
                blitzer.append((i, k))
    if blitzer:
        b.fehler("Falsche Frames", "; ".join(f"{k} Frame(s) bei {zeit(i)}" for i, k in blitzer[:6]))
    else:
        b.ok("Falsche Frames", "keine Blitzer an Schnittkanten")

    # Vollbild-Passagen (Grafik ohne Sprecher) zählen nicht als Take: dort sind stehende Frames gewollt
    voll = np.zeros(n, dtype=bool)
    bereiche, quelle, zoom_ende = vollbild_bereiche(master, args.vollbild, args.reel_ts, args.version)
    for a, e in bereiche:
        voll[max(0, a - VOLL_RAND):min(n, e + VOLL_RAND)] = True
    if quelle:
        b.zeilen.append(f"ℹ️ **Vollbild** {int(voll.sum())} Frames in {len(bereiche)} Passagen aus `{quelle}` bei Einfrieren, "
                        "Standbild und Grading ausgelassen (Grafik ohne Sprecher)"
                        + (f", Hook-Zoom bis {zeit(zoom_ende)} beim Grading" if zoom_ende else ""))
    # Hook-Zoom: Bildausschnitt wandert, Einfrieren bleibt geprüft, nur das Grading nicht
    ohne_grading = voll.copy()
    ohne_grading[:min(n, zoom_ende + VOLL_RAND)] = True

    f54 = f.reshape(n, 35, 2, 54, 2).mean(axis=(2, 4))
    dk = np.abs(np.diff(f54, axis=0)).mean(axis=(1, 2))
    # letzter Frame = bekanntes cfr-Duplikat; Blitzer-Frames sind schon gemeldet und zählen hier nicht doppelt
    schon = {i + j for i, k in blitzer for j in range(k + 1)}
    stand = [i + 1 for i in range(len(dk) - 1) if dk[i] < FREEZE and i + 1 not in schon and not voll[i + 1]]
    laeufe = []
    for a in stand:
        if laeufe and a == laeufe[-1][1] + 1:
            laeufe[-1][1] = a
        else:
            laeufe.append([a, a])
    # Kurze Läufe = Decoder-Fehler (typisch bei HEVC-Quellen) → rot.
    # Lange Läufe sind oft gewollt (ruhender Bildschirm, Standbild-Effekt) → gelb, selbst ansehen.
    kurz = [l for l in laeufe if l[1] - l[0] + 1 <= STANDBILD_AB]
    lang = [l for l in laeufe if l[1] - l[0] + 1 > STANDBILD_AB]
    if kurz:
        b.fehler("Eingefroren", f"{sum(e - a + 1 for a, e in kurz)} Frames in {len(kurz)} kurzen Läufen, erster {zeit(kurz[0][0])}")
    else:
        b.ok("Eingefroren", "keine kurz stehenden Frames")
    if lang:
        b.warn("Standbild", "; ".join(f"{e - a + 1} Frames ab {zeit(a)}" for a, e in lang[:4]) + ", gewollt oder eingefroren? selbst ansehen")

    schnitte = [i + 1 for i in range(len(d1)) if d1[i] > SCHNITT and not any(i + 1 in range(s, s + k + 1) for s, k in blitzer)]
    # Kanten, die näher als 10 Frames liegen, zählen als eine (Gestik, Untertitel-Wechsel)
    kanten = [s for j, s in enumerate(schnitte) if j == 0 or s - schnitte[j - 1] > 10]

    # ---- Grading: stille Bildteile (Hintergrund) statt Gesamtbild ----
    # Untertitel und Armbewegungen lösen am ganzen Take-Bereich falsche „Sprünge“ aus. Still = die 30 % Blöcke
    # mit der kleinsten zeitlichen Streuung, Overlays fallen damit von selbst raus.
    bl = f.reshape(n, 7, 10, 12, 9).mean(axis=(2, 4)).reshape(n, -1)
    still = bl.std(axis=0) <= np.quantile(bl.std(axis=0), 0.3)
    sig = bl[:, still].mean(axis=1)
    w = 8
    stufe = np.array([sig[i:i + w].mean() - sig[i - w:i].mean() if w <= i < n - w and not ohne_grading[i - w:i + w].any() else 0.0
                      for i in range(n)])
    spitzen = [i for i in range(n) if abs(stufe[i]) > HELL_SPRUNG and abs(stufe[i]) == np.abs(stufe[max(0, i - 6):i + 7]).max()]
    if spitzen:
        b.warn("Grading zwischen Takes", "; ".join(f"{stufe[i]:+.0f} Luma bei {zeit(i)}" for i in spitzen[:6]))
    else:
        b.ok("Grading zwischen Takes", f"keine Helligkeitsstufe (größte {np.abs(stufe).max():.1f})")
    sync = sync_messen(master, args.take, args.gesicht) if args.take else None
    if args.take:
        tf = frames_lesen(args.take, f"crop={w0}:{h0}:{x0}:{y0}", *KLEIN)
        L = min(n, len(tf))
        tbl = tf[:L].reshape(L, 7, 10, 12, 9).mean(axis=(2, 4)).reshape(L, -1)
        dl = float((bl[:L, still] - tbl[:, still]).mean())
        dc = farbabstand(master, args.take)
        yt = float(frames_lesen(args.take, "null", 54, 96).mean())
        # Das Licht hat der Nutzer in licht.py gewählt. Die Zahl ist ein Hinweis, kein Befund.
        hinweis = "" if YAVG_MIN <= yt <= YAVG_MAX else f", außerhalb {YAVG_MIN} bis {YAVG_MAX}: mit der Wahl aus licht.py abgleichen"
        b.zeilen.append(f"ℹ️ **Helligkeit Take** YAVG {yt:.0f} (Richtwert um 118{hinweis})")
        if sync and not sync[1]:
            # Take liegt gezoomt und verschoben im Master, der Hof über dem Kopf dunkelt die Wand ab:
            # Luma ist dann nicht vergleichbar. Die Chroma im unteren Streifen bleibt vergleichbar.
            b.pruef(dc <= MASTER_ZU_TAKE, "Farbe Master = Take",
                    f"Farbabstand {dc:.1f} (Soll ≤ {MASTER_ZU_TAKE:.0f}, sonst Farbstich), Luma {dl:+.1f} nicht vergleichbar, "
                    "weil der Take gezoomt im Bild liegt", stufe="gelb")
        else:
            b.pruef(abs(dl) <= MASTER_ZU_TAKE and dc <= MASTER_ZU_TAKE, "Farbe Master = Take",
                    f"Luma {dl:+.1f}, Farbabstand {dc:.1f} in den stillen Bildteilen (Soll ≤ {MASTER_ZU_TAKE:.0f}, sonst Farbstich)", stufe="gelb")
    else:
        b.zeilen.append(f"ℹ️ **Helligkeit** Master-YAVG {float(frames_lesen(master, 'null', 54, 96).mean()):.0f}, ohne `--take` kein Grading-Vergleich")

    # ---- Gleiche Lautstärke: Sprachpegel je 5 s gegen den Median ----
    x = ton_samples(master)
    pegel = [(a, min(a + 150, n), sprachpegel(x, a / FPS, min(a + 150, n) / FPS)) for a in range(0, n, 150)]
    pegel = [(a, e, p) for a, e, p in pegel if p is not None and e - a >= 60]
    if pegel:
        mitte = float(np.median([p for _, _, p in pegel]))
        aus = [(a, e, p - mitte) for a, e, p in pegel if abs(p - mitte) > PEGEL_SPRUNG]
        if aus:
            b.warn("Lautstärke gleichmäßig", "; ".join(f"{d:+.1f} dB bei {a / FPS:.0f}–{e / FPS:.0f} s" for a, e, d in aus[:6]))
        else:
            b.ok("Lautstärke gleichmäßig", f"{len(pegel)} Abschnitte à 5 s innerhalb ±{PEGEL_SPRUNG:.0f} dB")

    # ---- Sync gegen den Take ----
    if sync:
        best, klar = sync
        if not klar:
            # Kein klares Minimum: der Take liegt gezoomt und verschoben im Master (Zoom, Augenhöhe), Bildvergleich geht nicht.
            # Den Ton-Sync sichern bauen.sh (Ton am Stück, Takt-Prüfung) und naht_check.py.
            b.zeilen.append(f"ℹ️ **Sync** per Bild nicht messbar, Take liegt gezoomt im Master (bester Versatz {best:+d}). "
                            "Bei ungezoomtem Take Gesicht per `--gesicht` setzen")
        else:
            b.pruef(best == 0, "Sync", f"bester Versatz {best:+d} Frames (Soll 0)")

    # ---- Body gegen abgenommene Referenz ----
    if args.referenz:
        r = lauf(["ffmpeg", "-nostats", "-i", master, "-i", args.referenz, "-filter_complex",
                  f"[0:v]trim=start_frame={args.ab_frame},setpts=PTS-STARTPTS[a];[1:v]trim=start_frame={args.ab_frame},setpts=PTS-STARTPTS[b];[a][b]psnr",
                  "-f", "null", "-"])
        mt = re.search(r"average:([\d.]+|inf)", r.stderr)
        psnr = float("inf") if mt and mt.group(1) == "inf" else float(mt.group(1)) if mt else 0.0
        b.pruef(psnr >= PSNR_MIN, "Body gegen Referenz", f"{psnr:.1f} dB ab Frame {args.ab_frame} (Soll ≥ 40)")

    # ---- Kontaktbogen: 8 Stellen + bis zu 4 Kanten, Claude sieht ihn selbst an ----
    stellen = sorted(set([int(n * q) for q in (0, 0.04, 0.12, 0.25, 0.4, 0.55, 0.7, 0.88)] + kanten[:4]))[:12]
    bogen = str(Path(master).with_name(Path(master).stem + "-abnahme.jpg"))
    sel = "+".join(f"eq(n\\,{s})" for s in stellen)
    lauf(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", f"select='{sel}',scale=270:-1,tile=6x2", "-frames:v", "1", bogen])
    b.zeilen.append(f"🖼️ Kontaktbogen `{bogen}` (Frames {', '.join(map(str, stellen))}): Plakat ab y 300, Untertitel nicht im Gesicht, kein Text am Rand selbst prüfen")
    return b, bogen


def reparieren(master, was):
    """Nur Technik: Farbtags setzen und/oder Ton auf −14 LUFS mit Spitzen ≤ −1 dBTP. Bild wird kopiert, nie neu kodiert.

    Ton: feste Verstärkung statt loudnorm (loudnorm hebt die Spitzen wieder an), danach ein
    vierfach überabgetasteter Limiter, der echte Spitzen fängt. AAC legt beim Kodieren noch etwas drauf,
    deshalb nachmessen und bei Bedarf 0,5 dB tiefer begrenzen (höchstens drei Runden).
    """
    ziel = Path(master)
    sicher = ziel.with_name(ziel.stem + "-vor-fix.mp4")  # neben dem Master, nicht in $TMPDIR
    shutil.copy2(master, sicher)
    tmp = ziel.with_name(ziel.stem + ".fix.mp4")
    lufs, _ = lautheit(str(sicher))
    grenze = -2.0
    for _ in range(3):
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(sicher), "-map", "0:v", "-map", "0:a", "-c:v", "copy"]
        if "farbtags" in was:
            cmd += ["-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0"]
        if "ton" in was:
            cmd += ["-af", f"volume={-14 - lufs:.2f}dB,aresample=192000,alimiter=limit={10 ** (grenze / 20):.4f}:level=false:latency=true,aresample=48000",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
        else:
            cmd += ["-c:a", "copy"]
        try:
            subprocess.run(cmd + ["-movflags", "+faststart", str(tmp)], check=True)
        except subprocess.CalledProcessError:
            tmp.unlink(missing_ok=True)
            raise
        if "ton" not in was or lautheit(str(tmp))[1] <= TP_MAX:
            break
        grenze -= 0.5
    shutil.move(str(tmp), master)
    return sicher


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("master")
    p.add_argument("--take")
    p.add_argument("--referenz")
    p.add_argument("--ab-frame", type=int, default=0)
    p.add_argument("--gesicht", default="420,920,240,240")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--vollbild", help="Vollbild-Passagen als Master-Frames 'a-b,c-d' (sonst aus reel.ts gelesen)")
    p.add_argument("--reel-ts", help="Pfad zu reel.ts (Standard: <projekt>/remotion/src/reel.ts)")
    p.add_argument("--version", help="Version, falls nicht im Dateinamen (v1, v2 ...)")
    args = p.parse_args()

    b, _ = pruefen(args.master, args)
    if args.fix and b.fixbar:
        sicher = reparieren(args.master, set(b.fixbar))
        print(f"== Technik repariert ({', '.join(sorted(set(b.fixbar)))}), Original gesichert: {sicher}")
        b, _ = pruefen(args.master, args)

    ampel = "🔴 ROT, nicht freigeben" if b.rot else "🟡 GELB, Befunde melden" if b.gelb else "🟢 GRÜN"
    text = f"# Abnahme `{Path(args.master).name}`: {ampel}\n\n" + "\n".join(f"- {z}" for z in b.zeilen) + "\n"
    Path(args.master).with_name(Path(args.master).stem + "-abnahme.md").write_text(text)
    print(text)
    sys.exit(1 if b.rot else 2 if b.gelb else 0)


if __name__ == "__main__":
    main()
