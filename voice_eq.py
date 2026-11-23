"""목소리 EQ 프리셋 — 성별·나이·마이크 종류·용도에 맞는 '시작점' EQ.

음향을 잘 몰라도 고르기만 하면 무난한 출발점을 잡아 주고,
들어 보고 '먹먹해요 / 또렷하게 / 쏘아요 …' 버튼으로 조금씩 다듬습니다.

원칙
- 깎는 것 위주, 올리는 것은 작게 (한 밴드 최대 ±4 dB). 하울링·과장 방지.
- 로우컷으로 목소리 아래의 웅웅거림(무대 울림, 핸들링 노이즈)을 먼저 정리.
- 남성 기본음 약 85~180 Hz, 여성 약 165~255 Hz, 어린이 약 250~400 Hz → 로우컷 위치가 다름.
- 200~500 Hz = 두툼함/먹먹함, 2.5~4 kHz = 또렷함(말이 들리는 곳), 5~8 kHz = 치찰음(ㅅ·ㅊ), 10 kHz~ = 공기감.
- 나이가 들수록 목소리의 고음 에너지가 줄고 숨소리·떨림이 늘어 또렷함(2.5~3 kHz)을 조금 더 보탬.
WING: 밴드 l·h = 쉘프, 1~4 = 피크. X32: 1~4번만 씀.
"""

GENDERS = {"male": "남성", "female": "여성", "child": "어린이"}
AGES = {"young": "청년 (20~30대)", "middle": "장년 (40~50대)", "senior": "어르신 (60대 이상)"}
MICS = {"handheld": "핸드 마이크", "lapel": "핀 마이크 (옷깃)", "headset": "헤드셋 마이크", "stand": "강대상·스탠드 마이크"}
USES = {"speech": "말씀·설교·기도", "sing": "찬양 (노래)"}

# 기본 프리셋: 로우컷 Hz, 밴드 1~4 (주파수 Hz, 게인 dB, Q), 하이 쉘프 (Hz, dB)
BASE = {
    ("male", "young"):    {"lc": 90,  "b": [(180, -1.5, 1.0), (380, -1.5, 1.4), (3000, 2.0, 1.0), (6500, -1.0, 2.0)], "h": (10000, 1.0)},
    ("male", "middle"):   {"lc": 100, "b": [(200, -2.0, 1.0), (420, -2.0, 1.4), (3000, 2.0, 1.0), (6500, -1.0, 2.0)], "h": (10000, 1.0)},
    ("male", "senior"):   {"lc": 110, "b": [(200, -1.0, 1.0), (450, -2.0, 1.4), (2500, 3.0, 1.0), (5000, 1.0, 1.5)], "h": (10000, 1.5)},
    ("female", "young"):  {"lc": 140, "b": [(250, -1.0, 1.0), (500, -1.5, 1.4), (3500, 1.5, 1.0), (7500, -2.0, 2.0)], "h": (12000, 1.0)},
    ("female", "middle"): {"lc": 130, "b": [(250, -1.5, 1.0), (500, -2.0, 1.4), (3000, 2.0, 1.0), (7000, -1.5, 2.0)], "h": (12000, 1.0)},
    ("female", "senior"): {"lc": 130, "b": [(300, -1.0, 1.0), (600, -1.5, 1.4), (2500, 3.0, 1.0), (5000, 1.5, 1.5)], "h": (11000, 1.5)},
    ("child", "young"):   {"lc": 160, "b": [(300, -1.0, 1.0), (800, -1.5, 1.4), (3500, 1.0, 1.0), (7000, -2.0, 2.0)], "h": (12000, 0.5)},
}
for _a in ("middle", "senior"):
    BASE[("child", _a)] = BASE[("child", "young")]

