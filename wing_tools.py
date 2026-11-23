"""AI 가 사용할 수 있는 WING 조작 도구들 (정의 + 실행)."""

import json

from wing_osc import WingClient, number_of, text_of

LIMITS = {"ch": 40, "aux": 8, "bus": 16, "main": 4, "mtx": 8, "dca": 16}
KIND_KO = {"ch": "채널", "aux": "AUX", "bus": "버스", "main": "메인", "mtx": "매트릭스", "dca": "DCA"}
MAX_RAISE_DB = 10.0  # 한 번에 이보다 크게 올리려면 사용자 확인 필요

KIND_ENUM = list(LIMITS.keys())

TOOLS = [
    {
        "name": "list_strips",
        "description": "채널/버스 등의 목록과 이름, 페이더(dB), 뮤트 상태를 봅니다. "
                       "어떤 채널이 어떤 악기인지, 어떤 버스가 어떤 모니터인지 알아낼 때 먼저 사용하세요. "
                       "이름이 비어 있고 페이더가 -144 인 항목은 생략됩니다.",
        "input_schema": {
            "type": "object",
            "properties": {"kind": {"type": "string", "enum": KIND_ENUM, "description": "ch=입력 채널, bus=버스(모니터 믹스 등), main=메인, dca, aux, mtx"}},
            "required": ["kind"],
        },
    },
    {
        "name": "get_monitor_mix",
        "description": "특정 버스(모니터 스피커/인이어 믹스)에 어떤 채널이 얼마나 보내지고 있는지 봅니다.",
        "input_schema": {
            "type": "object",
            "properties": {"bus": {"type": "integer", "minimum": 1, "maximum": 16}},
            "required": ["bus"],
        },
    },
    {
        "name": "set_send",
        "description": "입력 채널 소리를 버스(모니터)로 보내는 양을 설정합니다. "
                       "모니터에 어떤 악기 소리가 나오게 하려면 on=true 와 level_db 를 함께 설정하세요. "
                       "level_db 는 -144(소리 없음)~+10 dB, 0 dB 가 기준(유니티)입니다. 처음 넣을 때는 -10 dB 정도에서 시작하는 것이 안전합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "bus": {"type": "integer", "minimum": 1, "maximum": 16},
                "on": {"type": "boolean", "description": "센드 켜기/끄기 (바꾸지 않으려면 생략)"},
                "level_db": {"type": "number", "description": "센드 레벨 dB (바꾸지 않으려면 생략)"},
                "confirmed": {"type": "boolean", "description": "사용자가 큰 변경을 확인했으면 true"},
            },
            "required": ["channel", "bus"],
        },
    },
    {
        "name": "get_channel_detail",
        "description": "한 입력 채널의 자세한 설정을 봅니다: 입력 연결(스테이지박스 번호), 프리앰프 게인, +48V, TRIM, 로우컷·하이컷, "
                       "게이트, 6밴드 EQ(로우·1~4·하이: 게인/주파수/Q), 컴프(문턱·비율·보충게인), 인서트 이펙트. "
                       "콘솔 HOME 화면 내용을 설명하거나 소리를 다듬기 전에 먼저 사용하세요.",
        "input_schema": {"type": "object", "properties": {"channel": {"type": "integer", "minimum": 1, "maximum": 40}}, "required": ["channel"]},
    },
    {
        "name": "voice_eq_preset",
        "description": "마이크 채널에 목소리 EQ 프리셋(시작점)을 적용합니다. 성별·나이·마이크 종류·용도에 맞춰 로우컷과 EQ를 한 번에 맞춥니다. "
                       "사용자가 '목사님 핀마이크를 60대 남성에 맞춰 줘', '여성 찬양 보컬 EQ 잡아 줘'처럼 말하면 쓰세요. "
                       "모르는 항목(나이·마이크 종류 등)은 짐작하지 말고 물어보거나, 말씀 목적이면 use=speech로 하세요. "
                       "preview_only=true 로 먼저 바뀔 내용을 보여 줄 수 있습니다. 적용 뒤에는 실제로 들어 보고 voice_eq_tweak 으로 다듬으라고 안내하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "gender": {"type": "string", "enum": ["male", "female", "child"]},
                "age": {"type": "string", "enum": ["young", "middle", "senior"], "description": "young=20~30대, middle=40~50대, senior=60대 이상 (어린이는 young)"},
                "mic": {"type": "string", "enum": ["handheld", "lapel", "headset", "stand"], "description": "핸드, 핀(옷깃), 헤드셋, 강대상·스탠드"},
                "use": {"type": "string", "enum": ["speech", "sing"], "description": "speech=말씀·설교·기도, sing=찬양"},
                "preview_only": {"type": "boolean"},
            },
            "required": ["channel", "gender", "age"],
        },
    },
    {
        "name": "tone_preset",
        "description": "채널에 톤 프리셋(로우컷·EQ·컴프)을 적용합니다. 다음 중 하나를 지정하세요.\n"
                       "- preset: 악기 프리셋 kick, snare, tom, overhead, bass, egtr(일렉), agtr(어쿠스틱), keys(피아노·건반), pad(신디 패드·오르간), "
                       "choir(성가대·그룹 마이크), playback(MR·영상), flat(평평하게 초기화). 또는 우리 교회가 저장한 톤 이름\n"
                       "- from_channel: 그 채널의 지금 톤을 그대로 복사\n"
                       "목소리(설교·보컬)에는 voice_eq_preset 을 쓰세요. preview_only=true 로 먼저 바뀔 내용을 보여 줄 수 있고, "
                       "되돌리기는 voice_eq_tweak(undo=true).",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "preset": {"type": "string"},
                "from_channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "preview_only": {"type": "boolean"},
            },
            "required": ["channel"],
        },
    },
    {
        "name": "comp_preset",
        "description": "채널 컴프(크기를 고르게 하는 장치)를 용도별 시작값으로 맞춥니다. preset: speech(말씀·설교·기도), vocal(찬양 보컬), "
                       "gentle(살짝 자연스럽게), choir(성가대·그룹), agtr(어쿠스틱 기타), bass(베이스), kick(킥·드럼), limit(갑자기 큰 소리 막기). "
                       "컴프 종류가 COMP(기본)일 때만 됩니다. preview_only=true 로 먼저 보여 줄 수 있고, 되돌리기는 voice_eq_tweak(undo=true).",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "preset": {"type": "string", "enum": ["speech", "vocal", "gentle", "choir", "agtr", "bass", "kick", "limit"]},
                "preview_only": {"type": "boolean"},
            },
            "required": ["channel", "preset"],
        },
    },
    {
        "name": "comp_tweak",
        "description": "들어 본 느낌대로 컴프를 조금 다듬습니다. kind: uneven(크기가 들쭉날쭉 → 더 누름), squashed(눌려서 답답 → 덜 누름), "
                       "quiet(작아짐 → 보충 게인 +1), pumping(출렁거림 → 릴리즈 느리게), dull(첫소리가 죽음 → 어택 느리게), "
                       "peaks(갑자기 튀는 소리 → 어택 빠르게·비율 올림). 한 번에 하나씩, 들어 보고 반복하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "kind": {"type": "string", "enum": ["uneven", "squashed", "quiet", "pumping", "dull", "peaks"]},
            },
            "required": ["channel", "kind"],
        },
    },
    {
        "name": "set_dyn_raw",
        "description": "76LA 같은 빈티지 컴프 모델의 세부값을 바꿉니다(get_channel_detail 의 컴프 '세부값' 이름 그대로). "
                       "예: 76LA 의 in(높일수록 많이 누름), out(출력), att, rel. 작은 폭으로 바꾸세요.",
        "input_schema": {
            "type": "object",
            "properties": {"channel": {"type": "integer", "minimum": 1, "maximum": 40}, "param": {"type": "string"}, "value": {"type": "number"}},
            "required": ["channel", "param", "value"],
        },
    },
    {
        "name": "tone_save",
        "description": "채널의 지금 톤(로우컷·EQ·컴프)을 이름 붙여 '우리 교회 톤'으로 저장합니다. 같은 이름이면 덮어씁니다. "
                       "저장한 톤은 tone_preset 의 preset 에 이름으로 쓸 수 있습니다.",
        "input_schema": {
            "type": "object",
            "properties": {"channel": {"type": "integer", "minimum": 1, "maximum": 40}, "name": {"type": "string"}},
            "required": ["channel", "name"],
        },
    },
    {
        "name": "voice_eq_tweak",
        "description": "들어 본 느낌대로 목소리 EQ를 조금(1~1.5 dB) 다듬습니다. kind: "
                       "muddy=먹먹해요, clear=말이 잘 안 들려요(또렷하게), harsh=쏘아요·치찰음, thin=얇아요(따뜻하게), "
                       "boomy=웅웅거려요(저음 많음), dull=어두워요(밝게), nasal=코맹맹이. 한 번에 하나씩, 들어 보고 반복하세요. "
                       "undo=true 로 마지막 목소리 EQ 변경(프리셋 또는 다듬기)을 되돌립니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "kind": {"type": "string", "enum": ["muddy", "clear", "harsh", "thin", "boomy", "dull", "nasal"]},
                "undo": {"type": "boolean"},
            },
            "required": ["channel"],
        },
    },
    {
        "name": "set_channel_param",
        "description": "입력 채널의 설정 하나를 바꿉니다. param 종류:\n"
                       "- gain: 프리앰프 게인 dB(스테이지박스 입력). 3 dB 넘게 올리면 확인 필요\n"
                       "- phantom: +48V 켜기(1)/끄기(0). 항상 사용자 확인 후 confirmed=true. 바꾸기 전 채널 뮤트를 권하세요\n"
                       "- trim: -18~18 dB / invert: 위상 반전 0·1\n"
                       "- lc, hc: 로우컷/하이컷 켜기 0·1 / lcf, hcf: 주파수 Hz\n"
                       "- gate_on: 게이트 슬롯 켜기 0·1 (이 콘솔은 게이트 슬롯에 디에서 등 다른 처리기가 들어 있을 수 있음)\n"
                       "- eq_on: EQ 켜기 0·1 / eq_<밴드><g|f|q>: 밴드는 l(로우),1,2,3,4,h(하이). 예: eq_2g=-3 (2번 밴드 3 dB 깎기), eq_2f=400 (주파수), eq_2q=2. 6 dB 넘게 부스트하면 확인 필요\n"
                       "- dyn_on, dyn_thr(문턱 dB), dyn_ratio(비율), dyn_gain(보충 게인 dB), dyn_att(어택 ms), dyn_rel(릴리즈 ms): 컴프 종류가 COMP일 때\n"
                       "- preins_on, postins_on: 인서트 이펙트 켜기 0·1\n"
                       "하울링 대처는 EQ를 '깎는' 방향(음수 게인)으로, 작은 폭부터 하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "param": {"type": "string"},
                "value": {"type": "number"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["channel", "param", "value"],
        },
    },
    {
        "name": "get_routing",
        "description": "콘솔 ROUTING 정보를 봅니다: 각 채널이 어느 입력 단자(예: AES50 A 16번 = 스테이지박스 16번)에서 오는지, "
                       "각 버스·메인·매트릭스가 어느 출력 단자(스테이지박스 출력, 본체 출력, USB 등)로 나가는지, 녹음용 출력. "
                       "'모니터 소리가 어디로 나가?', '이 마이크는 몇 번에 꽂혀 있어?' 같은 질문에 사용.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_channel_input",
        "description": "채널의 입력 단자를 바꿉니다(ROUTING → CHANNELS). 예: 채널 1을 AES50 A 20번으로. group: A/B/C(AES50 스테이지박스), LCL(본체 입력), AUX, USB, SC, AES, CRD, MOD. "
                       "소리가 바로 바뀌거나 끊길 수 있으므로 먼저 confirmed 없이 호출해 바뀔 내용을 받고, 사용자에게 보여준 뒤 동의하면 confirmed=true 로 다시 호출하세요.",
        "input_schema": {
            "type": "object",
            "properties": {"channel": {"type": "integer", "minimum": 1, "maximum": 40}, "group": {"type": "string"},
                           "number": {"type": "integer", "minimum": 1}, "confirmed": {"type": "boolean"}},
            "required": ["channel", "group", "number"],
        },
    },
    {
        "name": "set_output_routing",
        "description": "출력 단자에 무엇을 내보낼지 바꿉니다(ROUTING → OUTPUTS). 예: 버스 8(MONITOR)을 AES50 A 3-4번으로(stereo=true면 두 칸 L/R). "
                       "source: bus, main, mtx, off(끄기). output_group: LCL, AUX, A, B, C, AES, SC, USB, CRD, MOD, REC. "
                       "그 단자에 원래 연결된 것은 덮어써집니다. 먼저 confirmed 없이 호출해 바뀔 내용을 받고, 사용자 동의 후 confirmed=true.",
        "input_schema": {
            "type": "object",
            "properties": {"output_group": {"type": "string"}, "output_number": {"type": "integer", "minimum": 1},
                           "source": {"type": "string", "enum": ["bus", "main", "mtx", "off"]},
                           "source_number": {"type": "integer", "minimum": 1}, "stereo": {"type": "boolean"},
                           "confirmed": {"type": "boolean"}},
            "required": ["output_group", "output_number", "source"],
        },
    },
    {
        "name": "undo_routing",
        "description": "가장 최근의 라우팅 변경(입력 또는 출력)을 이전 상태로 되돌립니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_effects",
        "description": "이펙트 랙(EFFECTS 화면) 16칸의 종류, 섞는 양(%), 어느 채널·버스에 인서트되어 있는지 봅니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_effect_param",
        "description": "이펙트 슬롯(1~16)의 세부 설정 하나를 바꿉니다. 예: 리버브 잔향 길이 dcy=2.0(초), 디에서 hi=25, 리미터 sqz=15. "
                       "설정 이름과 지금 값은 list_effects 결과의 '설정' 목록에서 확인하세요(이펙트 종류마다 다름). 조금씩 바꾸세요.",
        "input_schema": {
            "type": "object",
            "properties": {"slot": {"type": "integer", "minimum": 1, "maximum": 16}, "param": {"type": "string"}, "value": {"type": "number"}},
            "required": ["slot", "param", "value"],
        },
    },
    {
        "name": "set_effect_mix",
        "description": "이펙트 슬롯(1~16)의 섞는 양(원음 대비 효과음, 0~100%)을 바꿉니다. 리버브가 너무 많다/적다 같은 요청에 사용.",
        "input_schema": {
            "type": "object",
            "properties": {"slot": {"type": "integer", "minimum": 1, "maximum": 16}, "mix_percent": {"type": "number"}},
            "required": ["slot", "mix_percent"],
        },
    },
    {
        "name": "list_scenes",
        "description": "저장된 '예배 순서' 버튼(예: 찬양, 설교, 기도회) 목록과, 각 순서가 지금 콘솔 상태와 몇 군데 다른지 봅니다.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "save_scene",
        "description": "지금 콘솔 상태를 '예배 순서' 버튼으로 저장합니다(같은 이름이 있으면 덮어씀). 기본으로 채널 뮤트와 채널 페이더만 담습니다. "
                       "모니터 센드는 예배 중 맞춘 모니터를 덮어쓸 수 있어 사용자가 원할 때만 포함하세요. MAIN 뮤트는 담지 않습니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "예: 찬양, 설교, 기도회, 광고 영상"},
                "include_monitor_sends": {"type": "boolean"},
                "include_main_sends": {"type": "boolean", "description": "CENTER·YOUTUBE 등 메인 출력 센드 포함"},
                "include_bus_masters": {"type": "boolean", "description": "모니터(버스) 전체 볼륨·뮤트 포함"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "recall_scene",
        "description": "저장된 '예배 순서'로 콘솔을 전환합니다(페이더는 1초 동안 부드럽게). 사용자가 그 순서로 바꾸라고 분명히 요청했을 때만 쓰세요. "
                       "무엇이 바뀌는지만 보려면 preview_only=true.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "preview_only": {"type": "boolean"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_main_mix",
        "description": "메인 출력(main 1~4, 예: MAIN, CENTER, YOUTUBE)에 각 채널이 얼마나 들어가는지 봅니다. "
                       "채널마다 켜짐 여부, 채널 페이더, 메인 센드 레벨, 실제 크기(페이더+센드)를 돌려줍니다. "
                       "set_main_send 로 조절하기 전에 현재 값을 확인할 때 사용하세요.",
        "input_schema": {
            "type": "object",
            "properties": {"main": {"type": "integer", "minimum": 1, "maximum": 4}},
            "required": ["main"],
        },
    },
    {
        "name": "set_main_send",
        "description": "입력 채널을 메인 출력(main 2~4: 예: CENTER, YOUTUBE 방송)으로 보내는 양을 설정합니다. "
                       "실제 크기는 채널 페이더 + 이 값입니다. main 1(MAIN 예배당)의 크기는 채널 페이더(set_fader)로 조절하세요. "
                       "메인 번호와 이름은 list_strips(kind=main) 으로 확인하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "main": {"type": "integer", "minimum": 1, "maximum": 4},
                "on": {"type": "boolean", "description": "이 메인으로 보내기 켜기/끄기 (바꾸지 않으려면 생략)"},
                "level_db": {"type": "number", "description": "보내는 양 dB, -144~+10, 0 이 기준 (바꾸지 않으려면 생략)"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["channel", "main"],
        },
    },
    {
        "name": "set_fader",
        "description": "페이더를 지정한 dB 로 맞춥니다(-144~+10). 상대적으로 조금 올리고 내릴 때는 adjust_fader 를 쓰세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": KIND_ENUM},
                "index": {"type": "integer", "minimum": 1},
                "db": {"type": "number"},
                "confirmed": {"type": "boolean", "description": "사용자가 큰 변경을 확인했으면 true"},
            },
            "required": ["kind", "index", "db"],
        },
    },
    {
        "name": "adjust_fader",
        "description": "페이더를 현재 값에서 delta_db 만큼 올리거나 내립니다(예: +3, -2).",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": KIND_ENUM},
                "index": {"type": "integer", "minimum": 1},
                "delta_db": {"type": "number"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["kind", "index", "delta_db"],
        },
    },
    {
        "name": "set_mute",
        "description": "뮤트를 켜거나 끕니다. 메인(main) 뮤트는 예배 전체 소리가 끊기므로 반드시 사용자 확인 후 confirmed=true 로 호출하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": KIND_ENUM},
                "index": {"type": "integer", "minimum": 1},
                "muted": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["kind", "index", "muted"],
        },
    },
    {
        "name": "set_low_cut",
        "description": "입력 채널의 로우컷(HPF)을 켜고 주파수(Hz, 20~2000)를 설정합니다. 보컬·말소리의 웅웅거림, 무대 진동 소음, 저역 하울링에 사용합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "integer", "minimum": 1, "maximum": 40},
                "on": {"type": "boolean"},
                "freq_hz": {"type": "number"},
            },
            "required": ["channel", "on"],
        },
    },
]


