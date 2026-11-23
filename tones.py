"""톤 프리셋 — 악기별 시작 톤(로우컷·EQ·컴프), 우리 교회 톤 저장, 채널 톤 복사.

목소리(설교·보컬)는 voice_eq.py 의 '목소리 EQ 도우미'를 쓰고, 여기는 악기·그 밖의 소스용입니다.
- 악기 프리셋은 '시작점'이라 밴드당 ±4 dB 이내, 컴프는 부드럽게.
- 저장한 톤은 tones.json (교회별 정보 — 배포판·GitHub 에 넣지 않음).
- 적용 전 미리보기, 적용 후 되돌리기(목소리 EQ 와 같은 되돌리기 목록).
WING: 밴드 l·h = 쉘프, 1~4 = 피크. X32: 1~4번만. 컴프 값은 컴프 종류가 COMP(기본)일 때만 바꿈.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path

HERE = Path(__file__).parent

# 악기: 로우컷 Hz(None=끔), 밴드 1~4 (Hz, dB, Q), 하이 쉘프 (Hz, dB), 컴프 (문턱 dB, 비율, 어택 ms, 릴리즈 ms, 보충 dB) 또는 None
INSTRUMENTS = {
    "kick":     {"label": "킥 (베이스 드럼)", "icon": "🥁", "lc": 35,
                 "b": [(60, 3.0, 1.4), (350, -4.0, 1.4), (3500, 3.0, 2.0), (8000, -2.0, 1.0)], "h": (10000, 0.0),
                 "comp": (-18, 4.0, 10, 120, 2.0),
                 "why": "60 Hz 쿵 소리를 살리고, 350 Hz 박스 소리를 깎고, 3.5 kHz 비터(때리는) 소리를 보탬"},
    "snare":    {"label": "스네어", "icon": "🥁", "lc": 90,
                 "b": [(200, 2.0, 1.4), (500, -2.0, 2.0), (2500, 1.0, 1.5), (6000, 2.0, 1.0)], "h": (10000, 1.0),
                 "comp": (-16, 3.0, 5, 100, 1.0),
                 "why": "200 Hz 몸통을 살리고 500 Hz 깡통 소리를 깎고 6 kHz 스내피(촤르르)를 보탬"},
    "tom":      {"label": "탐", "icon": "🥁", "lc": 60,
                 "b": [(100, 2.0, 1.4), (400, -3.0, 1.4), (3000, 2.0, 1.5), (7000, -1.0, 1.0)], "h": (10000, 0.0),
                 "comp": (-16, 3.0, 10, 150, 1.0),
                 "why": "울림(100 Hz)과 어택(3 kHz)을 살리고 400 Hz 탁한 소리를 깎음"},
    "overhead": {"label": "오버헤드·하이햇 (심벌)", "icon": "🔔", "lc": 200,
                 "b": [(400, -2.0, 1.0), (1000, -1.0, 1.0), (5000, 1.0, 1.0), (9000, 1.0, 1.0)], "h": (12000, 1.5),
                 "comp": None,
                 "why": "심벌 아래쪽의 드럼 울림을 로우컷으로 정리하고 반짝임(10 kHz 이상)을 조금 보탬"},
    "bass":     {"label": "베이스 기타 (DI)", "icon": "🎸", "lc": 40,
                 "b": [(80, 2.0, 1.0), (250, -2.0, 1.4), (800, 1.0, 1.4), (2500, 1.5, 1.4)], "h": (6000, -2.0),
                 "comp": (-20, 4.0, 20, 200, 2.0),
                 "why": "80 Hz 바닥을 받치고 250 Hz 뭉침을 깎고 줄 소리(800 Hz~2.5 kHz)로 음이 들리게 함. 컴프로 크기를 고르게"},
    "egtr":     {"label": "일렉 기타 (앰프 마이크)", "icon": "🎸", "lc": 90,
                 "b": [(200, -1.5, 1.0), (500, -1.0, 1.4), (2500, 1.5, 1.4), (5000, -1.0, 1.4)], "h": (9000, -2.0),
                 "comp": None,
                 "why": "보컬 자리를 비켜 주도록 저음을 정리하고 2.5 kHz로 선명하게, 너무 높은 지글거림은 줄임"},
    "agtr":     {"label": "어쿠스틱 기타", "icon": "🎸", "lc": 90,
                 "b": [(200, -2.5, 1.0), (800, -1.0, 1.4), (3000, 1.5, 1.4), (6000, 1.0, 1.0)], "h": (12000, 2.0),
                 "comp": (-18, 3.0, 15, 150, 1.0),
                 "why": "통 울림(200 Hz)으로 붕붕거리는 것을 깎고 줄 튕기는 소리와 반짝임을 보탬"},
    "keys":     {"label": "피아노·건반", "icon": "🎹", "lc": 50,
                 "b": [(250, -1.5, 1.0), (600, -1.0, 1.4), (3000, 1.0, 1.4), (8000, 0.5, 1.0)], "h": (12000, 1.0),
                 "comp": None,
                 "why": "저음은 남기고 250~600 Hz 탁함만 조금 정리, 또렷함과 공기감을 살짝"},
    "pad":      {"label": "신디 패드·오르간", "icon": "🎹", "lc": 80,
                 "b": [(250, -2.0, 1.0), (500, -1.5, 1.4), (2500, -1.0, 1.0), (8000, 0.0, 1.0)], "h": (12000, 0.5),
                 "comp": None,
                 "why": "배경을 채우는 소리라 보컬과 겹치는 대역(250 Hz~2.5 kHz)을 조금 비켜 줌"},
    "choir":    {"label": "성가대·찬양팀 그룹 마이크", "icon": "👥", "lc": 120,
                 "b": [(250, -2.0, 1.0), (500, -1.5, 1.4), (3000, 2.0, 1.0), (7000, -1.0, 2.0)], "h": (12000, 2.0),
                 "comp": None,
                 "why": "멀리서 받는 마이크라 무대 울림·저음을 정리하고 가사가 들리도록 또렷함을 보탬"},
    "playback": {"label": "MR·반주·영상 소리", "icon": "🎬", "lc": 30,
                 "b": [(200, 0.0, 1.0), (500, 0.0, 1.0), (3000, 0.0, 1.0), (8000, 0.0, 1.0)], "h": (12000, 0.0),
                 "comp": None,
                 "why": "이미 다듬어진 소리라 거의 손대지 않고 아주 낮은 잡음만 정리"},
    "flat":     {"label": "평평하게 (초기화)", "icon": "↺", "lc": None,
                 "b": [(200, 0.0, 1.0), (500, 0.0, 1.0), (3000, 0.0, 1.0), (8000, 0.0, 1.0)], "h": (12000, 0.0),
                 "comp": "off",
                 "why": "EQ를 모두 0 dB로, 로우컷과 컴프를 끔. 처음부터 다시 잡고 싶을 때"},
}

# 저장·복사할 때 담는 항목
CAPTURE_KEYS = ["lc", "lcf", "eq_on"] + [f"eq_{b}{p}" for b in "l1234h" for p in "gfq"] + \
               ["dyn_on", "dyn_thr", "dyn_ratio", "dyn_gain", "dyn_att", "dyn_rel"]
LABELS = {"lc": "로우컷 켜기", "lcf": "로우컷 주파수", "eq_on": "EQ 켜기", "dyn_on": "컴프 켜기", "dyn_thr": "컴프 문턱",
          "dyn_ratio": "컴프 비율", "dyn_gain": "컴프 보충 게인", "dyn_att": "컴프 어택", "dyn_rel": "컴프 릴리즈"}
BAND_KO = {"l": "로우", "1": "1번", "2": "2번", "3": "3번", "4": "4번", "h": "하이"}


def _label(key, val):
    if key in LABELS:
        return LABELS[key]
    b, p = key[3], key[4]
    return f"EQ {BAND_KO[b]} " + {"g": "게인", "f": "주파수", "q": "폭(Q)"}[p]


def _fmt_hz(f):
    return f"{round(f / 1000, 1)}k" if f >= 1000 else f"{round(f)}"


# ---------------------------------------------------------------- 저장소
class ToneStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.tones = []
        self._read()

    def path(self):
        return Path(os.environ.get("CONSOLEMATE_TONES") or (HERE / "tones.json"))

    def _read(self):
        try:
            self.tones = json.loads(self.path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.tones = []

    def _write(self):
        p = self.path()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.tones, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)

    def find(self, key):
        key = str(key or "").strip()
        return next((t for t in self.tones if t["id"] == key or t["name"] == key), None)

    def save(self, name, values, source):
        name = str(name or "").strip()[:30]
        if not name:
            raise ValueError("톤 이름을 입력해 주세요.")
        with self.lock:
            t = self.find(name)
            if t is None:
                t = {"id": uuid.uuid4().hex[:8], "name": name}
                self.tones.append(t)
            t.update(values=values, source=source, saved=time.strftime("%Y-%m-%d %H:%M"))
            self._write()
            return t

    def delete(self, key):
        with self.lock:
            t = self.find(key)
            if t is None:
                raise ValueError("없는 톤입니다.")
            self.tones.remove(t)
            self._write()

    def replace_all(self, tones):
        with self.lock:
            self.tones = [t for t in tones if isinstance(t, dict) and t.get("name") and isinstance(t.get("values"), dict)]
            self._write()


STORE = ToneStore()


def options():
    return {"instruments": {k: {"label": v["label"], "icon": v["icon"], "why": v["why"]} for k, v in INSTRUMENTS.items()},
            "saved": [{"id": t["id"], "name": t["name"], "source": t.get("source", ""), "saved": t.get("saved", "")} for t in STORE.tones]}


# ---------------------------------------------------------------- 만들기
def instrument_items(key):
    p = INSTRUMENTS.get(key)
    if p is None:
        raise ValueError("목록에 있는 악기를 골라 주세요.")
    items = []
    if p["lc"] is None:
        items.append(("lc", 0, "로우컷 끄기"))
    else:
        items += [("lc", 1, "로우컷 켜기"), ("lcf", p["lc"], f"로우컷 {p['lc']} Hz")]
    items += [("eq_on", 1, "EQ 켜기"), ("eq_lg", 0.0, "로우 쉘프 0 dB")]
    for i, (f, g, q) in enumerate(p["b"], start=1):
        items += [(f"eq_{i}f", f, None), (f"eq_{i}q", q, None), (f"eq_{i}g", g, f"{i}번 {_fmt_hz(f)} Hz {g:+.1f} dB")]
    hf, hg = p["h"]
    items += [("eq_hf", hf, None), ("eq_hg", hg, f"하이 쉘프 {_fmt_hz(hf)} Hz {hg:+.1f} dB")]
    c = p["comp"]
    if c == "off":
        items.append(("dyn_on", 0, "컴프 끄기"))
    elif c:
        thr, ratio, att, rel, gain = c
        items += [("dyn_on", 1, "컴프 켜기"), ("dyn_thr", thr, f"컴프 문턱 {thr} dB"), ("dyn_ratio", ratio, f"컴프 비율 {ratio:g}:1"),
                  ("dyn_att", att, None), ("dyn_rel", rel, None), ("dyn_gain", gain, f"컴프 보충 {gain:+.1f} dB")]
    return items, [f"{p['label']}: {p['why']}"]


def capture(tools, ch):
    """채널의 지금 톤(로우컷·EQ·컴프)을 값 사전으로."""
    vals = {}
    for key in CAPTURE_KEYS:
        try:
            addr = tools._param_spec(ch, key)[0]
        except Exception:
            continue
        v = tools._num_opt(addr)
        if v is not None:
            vals[key] = round(float(v), 2)
    if tools.family == "wing":
        vals["_eq_mdl"] = tools._txt(f"/ch/{ch}/eq/mdl") or ""
        vals["_dyn_mdl"] = tools._txt(f"/ch/{ch}/dyn/mdl") or ""
    return vals


BOOL_KO = {"lc": "로우컷", "eq_on": "EQ", "dyn_on": "컴프"}


def saved_items(values):
    items = []
    for key in CAPTURE_KEYS:
        if key in values:
            v = values[key]
            label = f"{BOOL_KO[key]} {'켜기' if v else '끄기'}" if key in BOOL_KO else f"{_label(key, v)} {v:g}"
            items.append((key, v, label))
    return items


def apply_items(tools, ch, items, preview=False):
    """설정 목록 적용(또는 미리보기). EQ 종류가 STD 가 아니거나 컴프 종류가 COMP 가 아니면 그 부분은 건너뜀."""
    ch = int(ch)
    notes = []
    if tools.family == "x32":
        items = [it for it in items if not it[0].startswith(("eq_l", "eq_h"))]
    else:
        eq_mdl = tools._txt(f"/ch/{ch}/eq/mdl")
        if eq_mdl not in (None, "", "STD"):
            items = [it for it in items if not it[0].startswith("eq_")]
            notes.append(f"이 채널의 EQ 종류({eq_mdl})는 바꾸지 않고 그대로 뒀어요 (STD EQ에서만 적용).")
        dyn_mdl = tools._txt(f"/ch/{ch}/dyn/mdl")
        if dyn_mdl not in (None, "", "COMP"):
            items = [it for it in items if not it[0].startswith("dyn_") or it[0] == "dyn_on"]
            if any(it[0].startswith("dyn_") for it in items):
                notes.append(f"컴프 종류가 {dyn_mdl}라 켜기/끄기만 바꾸고 세부값은 그대로 뒀어요.")
    before, changes = {}, []
    for key, val, label in items:
        addr = tools._param_spec(ch, key)[0]
        cur = tools._num_opt(addr)
        before[key] = cur
        if label and (cur is None or abs(float(cur) - float(val)) > 0.05):
            changes.append({"key": key, "label": label, "from": None if cur is None else round(float(cur), 1), "to": val})
    if not preview:
        for key, val, _ in items:
            tools.set_channel_param(ch, key, val, confirmed=True)
    return {"channel": ch, "name": tools._name("ch", ch), "changes": changes, "notes": notes, "undo": before}
