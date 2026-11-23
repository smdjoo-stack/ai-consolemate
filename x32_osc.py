"""Behringer X32 / Midas M32 통신 (OSC, UDP 10023).

프로그램의 나머지 부분은 WING 방식 주소(/ch/1/fdr 등, 값은 dB)로 말합니다.
이 파일의 X32Client 가 그것을 X32 주소(/ch/01/mix/fader, 값은 0~1)로 바꿔 주므로
화면·AI·예배 순서 기능을 그대로 쓸 수 있습니다.

근거: Patrick-Gilles Maillot, "Unofficial X32/M32 OSC Remote Protocol" (페이더 법칙, 주소, 입력 번호, headamp 번호)
"""

import math
import re
import socket
import threading
import time

from wing_osc import encode, decode

OSC_PORT = 10023
FAMILY = "x32"
NEG_INF = -144.0          # 프로그램 안에서 -∞ 를 나타내는 값 (WING 과 같게)


class Unsupported(TimeoutError):
    """X32에 없는 항목. 기존 코드가 '값 없음'으로 처리하도록 TimeoutError 의 한 종류로 둡니다."""


# ---------------------------------------------------------------- 값 변환
def fader_to_db(f):
    f = float(f)
    if f <= 0:
        return NEG_INF
    if f >= 0.5:
        return f * 40 - 30
    if f >= 0.25:
        return f * 80 - 50
    if f >= 0.0625:
        return f * 160 - 70
    return f * 480 - 90


def db_to_fader(db):
    db = float(db)
    if db <= -90:
        return 0.0
    if db < -60:
        f = (db + 90) / 480
    elif db < -30:
        f = (db + 70) / 160
    elif db < -10:
        f = (db + 50) / 80
    else:
        f = (db + 30) / 40
    return max(0.0, min(1.0, f))


def _lin(v, lo, hi):
    return max(0.0, min(1.0, (float(v) - lo) / (hi - lo)))


def _log(v, lo, hi):
    v = max(min(lo, hi), min(max(lo, hi), float(v)))
    return max(0.0, min(1.0, math.log(v / lo) / math.log(hi / lo)))


GATE_MODES = ["EXP2", "EXP3", "EXP4", "GATE", "DUCK"]
DYN_MODES = ["COMP", "EXP"]
RATIOS = [1.1, 1.3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 20.0, 100.0]
INSERTS = ["NONE"] + [f"FX{n}{s}" for n in range(1, 9) for s in "LR"] + [f"AUX{n}" for n in range(1, 7)]
IN_BLOCKS = ["1-8", "9-16", "17-24", "25-32"]


# 규칙: (종류, x32주소, 추가값)
#  fader: 0~1 ↔ dB / onmute: X32 'on'(1=소리 남) ↔ 뮤트 / bool / text / lin(lo,hi) / log(lo,hi)
#  enum(목록): 숫자 ↔ 글자 / ratio / const(값) / headamp
def _strip(kind, n):
    """WING 의 채널·AUX 를 X32 주소 앞부분으로."""
    if kind == "ch" and 1 <= n <= 32:
        return f"/ch/{n:02d}"
    if kind == "aux" and 1 <= n <= 8:
        return f"/auxin/{n:02d}"
    return None


