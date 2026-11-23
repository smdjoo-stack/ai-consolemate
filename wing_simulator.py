"""콘솔 없이 테스트하기 위한 가짜 WING.

실행: python wing_simulator.py
그 다음 config.json 의 "wing_ip" 를 "127.0.0.1" 로 두고 app.py 를 실행하면 됩니다.
실제 콘솔의 모든 동작을 흉내 내지는 않습니다(이름·페이더·뮤트·센드 정도).
"""

import socket
import threading

from wing_osc import OSC_PORT, DISCOVERY_PORT, decode, encode

state = {}

CH_NAMES = {
    1: "목사님 핀마이크", 2: "강대상 마이크", 3: "인도자 보컬", 4: "싱어1", 5: "싱어2",
    6: "싱어3", 7: "어쿠스틱기타", 8: "일렉기타", 9: "베이스", 10: "건반 L",
    11: "건반 R", 12: "킥", 13: "스네어", 14: "오버헤드 L", 15: "오버헤드 R",
}
BUS_NAMES = {1: "인도자 모니터", 2: "싱어 모니터", 3: "드럼 모니터", 4: "건반 모니터", 5: "베이스 모니터"}

for i in range(1, 41):
    state[f"/ch/{i}/name"] = CH_NAMES.get(i, "")
    state[f"/ch/{i}/fdr"] = 0.0 if i in CH_NAMES else -144.0
    state[f"/ch/{i}/mute"] = 0
    state[f"/ch/{i}/pan"] = 0.0
    state[f"/ch/{i}/flt/lc"] = 0
    state[f"/ch/{i}/flt/lcf"] = 80.0
    for b in range(1, 17):
        state[f"/ch/{i}/send/{b}/on"] = 0
        state[f"/ch/{i}/send/{b}/lvl"] = -144.0
for i in range(1, 9):
    state[f"/aux/{i}/name"] = ""
    state[f"/aux/{i}/fdr"] = -144.0
    state[f"/aux/{i}/mute"] = 0
for i in range(1, 17):
    state[f"/bus/{i}/name"] = BUS_NAMES.get(i, "")
    state[f"/bus/{i}/fdr"] = 0.0
    state[f"/bus/{i}/mute"] = 0
    state[f"/dca/{i}/name"] = ""
    state[f"/dca/{i}/fdr"] = 0.0
    state[f"/dca/{i}/mute"] = 0
for i in range(1, 5):
    state[f"/main/{i}/name"] = "메인 LR" if i == 1 else ""
    state[f"/main/{i}/fdr"] = 0.0
    state[f"/main/{i}/mute"] = 0
for i in range(1, 9):
    state[f"/mtx/{i}/name"] = ""
    state[f"/mtx/{i}/fdr"] = 0.0
    state[f"/mtx/{i}/mute"] = 0

# 채널 상세: 입력 연결(AES50 A 의 같은 번호), 프리앰프, 필터, 게이트, EQ, 컴프, 인서트
EQ_DEFAULT = {"l": (0.0, 80.0, 1.0), "1": (0.0, 200.0, 2.0), "2": (0.0, 500.0, 2.0), "3": (0.0, 1000.0, 2.0),
              "4": (0.0, 4000.0, 2.0), "h": (0.0, 10000.0, 1.0)}
