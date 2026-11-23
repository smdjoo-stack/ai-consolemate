"""Claude 구독(Pro/Max)으로 프로그램 대화창 쓰기 — Claude Code 를 통해 답합니다.

- API 키·충전 없이, Claude 계정 구독으로 대화합니다.
- Claude 데스크톱 앱에 들어 있는 Claude Code(claude.exe)를 찾아 씁니다. (따로 설치한 claude 명령도 됨)
- 처음 한 번 'Claude 계정으로 로그인'(브라우저)이 필요합니다.
- 콘솔 조작은 wing_mcp.py(같은 도구 26개)를 Claude Code 에 연결해서 합니다.
"""

import glob
import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).parent
SERVER = "ai-consolemate"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def find_cli():
    """claude.exe 위치 (가장 최근 버전). 없으면 None."""
    base = os.environ.get("LOCALAPPDATA", "")
    cands = glob.glob(os.path.join(base, "Claude-Data", "*", "claude-code", "*", "*", "claude.exe")) + \
            glob.glob(os.path.join(base, "AnthropicClaude", "**", "claude.exe"), recursive=True)
    cands = [c for c in cands if os.path.isfile(c)]
    if cands:
        return max(cands, key=os.path.getmtime)
    return shutil.which("claude")


def _env():
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)        # 키가 있으면 키(유료 API)로 가 버리므로 빼고 구독 로그인만 씀
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def login_status():
    """(로그인 여부, 설명)"""
    cli = find_cli()
    if not cli:
        return False, "Claude 앱(또는 Claude Code)을 찾지 못했습니다. Claude 데스크톱 앱을 설치해 주세요."
    try:
        r = subprocess.run([cli, "auth", "status"], capture_output=True, text=True, encoding="utf-8",
                           timeout=30, env=_env(), creationflags=NO_WINDOW)
        j = json.loads(r.stdout or "{}")
    except Exception as e:
        return False, f"상태 확인 실패: {e}"
    if j.get("loggedIn"):
        who = j.get("email") or j.get("account", {}).get("email") or ""
        plan = j.get("subscriptionType") or j.get("plan") or ""
        return True, "Claude 계정으로 로그인됨" + (f" ({plan})" if plan else "") + (f" · {who}" if who else "")
    return False, "아직 Claude 계정으로 로그인하지 않았습니다."


def start_login():
    """새 창에서 'claude auth login' 실행 → 브라우저에서 Claude 계정으로 로그인."""
    cli = find_cli()
    if not cli:
        raise RuntimeError("Claude 앱(또는 Claude Code)을 찾지 못했습니다.")
    flags = subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
    subprocess.Popen([cli, "auth", "login"], env=_env(), creationflags=flags, cwd=str(HERE))


def _mcp_config_file():
    py = os.environ.get("CONSOLEMATE_PYTHON") or shutil.which("python") or ""
    import sys
    py = sys.executable or py
    cfg = {"mcpServers": {SERVER: {"command": py, "args": [str(HERE / "wing_mcp.py")], "env": {"PYTHONIOENCODING": "utf-8"}}}}
    p = Path(tempfile.gettempdir()) / "consolemate_mcp.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return str(p)


class SubscriptionClient:
    provider = "subscription"

    def __init__(self):
        self.session_id = None
        self.lock = threading.Lock()

    def reset(self):
        self.session_id = None

    def chat(self, system_text, user_text, timeout=300):
        cli = find_cli()
        if not cli:
            return {"reply": "Claude 앱(Claude Code)을 찾지 못했습니다.", "actions": [], "_error": "Claude 앱 없음"}
        sp = Path(tempfile.gettempdir()) / "consolemate_system.txt"
        sp.write_text(system_text, encoding="utf-8")
        cmd = [cli, "-p", user_text, "--output-format", "stream-json", "--verbose",
               "--mcp-config", _mcp_config_file(), "--strict-mcp-config",
               "--tools", "", "--allowedTools", f"mcp__{SERVER}",
               "--append-system-prompt-file", str(sp), "--max-turns", "20"]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=timeout, env=_env(), cwd=tempfile.gettempdir(), creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired:
            return {"reply": "답이 너무 오래 걸려 멈췄습니다. 다시 말씀해 주세요.", "actions": [], "_error": "구독 응답 시간 초과"}
        actions, result = [], None
        for line in (r.stdout or "").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "assistant":
                for b in (ev.get("message") or {}).get("content") or []:
                    if b.get("type") == "tool_use":
                        actions.append({"tool": b.get("name", "").replace(f"mcp__{SERVER}__", ""), "input": b.get("input"),
                                        "error": False, "result": ""})
            elif ev.get("type") == "user":
                for b in (ev.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and actions:
                        c = b.get("content")
                        text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
                        actions[-1]["result"] = text[:300]
                        actions[-1]["error"] = bool(b.get("is_error"))
            elif ev.get("type") == "result":
                result = ev
        if result is None:
            err = (r.stderr or r.stdout or "").strip()[:300]
            return {"reply": f"Claude 구독 연결 오류: {err or '응답 없음'}", "actions": actions, "_error": "구독 연결 오류"}
        if result.get("session_id"):
            self.session_id = result["session_id"]
        text = (result.get("result") or "").strip()
        if result.get("is_error"):
            if "log" in text.lower() and "in" in text.lower():
                return {"reply": "Claude 계정 로그인이 필요합니다. ⚙ 설정 → 🔑 AI 연결 → 'Claude 계정으로 로그인'을 눌러 주세요.",
                        "actions": actions, "_error": "Claude 구독 로그인 필요"}
            if "limit" in text.lower():
                return {"reply": f"구독 사용량 한도에 걸렸습니다. 잠시 뒤 다시 해 주세요. ({text})", "actions": actions, "_error": "구독 사용량 한도"}
            return {"reply": f"Claude 구독 오류: {text}", "actions": actions, "_error": "구독 오류"}
        return {"reply": text or "(응답 없음)", "actions": actions}
