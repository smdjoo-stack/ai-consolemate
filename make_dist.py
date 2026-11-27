"""다른 교회에 나눠 줄 배포판(zip)을 만듭니다.

우리 교회 정보(API 키, 예배 순서 버튼, 스피커 이름표, 교회 메모)는 넣지 않습니다.
실행: 배포판_만들기.bat 더블클릭  (또는 py -3 make_dist.py)
결과: dist/AI콘솔메이트_YYYYMMDD.zip
"""

import json
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
FILES = [
    "app.py", "wing_osc.py", "wing_tools.py", "scenes.py", "speakers.py", "manuals.py", "consoles.py", "x32_osc.py", "gemini.py", "voice_eq.py", "tones.py", "claude_sub.py", "compressor.py", "refsong.py",
    "wing_simulator.py", "x32_simulator.py", "wing_mcp.py",
    "wing_knowledge.md", "index.html", "requirements.txt", "start.bat", "install.bat", "실행.bat",
    "테스트(콘솔없이).bat", "README.md", "LICENSE",
]
NEVER = {"config.json", "scenes.json", "speakers.json", "tones.json"}     # 교회별 정보 — 절대 넣지 않음

FIRST = """AI 콘솔메이트 설치 방법
========================

1. 이 압축 파일을 원하는 곳(예: 문서 폴더)에 '압축 풀기' 하세요.
2. 풀린 폴더에서 install.bat 을 더블클릭하세요.
   - Python이 없으면 자동으로 설치합니다(무료, 공식 배포판). 중간에 허락을 물으면 '예'.
   - 바탕화면에 'AI 콘솔메이트' 아이콘이 생깁니다.
3. 브라우저가 열리면 '처음 설정' 안내를 따라 하세요:
   콘솔 찾기 → 교회 이름·메모 → (선택) Claude API 키 → 완료
4. 다음부터는 바탕화면 'AI 콘솔메이트' 아이콘만 누르면 됩니다.

필요한 것
- Behringer WING / WING Compact / WING Rack 콘솔
  또는 Behringer X32 (Compact·Producer·Rack·Core 포함) / Midas M32 콘솔
  (X32·M32는 라우팅 바꾸기와 이펙트 조절이 아직 안 됩니다)
- 콘솔과 이 PC가 같은 공유기(네트워크)에 연결
- 콘솔 SETUP → REMOTE 에서 원격 잠금(REMOTE LOCK) 꺼짐
- (AI 대화를 쓰려면) Claude API 키 — https://console.anthropic.com

자세한 내용은 README.md 를 보세요.
"""


def main():
    stamp = time.strftime("%Y%m%d")
    out_dir = HERE / "dist"
    out_dir.mkdir(exist_ok=True)
    zpath = out_dir / f"AI콘솔메이트_{stamp}.zip"
    root = "AI콘솔메이트"
    missing = [f for f in FILES if not (HERE / f).exists()]
    if missing:
        raise SystemExit(f"빠진 파일: {missing}")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            assert f not in NEVER
            z.write(HERE / f, f"{root}/{f}")
        # 빈 기본 설정 (처음 켜면 설정 마법사가 열림)
        z.writestr(f"{root}/config.json", json.dumps({
            "anthropic_api_key": "", "wing_ip": "", "web_port": 8800, "allow_other_devices": False, "open_browser": True,
        }, ensure_ascii=False, indent=2))
        z.writestr(f"{root}/처음_읽어주세요.txt", FIRST)
    # 안전 확인: 우리 교회 정보가 들어가지 않았는지
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        cfg = json.loads(z.read(f"{root}/config.json"))
        assert cfg["anthropic_api_key"] == "", "API 키가 들어감!"
        assert not any(n.endswith(("scenes.json", "speakers.json", "tones.json")) or "/manuals/" in n for n in names), "교회 설정이 들어감!"
    print(f"만들었습니다: {zpath}  ({zpath.stat().st_size // 1024} KB, 파일 {len(names)}개)")
    print("우리 교회 API 키·예배 순서·스피커 이름표·교회 메모는 들어 있지 않습니다.")