for i in range(1, 41):
    state[f"/ch/{i}/in/conn/grp"] = "A"
    state[f"/ch/{i}/in/conn/in"] = str(i)          # 실제 콘솔처럼 글자 값이 입력 번호
    state[f"/io/in/A/{i}/g"] = 30.0
    state[f"/io/in/A/{i}/vph"] = 1 if i in (12, 13, 14, 15) else 0
    state[f"/io/in/A/{i}/name"] = CH_NAMES.get(i, "")
    state[f"/ch/{i}/in/set/trim"] = 0.0
    state[f"/ch/{i}/in/set/inv"] = 0
    state[f"/ch/{i}/flt/hc"] = 0
    state[f"/ch/{i}/flt/hcf"] = 10000.0
    state[f"/ch/{i}/gate/on"] = 0
    state[f"/ch/{i}/gate/mdl"] = "GATE"
    state[f"/ch/{i}/eq/on"] = 1
    state[f"/ch/{i}/eq/mdl"] = "STD"
    for b, (g, f, q) in EQ_DEFAULT.items():
        state[f"/ch/{i}/eq/{b}g"], state[f"/ch/{i}/eq/{b}f"], state[f"/ch/{i}/eq/{b}q"] = g, f, q
    state[f"/ch/{i}/eq/leq"] = "SHV"
    state[f"/ch/{i}/eq/heq"] = "SHV"
    state[f"/ch/{i}/dyn/on"] = 1 if i <= 6 else 0
    state[f"/ch/{i}/dyn/mdl"] = "COMP"
    if i == 9:      # 실제 콘솔처럼 빈티지 컴프(76LA) 하나
        state[f"/ch/{i}/dyn/mdl"] = "76LA"
        for k, v in (("mix", 100.0), ("gain", 0.0), ("in", -40.0), ("out", -14.0), ("att", 7.0), ("rel", 1.0), ("ratio", "4")):
            state[f"/ch/{i}/dyn/{k}"] = v
    else:
        for k, v in (("thr", -20.0), ("ratio", 3.0), ("gain", 0.0), ("att", 20.0), ("rel", 100.0), ("knee", 3.0), ("mix", 100.0)):
            state[f"/ch/{i}/dyn/{k}"] = v
    for slot in ("preins", "postins"):
        state[f"/ch/{i}/{slot}/on"] = 0
        state[f"/ch/{i}/{slot}/ins"] = "NONE"
state["/ch/3/postins/ins"] = "FX2"
state["/ch/3/postins/on"] = 1
for i in range(1, 17):
    state[f"/fx/{i}/mdl"] = {1: "HALL", 2: "DE-S2", 3: "DELAY"}.get(i, "NONE")
    state[f"/fx/{i}/fxmix"] = 100.0
for k, v in (("dcy", 2.5), ("pdel", 30.0), ("size", 40.0), ("lc", 100.0), ("hc", 7000.0)):
    state[f"/fx/1/{k}"] = v
for k, v in (("lo", 20.0), ("hi", 25.0), ("mode", "st")):
    state[f"/fx/2/{k}"] = v
for k, v in (("time", 350.0), ("fb", 30.0)):
    state[f"/fx/3/{k}"] = v
for kind, count in (("aux", 8), ("bus", 16), ("main", 4), ("mtx", 8)):   # 실제 콘솔처럼 모든 곳에 인서트 자리
    for i in range(1, count + 1):
        for slot in ("preins", "postins"):
            state[f"/{kind}/{i}/{slot}/on"] = 0
            state[f"/{kind}/{i}/{slot}/ins"] = "NONE"
state["/bus/1/preins/ins"] = "FX1"
state["/bus/1/preins/on"] = 1

# 그 밖의 입력 그룹 (이름 비어 있음) - 입력 단자 고르기 창용
for grp, count in (("LCL", 8), ("AUX", 8), ("USB", 48)):
    for n in range(1, count + 1):
        state[f"/io/in/{grp}/{n}/name"] = ""
for n in range(41, 49):
    state[f"/io/in/A/{n}/name"] = ""
state["/io/in/A/20/name"] = "예비 무선마이크"

# 출력 라우팅: 실제 콘솔처럼 그룹마다 grp(무엇을)·in(몇 번, 글자 값) 을 가짐
for grp, count in (("LCL", 8), ("AUX", 8), ("A", 48), ("B", 48), ("C", 48), ("AES", 2), ("SC", 32),
                   ("USB", 48), ("CRD", 64), ("MOD", 64), ("REC", 4)):
    for n in range(1, count + 1):
        state[f"/io/out/{grp}/{n}/grp"] = "OFF"
        state[f"/io/out/{grp}/{n}/in"] = "1"
def route(grp, n, src, idx):
    state[f"/io/out/{grp}/{n}/grp"], state[f"/io/out/{grp}/{n}/in"] = src, str(idx)
