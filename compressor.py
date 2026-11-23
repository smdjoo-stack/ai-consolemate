"""컴프(컴프레서) 도우미 — 용도별 시작값과 '들어 보니…' 다듬기.

컴프 = 큰 소리는 살짝 누르고 작은 소리는 올려서 크기를 고르게 하는 장치.
- 문턱(Threshold): 이보다 큰 소리부터 누름 (낮을수록 많이 누름)
- 비율(Ratio): 얼마나 세게 누를지 (2:1 살짝, 4:1 보통, 10:1 이상 = 리미터처럼)
- 어택(Attack): 누르기 시작하는 빠르기 (느리면 톡 쏘는 첫소리가 살아남)
- 릴리즈(Release): 다시 놓아주는 빠르기 (너무 빠르면 출렁, 너무 느리면 계속 눌림)
- 니(Knee): 부드럽게 누르기 시작하는 정도 (클수록 자연스러움)
- 보충 게인(Make-up): 누른 만큼 전체를 다시 올림
- 섞는 양(Mix): 100% = 다 눌린 소리, 줄이면 원래 소리를 섞어 자연스럽게(병렬 컴프)
WING 기본 COMP 일 때 세부값을 바꿉니다. 76LA 같은 빈티지 모델은 화면의 '세부값'에서 직접 조절하세요.
"""

PRESETS = {
    "speech":  {"label": "말씀·설교·기도", "thr": -24, "ratio": 3.0, "att": 15, "rel": 150, "knee": 3, "gain": 2.0,
                "why": "말소리 크기를 고르게 해서 작은 목소리도 잘 들리게. 자연스럽게 3:1"},
    "vocal":   {"label": "찬양 보컬", "thr": -20, "ratio": 4.0, "att": 10, "rel": 120, "knee": 3, "gain": 3.0,
                "why": "노래의 큰 소리·작은 소리 차이를 줄여 반주 위에 또렷이 들리게"},
    "gentle":  {"label": "살짝만 고르게 (자연스럽게)", "thr": -18, "ratio": 2.0, "att": 20, "rel": 200, "knee": 5, "gain": 1.0,
                "why": "거의 티 안 나게 튀는 부분만 살짝"},
    "choir":   {"label": "성가대·그룹 마이크", "thr": -22, "ratio": 2.5, "att": 20, "rel": 200, "knee": 5, "gain": 1.0,
                "why": "여러 사람 소리를 부드럽게 묶음"},
    "agtr":    {"label": "어쿠스틱 기타", "thr": -18, "ratio": 3.0, "att": 15, "rel": 150, "knee": 3, "gain": 1.0,
                "why": "스트로크의 튀는 소리를 고르게, 첫소리는 살림"},
    "bass":    {"label": "베이스", "thr": -20, "ratio": 4.0, "att": 20, "rel": 200, "knee": 3, "gain": 2.0,
                "why": "음마다 크기가 들쭉날쭉한 것을 고르게 받쳐 줌"},
    "kick":    {"label": "킥·드럼", "thr": -18, "ratio": 4.0, "att": 10, "rel": 120, "knee": 2, "gain": 2.0,
                "why": "때리는 첫소리(어택)는 살리고 울림은 정리"},
    "limit":   {"label": "갑자기 큰 소리 막기 (리미터처럼)", "thr": -8, "ratio": 10.0, "att": 3, "rel": 80, "knee": 2, "gain": 0.0,
                "why": "평소엔 거의 안 건드리고, 갑자기 소리 지르거나 마이크를 칠 때만 세게 막음"},
}

# 들어 보니… (문턱·비율·게인·어택·릴리즈 변화)
TWEAKS = {
    "uneven":  {"label": "크기가 들쭉날쭉해요", "thr": -3, "say": "더 고르게: 문턱을 3 dB 낮춰 더 일찍 누르게 했어요"},
    "squashed": {"label": "눌려서 답답해요", "thr": 3, "ratio": -1, "say": "덜 누르게: 문턱을 3 dB 올리고 비율을 한 단계 낮췄어요"},
    "quiet":   {"label": "작아졌어요", "gain": 1.0, "say": "보충 게인을 1 dB 올렸어요"},
    "pumping": {"label": "출렁거려요 (숨 쉬듯)", "rel": 1.5, "say": "릴리즈를 1.5배 느리게 해서 출렁임을 줄였어요"},
    "dull":    {"label": "첫소리가 죽었어요 (톡 쏘는 맛 없음)", "att": 5, "say": "어택을 5 ms 느리게 해서 첫소리를 살렸어요"},
    "peaks":   {"label": "갑자기 튀는 소리가 커요", "att": -5, "ratio": 1, "say": "어택을 5 ms 빠르게, 비율을 한 단계 올렸어요"},
}
RATIO_STEPS = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 20.0]