def translate(addr):
    m = re.fullmatch(r"/(ch|aux)/(\d+)/(.+)", addr)
    if m:
        p = _strip(m.group(1), int(m.group(2)))
        rest = m.group(3)
        if p is None:
            return None
        simple = {"name": ("text", "config/name"), "$name": ("text", "config/name"),
                  "fdr": ("fader", "mix/fader"), "mute": ("onmute", "mix/on")}
        if rest in simple:
            k, a = simple[rest]
            return (k, f"{p}/{a}", None)
        s = re.fullmatch(r"send/(\d+)/(on|lvl)", rest)
        if s:
            b = int(s.group(1))
            if not 1 <= b <= 16:
                return None
            return ("bool", f"{p}/mix/{b:02d}/on", None) if s.group(2) == "on" else ("fader", f"{p}/mix/{b:02d}/level", None)
        s = re.fullmatch(r"main/(\d+)/(on|lvl)", rest)
        if s:
            mm, what = int(s.group(1)), s.group(2)
            if mm == 1:     # 채널 → LR: 켜기/끄기만 있고 크기는 채널 페이더
                return ("bool", f"{p}/mix/st", None) if what == "on" else ("const", None, 0.0)
            if mm == 2:     # 채널 → MONO(가운데)
                return ("bool", f"{p}/mix/mono", None) if what == "on" else ("fader", f"{p}/mix/mlevel", None)
            return None
        if m.group(1) != "ch":
            return None
        ch = {
            "in/conn/grp": ("srcgrp", p, None), "in/conn/in": ("srcnum", p, None),
            "in/set/trim": ("lin", f"{p}/preamp/trim", (-18, 18)), "in/set/inv": ("bool", f"{p}/preamp/invert", None),
            "flt/lc": ("bool", f"{p}/preamp/hpon", None), "flt/lcf": ("log", f"{p}/preamp/hpf", (20, 400)),
            "gate/on": ("bool", f"{p}/gate/on", None), "gate/mdl": ("enum", f"{p}/gate/mode", GATE_MODES),
            "eq/on": ("bool", f"{p}/eq/on", None), "eq/mdl": ("const", None, "STD"),
            "dyn/on": ("bool", f"{p}/dyn/on", None), "dyn/mdl": ("enum", f"{p}/dyn/mode", DYN_MODES),
            "dyn/thr": ("lin", f"{p}/dyn/thr", (-60, 0)), "dyn/ratio": ("ratio", f"{p}/dyn/ratio", None),
            "dyn/gain": ("lin", f"{p}/dyn/mgain", (0, 24)), "dyn/att": ("lin", f"{p}/dyn/attack", (0, 120)),
            "dyn/rel": ("log", f"{p}/dyn/release", (5, 4000)),
            "dyn/knee": ("lin", f"{p}/dyn/knee", (0, 5)), "dyn/mix": ("lin", f"{p}/dyn/mix", (0, 100)),
            "preins/on": ("bool", f"{p}/insert/on", None), "preins/ins": ("enum", f"{p}/insert/sel", INSERTS),
        }
        if rest in ch:
            return ch[rest]
        e = re.fullmatch(r"eq/([1-4])([gfq])", rest)
        if e:
            band, part = e.group(1), e.group(2)
            return {"g": ("lin", f"{p}/eq/{band}/g", (-15, 15)), "f": ("log", f"{p}/eq/{band}/f", (20, 20000)),
                    "q": ("log", f"{p}/eq/{band}/q", (10, 0.3))}[part]
        return None

    m = re.fullmatch(r"/(bus|main|mtx|dca)/(\d+)/(.+)", addr)
    if m:
        kind, n, rest = m.group(1), int(m.group(2)), m.group(3)
        if kind == "bus" and 1 <= n <= 16:
            p, mixp = f"/bus/{n:02d}", f"/bus/{n:02d}/mix"
        elif kind == "main" and n in (1, 2):
            p = "/main/st" if n == 1 else "/main/m"
            mixp = p + "/mix"
        elif kind == "mtx" and 1 <= n <= 6:
            p, mixp = f"/mtx/{n:02d}", f"/mtx/{n:02d}/mix"
        elif kind == "dca" and 1 <= n <= 8:
            p, mixp = f"/dca/{n}", f"/dca/{n}"
        else:
            return None
        if rest in ("name", "$name"):
            return ("text", f"{p}/config/name", None)
        if rest == "fdr":
            return ("fader", f"{mixp}/fader", None)
        if rest == "mute":
            return ("onmute", f"{mixp}/on", None)
        s = re.fullmatch(r"send/MX(\d+)/(on|lvl)", rest)
        if s and kind in ("bus", "main"):
            x = int(s.group(1))
            if not 1 <= x <= 6:
                return None
            return ("bool", f"{mixp}/{x:02d}/on", None) if s.group(2) == "on" else ("fader", f"{mixp}/{x:02d}/level", None)
        return None

    m = re.fullmatch(r"/io/in/(LCL|A|B)/(\d+)/(g|vph|name)", addr)
    if m:
        grp, n, what = m.group(1), int(m.group(2)), m.group(3)
        base, top = {"LCL": (-1, 32), "A": (31, 48), "B": (79, 48)}[grp]
        if not 1 <= n <= top:
            return None
        if what == "name":
            return ("const", None, "")
        h = f"/headamp/{base + n:03d}"
        return ("lin", f"{h}/gain", (-12, 60)) if what == "g" else ("bool", f"{h}/phantom", None)
    if addr == "/$ctl/OSC/ronly":
        return ("const", None, 0)
    return None


