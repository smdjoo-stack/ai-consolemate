"""Claude 앱(구독)에 연결하는 WING 조작 도구 서버 (MCP).

Claude 데스크톱 앱이 이 파일을 자동으로 실행합니다. 직접 실행할 필요는 없습니다.
콘솔 IP 는 같은 폴더의 config.json 의 wing_ip 를 사용합니다(비어 있으면 자동 검색).
"""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from wing_osc import WingClient, discover
from wing_tools import WingTools

HERE = Path(__file__).parent

INSTRUCTIONS = """교회 예배 음향용 Behringer WING 콘솔을 조작하는 도구입니다. 사용자는 음향 비전문가 봉사자일 수 있습니다.
- 쉬운 한국어로 짧게 답하고, 전문 용어는 한 줄로 풀어 주세요.
- 바꾸기 전에 상태를 확인하세요. 악기는 list_strips(kind="ch") 의 채널 이름으로, 모니터는 list_strips(kind="bus") 의 버스 이름으로 찾습니다. 애매하면 후보를 보여주고 물어보세요.
- "○○ 모니터에 △△ 소리 넣어/키워/줄여/빼" 요청은 set_send(채널→버스)로 처리합니다. 새로 넣을 때는 -10 dB 로 켜고, "조금" 2~3 dB, "많이" 5~6 dB.
- 예배 중일 수 있으니 작게, 단계적으로 바꾸세요. 메인 뮤트와 10 dB 넘는 증가는 사용자 확인 후 confirmed=true 로만 하세요.
- 바꾼 뒤에는 이전 → 이후 값을 한두 줄로 알려 주세요.
- 소리를 직접 들을 수 없으니, 하울링·소리 안 남 같은 문제는 확인 순서를 안내하고 콘솔에서 확인 가능한 것은 도구로 확인하세요.
- 도구에 없는 기능(씬 불러오기, 출력 패치, EQ 세부 조정)은 콘솔에서 하는 방법을 안내하세요."""

mcp = FastMCP("AI 콘솔메이트", instructions=INSTRUCTIONS)
_tools = None


def tools() -> WingTools:
    global _tools
    if _tools is None:
        cfg_path = HERE / "config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        ip = (cfg.get("wing_ip") or "").strip()
        if not ip:
            found = discover()
            if not found:
                raise RuntimeError("WING 콘솔을 찾지 못했습니다. 네트워크 연결을 확인하거나 config.json 의 wing_ip 에 콘솔 IP 를 적어 주세요.")
            ip = found[0]["ip"]
        _tools = WingTools(WingClient(ip))
    return _tools


def call(name: str, **args) -> str:
    args = {k: v for k, v in args.items() if v is not None}
    out, is_err = tools().run(name, args)
    if is_err:
        raise RuntimeError(out)
    return out


@mcp.tool()
def list_strips(kind: str) -> str:
    """채널/버스 등의 이름, 페이더(dB), 뮤트 상태 목록. 어떤 채널이 어떤 악기인지, 어떤 버스가 어떤 모니터인지 찾을 때 먼저 사용.

    Args:
        kind: ch(입력 채널), bus(버스: 모니터 믹스 등), main(메인), dca, aux, mtx 중 하나
    """
    return call("list_strips", kind=kind)


@mcp.tool()
def get_monitor_mix(bus: int) -> str:
    """특정 버스(모니터 스피커/인이어)에 어떤 채널이 얼마나 보내지고 있는지 확인.

    Args:
        bus: 버스 번호 1~16
    """
    return call("get_monitor_mix", bus=bus)


@mcp.tool()
def set_send(channel: int, bus: int, on: bool | None = None, level_db: float | None = None, confirmed: bool = False) -> str:
    """입력 채널 소리를 버스(모니터)로 보내는 양을 설정. 모니터에 악기 소리를 넣으려면 on=true 와 level_db 를 함께 지정.

    Args:
        channel: 입력 채널 번호 1~40
        bus: 버스(모니터) 번호 1~16
        on: 센드 켜기/끄기 (바꾸지 않으려면 생략)
        level_db: 센드 레벨 dB, -144(없음)~+10, 0 이 기준. 새로 넣을 때는 -10 부터.
        confirmed: 10 dB 넘게 올리는 큰 변경을 사용자가 확인했으면 true
    """
    return call("set_send", channel=channel, bus=bus, on=on, level_db=level_db, confirmed=confirmed)


@mcp.tool()
def set_fader(kind: str, index: int, db: float, confirmed: bool = False) -> str:
    """페이더를 지정한 dB(-144~+10)로 맞춤. 조금 올리고 내릴 때는 adjust_fader 사용.

    Args:
        kind: ch, aux, bus, main, mtx, dca 중 하나
        index: 번호
        db: 목표 dB
        confirmed: 10 dB 넘게 올리는 큰 변경을 사용자가 확인했으면 true
    """
    return call("set_fader", kind=kind, index=index, db=db, confirmed=confirmed)


@mcp.tool()
def adjust_fader(kind: str, index: int, delta_db: float, confirmed: bool = False) -> str:
    """페이더를 현재 값에서 delta_db 만큼 올리거나 내림(예: 3, -2).

    Args:
        kind: ch, aux, bus, main, mtx, dca 중 하나
        index: 번호
        delta_db: 변화량 dB
        confirmed: 큰 변경을 사용자가 확인했으면 true
    """
    return call("adjust_fader", kind=kind, index=index, delta_db=delta_db, confirmed=confirmed)


@mcp.tool()
def set_mute(kind: str, index: int, muted: bool, confirmed: bool = False) -> str:
    """뮤트 켜기/끄기. 메인(main) 뮤트는 예배당 전체 소리가 꺼지므로 사용자 확인 후 confirmed=true 로만 호출.

    Args:
        kind: ch, aux, bus, main, mtx, dca 중 하나
        index: 번호
        muted: true=뮤트, false=뮤트 해제
        confirmed: 사용자가 확인했으면 true
    """
    return call("set_mute", kind=kind, index=index, muted=muted, confirmed=confirmed)


@mcp.tool()
def set_low_cut(channel: int, on: bool, freq_hz: float | None = None) -> str:
    """입력 채널 로우컷(HPa) 켜기/끄기와 주파수(20~2000 Hz) 설정. 말소리 웅웅거림, 진동 소음, 저역 하울링에 사용.

    Args:
        channel: 입력 채널 번호 1~40
        on: 로우컷 켜기/끄기
        freq_hz: 차단 주파수 Hz (바꾸지 않으려면 생략)
    """
    return call("set_low_cut", channel=channel, on=on, freq_hz=freq_hz)


if __name__ == "__main__":
    mcp.run()
