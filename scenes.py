"""예배 순서 버튼(씬) 저장소.

콘솔의 스냅샷이 아니라 이 프로그램이 직접 저장합니다 (scenes.json).
각 씬은 "OSC 주소 → 값" 목록과, 무엇을 담았는지(scope)를 가집니다.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path

# 시험용: CONSOLEMATE_SCENES 환경변수로 다른 파일을 쓸 수 있음
PATH = Path(os.environ.get("CONSOLEMATE_SCENES") or (Path(__file__).parent / "scenes.json"))

# 저장할 때 고를 수 있는 범위
SCOPE_DEFAULT = {"mute": True, "fader": True, "sends": False, "mains": False, "buses": False}
SCOPE_LABELS = {
    "mute": "채널 뮤트",
    "fader": "채널 페이더(MAIN 크기)",
    "sends": "모니터 센드",
    "mains": "메인 출력 센드(CENTER·YOUTUBE 등)",
    "buses": "모니터(버스) 전체 볼륨·뮤트",
}
COLORS = ["#8b6cff", "#22d3ee", "#34d399", "#fbbf24", "#f472b6", "#fb923c", "#5b8cff", "#a3e635"]


class SceneStore:
    def __init__(self, path: Path = PATH):
        self.path = path
        self.lock = threading.RLock()
        self.scenes = []
        self.active_id = None          # 마지막으로 적용한 씬
        self.last_undo = None          # {"scene": 이름, "values": {...}, "at": 시각}
        if path.exists():
            try:
                self.scenes = json.loads(path.read_text(encoding="utf-8")).get("scenes", [])
            except (OSError, ValueError):
                self.scenes = []

    def _write(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"scenes": self.scenes}, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def find(self, key):
        """id 또는 이름으로 찾기 (이름은 공백·대소문자 무시)."""
        if not key:
            return None
        k = str(key).strip().lower().replace(" ", "")
        with self.lock:
            for s in self.scenes:
                if s["id"] == key or s["name"].strip().lower().replace(" ", "") == k:
                    return s
        return None

    def upsert(self, name, values, scope, sid=None):
        name = str(name).strip()[:30]
        if not name:
            raise ValueError("이름을 입력해 주세요.")
        with self.lock:
            s = self.find(sid) if sid else self.find(name)
            now = time.strftime("%Y-%m-%d %H:%M")
            if s is None:
                s = {"id": uuid.uuid4().hex[:8], "name": name, "color": COLORS[len(self.scenes) % len(COLORS)], "created": now}
                self.scenes.append(s)
            s.update({"name": name, "values": values, "scope": scope, "updated": now})
            self._write()
            return s

    def delete(self, sid):
        with self.lock:
            self.scenes = [s for s in self.scenes if s["id"] != sid]
            if self.active_id == sid:
                self.active_id = None
            self._write()

    def rename(self, sid, name):
        name = str(name).strip()[:30]
        if not name:
            raise ValueError("이름을 입력해 주세요.")
        with self.lock:
            s = self.find(sid)
            if not s:
                raise KeyError("없는 순서입니다.")
            other = self.find(name)
            if other and other["id"] != sid:
                raise ValueError("같은 이름이 이미 있습니다.")
            s["name"] = name
            self._write()

    def move(self, sid, delta):
        with self.lock:
            i = next((n for n, s in enumerate(self.scenes) if s["id"] == sid), None)
            if i is None:
                return
            j = max(0, min(len(self.scenes) - 1, i + int(delta)))
            self.scenes.insert(j, self.scenes.pop(i))
            self._write()


STORE = SceneStore()
