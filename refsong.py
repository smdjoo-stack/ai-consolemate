"""기준 노래 분석 — '이 노래처럼' 들리게 하려면 무엇을 바꿀지 제안하기 위한 숫자들.

- 음악 파일(MP3·WAV·FLAC·OGG)을 받아 소리 균형(1/3 옥타브), 강약(크기 변화 폭·피크), 스테레오 폭을 잽니다.
- '보통 음원'의 평균적인 소리 균형과 비교해서 이 노래의 특징을 쉬운 말로 설명합니다.
- 실제 콘솔 조절 제안은 AI(대화창)가 이 결과와 지금 콘솔 상태를 함께 보고 합니다 (바꾸기 전에 미리보기).
유튜브에서 내려받은 파일 대신, 가지고 있는 음원·MR·우리 예배 녹음을 쓰세요.
"""

import io
import math

MAX_SECONDS = 600
# 1/3 옥타브 중심 주파수
CENTERS = [31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500,
           3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]
# 보통 음원(팝·CCM 믹스)의 평균적인 기울기 — 핑크 노이즈 기준 dB (대략값)
TYPICAL = {31.5: -4, 40: -2, 50: -1, 63: 0, 2000: 0, 4000: -2, 8000: -4.5, 12500: -7.5, 16000: -10}
GROUPS = [("저음 바닥", 30, 60, "킥·베이스의 깊은 울림"), ("베이스", 60, 250, "베이스·킥의 몸통"),
          ("먹먹한 대역", 250, 500, "많으면 답답하고 뭉침"), ("중음", 500, 2000, "악기·목소리의 몸통"),
          ("또렷함", 2000, 5000, "가사·말이 들리는 곳"), ("밝음", 5000, 10000, "심벌·치찰음·선명함"),
          ("공기감", 10000, 16500, "반짝임·숨소리")]


def _typical(fc):
    pts = sorted(TYPICAL.items())
    if fc <= pts[0][0]:
        return pts[0][1]
    for (f1, v1), (f2, v2) in zip(pts, pts[1:]):
        if f1 <= fc <= f2:
            t = math.log(fc / f1) / math.log(f2 / f1)
            return v1 + t * (v2 - v1)
    return pts[-1][1]


def _read(data, name):
    import numpy as np
    import soundfile as sf
    try:
        with sf.SoundFile(io.BytesIO(data)) as f:
            sr = f.samplerate
            frames = min(f.frames if f.frames > 0 else sr * MAX_SECONDS, sr * MAX_SECONDS)
            x = f.read(frames, dtype="float32", always_2d=True)
    except Exception as e:
        raise ValueError(f"음악 파일을 읽지 못했습니다 ({type(e).__name__}). MP3·WAV·FLAC·OGG 파일을 써 주세요. "
                         "(m4a·aac 는 아직 안 돼요)")
    return x, sr


def analyze(data: bytes, name: str = ""):
    x, sr = _read(data, name)
    return analyze_array(x, sr, name)