route("LCL", 1, "MAIN", 1); route("LCL", 2, "MAIN", 2)          # 메인 LR → 본체 출력 1-2
for b in range(1, 6):                                           # 모니터 버스 1~5 → 스테이지박스 출력 1~5
    route("A", b, "BUS", 2 * b - 1)
route("REC", 1, "MAIN", 1); route("REC", 2, "MAIN", 2)          # USB 녹음기 ← 메인
for n in range(1, 16):                                          # USB(PC) 1-15 ← 스테이지박스 입력 1-15 (멀티트랙 녹음)
    route("USB", n, "A", n)

# 원격 잠금 상태 (0 = 꺼짐, 원격 조작 가능)
state["/$ctl/OSC/ronly"] = 0

# 메인 출력 2~4, 채널 → 메인 센드, 메인/버스 → 매트릭스 센드
state["/main/2/name"] = "CENTER"
state["/main/4/name"] = "YOUTUBE"
state["/mtx/1/name"] = "BABY"
state["/mtx/2/name"] = "CAFE"
for i in range(1, 41):
    for m in range(1, 5):
        state[f"/ch/{i}/main/{m}/on"] = 1 if i in CH_NAMES else 0
        state[f"/ch/{i}/main/{m}/lvl"] = 0.0
for src in [f"/main/{m}" for m in range(1, 5)] + [f"/bus/{b}" for b in range(1, 17)]:
    for x in range(1, 9):
        state[f"{src}/send/MX{x}/on"] = 0
        state[f"{src}/send/MX{x}/lvl"] = -144.0
state["/main/1/send/MX1/on"] = 1
state["/main/1/send/MX1/lvl"] = 0.0
state["/main/1/send/MX2/on"] = 1
state["/main/1/send/MX2/lvl"] = -6.0

# 콘솔 화면 표시 이름($name): 여기서는 저장 이름과 같게
for k in [k for k in list(state) if k.endswith("/name") and not k.startswith("/dca/")]:
    state[k[:-len("name")] + "$name"] = state[k]

# 예시: 인도자 모니터에 인도자 보컬과 건반이 들어가 있는 상태
state["/ch/3/send/1/on"] = 1
state["/ch/3/send/1/lvl"] = 0.0
state["/ch/10/send/1/on"] = 1
state["/ch/10/send/1/lvl"] = -10.0


def reply_args(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, int):
        return [str(value), value]
    return [f"{value:.1f}", 0.5, float(value)]  # [표시 문자, 0~1 값, 실제 값]


def serve_osc():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", OSC_PORT))
    print(f"[가짜 WING] OSC 대기 중: 127.0.0.1:{OSC_PORT}")
    while True:
        data, addr = s.recvfrom(4096)
        try:
            address, args = decode(data)
        except Exception:
            continue
        if address not in state:
            # 실제 콘솔처럼: 노드를 물으면 바로 아래 설정 이름 목록을 돌려줌 (예: /fx/1 → mdl, fxmix, dcy …)
            prefix = address.rstrip("/") + "/"
            kids = []
            for k in state:
                if k.startswith(prefix):
                    child = k[len(prefix):].split("/")[0]
                    if child not in kids:
                        kids.append(child)
            if kids and not args:
                s.sendto(encode(address, kids), addr)
            continue
        if args:
            old = state[address]
            new = args[0]
            if isinstance(old, int) and not isinstance(new, str):
                new = int(new)
            elif isinstance(old, float) and not isinstance(new, str):
                new = float(new)
            state[address] = new
            if address.endswith("/name") and address[:-4] + "$name" in state:
                state[address[:-4] + "$name"] = new
            print(f"[가짜 WING] 설정 {address} = {new}")
        else:
            s.sendto(encode(address, reply_args(state[address])), addr)


def serve_discovery():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", DISCOVERY_PORT))
    while True:
        data, addr = s.recvfrom(1024)
        if data.startswith(b"WING?"):
            s.sendto(b"WING,127.0.0.1,SIMULATOR,wing-fullsize,TEST0000,3.0.6", addr)


if __name__ == "__main__":
    threading.Thread(target=serve_discovery, daemon=True).start()
    serve_osc()
