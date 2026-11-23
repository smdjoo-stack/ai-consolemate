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


if __name__ == "__main__":
    main()
