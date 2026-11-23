"""AI 콘솔메이트 - 말로 요청하면 Claude 가 WING 콘솔을 조작하거나 방법을 알려줍니다.

실행: python app.py  →  브라우저에서 http://localhost:8800
"""

import json
import os
import socket
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import anthropic
except ImportError:  # 보기 전용(구독) 모드에서는 필요 없음
    anthropic = None

from wing_osc import WingClient, number_of
import consoles
from consoles import discover
from wing_tools import TOOLS, NeedConfirm, ToolError, WingTools
from scenes import STORE, SCOPE_DEFAULT, SCOPE_LABELS
import speakers
import manuals
import gemini
import claude_sub

HERE = Path(__file__).parent
MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """당신은 교회 예배 음향을 돕는 'AI 콘솔메이트'입니다. 자신을 소개할 때 이 이름을 쓰세요.
사용자는 음향 전문가가 아닌 봉사자일 수 있습니다. Behringer WING 디지털 콘솔을 도구로 직접 조작할 수 있습니다.

작업 원칙:
- 한국어로, 쉬운 말로 짧게 답하세요. 전문 용어는 처음 나올 때 한 줄로 풀어 주세요.
- 답은 일반 글자로만 표시되는 화면에 나옵니다. **굵게**, # 제목, 표 같은 마크다운 기호는 쓰지 말고, 목록은 "- " 로 시작하는 줄로만 쓰세요.
- 무엇을 바꾸기 전에 먼저 상태를 확인하세요. 채널 이름(list_strips kind=ch)으로 악기를 찾고,
  버스 이름(list_strips kind=bus)으로 어느 모니터인지 찾으세요. 이름이 애매하면 추측하지 말고 후보를 보여주며 물어보세요.
- "모니터에 ○○ 소리 나오게/더 크게/작게" 요청은 해당 채널 → 해당 버스의 센드(set_send)로 처리합니다.
- 채널의 게인·+48V·필터·EQ·컴프·인서트는 get_channel_detail 로 먼저 확인하고 set_channel_param 으로 조절합니다.
  이펙트 랙은 list_effects / set_effect_mix. 입력·출력 단자 연결(ROUTING)은 get_routing 으로 확인하고, set_channel_input / set_output_routing 으로 바꿉니다.
  라우팅 변경은 예배 소리가 통째로 끊길 수 있으니: 먼저 confirmed 없이 호출해 바뀔 내용을 사용자에게 그대로 보여 주고,
  사용자가 분명히 동의했을 때만 confirmed=true 로 다시 호출하세요. 잘못되면 undo_routing 으로 되돌립니다. 예배 중이면 한 번 더 주의를 주세요. 소리를 다듬을 때는 작게(EQ 2~3 dB) 바꾸고 결과를 들어 보라고 하세요.
  +48V는 반드시 사용자 확인 후, 그 채널을 먼저 뮤트하도록 권하세요.
- 마이크 목소리 톤을 잡아 달라는 요청(예: "목사님 핀마이크 60대 남성에 맞춰 줘")은 voice_eq_preset 으로 시작점을 잡고,
  "먹먹해요/안 들려요/쏘아요/얇아요" 같은 느낌은 voice_eq_tweak 으로 한 번에 하나씩 다듬으세요. 성별·나이·마이크 종류를 모르면 물어보세요.
- 악기 톤(킥·베이스·어쿠스틱 기타·피아노 등)은 tone_preset 으로 시작점을 잡고, "이 톤 저장해 줘"는 tone_save,
  "1번 톤을 2번에도 똑같이"는 tone_preset(from_channel=1). 악기 채널도 voice_eq_tweak 의 다듬기·되돌리기를 쓸 수 있습니다.
- '예배 순서' 버튼(찬양, 설교 등)은 list_scenes / save_scene / recall_scene 으로 다룹니다. 화면 위쪽 '예배 순서' 줄에서 사람이 직접 누를 수도 있습니다.
  전환은 사용자가 분명히 요청할 때만 하고, 무엇이 바뀌는지 궁금해하면 preview_only 로 먼저 보여 주세요.
- 메인 출력(main 2~4, 예: CENTER, YOUTUBE 방송)에 보내는 양은 get_main_mix 로 현재 값을 확인한 뒤 set_main_send 로, MAIN(main 1, 예배당) 크기는 채널 페이더(set_fader)로 조절합니다.
  새로 넣을 때는 -10 dB 정도로 켜고, "조금"은 2~3 dB, "많이"는 5~6 dB 정도로 조절하세요.
- 예배 중일 수 있으니 변화는 작게, 단계적으로 하세요. 메인 뮤트나 큰 폭(10 dB 이상) 증가는 사용자 확인 후에만 하세요.
- 바꾼 뒤에는 무엇을 얼마나 바꿨는지(이전 → 이후) 한두 줄로 알려 주세요.
- 소리를 직접 들을 수는 없습니다. 하울링, 소리 안 남 같은 문제는 원인 후보를 확인 순서대로 안내하고,
  콘솔로 확인·조치할 수 있는 부분은 도구로 확인해 주세요. 케이블·전원·무선마이크 배터리처럼 사람이 확인해야 하는 것은 체크리스트로 알려 주세요.
- 할 수 없는 일(씬 불러오기, 출력 패치 변경, EQ 세부 조정 등 도구에 없는 기능)은 솔직히 말하고 콘솔에서 하는 방법을 안내하세요.
- 콘솔 응답이 없다는 오류가 나면 네트워크와 콘솔 설정(SETUP → Remote, OSC 허용, Remote Lock 꺼짐)을 확인하도록 안내하세요.
- 콘솔에서 사람이 직접 하는 방법을 안내할 때는 아래 <console_manual> 참고 자료(공식 사용 설명서 요약)를 우선 따르세요.
  설명서 내용이면 "(설명서 p.숫자)"를 짧게 붙이고, 참고 자료에 "설명서에서 확인 못 함"으로 적힌 내용은 콘솔 화면에서 확인하라고 덧붙이세요.
- 참고 자료가 다른 기종(예: X32, M32)의 설명서이면, 사람이 콘솔에서 하는 방법은 그 자료를 따르고,
  도구로 하는 직접 조작은 WING 계열에서만 된다는 점을 기억하세요."""