class ToolError(Exception):
    pass


class NeedConfirm(ToolError):
    """큰 폭 증가 - 사용자 확인 필요"""


class WingTools:
    LIMITS = LIMITS
    family = "wing"
    model_label = "WING"

    def __init__(self, client: WingClient):
        self.w = client

    # -------------------------------------------------- helpers
    def _check(self, kind, index):
        if kind not in LIMITS:
            raise ToolError(f"알 수 없는 종류: {kind}")
        if not 1 <= int(index) <= self.LIMITS[kind]:
            raise ToolError(f"{KIND_KO[kind]} 번호는 1~{self.LIMITS[kind]} 입니다.")
        return f"/{kind}/{int(index)}"

    def _num(self, address):
        return number_of(self.w.get(address))

    def _name(self, kind, index):
        """콘솔 화면에 표시되는 이름($name)을 우선 사용하고, 없으면 저장된 이름(name)."""
        paths = [f"/{kind}/{index}/name"] if kind == "dca" else [f"/{kind}/{index}/$name", f"/{kind}/{index}/name"]
        for p in paths:
            try:
                n = text_of(self.w.get(p)).strip()
            except TimeoutError:
                continue
            if n:
                return n
        return ""

    @staticmethod
    def _db(v):
        if v is None:
            return None
        return "-∞" if v <= -143.9 else round(float(v), 1)

    @staticmethod
    def _clamp(db):
        return max(-144.0, min(10.0, float(db)))

    # -------------------------------------------------- tools
    def list_strips(self, kind):
        out = []
        for i in range(1, self.LIMITS[kind] + 1):
            base = self._check(kind, i)
            name = self._name(kind, i)
            fdr = self._num(f"{base}/fdr")
            if not name and (fdr is None or fdr <= -143.9):
                continue
            mute = self._num(f"{base}/mute")
            out.append({"번호": i, "이름": name or "(이름 없음)", "페이더_dB": self._db(fdr), "뮤트": bool(mute)})
        return {"종류": KIND_KO[kind], "목록": out}

    def get_monitor_mix(self, bus):
        self._check("bus", bus)
        sends = []
        for ch in range(1, self.LIMITS["ch"] + 1):
            on = self._num(f"/ch/{ch}/send/{bus}/on")
            lvl = self._num(f"/ch/{ch}/send/{bus}/lvl")
            if on or (lvl is not None and lvl > -143.9):
                sends.append({"채널": ch, "이름": self._name("ch", ch) or "(이름 없음)",
                              "켜짐": bool(on), "레벨_dB": self._db(lvl),
                              "채널_뮤트": bool(self._num(f"/ch/{ch}/mute")),
                              "채널_페이더_dB": self._db(self._num(f"/ch/{ch}/fdr"))})
        return {"버스": bus, "버스이름": self._name("bus", bus), "들어가는_채널": sends,
                "버스_페이더_dB": self._db(self._num(f"/bus/{bus}/fdr")),
                "버스_뮤트": bool(self._num(f"/bus/{bus}/mute"))}

    def set_send(self, channel, bus, on=None, level_db=None, confirmed=False):
        self._check("ch", channel)
        self._check("bus", bus)
        if on is None and level_db is None:
            raise ToolError("on 또는 level_db 중 하나는 지정해야 합니다.")
        base = f"/ch/{channel}/send/{bus}"
        result = {"채널": channel, "채널이름": self._name("ch", channel),
                  "버스": bus, "버스이름": self._name("bus", bus)}
        if level_db is not None:
            cur = self._num(f"{base}/lvl")
            target = self._clamp(level_db)
            if cur is not None and target - max(cur, -20.0) > MAX_RAISE_DB and not confirmed:
                raise ToolError(f"센드를 한 번에 {MAX_RAISE_DB:.0f} dB 넘게 올리는 변경입니다 "
                                f"(현재 {self._db(cur)} → {target} dB). 하울링 위험이 있으니 사용자에게 확인받은 뒤 confirmed=true 로 다시 호출하세요.")
            result["이전_레벨_dB"] = self._db(cur)
            result["현재_레벨_dB"] = self._db(number_of(self.w.set(f"{base}/lvl", target)))
        if on is not None:
            result["켜짐"] = bool(number_of(self.w.set(f"{base}/on", 1 if on else 0)))
        return result

    def set_fader(self, kind, index, db, confirmed=False):
        base = self._check(kind, index)
        cur = self._num(f"{base}/fdr")
        target = self._clamp(db)
        if cur is not None and target - max(cur, -20.0) > MAX_RAISE_DB and not confirmed:
            raise ToolError(f"페이더를 한 번에 {MAX_RAISE_DB:.0f} dB 넘게 올리는 변경입니다 "
                            f"(현재 {self._db(cur)} → {target} dB). 사용자에게 확인받은 뒤 confirmed=true 로 다시 호출하세요.")
        new = number_of(self.w.set(f"{base}/fdr", target))
        return {"대상": f"{KIND_KO[kind]} {index}", "이름": self._name(kind, index),
                "이전_dB": self._db(cur), "현재_dB": self._db(new)}

    def adjust_fader(self, kind, index, delta_db, confirmed=False):
        base = self._check(kind, index)
        cur = self._num(f"{base}/fdr")
        if cur is None:
            raise ToolError("현재 페이더 값을 읽지 못했습니다.")
        start = max(cur, -60.0) if delta_db > 0 else cur
        return self.set_fader(kind, index, start + float(delta_db), confirmed=confirmed or delta_db <= MAX_RAISE_DB)

    def set_mute(self, kind, index, muted, confirmed=False):
        base = self._check(kind, index)
        if kind == "main" and muted and not confirmed:
            raise ToolError("메인을 뮤트하면 예배당 전체 소리가 꺼집니다. 사용자에게 확인받은 뒤 confirmed=true 로 다시 호출하세요.")
        new = number_of(self.w.set(f"{base}/mute", 1 if muted else 0))
        return {"대상": f"{KIND_KO[kind]} {index}", "이름": self._name(kind, index), "뮤트": bool(new)}

    def set_low_cut(self, channel, on, freq_hz=None):
        base = self._check("ch", channel)
        result = {"채널": channel, "이름": self._name("ch", channel)}
        if freq_hz is not None:
            f = max(20.0, min(2000.0, float(freq_hz)))
            result["주파수_Hz"] = round(number_of(self.w.set(f"{base}/flt/lcf", f)) or f)
        result["로우컷"] = bool(number_of(self.w.set(f"{base}/flt/lc", 1 if on else 0)))
        return result

    # -------------------------------------------------- 화면용 전체 흐름
    def routing_overview(self):
        """화면 그림용: 채널 → 메인 스피커 / 각 모니터(버스)로 가는 소리를 한 번에 모읍니다."""
        channels = []
        for i in range(1, self.LIMITS["ch"] + 1):
            name = self._name("ch", i)
            fdr = self._num(f"/ch/{i}/fdr")
            mute = bool(self._num(f"/ch/{i}/mute"))
            channels.append({"ch": i, "name": name, "fader": self._db(fdr), "mute": mute,
                             "used": bool(name) or (fdr is not None and fdr > -143.9)})
        used = [c for c in channels if c["used"]]
        short = {"A": "A", "B": "B", "C": "C", "LCL": "본체", "AUX": "AUX", "USB": "USB", "CRD": "카드", "MOD": "모듈", "SC": "SC", "AES": "AES"}
        for c in used:
            src = self._source(c["ch"])
            c["src"] = f"{short.get(src[0], src[0])}{src[1]}" if src else ""
            c["srcLong"] = f"{self.GRP_KO.get(src[0], src[0])} {src[1]}번" if src else "입력 없음"

        # 메인 출력(MAIN, CENTER, YOUTUBE 등): 채널 → 메인 M 은 /ch/N/main/M/on,lvl (채널 페이더 뒤)
        mains = []
        for m in range(1, self.LIMITS["main"] + 1):
            name = self._name("main", m)
            if not name and m != 1:
                continue
            sends = []
            for c in used:
                on = self._num(f"/ch/{c['ch']}/main/{m}/on")
                lvl = self._num(f"/ch/{c['ch']}/main/{m}/lvl")
                fdr = c["fader"]
                if lvl is None:
                    continue
                # 실제로 들리는 크기 = 채널 페이더 + 메인 센드 레벨
                level = "-∞" if fdr in ("-∞", None) else self._db(max(-144.0, min(10.0, fdr + lvl)))
                sends.append({"ch": c["ch"], "level": level, "send": self._db(lvl), "on": bool(on)})
            mains.append({"main": m, "name": name or f"메인 {m}",
                          "fader": self._db(self._num(f"/main/{m}/fdr")),
                          "mute": bool(self._num(f"/main/{m}/mute")), "sends": sends})
        main = mains[0]

        bus_names = {b: self._name("bus", b) for b in range(1, 17)}
        buses = [b for b, n in bus_names.items() if n] or list(range(1, 9))
        monitors = []
        for b in buses:
            sends = []
            for c in used:
                on = self._num(f"/ch/{c['ch']}/send/{b}/on")
                lvl = self._num(f"/ch/{c['ch']}/send/{b}/lvl")
                if lvl is not None:
                    sends.append({"ch": c["ch"], "level": self._db(lvl), "on": bool(on)})
            monitors.append({"bus": b, "name": bus_names[b] or f"버스 {b}",
                             "fader": self._db(self._num(f"/bus/{b}/fdr")),
                             "mute": bool(self._num(f"/bus/{b}/mute")), "sends": sends})

        # 매트릭스(BABY, CAFE 등): 메인/버스 → 매트릭스 X 는 /main|bus/N/send/MX{X}/on,lvl
        sources = [("main", m["main"], f"m{m['main']}") for m in mains] + [("bus", m["bus"], f"b{m['bus']}") for m in monitors]
        matrices = []
        for x in range(1, self.LIMITS["mtx"] + 1):
            name = self._name("mtx", x)
            if not name:
                continue
            feeds = []
            for kind, idx, key in sources:
                on = self._num(f"/{kind}/{idx}/send/MX{x}/on")
                lvl = self._num(f"/{kind}/{idx}/send/MX{x}/lvl")
                if lvl is not None:
                    feeds.append({"src": key, "level": self._db(lvl), "on": bool(on)})
            matrices.append({"mtx": x, "name": name, "fader": self._db(self._num(f"/mtx/{x}/fdr")),
                             "mute": bool(self._num(f"/mtx/{x}/mute")), "feeds": feeds})
        try:
            routing = self.output_routing()
        except TimeoutError:
            routing = {"by_source": {}, "other": [], "nodes": {}}
        return {"channels": used, "main": main, "mains": mains, "monitors": monitors, "matrices": matrices,
                "outputs": routing["by_source"], "outputNodes": routing.get("nodes", {}), "outputRaw": routing.get("raw", {}),
                "outGroupLabels": {g: l for g, _, l in self.OUT_GROUPS}, "otherOutputs": routing["other"]}

    def _guarded_set(self, address, target, confirmed, what):
        cur = self._num(address)
        target = self._clamp(target)
        if cur is not None and target - max(cur, -20.0) > MAX_RAISE_DB and not confirmed:
            raise NeedConfirm(f"{what}을(를) 한 번에 {MAX_RAISE_DB:.0f} dB 넘게 올립니다 "
                              f"({self._db(cur)} → {round(target, 1)} dB). 하울링 위험이 있습니다.")
        return self._db(cur), self._db(number_of(self.w.set(address, target)))

    def get_main_mix(self, main):
        self._check("main", main)
        rows = []
        for ch in range(1, self.LIMITS["ch"] + 1):
            name = self._name("ch", ch)
            fdr = self._num(f"/ch/{ch}/fdr")
            if not name and (fdr is None or fdr <= -143.9):
                continue
            on = self._num(f"/ch/{ch}/main/{main}/on")
            lvl = self._num(f"/ch/{ch}/main/{main}/lvl")
            real = None if fdr is None or lvl is None or fdr <= -143.9 else max(-144.0, min(10.0, fdr + lvl))
            rows.append({"채널": ch, "이름": name or "(이름 없음)", "켜짐": bool(on),
                         "채널_페이더_dB": self._db(fdr), "메인_센드_dB": self._db(lvl),
                         "실제_크기_dB": self._db(real) if real is not None else "-∞",
                         "채널_뮤트": bool(self._num(f"/ch/{ch}/mute"))})
        return {"메인": main, "메인이름": self._name("main", main),
                "메인_페이더_dB": self._db(self._num(f"/main/{main}/fdr")),
                "메인_뮤트": bool(self._num(f"/main/{main}/mute")), "채널들": rows}

    def set_main_send(self, channel, main, on=None, level_db=None, confirmed=False):
        """채널 → 메인 출력(CENTER, YOUTUBE 등) 으로 보내는 양. level_db 는 '보내는 양'(채널 페이더와 별도)."""
        self._check("ch", channel)
        self._check("main", main)
        if on is None and level_db is None:
            raise ToolError("on 또는 level_db 중 하나는 지정해야 합니다.")
        base = f"/ch/{channel}/main/{main}"
        result = {"채널": channel, "채널이름": self._name("ch", channel), "메인": main, "메인이름": self._name("main", main)}
        if level_db is not None:
            try:
                result["이전_레벨_dB"], result["현재_레벨_dB"] = self._guarded_set(f"{base}/lvl", level_db, confirmed, "메인 센드")
            except NeedConfirm as e:
                raise ToolError(f"{e} 사용자에게 확인받은 뒤 confirmed=true 로 다시 호출하세요.")
        if on is not None:
            result["켜짐"] = bool(number_of(self.w.set(f"{base}/on", 1 if on else 0)))
        return result

    def control(self, target: dict, level=None, on=None, confirmed=False):
        """화면 슬라이더/버튼에서 오는 직접 조절.

        target: {"type":"bus","ch":N,"bus":B} | {"type":"main","ch":N,"main":M} | {"type":"mtx","src":"m1|b8","mtx":X}
        level: 화면에 보이는 값(dB). main 은 '실제로 들리는 크기'(채널 페이더+센드)로 받아 변환합니다.
        """
        t = target.get("type")
        if t == "bus":
            ch, b = int(target["ch"]), int(target["bus"])
            self._check("ch", ch); self._check("bus", b)
            base = f"/ch/{ch}/send/{b}"
            if level is not None:
                self._guarded_set(f"{base}/lvl", level, confirmed, "모니터 센드")
            if on is not None:
                self.w.set(f"{base}/on", 1 if on else 0)
        elif t == "main":
            ch, m = int(target["ch"]), int(target["main"])
            self._check("ch", ch); self._check("main", m)
            base = f"/ch/{ch}/main/{m}"
            if level is not None:
                if m == 1:
                    # MAIN 은 채널 페이더 자체를 움직임 (메인 센드는 0 dB 기준)
                    lvl = self._num(f"{base}/lvl") or 0.0
                    self._guarded_set(f"/ch/{ch}/fdr", float(level) - lvl, confirmed, "채널 페이더")
                else:
                    fdr = self._num(f"/ch/{ch}/fdr")
                    if fdr is None or fdr <= -143.9:
                        raise ToolError("채널 페이더가 내려가 있어(-∞) 이 출력으로 소리가 나가지 않습니다. 먼저 MAIN 에서 채널을 올려 주세요.")
                    self._guarded_set(f"{base}/lvl", float(level) - fdr, confirmed, "메인 센드")
            if on is not None:
                self.w.set(f"{base}/on", 1 if on else 0)
        elif t == "mtx":
            src, x = str(target["src"]), int(target["mtx"])
            kind = {"m": "main", "b": "bus"}.get(src[:1])
            if kind is None:
                raise ToolError("잘못된 출력 대상")
            idx = int(src[1:])
            self._check(kind, idx); self._check("mtx", x)
            base = f"/{kind}/{idx}/send/MX{x}"
            if level is not None:
                self._guarded_set(f"{base}/lvl", level, confirmed, "매트릭스 센드")
            if on is not None:
                self.w.set(f"{base}/on", 1 if on else 0)
        elif t == "master":
            # 버스·메인·매트릭스 자체의 전체 볼륨(페이더)과 뮤트
            kind, idx = str(target.get("kind")), int(target.get("index"))
            if kind not in ("bus", "main", "mtx"):
                raise ToolError("잘못된 대상")
            base = self._check(kind, idx)
            if level is not None:
                self._guarded_set(f"{base}/fdr", level, confirmed, f"{KIND_KO[kind]} 전체 볼륨")
            if on is not None:
                if kind == "main" and not on and not confirmed:
                    raise NeedConfirm(f"{self._name(kind, idx) or '메인'}을(를) 뮤트하면 그 출력의 소리가 전부 꺼집니다.")
                self.w.set(f"{base}/mute", 0 if on else 1)
        else:
            raise ToolError("알 수 없는 조절 대상")
        return {"ok": True}

    # -------------------------------------------------- 채널 상세 (입력·필터·게이트·EQ·컴프·인서트)
    GRP_KO = {"A": "AES50 A", "B": "AES50 B", "C": "AES50 C", "LCL": "본체 입력", "AUX": "본체 AUX 입력",
              "USB": "USB", "CRD": "확장 카드", "MOD": "내부 모듈", "SC": "StageConnect", "AES": "AES/EBU", "OFF": "없음",
              "BUS": "버스", "MAIN": "메인", "MTX": "매트릭스", "MON": "모니터(헤드폰·스피커)", "USR": "User Signal",
              "OSC": "테스트 신호", "PLAY": "USB 재생", "CH": "채널", "AUXC": "Aux 채널"}
    EQ_BANDS = [("l", "로우"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("h", "하이")]

    def _txt(self, address):
        try:
            return text_of(self.w.get(address))
        except TimeoutError:
            return None

    def _num_opt(self, address):
        try:
            return number_of(self.w.get(address))
        except TimeoutError:
            return None

    def _source(self, ch):
        grp = self._txt(f"/ch/{ch}/in/conn/grp")
        # 주의: 숫자 값은 0부터 세는 번호(15)이고, 글자 값이 실제 입력 번호(16)입니다 → 글자 값을 씀
        idx = self._txt(f"/ch/{ch}/in/conn/in")
        if not grp or not idx or grp == "OFF" or not str(idx).strip().isdigit():
            return None
        return grp, int(str(idx).strip())

    def channel_detail(self, channel):
        ch = int(channel)
        self._check("ch", ch)
        n = self._num_opt
        d = {"채널": ch, "이름": self._name("ch", ch), "페이더_dB": self._db(n(f"/ch/{ch}/fdr")), "뮤트": bool(n(f"/ch/{ch}/mute"))}
        src = self._source(ch)
        if src:
            grp, idx = src
            base = f"/io/in/{grp}/{idx}"
            g = n(f"{base}/g")
            d["입력"] = {"연결": f"{self.GRP_KO.get(grp, grp)} {idx}번", "게인_dB": None if g is None else round(g, 1),
                       "팬텀_48V": None if n(f"{base}/vph") is None else bool(n(f"{base}/vph")), "소스이름": self._txt(f"{base}/name") or ""}
        d["TRIM_dB"] = n(f"/ch/{ch}/in/set/trim")
        d["위상반전"] = bool(n(f"/ch/{ch}/in/set/inv"))
        d["필터"] = {"로우컷": bool(n(f"/ch/{ch}/flt/lc")), "로우컷_Hz": round(n(f"/ch/{ch}/flt/lcf") or 0),
                   "하이컷": bool(n(f"/ch/{ch}/flt/hc")), "하이컷_Hz": round(n(f"/ch/{ch}/flt/hcf") or 0)}
        d["게이트"] = {"켜짐": bool(n(f"/ch/{ch}/gate/on")), "종류": self._txt(f"/ch/{ch}/gate/mdl") or ""}
        eq = {"켜짐": bool(n(f"/ch/{ch}/eq/on")), "종류": self._txt(f"/ch/{ch}/eq/mdl") or "", "밴드": []}
        if eq["종류"] == "STD":
            for key, label in self.EQ_BANDS:
                g, f, q = n(f"/ch/{ch}/eq/{key}g"), n(f"/ch/{ch}/eq/{key}f"), n(f"/ch/{ch}/eq/{key}q")
                if g is None:
                    continue
                band = {"밴드": key, "이름": label, "게인_dB": round(g, 1), "주파수_Hz": round(f or 0), "Q": round(q or 0, 2)}
                if key in ("l", "h"):
                    band["모양"] = self._txt(f"/ch/{ch}/eq/{key}eq") or ""
                eq["밴드"].append(band)
        d["EQ"] = eq
        dyn = {"켜짐": bool(n(f"/ch/{ch}/dyn/on")), "종류": self._txt(f"/ch/{ch}/dyn/mdl") or ""}
        if dyn["종류"] in ("COMP", "EXP"):
            dyn.update({"문턱_dB": n(f"/ch/{ch}/dyn/thr"), "비율": n(f"/ch/{ch}/dyn/ratio"), "보충게인_dB": n(f"/ch/{ch}/dyn/gain"),
                        "어택_ms": n(f"/ch/{ch}/dyn/att"), "릴리즈_ms": n(f"/ch/{ch}/dyn/rel"),
                        "니": n(f"/ch/{ch}/dyn/knee"), "섞는양_%": n(f"/ch/{ch}/dyn/mix")})
        elif dyn["종류"] and self.family == "wing":
            dyn["세부값"] = self.dyn_raw_params(ch)
        d["컴프"] = dyn
        d["인서트"] = {k: {"켜짐": bool(n(f"/ch/{ch}/{k}/on")), "이펙트": self._txt(f"/ch/{ch}/{k}/ins") or "NONE"}
                     for k in ("preins", "postins")}
        return d

    def get_channel_detail(self, channel):
        """AI 도구 이름(get_channel_detail) → 채널 상세 (이전에는 이 연결이 빠져 있어 AI가 상세를 못 봤음)"""
        return self.channel_detail(channel)

    # 조절할 수 있는 항목: 키 → (주소 만들기, 종류, 최소, 최대, 한 번에 올려도 되는 최대 dB 또는 None)
    def _param_spec(self, ch, key):
        c = f"/ch/{ch}"
        simple = {
            "trim": (f"{c}/in/set/trim", "f", -18, 18, 6), "invert": (f"{c}/in/set/inv", "b", 0, 1, None),
            "lc": (f"{c}/flt/lc", "b", 0, 1, None), "lcf": (f"{c}/flt/lcf", "f", 20, 2000, None),
            "hc": (f"{c}/flt/hc", "b", 0, 1, None), "hcf": (f"{c}/flt/hcf", "f", 50, 20000, None),
            "gate_on": (f"{c}/gate/on", "b", 0, 1, None), "eq_on": (f"{c}/eq/on", "b", 0, 1, None),
            "dyn_on": (f"{c}/dyn/on", "b", 0, 1, None), "dyn_thr": (f"{c}/dyn/thr", "f", -60, 0, None),
            "dyn_ratio": (f"{c}/dyn/ratio", "f", 1.1, 100, None), "dyn_gain": (f"{c}/dyn/gain", "f", -6, 12, 6),
            "dyn_att": (f"{c}/dyn/att", "f", 0, 120, None), "dyn_rel": (f"{c}/dyn/rel", "f", 4, 4000, None),
            "dyn_knee": (f"{c}/dyn/knee", "f", 0, 5, None), "dyn_mix": (f"{c}/dyn/mix", "f", 0, 100, None),
            "preins_on": (f"{c}/preins/on", "b", 0, 1, None), "postins_on": (f"{c}/postins/on", "b", 0, 1, None),
        }
        if key in simple:
            return simple[key]
        if key.startswith("eq_") and len(key) == 5 and key[3] in "l1234h" and key[4] in "gfq":
            band, part = key[3], key[4]
            return {"g": (f"{c}/eq/{band}g", "f", -15, 15, 6), "f": (f"{c}/eq/{band}f", "f", 20, 20000, None),
                    "q": (f"{c}/eq/{band}q", "f", 0.44, 10, None)}[part]
        if key in ("gain", "phantom"):
            src = self._source(ch)
            if not src:
                raise ToolError("이 채널은 입력이 연결되어 있지 않아 게인/팬텀을 바꿀 수 없습니다.")
            base = f"/io/in/{src[0]}/{src[1]}"
            if self._num_opt(f"{base}/g") is None:
                raise ToolError("이 입력은 원격으로 게인을 조절할 수 없는 종류입니다(예: USB, 내부 신호).")
            return (f"{base}/g", "f", -3, 60, 3) if key == "gain" else (f"{base}/vph", "b", 0, 1, None)
        raise ToolError(f"알 수 없는 설정: {key}")

    def set_channel_param(self, channel, param, value, confirmed=False):
        ch = int(channel)
        self._check("ch", ch)
        addr, kind, lo, hi, max_raise = self._param_spec(ch, param)
        cur = self._num_opt(addr)
        if kind == "b":
            target = 1 if (value in (True, 1, "1", "on", "true", "켜기") or (isinstance(value, (int, float)) and value >= 0.5)) else 0
            if param == "phantom" and not confirmed and cur is not None and int(cur) != target:
                raise NeedConfirm("+48V 팬텀 전원을 바꾸면 스피커에서 '펑' 소리가 날 수 있습니다. 먼저 이 채널을 뮤트하는 것이 안전합니다.")
            new = number_of(self.w.set(addr, target))
            return {"설정": param, "주소": addr, "이전": cur, "현재": new}
        target = max(lo, min(hi, float(value)))
        if max_raise is not None and cur is not None and target - cur > max_raise and not confirmed:
            what = {"gain": "입력 게인", "trim": "TRIM", "dyn_gain": "컴프 보충 게인"}.get(param, "EQ 부스트")
            raise NeedConfirm(f"{what}을(를) 한 번에 {max_raise:g} dB 넘게 올립니다 ({cur:.1f} → {target:.1f} dB). 하울링·찢어짐 위험이 있습니다.")
        new = number_of(self.w.set(addr, target))
        return {"설정": param, "주소": addr, "이전": None if cur is None else round(cur, 2), "현재": None if new is None else round(new, 2)}

    def list_effects(self):
        """이펙트 랙 16칸: 종류, 섞는 양, 어느 채널·버스에 인서트되어 있는지."""
        fx = {i: {"슬롯": i, "종류": self._txt(f"/fx/{i}/mdl") or "", "섞는양_%": self._num_opt(f"/fx/{i}/fxmix"), "사용처": []}
              for i in range(1, 17)}
        old_timeout = self.w.timeout
        self.w.timeout = 0.25        # 없는 항목에서 오래 기다리지 않도록
        try:
            spots = [(kind, i, slot) for kind in ("ch", "aux", "bus", "main", "mtx")
                     for i in range(1, self.LIMITS[kind] + 1) for slot in ("preins", "postins")]
            found = [(k, i, s, self._txt(f"/{k}/{i}/{s}/ins")) for k, i, s in spots]
        finally:
            self.w.timeout = old_timeout
        for kind, i, slot, ins in found:
            if ins and ins.startswith("FX") and ins[2:].isdigit() and int(ins[2:]) in fx:
                fx[int(ins[2:])]["사용처"].append({"대상": f"{KIND_KO[kind]} {i}", "이름": self._name(kind, i),
                                                  "위치": "페이더 앞" if slot == "preins" else "페이더 뒤",
                                                  "켜짐": bool(self._num_opt(f"/{kind}/{i}/{slot}/on")),
                                                  "kind": kind, "idx": i, "pos": slot})
        # 이펙트가 들어 있거나, 비어 있어도 어딘가에 끼워져 있는 칸은 보여 줌 (콘솔 EFFECTS 화면과 같게)
        for v in fx.values():
            if v["종류"] in ("", "NONE"):
                v["종류"] = "비어 있음"
                v["섞는양_%"] = None
                v["설정"] = []
            else:
                try:
                    v["설정"] = self._fx_params(v["슬롯"])
                except TimeoutError:
                    v["설정"] = []
                v["주요"] = self.FX_KEY.get(v["종류"]) or (v["설정"][0]["이름"] if v["설정"] else None)
        return {"이펙트": [v for v in fx.values() if v["종류"] != "비어 있음" or v["사용처"]]}

    # 이펙트 세부값: 콘솔에 '/fx/N' 을 물으면 그 이펙트의 설정 이름 목록을 돌려줌
    FX_LABELS = {
        "mix": "섞는 양", "dcy": "잔향 길이 (DECAY)", "pdel": "프리딜레이", "size": "공간 크기", "mult": "저음 잔향 배율",
        "damp": "고음 감쇠", "lc": "로우컷", "hc": "하이컷", "xover": "크로스오버", "diff": "확산", "mdep": "흔들림 깊이",
        "mspd": "흔들림 속도", "hi": "고음 치찰음 줄임 (HIGH)", "lo": "저음 치찰음 줄임 (LOW)", "mode": "모드",
        "spd": "속도 (SPEED)", "phase": "위상", "wave": "파형", "att": "어택", "rel": "릴리즈", "knee": "니(KNEE)",
        "sqz": "압축 정도 (SQUEEZE)", "g": "게인", "st": "스테레오 폭", "tiltf": "틸트 주파수 (TILT F)", "lim": "리미터",
        "dist": "왜곡", "bass": "베이스 강도", "lg": "로우 게인", "lf": "로우 주파수", "hg": "하이 게인", "hf": "하이 주파수",
        "lmf": "로우미드", "hmf": "하이미드", "dly": "딜레이 시간", "time": "시간", "fb": "피드백", "depth": "깊이",
        "rate": "속도", "thr": "문턱", "ratio": "비율", "gain": "게인", "width": "폭", "tone": "톤", "drive": "드라이브",
        "wid": "폭 (WIDTH)", "int": "강도 (INTENSITY)", "g_thr": "게이트 문턱 (G-THR)", "g_range": "게이트 범위", "g_on": "게이트 켜기",
        "d_on": "컴프 켜기", "d_thr": "컴프 문턱", "d_ratio": "컴프 비율", "eq_on": "EQ 켜기", "gin": "입력 게인", "gout": "출력 게인",
        "hpf": "하이패스(로우컷)", "lpf": "로우패스(하이컷)", "tiltg": "틸트 게인", "invert": "위상 반전", "xf": "크로스오버 주파수",
        "dlyl": "왼쪽 딜레이", "dlyr": "오른쪽 딜레이", "depl": "왼쪽 깊이", "depr": "오른쪽 깊이", "sprd": "퍼짐",
    }
    # 콘솔 EFFECTS 화면 카드에 크게 보이는 '주요 값'
    FX_KEY = {"BPLATE": "dcy", "DE-S2": "hi", "CHORUS": "spd", "LIMITER": "sqz", "V-IMG": "wid", "SPKMAN": "tiltf",
              "P-BASS": "int", "*SOUL*": "g_thr"}

    def _fx_params(self, slot):
        names = self.w.get(f"/fx/{slot}")       # 이름 목록
        out = []
        for n in names:
            if not isinstance(n, str) or n.startswith("$") or n in ("mdl", "fxmix"):
                continue
            try:
                v = self.w.get(f"/fx/{slot}/{n}")
            except TimeoutError:
                continue
            nums = [a for a in v if isinstance(a, (int, float))]
            out.append({"이름": n, "설명": self.FX_LABELS.get(n, n.upper()), "표시값": text_of(v),
                        "값": nums[-1] if nums else None, "0~1": nums[0] if len(nums) >= 2 else None})
        return out

    def effect_detail(self, slot):
        s = int(slot)
        if not 1 <= s <= 16:
            raise ToolError("이펙트 슬롯은 1~16입니다.")
        return {"슬롯": s, "종류": self._txt(f"/fx/{s}/mdl") or "", "섞는양_%": self._num_opt(f"/fx/{s}/fxmix"),
                "설정": self._fx_params(s)}

    def set_effect_param(self, slot, param, value):
        s = int(slot)
        if not 1 <= s <= 16:
            raise ToolError("이펙트 슬롯은 1~16입니다.")
        names = [n for n in self.w.get(f"/fx/{s}") if isinstance(n, str) and not n.startswith("$") and n != "mdl"]
        if param not in names:
            raise ToolError(f"이 이펙트({self._txt(f'/fx/{s}/mdl')})에는 '{param}' 설정이 없습니다. 가능: {', '.join(names)}")
        addr = f"/fx/{s}/{param}"
        before = text_of(self.w.get(addr))
        after = text_of(self.w.set(addr, float(value)))
        return {"슬롯": s, "설정": param, "설명": self.FX_LABELS.get(param, param), "이전": before, "현재": after}

    def set_effect_mix(self, slot, mix_percent):
        s = int(slot)
        if not 1 <= s <= 16:
            raise ToolError("이펙트 슬롯은 1~16입니다.")
        cur = self._num_opt(f"/fx/{s}/fxmix")
        if cur is None:
            raise ToolError("이 이펙트는 섞는 양을 원격으로 바꿀 수 없습니다.")
        new = number_of(self.w.set(f"/fx/{s}/fxmix", max(0.0, min(100.0, float(mix_percent)))))
        return {"슬롯": s, "종류": self._txt(f"/fx/{s}/mdl"), "이전_%": cur, "현재_%": new}

    # -------------------------------------------------- 라우팅 (입력 단자 → 채널, 버스·메인 → 출력 단자)
    OUT_GROUPS = [("LCL", 8, "본체 출력"), ("AUX", 8, "본체 AUX 출력"), ("A", 48, "AES50 A"), ("B", 48, "AES50 B"),
                  ("C", 48, "AES50 C"), ("AES", 2, "AES/EBU"), ("SC", 32, "StageConnect"), ("USB", 48, "USB(PC)"),
                  ("CRD", 64, "확장 카드"), ("MOD", 64, "내부 모듈"), ("REC", 4, "USB 녹음기")]
    STEREO_SRC = {"BUS": ("b", "버스"), "MAIN": ("m", "메인"), "MTX": ("x", "매트릭스")}

    @staticmethod
    def _ranges(nums):
        """[1,2,3,7,8] → '1-3, 7-8'"""
        nums = sorted(set(nums))
        out, start, prev = [], None, None
        for n in nums:
            if start is None:
                start = prev = n
            elif n == prev + 1:
                prev = n
            else:
                out.append(f"{start}-{prev}" if prev != start else f"{start}")
                start = prev = n
        if start is not None:
            out.append(f"{start}-{prev}" if prev != start else f"{start}")
        return ", ".join(out)

    def output_routing(self, max_age=10.0):
        """모든 출력 단자가 무엇을 내보내는지 (10초 캐시). 결과: {'by_source': {'b8': [(grp, n)...]}, 'other': [...]}"""
        import time as _t
        cache = getattr(self, "_out_cache", None)
        if cache and _t.time() - cache[0] < max_age:
            return cache[1]
        old = self.w.timeout
        self.w.timeout = 0.25
        rows = []
        try:
            for grp, count, _label in self.OUT_GROUPS:
                for n in range(1, count + 1):
                    sg = self._txt(f"/io/out/{grp}/{n}/grp")
                    if sg is None:
                        break           # 이 그룹은 여기까지
                    if sg in ("OFF", ""):
                        continue
                    si = self._txt(f"/io/out/{grp}/{n}/in")
                    if si and si.strip().isdigit():
                        rows.append((grp, n, sg, int(si)))
        finally:
            self.w.timeout = old
        by_source, other = {}, {}
        for grp, n, sg, si in rows:
            if sg in self.STEREO_SRC:
                key = self.STEREO_SRC[sg][0] + str((si + 1) // 2)       # 스테레오 버스: 1,2 → 1번 / 31,32 → 16번
                by_source.setdefault(key, {}).setdefault(grp, []).append(n)
            else:
                other.setdefault((grp, sg), []).append((n, si))
        label = {g: l for g, _, l in self.OUT_GROUPS}
        result = {
            "by_source": {k: [f"{label.get(g, g)} {self._ranges(ns)}" for g, ns in v.items()] for k, v in by_source.items()},
            # 스피커 이름표용: 단자 번호 그대로 {'m1': {'A': [7, 8, 47, 48], ...}}
            "raw": {k: {g: sorted(ns) for g, ns in v.items()} for k, v in by_source.items()},
            # 도식용: 연속 구간마다 하나씩 (예: 'AES50 A 7-8', 'AES50 A 47-48')
            "nodes": {k: [f"{label.get(g, g)} {r}" for g, ns in v.items() for r in self._ranges(ns).split(", ")] for k, v in by_source.items()},
            "other": [f"{label.get(g, g)} {self._ranges([n for n, _ in v])} ← {self.GRP_KO.get(sg, sg)} {self._ranges([s for _, s in v])}"
                      for (g, sg), v in other.items()],
        }
        self._out_cache = (_t.time(), result)
        return result

    # ---------- 라우팅 변경 ----------
    IN_GROUPS = [("A", 48), ("B", 48), ("C", 48), ("LCL", 8), ("AUX", 8), ("USB", 48), ("SC", 32), ("AES", 2), ("CRD", 64), ("MOD", 64)]
    OUT_SRC = {"bus": ("BUS", 16), "main": ("MAIN", 4), "mtx": ("MTX", 8)}

    def input_catalog(self):
        """입력 단자 목록과 이름 (30초 캐시). [{grp, label, count, names{n: 이름}}]"""
        import time as _t
        c = getattr(self, "_in_cat", None)
        if c and _t.time() - c[0] < 30:
            return c[1]
        old = self.w.timeout
        self.w.timeout = 0.25
        out = []
        try:
            for grp, count in self.IN_GROUPS:
                if self._txt(f"/io/in/{grp}/1/name") is None:
                    continue                      # 이 콘솔에 없는 그룹
                names = {}
                if grp in ("A", "B", "C", "LCL", "AUX"):
                    for n in range(1, count + 1):
                        nm = self._txt(f"/io/in/{grp}/{n}/name")
                        if nm:
                            names[n] = nm
                out.append({"grp": grp, "label": self.GRP_KO.get(grp, grp), "count": count, "names": names})
        finally:
            self.w.timeout = old
        self._in_cat = (_t.time(), out)
        return out

    def _out_count(self, grp):
        return next((c for g, c, _ in self.OUT_GROUPS if g == grp), None)

    def _write_route(self, gaddr, iaddr, grp, num):
        """grp/in 을 쓰고 다시 읽어 확인. 틀리면 예외."""
        self.w.set(gaddr, str(grp))
        if grp != "OFF":
            self.w.set(iaddr, str(int(num)))
        g2 = self._txt(gaddr)
        i2 = self._txt(iaddr)
        if g2 != grp or (grp != "OFF" and (i2 or "").strip() != str(int(num))):
            raise ToolError(f"콘솔이 변경을 받아들이지 않았습니다(읽은 값: {g2} {i2}).")

    def _route_label(self, grp, num):
        if grp in ("OFF", None, ""):
            return "없음(꺼짐)"
        if grp in ("BUS", "MAIN", "MTX"):
            kind = {"BUS": "bus", "MAIN": "main", "MTX": "mtx"}[grp]
            idx = (int(num) + 1) // 2
            return f"{KIND_KO[kind]} {idx}({self._name(kind, idx) or '이름 없음'}) {'L' if int(num) % 2 else 'R'}"
        nm = self._txt(f"/io/in/{grp}/{num}/name") if grp in ("A", "B", "C", "LCL", "AUX") else ""
        return f"{self.GRP_KO.get(grp, grp)} {num}번" + (f"({nm})" if nm else "")

    def set_channel_input(self, channel, group, number, confirmed=False):
        ch = int(channel)
        self._check("ch", ch)
        grp = str(group).upper()
        count = dict(self.IN_GROUPS).get(grp)
        if count is None:
            raise ToolError(f"알 수 없는 입력 그룹: {group} (가능: {', '.join(g for g, _ in self.IN_GROUPS)})")
        num = int(number)
        if not 1 <= num <= count:
            raise ToolError(f"{self.GRP_KO.get(grp, grp)} 번호는 1~{count} 입니다.")
        gaddr, iaddr = f"/ch/{ch}/in/conn/grp", f"/ch/{ch}/in/conn/in"
        prev = (self._txt(gaddr), (self._txt(iaddr) or "1").strip())
        before, after = self._route_label(prev[0], prev[1]), self._route_label(grp, num)
        name = self._name("ch", ch) or f"채널 {ch}"
        if prev == (grp, str(num)):
            return {"채널": name, "결과": f"이미 {after} 입니다."}
        if not confirmed:
            raise NeedConfirm(f"{name} 채널의 입력을 {before} → {after} (으)로 바꿉니다. 이 채널 소리가 바로 바뀌거나 끊길 수 있습니다.")
        try:
            self._write_route(gaddr, iaddr, grp, num)
        except ToolError:
            self._write_route(gaddr, iaddr, prev[0], prev[1])      # 원래대로
            raise
        self.last_route_undo = {"text": f"{name} 입력 {after} → {before}", "items": [(gaddr, iaddr, prev[0], prev[1])]}
        self._in_cat = None
        return {"채널": name, "이전": before, "현재": after, "되돌리기": "가능"}

    def set_output_routing(self, output_group, output_number, source, source_number=1, stereo=True, confirmed=False):
        og = str(output_group).upper()
        count = self._out_count(og)
        if count is None:
            raise ToolError(f"알 수 없는 출력 그룹: {output_group} (가능: {', '.join(g for g, _, _ in self.OUT_GROUPS)})")
        start = int(output_number)
        n_out = 2 if stereo and str(source).lower() != "off" else 1
        if not 1 <= start or start + n_out - 1 > count:
            raise ToolError(f"{self.GRP_KO.get(og, og)} 출력 번호는 1~{count} 입니다" + (" (스테레오는 두 칸 사용)" if n_out == 2 else "") + ".")
        src = str(source).lower()
        if src == "off":
            targets = [("OFF", 1)]
        else:
            if src not in self.OUT_SRC:
                raise ToolError("source 는 bus, main, mtx, off 중 하나입니다.")
            sg, smax = self.OUT_SRC[src]
            si = int(source_number)
            if not 1 <= si <= smax:
                raise ToolError(f"{KIND_KO[src]} 번호는 1~{smax} 입니다.")
            targets = [(sg, 2 * si - 1), (sg, 2 * si)][:n_out]
        items, lines = [], []
        for k, (tg, tn) in enumerate(targets):
            n = start + k
            gaddr, iaddr = f"/io/out/{og}/{n}/grp", f"/io/out/{og}/{n}/in"
            pg, pn = self._txt(gaddr), (self._txt(iaddr) or "1").strip()
            items.append((gaddr, iaddr, pg, pn, tg, tn))
            lines.append(f"{self.GRP_KO.get(og, og)} 출력 {n}: {self._route_label(pg, pn)} → {self._route_label(tg, tn)}")
        if all((pg, pn) == (tg, str(tn)) or (pg == tg == "OFF") for _, _, pg, pn, tg, tn in items):
            return {"결과": "이미 그렇게 연결되어 있습니다.", "내용": lines}
        if not confirmed:
            raise NeedConfirm("출력 연결을 바꿉니다:\n" + "\n".join(lines) + "\n이 단자에 연결된 스피커·모니터 소리가 바로 바뀝니다.")
        done = []
        try:
            for gaddr, iaddr, pg, pn, tg, tn in items:
                self._write_route(gaddr, iaddr, tg, tn)
                done.append((gaddr, iaddr, pg, pn))
        except ToolError:
            for gaddr, iaddr, pg, pn in done:
                self._write_route(gaddr, iaddr, pg, pn)
            raise
        self.last_route_undo = {"text": "출력 연결 되돌리기", "items": [(g, i, pg, pn) for g, i, pg, pn, _, _ in items]}
        self._out_cache = None
        return {"바뀐_것": lines, "되돌리기": "가능"}

    def undo_routing(self):
        u = getattr(self, "last_route_undo", None)
        if not u:
            raise ToolError("되돌릴 라우팅 변경이 없습니다.")
        for gaddr, iaddr, pg, pn in u["items"]:
            self._write_route(gaddr, iaddr, pg or "OFF", pn)
        self.last_route_undo = None
        self._out_cache = None
        self._in_cat = None
        return {"되돌림": u["text"]}

    def outputs_in_group(self, grp):
        """출력 고르기 창용: 그룹 안 각 출력 단자에 지금 무엇이 연결되어 있는지."""
        g = str(grp).upper()
        count = self._out_count(g)
        if count is None:
            raise ToolError("알 수 없는 출력 그룹")
        old = self.w.timeout
        self.w.timeout = 0.25
        try:
            rows = []
            for n in range(1, count + 1):
                pg = self._txt(f"/io/out/{g}/{n}/grp")
                if pg is None:
                    break
                pn = (self._txt(f"/io/out/{g}/{n}/in") or "1").strip()
                rows.append({"n": n, "now": self._route_label(pg, pn), "off": pg == "OFF"})
        finally:
            self.w.timeout = old
        return {"grp": g, "label": self.GRP_KO.get(g, g), "outputs": rows}

    def get_routing(self):
        """AI 도구: 입력 단자 → 채널, 버스·메인·매트릭스 → 출력 단자."""
        inputs = []
        for ch in self._used_channels():
            src = self._source(ch)
            inputs.append({"채널": ch, "이름": self._name("ch", ch),
                           "입력단자": f"{self.GRP_KO.get(src[0], src[0])} {src[1]}번" if src else "없음"})
        out = self.output_routing(max_age=0)
        names = {}
        for key in out["by_source"]:
            kind = {"b": "bus", "m": "main", "x": "mtx"}[key[0]]
            names[key] = f"{KIND_KO[kind]} {key[1:]} ({self._name(kind, int(key[1:])) or '이름 없음'})"
        import speakers as _spk
        return {"입력": inputs,
                "출력": [{"보내는_것": names[k], "출력단자": v} for k, v in out["by_source"].items()],
                "스피커_이름표(사람이 붙인 이름, 키=출력그룹:번호)": _spk.load(),
                "기타_출력(녹음 등)": out["other"],
                "참고": "변경은 set_channel_input / set_output_routing (항상 사용자 확인 후), 되돌리기는 undo_routing."}

    # -------------------------------------------------- 예배 순서(씬)
    def _used_channels(self):
        used = []
        for ch in range(1, self.LIMITS["ch"] + 1):
            name = self._name("ch", ch)
            fdr = self._num(f"/ch/{ch}/fdr")
            if name or (fdr is not None and fdr > -143.9):
                used.append(ch)
        return used

    def capture_state(self, scope):
        """지금 콘솔 상태 중 scope 에 해당하는 값을 모읍니다. MAIN 1 뮤트는 안전을 위해 절대 담지 않습니다."""
        vals = {}
        chans = self._used_channels()
        buses = [b for b in range(1, 17) if self._name("bus", b)]
        mains = [m for m in range(2, self.LIMITS["main"] + 1) if self._name("main", m)]
        for ch in chans:
            if scope.get("mute"):
                vals[f"/ch/{ch}/mute"] = int(self._num(f"/ch/{ch}/mute") or 0)
            if scope.get("fader"):
                vals[f"/ch/{ch}/fdr"] = round(float(self._num(f"/ch/{ch}/fdr")), 2)
            if scope.get("sends"):
                for b in buses:
                    vals[f"/ch/{ch}/send/{b}/on"] = int(self._num(f"/ch/{ch}/send/{b}/on") or 0)
                    vals[f"/ch/{ch}/send/{b}/lvl"] = round(float(self._num(f"/ch/{ch}/send/{b}/lvl")), 2)
            if scope.get("mains"):
                for m in mains:
                    vals[f"/ch/{ch}/main/{m}/on"] = int(self._num(f"/ch/{ch}/main/{m}/on") or 0)
                    vals[f"/ch/{ch}/main/{m}/lvl"] = round(float(self._num(f"/ch/{ch}/main/{m}/lvl")), 2)
        if scope.get("buses"):
            for b in buses:
                vals[f"/bus/{b}/fdr"] = round(float(self._num(f"/bus/{b}/fdr")), 2)
                vals[f"/bus/{b}/mute"] = int(self._num(f"/bus/{b}/mute") or 0)
        return vals

    def _label(self, addr, names):
        """주소를 사람이 읽을 수 있는 말로: '/ch/3/send/8/lvl' → 'BOX 2 → MONITOR 센드'."""
        def nm(kind, i):
            key = (kind, i)
            if key not in names:
                names[key] = self._name(kind, i) or f"{KIND_KO[kind]} {i}"
            return names[key]
        p = addr.strip("/").split("/")
        try:
            if p[0] == "ch":
                ch = nm("ch", int(p[1]))
                if p[2] == "mute":
                    return ch, "뮤트"
                if p[2] == "fdr":
                    return ch, "페이더"
                if p[2] == "send":
                    return ch, f"→ {nm('bus', int(p[3]))} " + ("센드 켜짐" if p[4] == "on" else "센드")
                if p[2] == "main":
                    return ch, f"→ {nm('main', int(p[3]))} " + ("보내기 켜짐" if p[4] == "on" else "보내기")
            if p[0] == "bus":
                return nm("bus", int(p[1])), ("볼륨" if p[2] == "fdr" else "뮤트")
        except (IndexError, ValueError):
            pass
        return addr, ""

    @staticmethod
    def _fmt(addr, v):
        if v is None:
            return "?"
        if addr.endswith("/mute"):
            return "뮤트" if v else "켜짐"
        if addr.endswith("/on"):
            return "켜짐" if v else "꺼짐"
        return "-∞" if v <= -143.9 else f"{v:+.1f} dB".replace("+0.0", "0.0")

    def diff_state(self, values):
        """저장된 값과 지금 콘솔 값의 차이 목록."""
        names, out = {}, []
        for addr, target in values.items():
            cur = self._num(addr)
            if cur is None:
                continue
            same = (int(cur) == int(target)) if (addr.endswith("/mute") or addr.endswith("/on")) else abs(float(cur) - float(target)) < 0.15 \
                or (float(cur) <= -143.9 and float(target) <= -143.9)
            if not same:
                who, what = self._label(addr, names)
                out.append({"addr": addr, "who": who, "what": what, "from": cur, "to": target,
                            "text": f"{who} {what}: {self._fmt(addr, cur)} → {self._fmt(addr, target)}"})
        return out

    def apply_state(self, values, fade_ms=1000):
        """값 적용. 뮤트·켜짐을 먼저 바꾸고, 레벨은 fade_ms 동안 부드럽게 움직입니다. 되돌리기용 이전 값을 돌려줍니다."""
        import time as _t
        changes = self.diff_state(values)
        undo = {c["addr"]: c["from"] for c in changes}
        switches = [c for c in changes if c["addr"].endswith("/mute") or c["addr"].endswith("/on")]
        levels = [c for c in changes if c not in switches]
        # 1) 꺼지는 것(뮤트 켜기, 센드 끄기)을 먼저 → 2) 켜지는 것
        for c in sorted(switches, key=lambda c: 0 if (c["addr"].endswith("/mute") and c["to"]) or (c["addr"].endswith("/on") and not c["to"]) else 1):
            self.w.set(c["addr"], int(c["to"]))
        # 3) 레벨을 부드럽게
        steps = max(1, int(fade_ms) // 50) if fade_ms else 1
        def start(c):
            return max(float(c["from"]), -60.0)
        for i in range(1, steps + 1):
            for c in levels:
                to = float(c["to"])
                end = max(to, -60.0)
                v = start(c) + (end - start(c)) * i / steps
                self.w.send(c["addr"], float(to if (i == steps) else v))
            if steps > 1:
                _t.sleep(fade_ms / 1000 / steps)
        for c in levels:     # 마지막 값 확실히
            self.w.set(c["addr"], float(c["to"]))
        return changes, undo

    # AI 도구: 예배 순서
    def list_scenes(self):
        from scenes import STORE, SCOPE_LABELS
        out = []
        for s in STORE.scenes:
            d = self.diff_state(s.get("values", {}))
            out.append({"이름": s["name"], "담은_것": [SCOPE_LABELS[k] for k, v in s.get("scope", {}).items() if v],
                        "항목_수": len(s.get("values", {})), "지금과_다른_항목_수": len(d)})
        return {"예배_순서": out, "마지막_적용": next((s["name"] for s in STORE.scenes if s["id"] == STORE.active_id), None)}

    def save_scene(self, name, include_monitor_sends=False, include_main_sends=False, include_bus_masters=False):
        from scenes import STORE
        scope = {"mute": True, "fader": True, "sends": bool(include_monitor_sends),
                 "mains": bool(include_main_sends), "buses": bool(include_bus_masters)}
        s = STORE.upsert(name, self.capture_state(scope), scope)
        return {"저장됨": s["name"], "항목_수": len(s["values"])}

    def recall_scene(self, name, preview_only=False):
        from scenes import STORE
        s = STORE.find(name)
        if not s:
            raise ToolError(f"'{name}' 예배 순서가 없습니다. list_scenes 로 이름을 확인하세요.")
        if preview_only:
            d = self.diff_state(s["values"])
            return {"순서": s["name"], "바뀔_항목": [c["text"] for c in d][:40], "바뀔_항목_수": len(d)}
        changes, undo = self.apply_state(s["values"])
        STORE.active_id = s["id"]
        STORE.last_undo = {"scene": s["name"], "values": undo, "at": __import__("time").strftime("%H:%M:%S")}
        return {"적용됨": s["name"], "바뀐_항목": [c["text"] for c in changes][:40], "바뀐_항목_수": len(changes),
                "되돌리기": "화면의 되돌리기 버튼으로 이전 상태로 돌아갈 수 있습니다."}

    # -------------------------------------------------- 목소리 EQ (성별·나이·마이크 프리셋)
    def _voice_undo(self, ch):
        if not hasattr(self, "voice_undo_stack"):
            self.voice_undo_stack = {}
        return self.voice_undo_stack.setdefault(int(ch), [])

    def voice_eq_preset(self, channel, gender, age, mic="handheld", use="speech", preview_only=False):
        import voice_eq
        self._check("ch", channel)
        try:
            r = voice_eq.apply(self, channel, gender, age, mic, use, preview=bool(preview_only))
        except ValueError as e:
            raise ToolError(str(e))
        if not preview_only:
            self._voice_undo(channel).append(r["undo"])
        r.pop("undo", None)
        r["안내"] = "미리보기입니다. 적용하려면 preview_only 없이 다시 호출하세요." if preview_only else \
            "적용했어요. 실제로 들어 보고 먹먹함·또렷함·치찰음 등을 voice_eq_tweak 으로 조금씩 다듬으세요. 되돌리기 가능."
        return r

    def voice_eq_tweak(self, channel, kind=None, undo=False):
        import voice_eq
        self._check("ch", channel)
        if undo:
            stack = self._voice_undo(channel)
            if not stack:
                raise ToolError("되돌릴 목소리 EQ 변경이 없습니다.")
            voice_eq.restore(self, channel, stack.pop())
            return {"채널": int(channel), "되돌림": True, "남은_되돌리기": len(stack)}
        if not kind:
            raise ToolError("kind 를 골라 주세요.")
        try:
            r = voice_eq.tweak(self, channel, kind)
        except ValueError as e:
            raise ToolError(str(e))
        self._voice_undo(channel).append(r.pop("undo"))
        return r

    # -------------------------------------------------- 컴프 (용도별 시작값·다듬기·빈티지 모델 세부값)
    DYN_LABELS = {"in": "입력 (높일수록 많이 누름)", "out": "출력", "att": "어택", "rel": "릴리즈", "ratio": "비율", "gain": "게인",
                  "mix": "섞는 양 %", "thr": "문턱", "knee": "니", "peak": "피크 리덕션", "comp": "컴프 양", "drive": "드라이브",
                  "hpf": "사이드체인 로우컷", "lim": "리미트"}

    def dyn_raw_params(self, ch):
        """빈티지 컴프(76LA 등)의 세부값 — 콘솔에 있는 그대로 [이름, 값, 표시]"""
        try:
            names = self.w.get(f"/ch/{int(ch)}/dyn")
        except TimeoutError:
            return []
        out = []
        for p in names:
            if p in ("on", "mdl") or p.startswith("$"):
                continue
            try:
                args = self.w.get(f"/ch/{int(ch)}/dyn/{p}")
            except TimeoutError:
                continue
            num = number_of(args)
            out.append({"이름": p, "설명": self.DYN_LABELS.get(p, p), "표시값": text_of(args),
                        "값": num if isinstance(num, (int, float)) and len(args) > 1 else None})
        return out

    def set_dyn_raw(self, channel, param, value):
        ch = int(channel)
        self._check("ch", ch)
        names = {p["이름"] for p in self.dyn_raw_params(ch)}
        if param not in names:
            raise ToolError(f"이 컴프에는 '{param}' 값이 없습니다. 고를 수 있는 것: {', '.join(sorted(names))}")
        cur = self._num_opt(f"/ch/{ch}/dyn/{param}")
        new = number_of(self.w.set(f"/ch/{ch}/dyn/{param}", float(value)))
        return {"채널": ch, "설정": param, "이전": cur, "현재": new}

    def comp_preset(self, channel, preset, preview_only=False):
        import compressor
        self._check("ch", channel)
        try:
            r = compressor.apply(self, channel, preset, preview=bool(preview_only))
        except ValueError as e:
            raise ToolError(str(e))
        if not preview_only:
            self._voice_undo(channel).append(r["undo"])
        r.pop("undo", None)
        return r

    def comp_tweak(self, channel, kind):
        import compressor
        self._check("ch", channel)
        try:
            r = compressor.tweak(self, channel, kind)
        except ValueError as e:
            raise ToolError(str(e))
        self._voice_undo(channel).append(r.pop("undo"))
        return r

    # -------------------------------------------------- 톤 프리셋 (악기·우리 교회 톤·복사)
    def tone_preset(self, channel, preset=None, from_channel=None, preview_only=False):
        import tones
        self._check("ch", channel)
        try:
            if from_channel:
                self._check("ch", from_channel)
                if int(from_channel) == int(channel):
                    raise ToolError("같은 채널로는 복사할 수 없습니다.")
                items = tones.saved_items(tones.capture(self, int(from_channel)))
                title = f"{self._name('ch', int(from_channel)) or '채널 ' + str(from_channel)} 톤 복사"
                why = [f"채널 {from_channel}의 로우컷·EQ·컴프를 그대로 가져옴"]
            elif preset in tones.INSTRUMENTS:
                items, why = tones.instrument_items(preset)
                title = tones.INSTRUMENTS[preset]["label"]
            else:
                t = tones.STORE.find(preset)
                if t is None:
                    names = list(tones.INSTRUMENTS) + [x["name"] for x in tones.STORE.tones]
                    raise ToolError(f"'{preset}' 톤이 없습니다. 고를 수 있는 것: {', '.join(names)}")
                items, title = tones.saved_items(t["values"]), f"우리 교회 톤 ‘{t['name']}’"
                why = [f"{t.get('saved', '')}에 {t.get('source', '')}에서 저장한 톤"]
            r = tones.apply_items(self, channel, items, preview=bool(preview_only))
        except ValueError as e:
            raise ToolError(str(e))
        if not preview_only:
            self._voice_undo(channel).append(r["undo"])
        r.pop("undo", None)
        r.update(preset=title, why=why)
        return r

    def tone_save(self, channel, name):
        import tones
        self._check("ch", channel)
        vals = tones.capture(self, int(channel))
        src = f"{self._name('ch', int(channel)) or '채널'} (채널 {int(channel)})"
        try:
            t = tones.STORE.save(name, vals, src)
        except ValueError as e:
            raise ToolError(str(e))
        return {"저장": t["name"], "항목_수": len([k for k in vals if not k.startswith("_")]), "출처": src}

    # -------------------------------------------------- dispatcher
    def run(self, name, args):
        fn = getattr(self, name, None)
        if name not in {t["name"] for t in TOOLS} or fn is None:
            return f"알 수 없는 도구: {name}", True
        try:
            return json.dumps(fn(**args), ensure_ascii=False), False
        except ToolError as e:
            return str(e), True
        except TimeoutError as e:
            return str(e), True
        except (TypeError, ValueError) as e:
            return f"잘못된 입력: {e}", True