# 마이크 종류별 보정 (로우컷 +Hz, 밴드별 게인 더하기, 설명)
MIC_ADJ = {
    "handheld": {"lc": 10, "g": [-1.0, 0, 0, 0], "why": "입에 가까워 저음이 부풀어(근접 효과) 200 Hz 부근을 조금 더 깎음"},
    "lapel":    {"lc": 20, "g": [0, -1.5, 1.0, 0], "f2": 750, "why": "가슴 울림(700~800 Hz)을 깎고, 입에서 멀어 줄어든 또렷함을 보탬"},
    "headset":  {"lc": 10, "g": [0, 0, 0, -1.0], "why": "입 옆이라 숨소리·치찰음이 잘 들어와 7 kHz 부근을 조금 깎음"},
    "stand":    {"lc": 0,  "g": [0, 0, 0.5, 0], "why": "입과 거리가 바뀌기 쉬워 또렷함을 조금 보탬"},
}
# 용도별 보정
USE_ADJ = {
    "speech": {"lc": 0,   "g": [0, 0, 0, 0],    "h": 0.0, "why": "말이 잘 들리도록 또렷함 위주"},
    "sing":   {"lc": -20, "g": [0.5, 0, -0.5, 0], "h": 0.5, "why": "노래는 따뜻함·공기감을 남기고 또렷함은 덜 올림"},
}

LIMIT = 4.0     # 프리셋이 만드는 밴드 게인 한계 (±)


def _clip(v, lim=LIMIT):
    return max(-lim, min(lim, round(v, 1)))


def options():
    return {"genders": GENDERS, "ages": AGES, "mics": MICS, "uses": USES, "tweaks": {k: v["label"] for k, v in TWEAKS.items()}}


def build(gender, age, mic="handheld", use="speech"):
    """→ (설정 목록[(키, 값, 설명)], 설명 문장 목록)"""
    if gender not in GENDERS or age not in AGES or mic not in MICS or use not in USES:
        raise ValueError("성별·나이·마이크·용도를 목록에서 골라 주세요.")
    base = BASE[(gender, age)]
    m, u = MIC_ADJ[mic], USE_ADJ[use]
    lc = max(60, base["lc"] + m["lc"] + u["lc"])
    items = [("lc", 1, "로우컷 켜기"), ("lcf", lc, f"로우컷 {lc} Hz"), ("eq_on", 1, "EQ 켜기"),
             ("eq_lg", 0.0, "로우 쉘프 0 dB (로우컷이 대신함)")]
    names = ["두툼함", "먹먹함", "또렷함", "치찰음"]
    for i, (f, g, q) in enumerate(base["b"], start=1):
        if i == 2 and m.get("f2"):
            f = m["f2"]
        g = _clip(g + m["g"][i - 1] + u["g"][i - 1])
        items += [(f"eq_{i}f", f, None), (f"eq_{i}q", q, None),
                  (f"eq_{i}g", g, f"{names[i - 1]} {f if f < 1000 else str(f / 1000).rstrip('0').rstrip('.') + 'k'} Hz {g:+.1f} dB")]
    hf, hg = base["h"]
    hg = _clip(hg + u["h"])
    items += [("eq_hf", hf, None), ("eq_hg", hg, f"공기감 {hf // 1000}k Hz 이상 {hg:+.1f} dB")]
    why = [f"{GENDERS[gender]} {AGES[age].split(' ')[0]}: 기본음 아래를 로우컷 {lc} Hz로 정리하고, 먹먹한 대역은 깎고 또렷한 대역은 조금 올림",
           f"{MICS[mic]}: {m['why']}", f"{USES[use]}: {u['why']}"]
    return items, why