# ---------------------------------------------------------------- 설정
def config_path():
    # 시험용: CONSOLEMATE_CONFIG 환경변수로 다른 설정 파일을 쓸 수 있음
    return Path(os.environ.get("CONSOLEMATE_CONFIG") or (HERE / "config.json"))


def update_config(**fields):
    """config.json 의 다른 설정은 그대로 두고 주어진 항목만 바꿈. 바뀐 전체 설정을 돌려줌."""
    path = config_path()
    cfg = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cfg.update(fields)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return cfg


def save_api_key(key: str):
    update_config(anthropic_api_key=key)


def build_system(cfg):
    """기본 안내 + 이 교회의 정보(이름·메모). 메모는 교회마다 다른 내용(버스 용도, 예배 순서 등)."""
    name = (cfg.get("church_name") or "").strip()
    notes = (cfg.get("church_notes") or "").strip()
    mid = cfg.get("knowledge") or manuals.BUILTIN_ID
    info = manuals.find(mid) or manuals.BUILTIN
    body = manuals.text_of(info["id"])
    extra = f'\n\n<console_manual title="{info["title"]}">\n{body}\n</console_manual>' if body else ""
    if name or notes:
        extra += "\n\n<church>\n" + (f"교회 이름: {name}\n" if name else "") + \
                (f"이 교회 음향팀 메모(콘솔 사용 방식, 버스 용도 등 — 우선 참고):\n{notes}\n" if notes else "") + "</church>"
    return SYSTEM_PROMPT + extra


def ai_provider(cfg):
    """쓸 AI 회사. 설정에 정해 두면 그것만 씀(고정) — 다른 회사로 자동으로 바뀌지 않음."""
    p = (cfg.get("ai_provider") or "").strip()
    if p in ("google", "anthropic", "subscription"):
        return p
    return "google" if cfg.get("google_api_key") else "anthropic"