CHURCH_FIRST = """AI 콘솔메이트 — 우리 교회 설정 포함판 (다른 PC로 옮기기)
====================================================

이 압축 파일에는 프로그램과 우리 교회 설정(교회 이름·메모, 예배 순서 버튼, 스피커 이름표,
우리 교회 톤, 설명서 요약)이 들어 있습니다. API 키는 안전을 위해 빼 두었습니다.
⚠ 교회 내부용입니다. 다른 교회에 줄 때는 make_dist.bat 으로 만든 일반 배포판을 주세요.

1. 새 PC의 원하는 곳(예: 문서 폴더)에 '압축 풀기' 하세요.
2. 풀린 폴더에서 install.bat 을 더블클릭하세요.
   - Python이 없으면 자동으로 설치합니다. 중간에 허락을 물으면 '예'.
   - 바탕화면에 'AI 콘솔메이트' 아이콘이 생깁니다.
3. 프로그램이 열리면 콘솔을 자동으로 찾아 연결합니다 (같은 공유기에 연결되어 있어야 해요).
4. AI 대화 연결: 오른쪽 위 ⚙ 설정 → 🔑
   - Claude 구독: 'Claude 구독 (Pro/Max)' → 'Claude 계정으로 로그인' → '로그인 확인' → 'Claude 구독으로 고정'
     (새 PC에 Claude 데스크톱 앱이 설치되어 있어야 합니다)
   - 또는 Claude API 키 / Google AI Studio 키를 넣어도 됩니다.
5. (선택) Claude 앱 채팅에서도 콘솔을 조작하려면 README.md 의 'Claude 구독으로 쓸 수 있나요?'를 보세요.

필요한 것: 콘솔과 같은 공유기(네트워크), 콘솔 SETUP → REMOTE 의 REMOTE LOCK 꺼짐.
"""
CHURCH_FILES = ["scenes.json", "speakers.json", "tones.json"]
KEEP_CFG = ["church_name", "church_notes", "setup_done", "ai_provider", "google_model", "knowledge",
            "console_family", "console_serial", "console_name", "web_port", "allow_other_devices"]


def main_church():
    """우리 교회 설정 포함판 — 같은 교회의 다른 PC로 옮길 때. API 키는 넣지 않음."""
    stamp = time.strftime("%Y%m%d")
    out_dir = HERE / "dist"
    out_dir.mkdir(exist_ok=True)
    try:
        cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    church = (cfg.get("church_name") or "우리교회").strip()
    safe = "".join(c for c in church if c.isalnum() or c in " _-").strip().replace(" ", "_") or "우리교회"
    zpath = out_dir / f"AI콘솔메이트_{safe}용_{stamp}.zip"
    root = "AI콘솔메이트"
    new_cfg = {k: cfg[k] for k in KEEP_CFG if k in cfg}
    new_cfg.update(anthropic_api_key="", google_api_key="", wing_ip="", open_browser=True)   # IP는 자동 찾기
    included = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in FILES:
            z.write(HERE / f, f"{root}/{f}")
        z.writestr(f"{root}/config.json", json.dumps(new_cfg, ensure_ascii=False, indent=2))
        for f in CHURCH_FILES:
            if (HERE / f).exists():
                z.write(HERE / f, f"{root}/{f}")
                included.append(f)
        mdir = HERE / "manuals"
        if mdir.is_dir():
            for p in mdir.iterdir():
                if p.is_file() and p.suffix in (".md", ".json"):
                    z.write(p, f"{root}/manuals/{p.name}")
                    included.append(f"manuals/{p.name}")
        z.writestr(f"{root}/처음_읽어주세요.txt", CHURCH_FIRST)
    # 안전 확인: 키가 들어가지 않았는지
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        c2 = json.loads(z.read(f"{root}/config.json"))
        assert not c2.get("anthropic_api_key") and not c2.get("google_api_key"), "API 키가 들어감!"
        import re
        real_key = re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}")     # 실제 키 모양 (설명 글자는 통과)
        for n in names:
            if n.endswith((".json", ".txt", ".md", ".py", ".html")):
                assert not real_key.search(z.read(n)), f"키가 들어간 파일: {n}"
    print(f"만들었습니다: {zpath}  ({zpath.stat().st_size // 1024} KB, 파일 {len(names)}개)")
    print(f"교회 설정 포함: {church} · " + (", ".join(included) if included else "(추가 설정 파일 없음)"))
    print("API 키는 넣지 않았습니다.")


if __name__ == "__main__":
    import sys
    if "--church" in sys.argv:
        main_church()
    else:
        main()