# 들어 보고 다듬기: (밴드 키, 더할 dB) 목록 + 로우컷 변화
TWEAKS = {
    "muddy":   {"label": "먹먹해요 (답답하게 뭉침)", "eq": [("2", -1.5)], "lc": 0, "say": "먹먹함(약 300~500 Hz)을 1.5 dB 더 깎았어요"},
    "clear":   {"label": "말이 잘 안 들려요 (또렷하게)", "eq": [("3", 1.5)], "lc": 0, "say": "또렷함(약 2.5~3.5 kHz)을 1.5 dB 올렸어요"},
    "harsh":   {"label": "쏘아요 · ㅅ 소리가 따가워요", "eq": [("4", -1.5)], "lc": 0, "say": "치찰음(약 5~8 kHz)을 1.5 dB 깎았어요"},
    "thin":    {"label": "얇아요 (따뜻하게)", "eq": [("1", 1.5)], "lc": -20, "say": "두툼함(약 200 Hz)을 1.5 dB 올리고 로우컷을 20 Hz 낮췄어요"},
    "boomy":   {"label": "웅웅거려요 (저음이 많아요)", "eq": [("1", -1.5)], "lc": 20, "say": "로우컷을 20 Hz 올리고 저음(약 200 Hz)을 1.5 dB 깎았어요"},
    "dull":    {"label": "어두워요 (밝게)", "eq": [("h", 1.0)], "lc": 0, "say": "공기감(10 kHz 이상)을 1 dB 올렸어요"},
    "nasal":   {"label": "코맹맹이 소리 같아요", "eq": [("2", -1.0)], "lc": 0, "f2": 1000, "say": "콧소리(약 1 kHz)를 1 dB 깎았어요"},
}
TWEAK_LIMIT = 6.0


def apply(tools, ch, gender, age, mic="handheld", use="speech", preview=False):
    """프리셋 적용 (또는 미리보기). 되돌리기용 이전 값을 함께 돌려줌."""
    ch = int(ch)
    items, why = build(gender, age, mic, use)
    if tools.family == "x32":
        items = [it for it in items if not it[0].startswith(("eq_l", "eq_h"))]
    mdl = tools._txt(f"/ch/{ch}/eq/mdl")
    if tools.family == "wing" and mdl not in (None, "", "STD"):
        raise ValueError(f"이 채널의 EQ 종류가 {mdl}이라 목소리 프리셋을 쓸 수 없어요. 콘솔에서 EQ 종류를 STD로 바꾼 뒤 다시 해 주세요.")
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
    return {"channel": ch, "name": tools._name("ch", ch), "changes": changes, "why": why, "undo": before,
            "preset": f"{GENDERS[gender]} · {AGES[age]} · {MICS[mic]} · {USES[use]}"}


def tweak(tools, ch, kind):
    t = TWEAKS.get(kind)
    if t is None:
        raise ValueError("알 수 없는 다듬기입니다.")
    ch = int(ch)
    before, done = {}, []
    for band, delta in t["eq"]:
        if tools.family == "x32" and band in ("l", "h"):
            band, delta = "4", delta     # X32는 4번 밴드로 대신
        key = f"eq_{band}g"
        addr = tools._param_spec(ch, key)[0]
        cur = float(tools._num_opt(addr) or 0.0)
        new = max(-TWEAK_LIMIT, min(TWEAK_LIMIT, round(cur + delta, 1)))
        before[key] = cur
        if abs(new - cur) < 0.05:
            done.append(f"{key} 는 이미 한계(±{TWEAK_LIMIT:g} dB)예요")
            continue
        tools.set_channel_param(ch, key, new, confirmed=True)
        f = tools._num_opt(tools._param_spec(ch, f"eq_{band}f")[0])
        where = "" if f is None else f" ({round(f / 1000, 1)}k Hz)" if f >= 1000 else f" ({round(f)} Hz)"
        done.append(f"{band}번 밴드{where} {cur:+.1f} → {new:+.1f} dB")
    if t.get("f2"):
        addr = tools._param_spec(ch, "eq_2f")[0]
        before["eq_2f"] = tools._num_opt(addr)
        tools.set_channel_param(ch, "eq_2f", t["f2"], confirmed=True)
    if t["lc"]:
        addr = tools._param_spec(ch, "lcf")[0]
        cur = float(tools._num_opt(addr) or 100)
        before["lcf"] = cur
        tools.set_channel_param(ch, "lcf", max(40, min(300, cur + t["lc"])), confirmed=True)
    say = t["say"] + (" — " + ", ".join(done) if done else "")
    return {"channel": ch, "name": tools._name("ch", ch), "say": say, "detail": done, "undo": before}


def restore(tools, ch, before):
    for key, val in (before or {}).items():
        if val is not None:
            tools.set_channel_param(int(ch), key, val, confirmed=True)
    return {"ok": True}
