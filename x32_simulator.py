"""시험용 가짜 X32 (UDP 127.0.0.1:10023). 실제 X32처럼 0~1 값과 X32 주소로 답합니다.

실행: python x32_simulator.py
"""

import socket

from wing_osc import encode, decode
from x32_osc import db_to_fader

state = {}
INT_KEYS = ("/on", "/st", "/mono", "/hpon", "/invert", "/phantom", "/mode", "/ratio", "/sel", "/source", "/type")

NAMES = {1: "KICK", 2: "SNARE", 3: "HIHAT", 4: "TOM", 5: "BASS", 6: "E.GTR", 7: "A.GTR", 8: "KEY",
         9: "PIANO", 10: "VOCAL 1", 11: "VOCAL 2", 12: "PASTOR", 13: "CHOIR L", 14: "CHOIR R"}
BUSES = {1: "DRUM MON", 2: "BASS MON", 3: "VOCAL MON", 4: "KEY MON", 5: "IEM 1", 6: "IEM 2"}

for i in range(1, 33):
    p = f"/ch/{i:02d}"
    state[f"{p}/config/name"] = NAMES.get(i, "")
    state[f"{p}/config/source"] = i
    state[f"{p}/mix/fader"] = db_to_fader(-5.0 if i in NAMES else -144)
    state[f"{p}/mix/on"] = 0 if i == 4 else 1
    state[f"{p}/mix/st"] = 1 if i in NAMES else 0
    state[f"{p}/mix/mono"] = 1 if i == 12 else 0
    state[f"{p}/mix/mlevel"] = db_to_fader(-6.0 if i == 12 else -144)
    for b in range(1, 17):
        on = i in NAMES and b in BUSES and (i + b) % 3 == 0
        state[f"{p}/mix/{b:02d}/on"] = 1 if on else 0
        state[f"{p}/mix/{b:02d}/level"] = db_to_fader(-8.0 if on else -144)
    state[f"{p}/preamp/trim"] = 0.5
    state[f"{p}/preamp/invert"] = 0
    state[f"{p}/preamp/hpon"] = 1 if i in (10, 11, 12) else 0
    state[f"{p}/preamp/hpf"] = 0.4
    state[f"{p}/gate/on"] = 0
    state[f"{p}/gate/mode"] = 3
    state[f"{p}/eq/on"] = 1
    for band in range(1, 5):
        state[f"{p}/eq/{band}/type"] = 2
        state[f"{p}/eq/{band}/g"] = 0.5
        state[f"{p}/eq/{band}/f"] = [0.2, 0.4, 0.6, 0.8][band - 1]
        state[f"{p}/eq/{band}/q"] = 0.46
    state[f"{p}/dyn/on"] = 1 if i in (10, 11) else 0
    state[f"{p}/dyn/mode"] = 0
    state[f"{p}/dyn/thr"] = 0.6
    state[f"{p}/dyn/ratio"] = 6
    state[f"{p}/dyn/mgain"] = 0.1
    state[f"{p}/dyn/attack"] = 0.1
    state[f"{p}/dyn/release"] = 0.5
    state[f"{p}/insert/on"] = 0
    state[f"{p}/insert/sel"] = 0
for b in range(1, 17):
    p = f"/bus/{b:02d}"
    state[f"{p}/config/name"] = BUSES.get(b, "")
    state[f"{p}/mix/fader"] = db_to_fader(0.0)
    state[f"{p}/mix/on"] = 1
    for x in range(1, 7):
        state[f"{p}/mix/{x:02d}/on"] = 0
        state[f"{p}/mix/{x:02d}/level"] = 0.0
for p, name in (("/main/st", ""), ("/main/m", "CENTER")):
    state[f"{p}/config/name"] = name
    state[f"{p}/mix/fader"] = db_to_fader(-2.0)
    state[f"{p}/mix/on"] = 1
    for x in range(1, 7):
        on = p == "/main/st" and x == 1
        state[f"{p}/mix/{x:02d}/on"] = 1 if on else 0
        state[f"{p}/mix/{x:02d}/level"] = db_to_fader(-3.0 if on else -144)
for x in range(1, 7):
    state[f"/mtx/{x:02d}/config/name"] = {1: "LOBBY"}.get(x, "")
    state[f"/mtx/{x:02d}/mix/fader"] = db_to_fader(-4.0)
    state[f"/mtx/{x:02d}/mix/on"] = 1
for d in range(1, 9):
    state[f"/dca/{d}/config/name"] = {1: "DRUMS", 2: "VOCALS"}.get(d, "")
    state[f"/dca/{d}/fader"] = db_to_fader(0.0)
    state[f"/dca/{d}/on"] = 1
for h in range(128):
    state[f"/headamp/{h:03d}/gain"] = 0.4
    state[f"/headamp/{h:03d}/phantom"] = 1 if h in (12, 13, 33) else 0
# 입력 1-8, 9-16 = 본체(AN), 17-24 = AES50 A 1-8, 25-32 = AES50 A 9-16
for blk, v in zip(("1-8", "9-16", "17-24", "25-32"), (0, 1, 4, 5)):
    state[f"/config/routing/IN/{blk}"] = v


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 10023))
    print("가짜 X32 실행 중: 127.0.0.1:10023")
    while True:
        try:
            data, addr = s.recvfrom(4096)
        except ConnectionResetError:
            continue
        try:
            a, args = decode(data)
        except Exception:
            continue
        if a == "/xinfo":
            s.sendto(encode("/xinfo", ["127.0.0.1", "X32-SIM", "X32", "4.06"]), addr)
        elif a == "/info":
            s.sendto(encode("/info", ["V2.05", "osc-server", "X32", "4.06"]), addr)
        elif a in state:
            if args:
                v = args[0]
                state[a] = int(v) if a.endswith(INT_KEYS) and isinstance(v, (int, float)) else v
            else:
                v = state[a]
                if a.endswith(INT_KEYS):
                    v = int(v)
                elif not isinstance(v, str):
                    v = float(v)
                s.sendto(encode(a, [v]), addr)
        # 모르는 주소는 실제 X32처럼 대답하지 않음


if __name__ == "__main__":
    main()
