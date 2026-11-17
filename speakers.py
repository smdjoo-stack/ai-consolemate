"""스피커 이름표: 출력 단자마다 어떤 스피커(장비)가 연결되어 있는지 사람이 붙인 이름.

콘솔은 단자 번호만 알고 실제 스피커는 모르므로, 이 프로그램이 따로 기억합니다 (speakers.json).
키는 '그룹:번호' (예: 'A:7' = AES50 A 출력 7번).
"""

import json
import os
import threading
from pathlib import Path

PATH = Path(os.environ.get("CONSOLEMATE_SPEAKERS") or (Path(__file__).parent / "speakers.json"))
TYPES = {
    "pa": ("🔊", "메인 스피커(PA)"), "sub": ("🔈", "서브우퍼"), "wedge": ("📢", "바닥 모니터"),
    "iem": ("🎧", "인이어"), "p16": ("🎛", "개인 모니터(P16 등)"), "stream": ("📡", "방송·녹음"),
    "room": ("🏠", "다른 공간(로비·자모실 등)"), "other": ("🔌", "기타 장비"),
}
_lock = threading.Lock()


def load():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_many(items):
    """items: [{'key': 'A:7', 'name': '메인 PA', 'type': 'pa'}, ...]  이름이 비면 지움."""
    with _lock:
        data = load()
        for it in items:
            key = str(it.get("key", "")).strip()
            if ":" not in key:
                raise ValueError("잘못된 단자")
            name = str(it.get("name", "")).strip()[:30]
            typ = it.get("type") if it.get("type") in TYPES else "other"
            if name:
                data[key] = {"name": name, "type": typ}
            else:
                data.pop(key, None)
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(PATH)
        return data