def options():
    return {"presets": {k: {"label": v["label"], "why": v["why"]} for k, v in PRESETS.items()},
            "tweaks": {k: v["label"] for k, v in TWEAKS.items()}}


def preset_items(key):
    p = PRESETS.get(key)
    if p is None:
        raise ValueError("목록에 있는 컴프 용도를 골라 주세요.")
    items = [("dyn_on", 1, "컴프 켜기"), ("dyn_thr", p["thr"], f"문턱 {p['thr']} dB"), ("dyn_ratio", p["ratio"], f"비율 {p['ratio']:g}:1"),
             ("dyn_att", p["att"], f"어택 {p['att']} ms"), ("dyn_rel", p["rel"], f"릴리즈 {p['rel']} ms"),
             ("dyn_knee", p["knee"], f"니 {p['knee']}"), ("dyn_gain", p["gain"], f"보충 게인 {p['gain']:+.1f} dB"),
             ("dyn_mix", 100, "섞는 양 100%")]
    return items, [f"{p['label']}: {p['why']}"]


def _need_comp(tools, ch):
    if tools.family == "wing":
        mdl = tools._txt(f"/ch/{ch}/dyn/mdl")
        if mdl not in (None, "", "COMP"):
            raise ValueError(f"이 채널의 컴프 종류가 {mdl}라 도우미 값을 쓸 수 없어요. 화면의 컴프 '세부값'에서 직접 조절하거나, "
                             f"콘솔에서 컴프 종류를 COMP로 바꾼 뒤 다시 해 주세요.")


def apply(tools, ch, key, preview=False):
    import tones
    ch = int(ch)
    _need_comp(tools, ch)
    items, why = preset_items(key)
    r = tones.apply_items(tools, ch, items, preview=preview)
    r.update(preset=f"컴프: {PRESETS[key]['label']}", why=why)
    return r


def tweak(tools, ch, kind):
    t = TWEAKS.get(kind)
    if t is None:
        raise ValueError("알 수 없는 다듬기입니다.")
    ch = int(ch)
    _need_comp(tools, ch)
    get = lambda k: tools._num_opt(tools._param_spec(ch, k)[0])
    before, done = {}, []
    if not get("dyn_on"):
        before["dyn_on"] = 0
        tools.set_channel_param(ch, "dyn_on", 1, confirmed=True)
        done.append("컴프 켜기")
    changes = []
    if "thr" in t:
        changes.append(("dyn_thr", lambda v: max(-50, min(0, v + t["thr"])), "문턱"))
    if "ratio" in t:
        def step(v, d=t["ratio"]):
            i = min(range(len(RATIO_STEPS)), key=lambda j: abs(RATIO_STEPS[j] - v))
            return RATIO_STEPS[max(0, min(len(RATIO_STEPS) - 1, i + d))]
        changes.append(("dyn_ratio", step, "비율"))
    if "gain" in t:
        changes.append(("dyn_gain", lambda v: min(8, v + t["gain"]), "보충 게인"))
    if "att" in t:
        changes.append(("dyn_att", lambda v: max(1, min(80, v + t["att"])), "어택"))
    if "rel" in t:
        changes.append(("dyn_rel", lambda v: max(20, min(1500, v * t["rel"])), "릴리즈"))
    for key, fn, name in changes:
        cur = get(key)
        if cur is None:
            continue
        new = round(fn(float(cur)), 1)
        before[key] = cur
        if abs(new - float(cur)) > 0.05:
            tools.set_channel_param(ch, key, new, confirmed=True)
            done.append(f"{name} {float(cur):g} → {new:g}")
    say = t["say"] + (" — " + ", ".join(done) if done else " — 이미 한계라 바뀐 것이 없어요")
    return {"channel": ch, "name": tools._name("ch", ch), "say": say, "undo": before}
