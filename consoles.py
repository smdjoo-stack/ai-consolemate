"""여러 기종의 콘솔을 한 가지 방식으로 찾고 여는 곳.

- WING / WING Compact / WING Rack  → wing_osc.WingClient  + WingTools
- X32 / X32 Compact / Producer / Rack / Core, Midas M32 → x32_osc.X32Client + X32Tools

화면·AI·예배 순서는 WING 방식 주소로 말하고, X32Client 가 X32 주소로 바꿔 줍니다.
"""

import wing_osc
import x32_osc
from wing_osc import WingClient
from x32_osc import X32Client
from wing_tools import WingTools, ToolError

FAMILY_LABEL = {"wing": "Behringer WING 계열", "x32": "Behringer X32 / Midas M32 계열"}


def model_label(info):
    raw = (info or {}).get("model", "")
    fam = (info or {}).get("family", "wing")
    if fam == "wing":
        return {"wing-fullsize": "WING", "wing-compact": "WING Compact", "wing-rack": "WING Rack"}.get(
            raw, raw.replace("-", " ").upper() if raw else "WING")
    return raw or "X32"


def discover(timeout=1.5):
    """WING 과 X32/M32 를 함께 찾음. 실제 콘솔을 연습용(127.0.0.1)보다 앞에."""
    found = [dict(f, family="wing") for f in wing_osc.discover(timeout=timeout)]
    seen = {f["ip"] for f in found}
    found += [f for f in x32_osc.discover(timeout=min(timeout, 1.0)) if f["ip"] not in seen]
    for f in found:
        f["label"] = model_label(f)
    return sorted(found, key=lambda f: f["ip"].startswith("127."))


def detect(ip):
    """IP 만 알 때 기종 알아내기. WING 이 먼저, 아니면 X32. 모르면 None."""
    try:
        c = WingClient(ip, timeout=0.7)
        try:
            c.get("/ch/1/name")
            return {"ip": ip, "family": "wing", "model": "", "name": ""}
        finally:
            c.close()
    except (TimeoutError, OSError):
        pass
    return x32_osc.probe(ip)


class X32Tools(WingTools):
    """X32/M32: 채널 32, 버스 16, 메인 = LR(1)·MONO(2), 매트릭스 6, DCA 8.
    입력·출력 단자 바꾸기와 이펙트 랙은 아직 지원하지 않습니다(콘솔에서 직접)."""
    LIMITS = {"ch": 32, "aux": 8, "bus": 16, "main": 2, "mtx": 6, "dca": 8}
    family = "x32"
    model_label = "X32"
    NOT_YET = "X32/M32에서는 ‘{}’ 기능을 이 프로그램에서 아직 쓸 수 없습니다. 콘솔의 {} 화면에서 직접 해 주세요."

    def _name(self, kind, index):
        n = super()._name(kind, index)
        if not n and kind == "main":
            return {1: "MAIN LR", 2: ""}.get(int(index), "")
        return n

    def output_routing(self, max_age=10.0):
        return {"by_source": {}, "other": [], "nodes": {}, "raw": {}}

    def input_catalog(self):
        raise ToolError(self.NOT_YET.format("입력 단자 바꾸기", "ROUTING"))

    def outputs_in_group(self, grp):
        raise ToolError(self.NOT_YET.format("출력 단자 보기·바꾸기", "ROUTING"))

    def set_channel_input(self, *a, **k):
        raise ToolError(self.NOT_YET.format("입력 단자 바꾸기", "ROUTING"))

    def set_output_routing(self, *a, **k):
        raise ToolError(self.NOT_YET.format("출력 단자 바꾸기", "ROUTING"))

    def undo_routing(self):
        raise ToolError("되돌릴 라우팅 변경이 없습니다.")

    def get_routing(self):
        rows = []
        for ch in self._used_channels():
            src = self._source(ch)
            rows.append({"채널": ch, "이름": self._name("ch", ch),
                         "입력": f"{self.GRP_KO.get(src[0], src[0])} {src[1]}번" if src else "없음"})
        return {"채널_입력": rows, "안내": "X32/M32에서는 출력 단자 연결은 이 프로그램에서 볼 수 없습니다. 콘솔 ROUTING 화면을 보세요."}

    def list_effects(self):
        raise ToolError(self.NOT_YET.format("이펙트 보기·조절", "EFFECTS"))

    def effect_detail(self, slot):
        raise ToolError(self.NOT_YET.format("이펙트 보기·조절", "EFFECTS"))

    def set_effect_param(self, *a, **k):
        raise ToolError(self.NOT_YET.format("이펙트 조절", "EFFECTS"))

    def set_effect_mix(self, *a, **k):
        raise ToolError(self.NOT_YET.format("이펙트 조절", "EFFECTS"))

    def _param_spec(self, ch, key):
        if key in ("hc", "hcf", "postins_on") or (key.startswith("eq_") and key[3:4] in ("l", "h")):
            raise ToolError("X32/M32에는 이 설정이 없거나 다른 곳에 있습니다. (EQ는 1~4번 밴드, 로우컷은 HPF)")
        return super()._param_spec(ch, key)


def open_console(ip, family=None):
    """(tools) — family 를 모르면 알아내서 엽니다. 못 찾으면 WING 으로 가정."""
    if family is None:
        info = detect(ip)
        family = info["family"] if info else "wing"
    if family == "x32":
        return X32Tools(X32Client(ip))
    return WingTools(WingClient(ip))


def probe_client(tools, timeout=1.0):
    """상태 점검용 별도 연결 (같은 기종)."""
    return type(tools.w)(tools.w.host, timeout=timeout)


def console_note(tools):
    """AI에게 알려 줄 '지금 연결된 콘솔' 정보."""
    if tools is None:
        return ""
    if tools.family == "x32":
        return ("<console>지금 연결된 콘솔: Behringer X32 / Midas M32 계열.\n"
                "- 도구의 번호 체계는 그대로 쓰되 범위가 다릅니다: 채널 1~32, AUX 입력 1~8, 버스 1~16, "
                "메인 1 = MAIN LR(스테레오), 메인 2 = MONO/CENTER, 매트릭스 1~6, DCA 1~8.\n"
                "- 채널 → MAIN LR 은 켜기/끄기만 있고 크기는 채널 페이더입니다. 채널 → MONO 는 따로 크기가 있습니다.\n"
                "- 게인은 X32 headamp(로컬·AES50 A/B), EQ는 1~4번 밴드(로우/하이 셸빙 밴드 없음), 로우컷은 HPF(20~400 Hz)입니다.\n"
                "- 입력·출력 단자 바꾸기와 이펙트 랙 조절은 이 프로그램에서 아직 안 됩니다. 콘솔에서 하는 방법을 안내하세요.\n"
                "- 콘솔 사용법 안내는 X32 설명서 자료가 있으면 그것을 따르세요.</console>")
    return ""
