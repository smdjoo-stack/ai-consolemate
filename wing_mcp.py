"""Claude 앱(구독)에 연결하는 콘솔 조작 도구 서버 (MCP).

Claude 데스크톱 앱이 이 파일을 자동으로 실행합니다. 직접 실행할 필요는 없습니다.
- API 키·크레딧 없이 Claude 구독(Pro/Max)으로 대화하며 콘솔을 조작합니다.
- 프로그램 화면(흐름도)과 같은 도구(wing_tools.TOOLS)를 모두 씁니다: 모니터·볼륨·채널 설정·목소리 EQ·톤 프리셋·
  라우팅·이펙트·예배 순서 등.
- 콘솔은 config.json 의 wing_ip(비어 있으면 자동 찾기)로 연결하고, IP가 바뀌면 다시 찾습니다.
- 예배 순서 버튼·우리 교회 톤은 프로그램과 같은 파일(scenes.json, tones.json)을 씁니다.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

import consoles
from wing_tools import TOOLS

BASE_RULES = """교회 예배 음향 콘솔(Behringer WING / X32 / Midas M32)을 조작하는 'AI 콘솔메이트' 도구입니다. 사용자는 음향 비전문가 봉사자일 수 있습니다.
- 쉬운 한국어로 짧게 답하고, 전문 용어는 처음 나올 때 한 줄로 풀어 주세요.
- 바꾸기 전에 상태를 확인하세요. 악기는 list_strips(kind="ch"), 모니터는 list_strips(kind="bus") 의 이름으로 찾고, 애매하면 후보를 보여 주며 물어보세요.
- "○○ 모니터에 △△ 넣어/키워/줄여" 는 set_send, CENTER·YOUTUBE 같은 메인 출력은 get_main_mix → set_main_send, MAIN 크기는 채널 페이더(set_fader).
- 목소리 톤은 voice_eq_preset(성별·나이·마이크·용도) 로 시작점을 잡고 voice_eq_tweak 으로 한 번에 하나씩 다듬기. 악기 톤은 tone_preset, 저장은 tone_save.
- 컴프(크기를 고르게)는 comp_preset(용도별) → comp_tweak(들쭉날쭉/답답/출렁…). 76LA 같은 빈티지 모델은 set_dyn_raw.
- 라우팅 변경은 소리가 통째로 끊길 수 있으니 먼저 confirmed 없이 호출해 바뀔 내용을 보여 주고, 사용자가 분명히 동의했을 때만 confirmed=true.
- 예배 중일 수 있으니 작게, 단계적으로. 메인 뮤트·+48V·10 dB 넘는 증가는 사용자 확인 후에만.
- 바꾼 뒤에는 이전 → 이후 값을 한두 줄로 알려 주세요. 소리를 직접 들을 수는 없으니 들어 보고 알려 달라고 하세요.
- 콘솔 사용법은 get_console_manual 로 공식 설명서 요약을 찾아 안내하고, 설명서 내용이면 (설명서 p.숫자)를 붙이세요.
- 프로그램 화면(브라우저의 흐름도)에도 바뀐 값이 자동으로 보입니다."""


def _cfg():
    p = Path(os.environ.get("CONSOLEMATE_CONFIG") or (HERE / "config.json"))
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _instructions():
    cfg = _cfg()
    extra = ""
    if cfg.get("church_name") or cfg.get("church_notes"):
        extra = "\n\n이 교회 정보(우선 참고):\n" + (f"교회 이름: {cfg['church_name']}\n" if cfg.get("church_name") else "") + \
                (cfg.get("church_notes") or "")
    return BASE_RULES + extra


server = Server("ai-consolemate", instructions=_instructions())
_tools = None


def tools(refresh=False):
    """콘솔 연결 (없거나 응답이 없으면 다시 찾기)."""
    global _tools
    if _tools is not None and not refresh:
        return _tools
    cfg = _cfg()
    ip = (cfg.get("wing_ip") or "").strip()
    fam = cfg.get("console_family") or None
    found = consoles.discover(timeout=1.5)
    real = [f for f in found if not f["ip"].startswith("127.")]
    if ip and not any(f["ip"] == ip for f in found):
        same = [f for f in real if cfg.get("console_serial") and f.get("serial") == cfg.get("console_serial")]
        if same or len(real) == 1:
            ip, fam = (same or real)[0]["ip"], (same or real)[0].get("family")
    if not ip:
        if not found:
            raise RuntimeError("콘솔을 찾지 못했습니다. 콘솔 전원·랜선·같은 공유기 연결을 확인해 주세요.")
        ip, fam = found[0]["ip"], found[0].get("family")
    _tools = consoles.open_console(ip, fam)
    return _tools


MANUAL_TOOL = types.Tool(
    name="get_console_manual",
    description="콘솔 공식 사용 설명서 요약(쪽 번호 포함)을 봅니다. 사람이 콘솔에서 직접 하는 방법을 안내할 때 먼저 찾아보세요. "
                "keyword 를 주면 그 단어가 들어간 부분만 돌려줍니다.",
    inputSchema={"type": "object", "properties": {"keyword": {"type": "string"}}},
)


def manual_text(keyword=""):
    import manuals
    cfg = _cfg()
    text = manuals.text_of(cfg.get("knowledge") or manuals.BUILTIN_ID)
    if not keyword:
        return text
    secs = [s for s in text.split("\n## ") if keyword.lower() in s.lower()]
    return ("\n## ".join(secs) if secs else f"'{keyword}'가 들어간 부분이 없습니다. 전체 목차:\n" +
            "\n".join(l for l in text.splitlines() if l.startswith("## ")))[:20000]


@server.list_tools()
async def list_tools():
    return [types.Tool(name=t["name"], description=t["description"], inputSchema=t["input_schema"]) for t in TOOLS] + [MANUAL_TOOL]


def _run(name, args):
    if name == "get_console_manual":
        return manual_text((args or {}).get("keyword", "")), False
    out, is_err = tools().run(name, args or {})
    if is_err and "응답 없음" in out:         # 콘솔 IP가 바뀌었을 수 있음 → 다시 찾아 한 번 더
        out, is_err = tools(refresh=True).run(name, args or {})
    return out, is_err


@server.call_tool()
async def call_tool(name, arguments):
    out, is_err = await asyncio.to_thread(_run, name, arguments or {})
    if is_err:
        raise RuntimeError(out)
    return [types.TextContent(type="text", text=out)]


async def main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