# ---------------------------------------------------------------- PC에서 나오는 소리 듣기 (유튜브·음원 앱)
class Listener:
    """PC 스피커로 나가는 소리를 그대로 받아(루프백) 분석합니다. 파일로 저장하지 않습니다."""

    def __init__(self):
        import threading
        self.lock = threading.Lock()
        self.job = {"state": "idle"}

    def status(self):
        return dict(self.job)

    def start(self, seconds, name, on_done, open_url=None):
        import threading
        with self.lock:
            if self.job.get("state") in ("waiting", "recording"):
                raise ValueError("이미 듣는 중이에요. 끝난 뒤 다시 해 주세요.")
            self.job = {"state": "waiting", "step": "재생을 기다리는 중… 노래를 재생해 주세요 (30초 안에)", "name": name}
        if open_url:
            import webbrowser
            webbrowser.open(open_url)
        threading.Thread(target=self._run, args=(int(seconds), name, on_done), daemon=True).start()

    def _run(self, seconds, name, on_done):
        import time
        import warnings
        import numpy as np
        try:
            warnings.filterwarnings("ignore")
            import soundcard as sc
            spk = sc.default_speaker()
            mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
            sr = 48000
            chunks, got, waited = [], 0, 0.0
            with mic.recorder(samplerate=sr, channels=2, blocksize=4800) as rec:
                while True:                                   # 소리가 나기 시작할 때까지 (최대 30초)
                    blk = rec.record(numframes=sr // 2)
                    if np.max(np.abs(blk)) > 0.003:
                        chunks.append(blk)
                        got = len(blk)
                        break
                    waited += 0.5
                    if waited >= 30:
                        raise ValueError(f"30초 동안 PC에서 소리가 나지 않았어요. 노래를 재생했는지, PC 소리가 꺼져 있지 않은지 "
                                         f"(출력 장치: {spk.name}) 확인해 주세요.")
                self.job.update(state="recording", step=f"듣는 중… 0/{seconds}초", started=time.time())
                while got < sr * seconds:
                    blk = rec.record(numframes=sr // 2)
                    chunks.append(blk)
                    got += len(blk)
                    self.job["step"] = f"듣는 중… {got // sr}/{seconds}초 (다른 소리는 잠시 꺼 주세요)"
            self.job.update(state="analyzing", step="분석하는 중…")
            x = np.concatenate(chunks).astype("float32")
            r = analyze_array(x, sr, name)
            r["source"] = f"PC 소리 {seconds}초 듣기 ({spk.name})"
            on_done(r)
            self.job = {"state": "done", "step": "완료", "name": name}
        except ValueError as e:
            self.job = {"state": "error", "error": str(e)}
        except ImportError:
            self.job = {"state": "error", "error": "PC 소리 듣기 부품(soundcard)이 없습니다. 프로그램을 다시 켜면 자동으로 설치됩니다."}
        except Exception as e:
            self.job = {"state": "error", "error": f"PC 소리를 받지 못했어요: {e}"}


LISTENER = Listener()


def analyze_array(x, sr, name=""):
    import numpy as np
    if len(x) < sr * 5:
        raise ValueError("5초보다 짧아서 분석하기 어려워요.")
    mono = x.mean(axis=1).astype(np.float64)
    dur = len(mono) / sr

    # ---- 소리 균형 (평균 스펙트럼)
    n = 8192
    win = np.hanning(n)
    hop = n // 2
    starts = range(0, len(mono) - n, hop)
    psd = np.zeros(n // 2 + 1)
    cnt = 0
    for s in starts:
        seg = mono[s:s + n]
        if np.max(np.abs(seg)) < 1e-4:
            continue
        psd += np.abs(np.fft.rfft(seg * win)) ** 2
        cnt += 1
    if cnt == 0:
        raise ValueError("소리가 거의 없는 파일입니다.")
    psd /= cnt
    freqs = np.fft.rfftfreq(n, 1 / sr)
    bands = []
    for fc in CENTERS:
        lo, hi = fc / 2 ** (1 / 6), fc * 2 ** (1 / 6)
        if hi > sr / 2:
            break
        p = psd[(freqs >= lo) & (freqs < hi)].sum()
        bands.append([fc, 10 * math.log10(p + 1e-20)])
    ref = np.median([db for fc, db in bands if 100 <= fc <= 5000])
    out_bands = []
    for fc, db in bands:
        rel = db - ref                       # 핑크 노이즈(옥타브마다 같은 에너지) 기준
        out_bands.append({"hz": fc, "db": round(rel, 1), "vsTypical": round(rel - _typical(fc), 1)})

    groups = []
    for label, lo, hi, what in GROUPS:
        vals = [b["vsTypical"] for b in out_bands if lo <= b["hz"] < hi]
        if not vals:
            continue
        v = round(sum(vals) / len(vals), 1)
        word = "많음" if v >= 3 else "조금 많음" if v >= 1.5 else "적음" if v <= -3 else "조금 적음" if v <= -1.5 else "보통"
        groups.append({"name": label, "range": f"{lo}~{hi if hi < 16000 else '16k'} Hz", "what": what, "db": v, "word": word})

    # ---- 강약 (400 ms 단위 크기)
    w, h = int(sr * 0.4), int(sr * 0.1)
    rms = []
    for s in range(0, len(mono) - w, h):
        r = math.sqrt(float(np.mean(mono[s:s + w] ** 2)) + 1e-20)
        rms.append(20 * math.log10(r))
    rms = np.array(rms)
    loud = rms[rms > rms.max() - 40] if len(rms) else rms
    lra = float(np.percentile(loud, 95) - np.percentile(loud, 10)) if len(loud) else 0.0
    overall = 10 * math.log10(float(np.mean(mono ** 2)) + 1e-20)
    peak = 20 * math.log10(float(np.max(np.abs(x))) + 1e-20)
    crest = peak - overall
    dyn_word = "아주 고르게 눌러 놓음 (컴프·리미터 강함)" if lra < 5 else "고른 편 (적당한 컴프)" if lra < 9 else \
               "자연스러운 강약" if lra < 14 else "강약이 큼 (거의 안 누름)"

    # ---- 스테레오 폭
    if x.shape[1] >= 2:
        l, r = x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)
        mid, side = (l + r) / 2, (l - r) / 2
        width = 10 * math.log10((float(np.mean(side ** 2)) + 1e-20) / (float(np.mean(mid ** 2)) + 1e-20))
        width_word = "거의 모노" if width < -20 else "좁은 편" if width < -12 else "보통" if width < -6 else "넓음"
    else:
        width, width_word = None, "모노 파일"

    res = {"name": name, "seconds": round(dur), "sampleRate": sr, "bands": out_bands, "groups": groups,
           "dynamics": {"range_db": round(lra, 1), "crest_db": round(crest, 1), "level_dbfs": round(overall, 1),
                        "peak_dbfs": round(peak, 1), "word": dyn_word},
           "stereo": {"side_db": None if width is None else round(width, 1), "word": width_word}}
    res["summary"] = summary_text(res)
    res["hints"] = quick_hints(res)
    return res


def summary_text(r):
    g = {x["name"]: x for x in r["groups"]}
    feats = [f"{x['name']}({x['range']}) {x['word']} {x['db']:+.1f} dB" for x in r["groups"] if x["word"] != "보통"]
    d = r["dynamics"]
    return (f"기준 노래 '{r['name']}' ({r['seconds'] // 60}분 {r['seconds'] % 60}초) 분석 — 보통 음원과 비교한 소리 균형: "
            + (", ".join(feats) if feats else "전체적으로 보통 음원과 비슷한 균형")
            + f". 강약: 크기 변화 폭 {d['range_db']} dB, 피크 여유 {d['crest_db']} dB → {d['word']}."
            + f" 스테레오: {r['stereo']['word']}.")


def quick_hints(r):
    """AI 없이도 보여 줄 간단한 방향 (콘솔은 바꾸지 않음)."""
    g = {x["name"]: x["db"] for x in r["groups"]}
    out = []
    if g.get("또렷함", 0) >= 1.5:
        out.append("가사가 또렷한 노래예요 → 보컬 채널에서 ‘말이 잘 안 들려요’를 한두 번 (2.5~3.5 kHz 조금 올림)")
    if g.get("먹먹한 대역", 0) <= -1.5:
        out.append("먹먹한 대역이 깔끔하게 정리돼 있어요 → 보컬·기타·건반에서 ‘먹먹해요’ 한 번 (300~500 Hz 조금 깎기)")
    if g.get("베이스", 0) >= 1.5 or g.get("저음 바닥", 0) >= 1.5:
        out.append("저음이 든든해요 → 베이스·킥 페이더를 조금 올리거나 톤 프리셋 ‘베이스’·‘킥’으로 몸통 살리기")
    if g.get("베이스", 0) <= -1.5:
        out.append("저음이 가벼운 편이에요 → 베이스·킥은 지금보다 조금 작게, 다른 악기에 로우컷을 확실히")
    if g.get("밝음", 0) >= 1.5 or g.get("공기감", 0) >= 1.5:
        out.append("밝고 반짝이는 소리예요 → 오버헤드·어쿠스틱 기타의 고음(10 kHz 이상)을 조금 살리기")
    if g.get("밝음", 0) <= -1.5:
        out.append("고음이 부드러운 편이에요 → 치찰음·심벌이 튀지 않게 ‘쏘아요’ 다듬기")
    d = r["dynamics"]["range_db"]
    if d < 9:
        out.append("크기가 고른 노래예요 → 보컬 컴프 도우미 ‘찬양 보컬’ 적용 (필요하면 ‘들쭉날쭉해요’)")
    elif d >= 14:
        out.append("강약이 큰 노래예요 → 컴프는 ‘살짝만 고르게’로 자연스럽게")
    if not out:
        out.append("특별히 치우친 곳이 없는 균형 잡힌 노래예요 → 악기별 톤 프리셋부터 맞추고 보컬이 잘 들리게 페이더 균형을 맞추세요")
    return out


def ai_prompt(r):
    return (r["summary"] + "\n\n이 노래처럼 들리도록 우리 콘솔에서 무엇을 바꾸면 좋을지 제안해 줘. "
            "먼저 지금 채널(악기·보컬)과 메인 상태를 확인하고, 보컬·악기별로 할 일을 우선순위대로 3~6가지만 쉬운 말로 알려 줘. "
            "녹음실 음원과 예배당은 다르니 하울링 위험이 없는 작은 변화(±3 dB 이내) 위주로. "
            "아직 콘솔은 바꾸지 말고, 바꿀 때는 목소리 EQ·톤 프리셋·컴프 도우미의 미리보기로 바뀔 내용을 먼저 보여 줘.")
