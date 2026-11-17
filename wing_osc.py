"""Behringer WING 과 OSC(UDP)로 통신하는 최소 클라이언트.

- WING 은 UDP 2223 포트에서 OSC 명령을 받습니다.
- 주소 뒤에 값을 붙이면 '설정', 값 없이 보내면 '조회'입니다.
- 외부 라이브러리 없이 파이썬 표준 라이브러리만 사용합니다.
"""

import socket
import struct
import threading
import time

OSC_PORT = 2223
DISCOVERY_PORT = 2222


# ---------------------------------------------------------------- OSC 인코딩
def _osc_str(s: str) -> bytes:
    b = s.encode("utf-8") + b"\x00"
    return b + b"\x00" * ((-len(b)) % 4)


def encode(address: str, args=()) -> bytes:
    tags = ","
    data = b""
    for a in args:
        if isinstance(a, bool):
            a = int(a)
        if isinstance(a, int):
            tags += "i"
            data += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"
            data += struct.pack(">f", a)
        elif isinstance(a, str):
            tags += "s"
            data += _osc_str(a)
        else:
            raise TypeError(f"지원하지 않는 OSC 값: {a!r}")
    return _osc_str(address) + _osc_str(tags) + data


def _read_str(buf: bytes, i: int):
    end = buf.index(b"\x00", i)
    s = buf[i:end].decode("utf-8", "replace")
    return s, (end + 4) & ~3


def decode(buf: bytes):
    """(주소, [값...]) 을 돌려줍니다."""
    address, i = _read_str(buf, 0)
    args = []
    if i >= len(buf) or buf[i] != ord(","):
        return address, args
    tags, i = _read_str(buf, i)
    for t in tags[1:]:
        if t == "i":
            args.append(struct.unpack(">i", buf[i:i + 4])[0])
            i += 4
        elif t == "f":
            args.append(struct.unpack(">f", buf[i:i + 4])[0])
            i += 4
        elif t == "s":
            s, i = _read_str(buf, i)
            args.append(s)
        else:
            break
    return address, args


def number_of(args):
    """응답 값들 중 숫자 값(마지막 숫자)을 꺼냅니다. WING 은 보통 [문자, 0~1 값, 실제 값] 형태로 답합니다."""
    nums = [a for a in args if isinstance(a, (int, float))]
    if nums:
        return nums[-1]
    for a in args:
        try:
            return float(a)
        except (TypeError, ValueError):
            pass
    return None


def text_of(args):
    for a in args:
        if isinstance(a, str):
            return a
    return "" if not args else str(args[0])


# ---------------------------------------------------------------- 콘솔 찾기
def discover(timeout: float = 1.5):
    """같은 네트워크의 WING 콘솔을 찾습니다. [{ip, name, model, serial, firmware}] 를 돌려줍니다."""
    found = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.3)
    try:
        s.bind(("", 0))
        for target in ("255.255.255.255", "127.0.0.1"):
            try:
                s.sendto(b"WING?", (target, DISCOVERY_PORT))
            except OSError:
                pass
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = s.recvfrom(1024)
            except (socket.timeout, ConnectionResetError):
                # Windows: 응답 없는 주소로 보낸 뒤 ConnectionResetError 가 날 수 있음
                continue
            text = data.decode("utf-8", "replace").strip("\x00 \r\n")
            if not text.startswith("WING"):
                continue
            parts = text.split(",")
            info = {
                "ip": parts[1] if len(parts) > 1 and parts[1] else addr[0],
                "name": parts[2] if len(parts) > 2 else "",
                "model": parts[3] if len(parts) > 3 else "",
                "serial": parts[4] if len(parts) > 4 else "",
                "firmware": parts[5] if len(parts) > 5 else "",
            }
            found[info["ip"]] = info
    finally:
        s.close()
    return list(found.values())


# ---------------------------------------------------------------- 클라이언트
class WingClient:
    def __init__(self, host: str, port: int = OSC_PORT, timeout: float = 1.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", 0))
        self._lock = threading.Lock()

    def _drain(self):
        self._sock.setblocking(False)
        try:
            while True:
                self._sock.recvfrom(4096)
        except OSError:  # BlockingIOError, ConnectionResetError 포함
            pass
        finally:
            self._sock.setblocking(True)

    def get(self, address: str):
        """값 조회. 응답 값 리스트를 돌려주고, 응답이 없으면 TimeoutError."""
        with self._lock:
            self._drain()
            self._sock.sendto(encode(address), (self.host, self.port))
            deadline = time.time() + self.timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError(
                        f"WING 응답 없음 ({self.host}:{self.port} {address}). "
                        "콘솔 IP, 네트워크 연결, 콘솔의 OSC 원격 설정을 확인하세요."
                    )
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

    def send(self, address: str, value):
        """값만 보내고 응답을 기다리지 않음 (페이더를 부드럽게 움직일 때 사용)."""
        with self._lock:
            self._sock.sendto(encode(address, [value]), (self.host, self.port))

    def set(self, address: str, value):
        """값 설정 후 다시 조회해서 실제로 바뀐 값을 돌려줍니다."""
        with self._lock:
            self._sock.sendto(encode(address, [value]), (self.host, self.port))
        time.sleep(0.02)
        return self.get(address)

    def close(self):
        self._sock.close()