def make_ai_client(cfg):
    """(client, key, provider). 키가 없으면 client=None (보기 전용)."""
    p = ai_provider(cfg)
    if p == "subscription":      # Claude 구독(Pro/Max) — 키 없이 Claude Code 로그인으로
        return (claude_sub.SubscriptionClient() if claude_sub.find_cli() else None), "subscription", p
    if p == "google":
        key = (cfg.get("google_api_key") or "").strip()
        return (gemini.GeminiClient(key, cfg.get("google_model") or "") if key else None), key, p
    key = (cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if anthropic is None:
        key = ""
    return (anthropic.Anthropic(api_key=key) if key else None), key, p


PROVIDER_LABEL = {"google": "Google AI Studio (Gemini)", "anthropic": "Claude API (충전식)", "subscription": "Claude 구독 (Pro/Max)"}


def key_hint(key: str):
    return "" if not key else (key[:7] + "…" + key[-4:] if len(key) > 14 else "설정됨")


def test_api_key(key: str):
    """키가 맞는지 확인 (모델 목록만 조회 - 요금 없음). (결과, 메시지)"""
    try:
        anthropic.Anthropic(api_key=key, max_retries=0, timeout=10).models.list(limit=1)
        return "ok", "키가 확인되었습니다."
    except anthropic.AuthenticationError:
        return "bad", "키가 올바르지 않습니다. 복사할 때 앞뒤가 잘리지 않았는지 확인해 주세요."
    except anthropic.PermissionDeniedError:
        return "bad", "이 키는 사용 권한이 없습니다. Claude Console에서 키 상태를 확인해 주세요."
    except anthropic.APIConnectionError:
        return "offline", "인터넷에 연결되지 않아 키를 확인하지 못했습니다. 키는 저장했고, 인터넷이 되면 바로 쓸 수 있어요."
    except anthropic.APIStatusError as e:
        return "offline", f"Claude 서버 응답 오류({e.status_code})로 확인하지 못했습니다. 키는 저장했습니다."


def load_config():
    path = config_path()
    if not path.exists():
        path.write_text(json.dumps({
            "anthropic_api_key": "",
            "wing_ip": "",
            "web_port": 8800,
            "allow_other_devices": False,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def connect_wing(cfg):
    ip = (cfg.get("wing_ip") or "").strip()
    if not ip:
        print("WING 콘솔을 찾는 중...")
        found = sorted(discover(), key=lambda f: f["ip"].startswith("127."))  # 실제 콘솔 우선
        if not found:
            print("콘솔을 찾지 못했습니다. 콘솔이 켜지면 자동으로 다시 찾습니다.")
            return None, "콘솔을 찾지 못함"
        ip = found[0]["ip"]
        print(f"찾음: {found[0]}")
        return consoles.open_console(ip, found[0].get("family")), ip
    return consoles.open_console(ip, cfg.get("console_family") or None), ip


# ---------------------------------------------------------------- AI 대화
class Assistant:
    def __init__(self, client, tools: WingTools | None):
        self.client = client
        self.tools = tools
        self.system_text = SYSTEM_PROMPT
        self.messages = []
        self.g_history = []      # Google(Gemini) 대화 기록
        self.lock = threading.Lock()
        # 마지막 AI 요청 결과 (상태 표시용)
        self.ai_ok = None
        self.ai_error = ""

    def chat(self, user_text: str):
        result = self._chat(user_text)
        err = result.pop("_error", None)
        self.ai_ok = err is None
        self.ai_error = err or ""
        return result

    def reset(self):
        with self.lock:
            self.messages = []
            self.g_history = []
            if hasattr(self.client, "reset"):
                self.client.reset()

    def _system(self):
        return self.system_text + ("\n\n" + consoles.console_note(self.tools) if self.tools is not None and self.tools.family != "wing" else "")

    def _run_tool(self, name, args):
        if self.tools is None:
            return "WING 콘솔에 연결되어 있지 않습니다. 콘솔 IP 설정을 확인하세요.", True
        return self.tools.run(name, args if isinstance(args, dict) else {})

    def _chat(self, user_text: str):
        if self.client is None:
            return {"reply": "AI가 연결되어 있지 않아 이 화면에서는 대화할 수 없습니다. ⚙ 설정 → 🔑 AI 연결에서 고르세요 (Claude 구독·Claude API·Google).", "actions": []}
        if getattr(self.client, "provider", "") == "subscription":
            with self.lock:
                return self.client.chat(self._system(), user_text)
        if getattr(self.client, "provider", "") == "google":
            with self.lock:
                if len(self.g_history) > 80:        # 너무 길어지면 앞부분 정리
                    self.g_history = []
                return gemini.chat(self.client, self._system(), self.g_history, TOOLS, self._run_tool, user_text)
        with self.lock:
            actions = []
            self.messages.append({"role": "user", "content": user_text})
            for _ in range(15):
                try:
                    response = self.client.beta.messages.create(
                        model=MODEL,
                        max_tokens=16000,
                        betas=["server-side-fallback-2026-07-01"],
                        fallbacks="default",
                        output_config={"effort": "low"},
                        cache_control={"type": "ephemeral"},
                        system=self._system(),
                        tools=TOOLS,
                        messages=self.messages,
                    )
                except anthropic.AuthenticationError:
                    self.messages.pop()
                    return {"reply": "API 키가 올바르지 않습니다. config.json 의 anthropic_api_key 를 확인해 주세요.", "actions": actions, "_error": "API 키가 올바르지 않음"}
                except anthropic.RateLimitError:
                    self.messages.pop()
                    return {"reply": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", "actions": actions, "_error": "요청이 너무 많음 (잠시 후 다시)"}
                except anthropic.APIConnectionError:
                    self.messages.pop()
                    return {"reply": "인터넷 연결을 확인해 주세요 (Claude 서버에 접속할 수 없음).", "actions": actions, "_error": "인터넷 연결 안 됨"}
                except anthropic.APIStatusError as e:
                    self.messages.pop()
                    if "credit balance" in str(e.message).lower():
                        return {"reply": "Claude API 계정의 충전 잔액(크레딧)이 부족해서 AI가 대답할 수 없습니다.\n"
                                         "- console.anthropic.com 에 로그인 → Plans & Billing(결제) → Buy credits 로 충전해 주세요.\n"
                                         "- 충전하면 프로그램을 다시 켜지 않아도 바로 됩니다. 흐름도·직접 조절·예배 순서는 지금도 쓸 수 있어요.\n"
                                         "- 충전 없이 쓰려면: Claude 앱(구독) 채팅에서 말하세요. 'AI 콘솔메이트' 도구가 연결되어 있어 같은 조작을 할 수 있어요.",
                                "actions": actions, "_error": "Claude 크레딧(충전 잔액) 부족 — console.anthropic.com 에서 충전"}
                    return {"reply": f"Claude API 오류 ({e.status_code}): {e.message}", "actions": actions, "_error": f"Claude API 오류 {e.status_code}"}

                self.messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "pause_turn":
                    continue
                if response.stop_reason == "refusal":
                    return {"reply": "이 요청은 처리할 수 없습니다.", "actions": actions}

                tool_uses = [b for b in response.content if b.type == "tool_use"]
                if response.stop_reason != "tool_use" or not tool_uses:
                    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
                    return {"reply": text or "(응답 없음)", "actions": actions}

                results = []
                for tu in tool_uses:
                    if self.tools is None:
                        out, is_err = "WING 콘솔에 연결되어 있지 않습니다. 콘솔 IP 설정을 확인하세요.", True
                    else:
                        args = tu.input if isinstance(tu.input, dict) else {}
                        out, is_err = self.tools.run(tu.name, args)
                    actions.append({"tool": tu.name, "input": tu.input, "error": is_err, "result": out[:300]})
                    results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out, "is_error": is_err})
                self.messages.append({"role": "user", "content": results})
            return {"reply": "작업 단계가 너무 많아 멈췄습니다. 요청을 나눠서 다시 말씀해 주세요.", "actions": actions}


# ---------------------------------------------------------------- 연결 상태 점검
class Health:
    """콘솔·AI 연결 상태를 점검하고, 콘솔이 안 보이면 자동으로 다시 찾습니다."""

    def __init__(self, assistant: Assistant, cfg: dict, status: dict, has_key: bool):
        self.a = assistant
        self.fixed_ip = (cfg.get("wing_ip") or "").strip()
        self.status = status
        self.has_key = has_key
        self.lock = threading.Lock()
        self.fails = 0
        self.last_ok = None
        self.last_discover = 0.0
        self.net_checked = 0.0
        self.net_ok = None

    def _discover(self):
        """콘솔을 다시 찾음 (10초에 한 번까지). 찾으면 새 주소로 바꿈.

        IP를 직접 정해 둔 경우에도, 그 IP에서 답이 없으면 같은 콘솔(이름·일련번호가 같거나,
        네트워크에 실제 콘솔이 하나뿐)을 찾아 새 IP로 옮기고 설정도 고칩니다.
        (공유기가 콘솔 IP를 바꾸는 경우 — 예: .54 → .58)"""
        if time.time() - self.last_discover < 10:
            return
        self.last_discover = time.time()
        # 실제 콘솔을 가짜(연습용, 127.0.0.1)보다 먼저 고름
        found = sorted(discover(timeout=1.2), key=lambda f: f["ip"].startswith("127."))
        if not found:
            return
        pick = found[0]
        if self.fixed_ip:
            cfg = (getattr(self, "state", None) or {}).get("cfg") or {}
            serial, name = cfg.get("console_serial") or "", cfg.get("console_name") or ""
            fam_now = self.a.tools.family if self.a.tools else None
            same = [f for f in found if (serial and f.get("serial") == serial) or (not serial and name and f.get("name") == name)]
            real = [f for f in found if not f["ip"].startswith("127.") and (fam_now is None or f.get("family") == fam_now)]
            if same:
                pick = same[0]
            elif not self.fixed_ip.startswith("127.") and len(real) == 1:
                pick = real[0]
            else:
                return      # 어느 콘솔인지 확실하지 않으면 바꾸지 않음
            if pick["ip"] == self.fixed_ip:
                return
            print(f"콘솔 IP가 바뀌었습니다: {self.fixed_ip} → {pick['ip']} (설정도 고칩니다)")
            self.fixed_ip = pick["ip"]
            new_cfg = update_config(wing_ip=pick["ip"], console_serial=pick.get("serial", ""), console_name=pick.get("name", ""))
            if getattr(self, "state", None) is not None:
                self.state["cfg"] = new_cfg
            self.moved = {"from": cfg.get("wing_ip", ""), "to": pick["ip"], "at": time.time()}
        ip = pick["ip"]
        fam = pick.get("family", "wing")
        if self.a.tools is None or self.a.tools.family != fam:
            self.a.tools = consoles.open_console(ip, fam)
        elif self.a.tools.w.host != ip:
            self.a.tools.w.host = ip
        self.status["family"] = fam
        print(f"콘솔 다시 찾음: {ip}")

    def _internet(self):
        """Claude 서버에 닿는지 (30초마다, 연결만 시도하고 데이터는 보내지 않음)."""
        if time.time() - self.net_checked > 30:
            self.net_checked = time.time()
            try:
                host = gemini.HOST if getattr(self.a.client, "provider", "") == "google" else "api.anthropic.com"
                socket.create_connection((host, 443), timeout=2).close()
                self.net_ok = True
            except OSError:
                self.net_ok = False
        return self.net_ok

    def check(self):
        with self.lock:
            warnings = []
            console = {"state": "down", "ip": "", "latency_ms": None, "message": ""}
            if self.a.tools is None:
                self._discover()
            if self.a.tools is None:
                console["message"] = "콘솔을 찾지 못했습니다"
            else:
                # 상태 점검은 따로 연결을 써서, 큰 요청(이펙트 목록 등)이 도는 동안에도 기다리지 않음
                host = self.a.tools.w.host
                if getattr(self, "_probe", None) is None or self._probe.host != host or type(self._probe) is not type(self.a.tools.w):
                    self._probe = consoles.probe_client(self.a.tools)
                w = self._probe
                console["ip"] = w.host
                console["family"] = self.a.tools.family
                console["model"] = self.a.tools.model_label
                try:
                    t0 = time.perf_counter()
                    ronly = number_of(w.get("/$ctl/OSC/ronly"))
                    console["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                    main_mute = number_of(w.get("/main/1/mute"))
                    self.fails = 0
                    self.last_ok = time.time()
                    console["state"] = "slow" if console["latency_ms"] > 300 else "ok"
                    console["message"] = "응답 느림" if console["state"] == "slow" else "정상"
                    if ronly:
                        warnings.append({"level": "err", "text": "콘솔의 원격 잠금(REMOTE LOCK)이 켜져 있어 이 프로그램에서 조작할 수 없습니다.",
                                         "hint": "콘솔 SETUP → REMOTE 화면에서 REMOTE LOCK을 끄세요."})
                    if main_mute:
                        name = self.a.tools._name("main", 1) or "MAIN"
                        warnings.append({"level": "warn", "text": f"{name}(예배당 메인 스피커)이 뮤트되어 있습니다.",
                                         "hint": "의도한 것이 아니라면 콘솔 오른쪽 메인 페이더의 MUTE를 풀어 주세요."})
                except TimeoutError:
                    self.fails += 1
                    console["message"] = "응답 없음"
                    if self.fails >= 2:
                        self._discover()
                        console["ip"] = self.a.tools.w.host
            moved = getattr(self, "moved", None)
            if moved and time.time() - moved["at"] < 120 and console["state"] != "down":
                warnings.append({"level": "good", "text": f"콘솔 IP가 바뀌어({moved['from']} → {moved['to']}) 자동으로 다시 연결했습니다.",
                                 "hint": "공유기가 콘솔 주소를 바꾼 것이에요. 설정도 새 주소로 고쳐 두었어요."})
            if console["state"] == "down":
                warnings.insert(0, {"level": "err", "text": "콘솔과 통신이 끊겼습니다. 화면의 값이 실제와 다를 수 있습니다.",
                                    "hint": "확인 순서: ① 콘솔 전원 ② 콘솔 뒷면 랜선(공유기 연결) ③ 이 PC의 네트워크 ④ 콘솔 SETUP → REMOTE의 REMOTE LOCK. 다시 연결되면 자동으로 복구됩니다."})
            self.status["connected"] = console["state"] != "down"
            self.status["wing"] = console["ip"]

            ai = {"state": "off", "message": "API 키 없음 (보기 전용)"}
            if self.has_key:
                net = self._internet()
                if net is False:
                    ai = {"state": "down", "message": "인터넷 연결 안 됨"}
                    warnings.append({"level": "warn", "text": "인터넷에 연결되지 않아 AI 대화를 쓸 수 없습니다.",
                                     "hint": "콘솔 조작과 화면은 그대로 쓸 수 있습니다. 이 PC의 인터넷 연결을 확인하세요."})
                elif self.a.ai_ok is False:
                    ai = {"state": "down", "message": self.a.ai_error}
                    warnings.append({"level": "warn", "text": f"AI 대화에 문제가 있습니다: {self.a.ai_error}",
                                     "hint": "console.anthropic.com → Plans & Billing 에서 충전하면 바로 다시 됩니다."
                                     if "크레딧" in self.a.ai_error else "⚙ 설정 → 🔑 API 키에서 키를 확인해 주세요."})
                else:
                    ai = {"state": "ok", "message": {"google": "Gemini", "subscription": "Claude 구독"}.get(
                        getattr(self.a.client, "provider", ""), "Claude") + " 준비됨"}
            ago = None if self.last_ok is None else round(time.time() - self.last_ok, 1)
            return {"console": console, "ai": ai, "warnings": warnings, "last_ok_sec_ago": ago}


# ---------------------------------------------------------------- 웹 서버
def make_handler(assistant: Assistant, status: dict, health: "Health", state: dict):
    page = (HERE / "index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _is_local(self):
            return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

        def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

        # ---------- 예배 순서(씬) ----------
        def _scenes_list(self):
            out = []
            for s in STORE.scenes:
                diff = None
                if assistant.tools is not None:
                    try:
                        diff = len(assistant.tools.diff_state(s.get("values", {})))
                    except TimeoutError:
                        diff = None
                out.append({"id": s["id"], "name": s["name"], "color": s.get("color"), "scope": s.get("scope", {}),
                            "count": len(s.get("values", {})), "diff": diff, "updated": s.get("updated")})
            undo = STORE.last_undo
            self._json({"scenes": out, "active": STORE.active_id, "scopeLabels": SCOPE_LABELS, "scopeDefault": SCOPE_DEFAULT,
                        "undo": {"scene": undo["scene"], "at": undo["at"], "count": len(undo["values"])} if undo else None})

        def _scenes_post(self, action, data):
            t = assistant.tools
            if t is None and action in ("save", "preview", "apply", "undo"):
                return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
            try:
                if action == "save":
                    scope = {k: bool((data.get("scope") or SCOPE_DEFAULT).get(k)) for k in SCOPE_DEFAULT}
                    if not any(scope.values()):
                        raise ValueError("담을 항목을 하나 이상 고르세요.")
                    s = STORE.upsert(data.get("name", ""), t.capture_state(scope), scope, data.get("id"))
                    return self._json({"ok": True, "id": s["id"], "count": len(s["values"])})
                s = STORE.find(data.get("id")) if action not in ("undo",) else None
                if action in ("preview", "apply", "delete", "rename", "move") and s is None:
                    raise KeyError("없는 예배 순서입니다.")
                if action == "preview":
                    d = t.diff_state(s["values"])
                    return self._json({"name": s["name"], "changes": [c["text"] for c in d]})
                if action == "apply":
                    fade = 1000 if data.get("smooth", True) else 0
                    changes, undo = t.apply_state(s["values"], fade)
                    STORE.active_id = s["id"]
                    STORE.last_undo = {"scene": s["name"], "values": undo, "at": time.strftime("%H:%M:%S")}
                    return self._json({"ok": True, "changed": len(changes)})
                if action == "undo":
                    u = STORE.last_undo
                    if not u:
                        raise KeyError("되돌릴 것이 없습니다.")
                    t.apply_state(u["values"], 1000)
                    STORE.last_undo = None
                    STORE.active_id = None
                    return self._json({"ok": True, "scene": u["scene"]})
                if action == "delete":
                    STORE.delete(s["id"])
                elif action == "rename":
                    STORE.rename(s["id"], data.get("name", ""))
                elif action == "move":
                    STORE.move(s["id"], int(data.get("delta", 0)))
                else:
                    return self._json({"error": "알 수 없는 요청"}, 404)
                return self._json({"ok": True})
            except (ValueError, KeyError) as e:
                return self._json({"error": str(e).strip("'\"")}, 400)
            except TimeoutError as e:
                return self._json({"error": str(e)}, 504)

        def do_GET(self):
            if self.path == "/":
                self._send(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/status":
                self._json(status)
            elif self.path == "/api/health":
                self._json(health.check())
            elif self.path == "/api/scenes":
                self._scenes_list()
            elif self.path == "/api/setup":
                cfg = state["cfg"]
                self._json({"setupDone": bool(cfg.get("setup_done")), "churchName": cfg.get("church_name", ""),
                            "notes": cfg.get("church_notes", ""), "wingIp": cfg.get("wing_ip", ""),
                            "connectedIp": assistant.tools.w.host if assistant.tools else "", "hasKey": bool(state["key"]),
                            "canEdit": self._is_local()})
            elif self.path == "/api/discover":
                found = sorted(discover(timeout=1.5), key=lambda f: f["ip"].startswith("127."))
                self._json({"consoles": [dict(f, practice=f["ip"].startswith("127.")) for f in found]})
            elif self.path == "/api/backup":
                if not self._is_local():
                    return self._json({"error": "이 컴퓨터에서만 내보낼 수 있습니다."}, 403)
                cfg = state["cfg"]
                body = json.dumps({"app": "AI 콘솔메이트", "version": 1, "saved": time.strftime("%Y-%m-%d %H:%M"),
                                   "church_name": cfg.get("church_name", ""), "church_notes": cfg.get("church_notes", ""),
                                   "scenes": STORE.scenes, "speakers": speakers.load(),
                                   "manuals": manuals.export_all(), "knowledge": cfg.get("knowledge", ""),
                                   "tones": __import__("tones").STORE.tones},
                                  ensure_ascii=False, indent=1).encode("utf-8")
                from urllib.parse import quote
                fname = quote(f"AI콘솔메이트_설정백업_{time.strftime('%Y%m%d')}.json")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{fname}")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/speakers":
                self._json({"speakers": speakers.load(), "types": {k: {"icon": v[0], "label": v[1]} for k, v in speakers.TYPES.items()}})
            elif self.path == "/api/settings":
                cfg = state["cfg"]
                sub_ok, sub_msg = claude_sub.login_status() if self._is_local() else (False, "")
                self._json({"hasKey": bool(state["key"]), "keyHint": "" if state["key"] == "subscription" else key_hint(state["key"]),
                            "provider": ai_provider(cfg), "providerLabel": PROVIDER_LABEL[ai_provider(cfg)],
                            "googleModel": cfg.get("google_model", ""),
                            "keys": {"google": key_hint(cfg.get("google_api_key", "")),
                                     "anthropic": key_hint(cfg.get("anthropic_api_key", ""))},
                            "subscription": {"cli": bool(claude_sub.find_cli()), "loggedIn": sub_ok, "message": sub_msg},
                            "canEdit": self._is_local(), "sdk": anthropic is not None})
            elif self.path == "/api/manuals":
                cfg = state["cfg"]
                model = ""
                if assistant.tools is not None:
                    try:
                        info = next((f for f in discover(timeout=0.8) if f["ip"] == assistant.tools.w.host), None)
                        model = consoles.model_label(info) if info else assistant.tools.model_label
                    except OSError:
                        pass
                self._json({"items": manuals.list_all(), "active": cfg.get("knowledge") or manuals.BUILTIN_ID,
                            "job": manuals.BUILDER.status(), "consoleModel": model, "hasKey": bool(state["key"]),
                            "canEdit": self._is_local()})
            elif self.path == "/api/voiceeq":
                import voice_eq
                self._json(voice_eq.options())
            elif self.path == "/api/tones":
                import tones
                self._json(tones.options())
            elif self.path.startswith("/api/manuals/view"):
                from urllib.parse import urlparse, parse_qs
                mid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
                if not manuals.find(mid):
                    return self._json({"error": "없는 자료입니다."}, 404)
                self._send(200, manuals.text_of(mid).encode("utf-8"), "text/plain; charset=utf-8")
            elif self.path.startswith("/api/channel"):
                from urllib.parse import urlparse, parse_qs
                if assistant.tools is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    ch = int((parse_qs(urlparse(self.path).query).get("ch") or ["0"])[0])
                    self._json(assistant.tools.channel_detail(ch))
                except (ToolError, ValueError) as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path.startswith("/api/inputs") or self.path.startswith("/api/outputs") or self.path == "/api/route/state":
                from urllib.parse import urlparse, parse_qs
                t = assistant.tools
                if t is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    if self.path.startswith("/api/inputs"):
                        self._json({"groups": t.input_catalog()})
                    elif self.path.startswith("/api/outputs"):
                        g = (parse_qs(urlparse(self.path).query).get("grp") or ["A"])[0]
                        self._json(t.outputs_in_group(g))
                    else:
                        u = getattr(t, "last_route_undo", None)
                        self._json({"undo": u["text"] if u else None,
                                    "outGroups": [{"grp": g, "label": l, "count": c} for g, c, l in t.OUT_GROUPS]})
                except ToolError as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path == "/api/effects":
                if assistant.tools is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    self._json(assistant.tools.list_effects())
                except ToolError as e:
                    self._json({"error": str(e), "unsupported": True}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path == "/api/routing":
                if assistant.tools is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    self._json(assistant.tools.routing_overview())
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            else:
                self._send(404, b"{}")

        def _manuals_post(self, data, raw=None):
            if not self._is_local():
                return self._json({"error": "설명서 자료는 이 프로그램이 켜진 컴퓨터에서만 바꿀 수 있습니다."}, 403)
            act = self.path.rsplit("/", 1)[-1]
            client = assistant.client
            needs_ai = act in ("search", "build")
            if needs_ai and client is None:
                return self._json({"error": "이 기능은 Claude API 키가 필요합니다. ⚙ 설정 → API 키에서 넣어 주세요."}, 400)
            if getattr(client, "provider", "") in ("google", "subscription"):
                if needs_ai:
                    return self._json({"error": "설명서 찾기·요약 만들기는 지금 Claude(Anthropic)로만 됩니다. "
                                                "Google 고정 상태에서는 이미 만든 설명서 요약을 고르거나 보기만 할 수 있어요."}, 400)
                client = None       # 파일 읽기는 되고, 요금 계산만 생략

            def use(mid):
                state["cfg"] = update_config(knowledge=mid)
                assistant.system_text = build_system(state["cfg"])
                assistant.reset()

            try:
                if act == "upload":
                    from urllib.parse import unquote
                    name = unquote(self.headers.get("X-Filename") or "manual.pdf")
                    model = unquote(self.headers.get("X-Model") or "")
                    return self._json(manuals.BUILDER.prepare(client, MODEL, raw, name, name, model))
                if act == "fetch":
                    blob, name = manuals.download(str(data.get("url", "")))
                    return self._json(manuals.BUILDER.prepare(client, MODEL, blob, name, str(data["url"]), str(data.get("model", ""))))
                if act == "search":
                    m = str(data.get("model", "")).strip()
                    if not m:
                        raise ValueError("콘솔 모델 이름을 넣어 주세요 (예: Behringer X32).")
                    return self._json(manuals.search(client, m, MODEL))
                if act == "build":
                    model = str(data.get("model", "")).strip() or "콘솔"
                    manuals.BUILDER.start(client, MODEL, str(data.get("token", "")), str(data.get("title", "")).strip(), model,
                                          on_done=use if data.get("use", True) else (lambda mid: None))
                    return self._json({"ok": True})
                if act == "use":
                    mid = str(data.get("id", ""))
                    if not manuals.find(mid):
                        raise ValueError("없는 자료입니다.")
                    use(mid)
                    return self._json({"ok": True})
                if act == "delete":
                    mid = str(data.get("id", ""))
                    manuals.delete(mid)
                    if (state["cfg"].get("knowledge") or "") == mid:
                        use(manuals.BUILTIN_ID)
                    return self._json({"ok": True})
                return self._json({"error": "알 수 없는 요청"}, 404)
            except (ValueError, KeyError, OSError) as e:
                return self._json({"error": str(e).strip("'\"")}, 400)
            except Exception as e:      # Claude API 오류 등
                msg = getattr(e, "message", None) or str(e)
                return self._json({"error": f"처리하지 못했습니다: {msg}"}, 502)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            if self.path == "/api/manuals/upload":
                if length > manuals.MAX_FILE:
                    return self._json({"error": "파일이 너무 큽니다(80 MB 초과)."}, 413)
                return self._manuals_post({}, self.rfile.read(length))
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json({"error": "bad json"}, 400)
            if self.path == "/api/chat":
                text = str(data.get("message", "")).strip()
                if not text:
                    return self._json({"reply": "", "actions": []})
                self._json(assistant.chat(text))
            elif self.path == "/api/set":
                if assistant.tools is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                level = data.get("level")
                try:
                    level = None if level is None else float(level)
                    assistant.tools.control(data.get("target") or {}, level=level, on=data.get("on"),
                                            confirmed=bool(data.get("confirmed")))
                    self._json({"ok": True})
                except NeedConfirm as e:
                    self._json({"needConfirm": True, "error": str(e)}, 409)
                except (ToolError, ValueError, KeyError, TypeError) as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path == "/api/settings":
                if not self._is_local():
                    return self._json({"error": "API 키는 이 프로그램이 켜진 컴퓨터에서만 바꿀 수 있습니다."}, 403)
                # provider: "google" | "anthropic" — 고른 회사로 고정해 저장 (자동 전환 없음)
                provider = data.get("provider") or ("anthropic" if "anthropic_api_key" in data else ai_provider(state["cfg"]))
                if provider not in ("google", "anthropic", "subscription"):
                    return self._json({"error": "알 수 없는 AI 종류입니다."}, 400)
                raw = data.get("key", data.get("anthropic_api_key"))
                key = None if raw is None else str(raw).strip().strip('"').strip("'")
                fields = {"ai_provider": provider}
                result, msg = "ok", f"{PROVIDER_LABEL[provider]}로 고정했습니다."
                if provider == "subscription":
                    if not claude_sub.find_cli():
                        return self._json({"error": "Claude 데스크톱 앱(Claude Code)을 찾지 못했습니다. Claude 앱을 설치해 주세요."}, 400)
                    ok, why = claude_sub.login_status()
                    if not ok:
                        result, msg = "nologin", "Claude 구독으로 고정했어요. 이제 'Claude 계정으로 로그인'을 한 번 해 주세요."
                    else:
                        msg = f"Claude 구독으로 고정했어요. {why}"
                elif provider == "google":
                    if key:
                        if not key.startswith("AIza") or len(key) < 30 or any(c.isspace() for c in key):
                            return self._json({"error": "Google AI Studio 키는 AIza 로 시작하는 긴 글자입니다. 다시 복사해 붙여 넣어 주세요."}, 400)
                        result, msg, model = gemini.test_key(key)
                        if result == "bad":
                            return self._json({"error": msg}, 400)
                        fields["google_api_key"] = key
                        if model:
                            fields["google_model"] = model
                    elif key == "":
                        fields["google_api_key"] = ""
                        result, msg = "removed", "Google 키를 지웠습니다. 이제 보기 전용으로 동작합니다."
                else:
                    if anthropic is None:
                        return self._json({"error": "AI 기능 부품(anthropic)이 설치되어 있지 않습니다. 실행.bat 으로 다시 켜 주세요."}, 500)
                    if key:
                        if not key.startswith("sk-ant-") or len(key) < 30 or any(c.isspace() for c in key):
                            return self._json({"error": "Claude API 키는 sk-ant- 로 시작하는 긴 글자입니다. 다시 복사해 붙여 넣어 주세요."}, 400)
                        result, msg = test_api_key(key)
                        if result == "bad":
                            return self._json({"error": msg}, 400)
                        fields["anthropic_api_key"] = key
                    elif key == "":
                        fields["anthropic_api_key"] = ""
                        result, msg = "removed", "Claude 키를 지웠습니다. 이제 보기 전용으로 동작합니다."
                state["cfg"] = update_config(**fields)
                client, active_key, _ = make_ai_client(state["cfg"])
                if client is None and result == "ok":
                    result, msg = "nokey", f"{PROVIDER_LABEL[provider]}로 고정했지만 키가 없습니다. 키를 넣어 주세요."
                state["key"] = active_key
                assistant.client = client
                assistant.reset()
                assistant.ai_ok, assistant.ai_error = None, ""
                health.has_key = bool(active_key)
                status["ai"] = bool(active_key)
                status["provider"] = provider
                self._json({"ok": True, "result": result, "message": msg, "keyHint": key_hint(active_key),
                            "provider": provider, "googleModel": state["cfg"].get("google_model", "")})
            elif self.path == "/api/sublogin":
                if not self._is_local():
                    return self._json({"error": "이 프로그램이 켜진 컴퓨터에서만 할 수 있습니다."}, 403)
                try:
                    claude_sub.start_login()
                    self._json({"ok": True, "message": "로그인 창과 브라우저가 열려요. Claude 계정으로 로그인한 뒤 '로그인 확인'을 누르세요."})
                except (RuntimeError, OSError) as e:
                    self._json({"error": str(e)}, 400)
            elif self.path.startswith("/api/route/"):
                t = assistant.tools
                if t is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    act = self.path.rsplit("/", 1)[-1]
                    if act == "input":
                        r = t.set_channel_input(data.get("ch"), data.get("grp"), data.get("num"), confirmed=bool(data.get("confirmed")))
                    elif act == "output":
                        r = t.set_output_routing(data.get("og"), data.get("on"), data.get("source"), data.get("sn") or 1,
                                                 stereo=bool(data.get("stereo", True)), confirmed=bool(data.get("confirmed")))
                    elif act == "undo":
                        r = t.undo_routing()
                    else:
                        return self._json({"error": "알 수 없는 요청"}, 404)
                    self._json({"ok": True, "result": r})
                except NeedConfirm as e:
                    self._json({"needConfirm": True, "error": str(e)}, 409)
                except (ToolError, ValueError, TypeError) as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path in ("/api/setup", "/api/restore"):
                if not self._is_local():
                    return self._json({"error": "설정은 이 프로그램이 켜진 컴퓨터에서만 바꿀 수 있습니다."}, 403)
                try:
                    fields = {}
                    if self.path == "/api/restore":
                        b = data.get("backup") or {}
                        if b.get("app") != "AI 콘솔메이트":
                            raise ValueError("AI 콘솔메이트 설정 백업 파일이 아닙니다.")
                        parts = set(data.get("parts") or ["church", "scenes", "speakers"])
                        if "church" in parts:
                            fields.update(church_name=str(b.get("church_name", ""))[:40], church_notes=str(b.get("church_notes", ""))[:4000])
                        if "scenes" in parts and isinstance(b.get("scenes"), list):
                            with STORE.lock:
                                STORE.scenes = b["scenes"]
                                STORE.active_id = None
                                STORE._write()
                        if "speakers" in parts and isinstance(b.get("speakers"), dict):
                            sp = b["speakers"]
                            speakers.save_many([{"key": k, "name": ""} for k in speakers.load()])     # 비우고
                            speakers.save_many([{"key": k, "name": v.get("name", ""), "type": v.get("type")} for k, v in sp.items()])
                        if "tones" in parts and isinstance(b.get("tones"), list):
                            __import__("tones").STORE.replace_all(b["tones"])
                        if "manuals" in parts and isinstance(b.get("manuals"), list):
                            manuals.import_all(b["manuals"])
                            if b.get("knowledge") and manuals.find(b["knowledge"]):
                                fields["knowledge"] = b["knowledge"]
                    else:
                        if "church_name" in data:
                            fields["church_name"] = str(data["church_name"]).strip()[:40]
                        if "notes" in data:
                            fields["church_notes"] = str(data["notes"])[:4000]
                        if data.get("setup_done"):
                            fields["setup_done"] = True
                        if "wing_ip" in data:
                            ip = str(data["wing_ip"]).strip()
                            if ip and not all(p.isdigit() and 0 <= int(p) <= 255 for p in ip.split(".")) or (ip and ip.count(".") != 3):
                                raise ValueError("IP 주소 형식이 아닙니다 (예: 192.168.0.10).")
                            fields["wing_ip"] = ip
                            # 바로 그 콘솔로 연결 (비우면 자동 찾기)
                            target = ip
                            if not target:
                                found = sorted(discover(timeout=1.5), key=lambda f: f["ip"].startswith("127."))
                                target = found[0]["ip"] if found else ""
                            if target:
                                fam = None if ip else (found[0].get("family") if found else None)
                                assistant.tools = consoles.open_console(target, fam)
                                status["family"] = assistant.tools.family
                                fields["console_family"] = assistant.tools.family
                                # 같은 콘솔을 나중에 IP가 바뀌어도 알아볼 수 있게 이름·일련번호를 기억
                                info = next((f for f in (found if not ip else discover(timeout=1.0)) if f["ip"] == target), None)
                                if info:
                                    fields["console_serial"] = info.get("serial", "")
                                    fields["console_name"] = info.get("name", "")
                            health.fixed_ip = ip
                    if fields:
                        state["cfg"] = update_config(**fields)
                        assistant.system_text = build_system(state["cfg"])
                    self._json({"ok": True, "connectedIp": assistant.tools.w.host if assistant.tools else ""})
                except (ValueError, OSError) as e:
                    self._json({"error": str(e)}, 400)
            elif self.path.startswith("/api/manuals/"):
                self._manuals_post(data)
            elif self.path.startswith("/api/voiceeq/"):
                t = assistant.tools
                if t is None:
                    return self._json({"error": "콘솔에 연결되어 있지 않습니다."}, 503)
                act = self.path.rsplit("/", 1)[-1]
                try:
                    ch = int(data.get("ch") or 0)
                    if act in ("preview", "apply"):
                        r = t.voice_eq_preset(ch, data.get("gender"), data.get("age"), data.get("mic") or "handheld",
                                              data.get("use") or "speech", preview_only=(act == "preview"))
                    elif act in ("tone_preview", "tone_apply"):
                        r = t.tone_preset(ch, preset=data.get("preset"), from_channel=data.get("from") or None,
                                          preview_only=(act == "tone_preview"))
                    elif act == "tone_save":
                        r = t.tone_save(ch, data.get("name"))
                    elif act == "tone_delete":
                        import tones
                        tones.STORE.delete(data.get("id"))
                        r = {"ok": True}
                    elif act == "tweak":
                        r = t.voice_eq_tweak(ch, kind=data.get("kind"))
                    elif act == "undo":
                        r = t.voice_eq_tweak(ch, undo=True)
                    elif act == "ab":       # EQ 껐다 켜서 비교 듣기
                        r = t.set_channel_param(ch, "eq_on", 1 if data.get("on") else 0)
                    else:
                        return self._json({"error": "알 수 없는 요청"}, 404)
                    r = dict(r) if isinstance(r, dict) else {"result": r}
                    r["undoCount"] = len(t._voice_undo(ch))
                    self._json({"ok": True, "result": r})
                except (ToolError, ValueError, TypeError) as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path == "/api/speakers":
                try:
                    self._json({"ok": True, "speakers": speakers.save_many(data.get("items") or [])})
                except (ValueError, OSError) as e:
                    self._json({"error": str(e)}, 400)
            elif self.path == "/api/fxparam":
                if assistant.tools is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    self._json({"ok": True, "result": assistant.tools.set_effect_param(data.get("slot"), str(data.get("param", "")), data.get("value"))})
                except (ToolError, ValueError, TypeError) as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path in ("/api/param", "/api/fxmix"):
                if assistant.tools is None:
                    return self._json({"error": "WING 콘솔에 연결되어 있지 않습니다."}, 503)
                try:
                    if self.path == "/api/param":
                        r = assistant.tools.set_channel_param(data.get("ch"), str(data.get("key", "")), data.get("value"),
                                                             confirmed=bool(data.get("confirmed")))
                    else:
                        r = assistant.tools.set_effect_mix(data.get("slot"), data.get("value"))
                    self._json({"ok": True, "result": r})
                except NeedConfirm as e:
                    self._json({"needConfirm": True, "error": str(e)}, 409)
                except (ToolError, ValueError, KeyError, TypeError) as e:
                    self._json({"error": str(e)}, 400)
                except TimeoutError as e:
                    self._json({"error": str(e)}, 504)
            elif self.path.startswith("/api/scenes/"):
                self._scenes_post(self.path.rsplit("/", 1)[-1], data)
            elif self.path == "/api/reset":
                assistant.reset()
                self._json({"ok": True})
            else:
                self._send(404, b"{}")

    return Handler


def already_running(port):
    """이미 켜져 있으면 True (두 번 눌러 두 개가 뜨는 것을 막음)."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    cfg = load_config()
    port = int(cfg.get("web_port") or 8800)
    if already_running(port):
        print("AI 콘솔메이트가 이미 켜져 있습니다. 화면만 다시 엽니다.")
        webbrowser.open(f"http://localhost:{port}")
        return
    ai_client, key, provider = make_ai_client(cfg)
    wing, where = connect_wing(cfg)
    status = {"connected": wing is not None, "wing": where, "ai": bool(key), "provider": provider,
              "family": wing.family if wing is not None else "wing"}
    print(f"AI: {PROVIDER_LABEL[provider]} (고정)")
    if not key:
        print("API 키가 없어 '보기 전용'으로 실행합니다. 대화를 쓰려면 ⚙ 설정 → API 키에서 키를 넣어 주세요.")
    if wing is not None:
        try:
            wing.w.get("/ch/1/name")
            print(f"WING 연결 확인: {where}")
        except TimeoutError:
            status["connected"] = False
            status["wing"] = f"{where} (응답 없음)"
            print(f"경고: {where} 에서 응답이 없습니다. 콘솔 IP 와 OSC 원격 설정을 확인하세요.")

    assistant = Assistant(ai_client, wing)
    assistant.system_text = build_system(cfg)
    host = "0.0.0.0" if cfg.get("allow_other_devices") else "127.0.0.1"
    health = Health(assistant, cfg, status, bool(key))
    state = {"key": key, "cfg": cfg}
    health.state = state
    # Windows 에서는 기본 설정이면 같은 포트를 두 프로그램이 함께 열 수 있어 막아 둠
    ThreadingHTTPServer.allow_reuse_address = False
    try:
        server = ThreadingHTTPServer((host, port), make_handler(assistant, status, health, state))
    except OSError:
        print(f"{port} 번 포트를 이미 다른 프로그램이 쓰고 있습니다. AI 콘솔메이트가 이미 켜져 있다면 화면만 엽니다.")
        webbrowser.open(f"http://localhost:{port}")
        return
    url = f"http://localhost:{port}"
    print(f"AI 콘솔메이트 실행 중: {url}  (종료: Ctrl+C)")
    if cfg.get("open_browser", True):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