# ---------------------------------------------------------------- 클라이언트
class X32Client:
    family = FAMILY

    def __init__(self, host: str, port: int = OSC_PORT, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", 0))
        self._lock = threading.Lock()
        self._blocks = (0.0, None)

    # ---- 날것의 X32 주소
    def _drain(self):
        self._sock.setblocking(False)
        try:
            while True:
                self._sock.recvfrom(4096)
        except OSError:
            pass
        finally:
            self._sock.setblocking(True)

    def raw_get(self, address):
        with self._lock:
            self._drain()
            self._sock.sendto(encode(address), (self.host, self.port))
            deadline = time.time() + self.timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError(f"X32 응답 없음 ({self.host}:{self.port} {address}). "
                                       "콘솔 IP와 네트워크 연결을 확인하세요.")
                self._sock.settimeout(remaining)
                try:
                    data, _ = self._sock.recvfrom(4096)
                except (socket.timeout, ConnectionResetError):
                    continue
                try:
                    addr, args = decode(data)
                except Exception:
                    continue
                if addr == address:
                    return args

    def raw_set(self, address, value):
        with self._lock:
            self._sock.sendto(encode(address, [value]), (self.host, self.port))

    def _raw_num(self, address):
        args = self.raw_get(address)
        nums = [a for a in args if isinstance(a, (int, float))]
        return nums[-1] if nums else None

    # ---- 입력 단자 (채널 source + 입력 블록 설정)
    def _routing_blocks(self):
        t, blocks = self._blocks
        if blocks is None or time.time() - t > 10:
            blocks = [self._raw_num(f"/config/routing/IN/{b}") for b in IN_BLOCKS]
            self._blocks = (time.time(), blocks)
        return blocks

    def _source(self, p):
        s = self._raw_num(f"{p}/config/source")
        s = int(s or 0)
        if s == 0:
            return "OFF", 0
        if s <= 32:
            v = self._routing_blocks()[(s - 1) // 8]
            off = (s - 1) % 8
            v = 0 if v is None else int(v)
            if v <= 3:
                return "LCL", v * 8 + off + 1
            if v <= 9:
                return "A", (v - 4) * 8 + off + 1
            if v <= 15:
                return "B", (v - 10) * 8 + off + 1
            return "CRD", (v - 16) * 8 + off + 1
        if s <= 38:
            return "AUX", s - 32
        if s <= 40:
            return "USB", s - 38
        if s <= 48:
            return "FX", s - 40
        return "BUS", s - 48

    # ---- WING 방식 주소로 조회·설정
    def get(self, address: str):
        r = translate(address)
        if r is None:
            raise Unsupported(f"X32에는 없는 항목: {address}")
        kind, xaddr, extra = r
        if kind == "const":
            return [extra]
        if kind in ("srcgrp", "srcnum"):
            grp, num = self._source(xaddr)
            return [grp] if kind == "srcgrp" else [str(num)]
        args = self.raw_get(xaddr)
        if kind == "text":
            return [next((a for a in args if isinstance(a, str)), "")]
        nums = [a for a in args if isinstance(a, (int, float))]
        if not nums:
            return [None]
        v = nums[-1]
        if kind == "fader":
            return [round(fader_to_db(v), 2)]
        if kind == "onmute":
            return [0 if int(v) else 1]
        if kind == "bool":
            return [1 if int(v) else 0]
        if kind == "lin":
            lo, hi = extra
            return [round(lo + float(v) * (hi - lo), 2)]
        if kind == "log":
            lo, hi = extra
            return [round(lo * (hi / lo) ** float(v), 2)]
        if kind == "enum":
            i = int(v)
            return [extra[i] if 0 <= i < len(extra) else str(i), i]
        if kind == "ratio":
            i = int(v)
            return [RATIOS[i] if 0 <= i < len(RATIOS) else None]
        return [v]

    def _encode_value(self, kind, extra, value):
        if kind == "fader":
            return float(db_to_fader(value))
        if kind == "onmute":
            return 0 if float(value) >= 0.5 else 1
        if kind == "bool":
            return 1 if float(value) >= 0.5 else 0
        if kind == "lin":
            return float(_lin(value, *extra))
        if kind == "log":
            return float(_log(value, *extra))
        if kind == "text":
            return str(value)[:12]
        if kind == "enum":
            if isinstance(value, str):
                if value not in extra:
                    raise ValueError(f"고를 수 있는 값: {', '.join(extra)}")
                return extra.index(value)
            return int(value)
        if kind == "ratio":
            v = float(value)
            return min(range(len(RATIOS)), key=lambda i: abs(RATIOS[i] - v))
        raise Unsupported("X32에서 바꿀 수 없는 항목입니다.")

    def send(self, address: str, value):
        r = translate(address)
        if r is None or r[0] in ("const", "srcgrp", "srcnum"):
            if r and r[0] == "const" and float(value or 0) == float(r[2] or 0):
                return
            raise Unsupported(f"X32에서 바꿀 수 없는 항목: {address}")
        kind, xaddr, extra = r
        self.raw_set(xaddr, self._encode_value(kind, extra, value))

    def set(self, address: str, value):
        self.send(address, value)
        time.sleep(0.02)
        return self.get(address)

    def close(self):
        self._sock.close()


# ---------------------------------------------------------------- 콘솔 찾기
def discover(timeout: float = 1.5):
    """같은 네트워크의 X32/M32 찾기 (/xinfo 방송). [{ip, name, model, serial, firmware, family}]"""
    found = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.3)
    try:
        s.bind(("", 0))
        for target in ("255.255.255.255", "127.0.0.1"):
            try:
                s.sendto(encode("/xinfo"), (target, OSC_PORT))
            except OSError:
                pass
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = s.recvfrom(1024)
            except (socket.timeout, ConnectionResetError):
                continue
            try:
                a, args = decode(data)
            except Exception:
                continue
            if a != "/xinfo":
                continue
            args = [str(x) for x in args] + ["", "", "", ""]
            ip = args[0] if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", args[0]) else addr[0]
            found[ip] = {"ip": ip, "name": args[1], "model": args[2], "serial": "", "firmware": args[3], "family": FAMILY}
    finally:
        s.close()
    return list(found.values())


def probe(ip, timeout=0.8):
    """그 IP 가 X32/M32 인지 확인 (/xinfo 응답). 맞으면 정보, 아니면 None."""
    c = X32Client(ip, timeout=timeout)
    try:
        args = c.raw_get("/xinfo")
        args = [str(x) for x in args] + ["", "", "", ""]
        return {"ip": ip, "name": args[1], "model": args[2], "serial": "", "firmware": args[3], "family": FAMILY}
    except TimeoutError:
        return None
    finally:
        c.close()
