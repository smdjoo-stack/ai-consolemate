"""콘솔 설명서 → AI 참고 자료(지식) 만들기.

- 설명서 PDF(또는 txt/md)를 올리거나, 모델 이름으로 인터넷에서 공식 설명서를 찾아 받습니다.
- Claude가 봉사자용 요약(쪽 번호 포함)을 만들어 manuals/ 폴더에 저장합니다.
- 설정에서 어떤 자료를 AI가 참고할지 고릅니다. 기본은 내장된 WING 설명서 요약입니다.
"""

import io
import ipaddress
import json
import os
import re
import socket
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).parent
BUILTIN_ID = "builtin-wing"
BUILTIN = {"id": BUILTIN_ID, "title": "Behringer WING 공식 설명서 요약 (기본 내장, 2025년 9월판)",
           "model": "WING / WING Compact / WING Rack", "builtin": True}
MAX_FILE = 80 * 1024 * 1024          # 80 MB
MAX_PDF_DIRECT = 22 * 1024 * 1024    # 글자가 없는 스캔본을 Claude에게 그대로 보낼 때 (요청 32 MB 한도)
USD_KRW = 1400


def folder():
    return Path(os.environ.get("CONSOLEMATE_MANUALS") or (HERE / "manuals"))


def _index_path():
    return folder() / "index.json"


def list_all():
    try:
        items = json.loads(_index_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        items = []
    return [BUILTIN] + [i for i in items if (folder() / f"{i['id']}.md").exists()]


def _save_index(items):
    folder().mkdir(exist_ok=True)
    items = [i for i in items if not i.get("builtin")]
    tmp = _index_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_index_path())


def find(mid):
    return next((i for i in list_all() if i["id"] == mid), None)


def text_of(mid):
    """AI에게 줄 참고 자료 본문."""
    if not mid or mid == BUILTIN_ID:
        p = HERE / "wing_knowledge.md"
    else:
        p = folder() / f"{mid}.md"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def delete(mid):
    if mid == BUILTIN_ID:
        raise ValueError("기본 내장 자료는 지울 수 없습니다.")
    items = [i for i in list_all() if i["id"] != mid]
    _save_index(items)
    try:
        (folder() / f"{mid}.md").unlink()
    except OSError:
        pass


def add(title, model, body, source, pages=None, mid=None):
    mid = mid or ("m" + uuid.uuid4().hex[:10])
    folder().mkdir(exist_ok=True)
    (folder() / f"{mid}.md").write_text(body, encoding="utf-8")
    items = [i for i in list_all() if i["id"] != mid]
    items.append({"id": mid, "title": title[:80], "model": model[:60], "source": source[:300], "pages": pages,
                  "chars": len(body), "created": time.strftime("%Y-%m-%d %H:%M")})
    _save_index(items)
    return mid


def export_all():
    """백업용: 직접 만든 자료(본문 포함)."""
    return [dict(i, body=text_of(i["id"])) for i in list_all() if not i.get("builtin")]


def import_all(items):
    n = 0
    for i in items or []:
        if isinstance(i, dict) and i.get("body") and re.fullmatch(r"m[0-9a-f]{10}", str(i.get("id", ""))):
            add(str(i.get("title", "설명서")), str(i.get("model", "")), str(i["body"]), str(i.get("source", "")),
                i.get("pages"), i["id"])
            n += 1
    return n


# ---------------------------------------------------------------- 파일 읽기
def extract(data: bytes, filename: str):
    """(본문 텍스트, 쪽수, 스캔본이면 PDF 원본 bytes)"""
    name = filename.lower()
    if data[:5] == b"%PDF-" or name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("PDF 읽기 부품(pypdf)이 없습니다. 프로그램을 다시 켜면 자동으로 설치됩니다.")
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = []
            for n, page in enumerate(reader.pages, 1):
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                t = re.sub(r"[ \t]+", " ", t).strip()
                if t:
                    pages.append(f"[p.{n}]\n{t}")
            count = len(reader.pages)
        except Exception as e:
            raise ValueError(f"PDF 파일을 열 수 없습니다 ({type(e).__name__}). 파일이 손상되었거나 암호가 걸려 있을 수 있습니다.")
        text = "\n\n".join(pages)
        if len(text) < 200 * max(1, count) * 0.1:      # 글자가 거의 없음 → 스캔(그림) 설명서
            if len(data) > MAX_PDF_DIRECT or count > 600:
                raise ValueError("글자를 읽을 수 없는 스캔본이고 파일이 너무 큽니다. 글자가 들어 있는 PDF(공식 홈페이지판)를 써 주세요.")
            return "", count, data
        return text, count, None
    for enc in ("utf-8", "cp949"):
        try:
            return data.decode(enc), None, None
        except UnicodeDecodeError:
            pass
    raise ValueError("PDF 또는 글자 파일(.txt, .md)만 읽을 수 있습니다.")


# ---------------------------------------------------------------- 인터넷에서 받기
def _public_host(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        raise ValueError("주소의 서버를 찾을 수 없습니다.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("내부 네트워크 주소에서는 받을 수 없습니다.")


def download(url: str):
    """공식 설명서 PDF 받기 (PDF만, 80 MB 이하). 실행하지 않고 글자만 읽습니다."""
    u = urlparse(url.strip())
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("http(s) 주소가 아닙니다.")
    _public_host(u.hostname)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AI-ConsoleMate manual reader)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            _public_host(urlparse(r.geturl()).hostname or "")
            size = int(r.headers.get("Content-Length") or 0)
            if size > MAX_FILE:
                raise ValueError("파일이 너무 큽니다(80 MB 초과).")
            data = r.read(MAX_FILE + 1)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"받지 못했습니다: {e}")
    if len(data) > MAX_FILE:
        raise ValueError("파일이 너무 큽니다(80 MB 초과).")
    if data[:5] != b"%PDF-":
        raise ValueError("PDF 파일이 아닙니다(웹 페이지일 수 있어요). 설명서 PDF로 바로 연결되는 주소를 골라 주세요.")
    name = Path(urlparse(url).path).name or "manual.pdf"
    return data, name


SEARCH_PROMPT = """음향 콘솔 "{model}" 의 제조사 공식 사용 설명서(User Manual / Owner's Manual / Quick Start Guide) PDF를 인터넷에서 찾아 주세요.
- 제조사 공식 사이트(예: behringer.com, cdn.mediavalet.com 의 Music Tribe 자료, yamaha.com, allen-heath.com, midasconsoles.com 등) 또는 공식 배포처의 PDF 직접 주소를 우선하세요.
- 검색 결과에 PDF 주소가 바로 없으면, 제조사 제품 페이지(다운로드/Downloads/Documentation 부분)를 열어(web_fetch) PDF 링크를 찾으세요.
  예: "{model} user manual pdf", "{model} manual site:behringer.com", "{model} manual mediavalet".
- 제3자 사이트 사본은 공식판을 못 찾았을 때만 official=false 로 넣으세요.
- 전체 사용 설명서를 퀵스타트보다 먼저, 최신판을 먼저 놓으세요. 한국어판이 있으면 함께 알려 주세요.
- 찾은 결과만 아래 형식의 JSON 한 덩어리로 답하세요(설명 문장 없이):
{{"model": "정식 모델 이름", "results": [{{"title": "문서 이름", "url": "https://...pdf", "kind": "사용 설명서|퀵스타트|기타", "official": true, "note": "판 날짜 등 한 줄"}}]}}
- 최대 5개. 확실한 PDF 주소를 못 찾으면 results 를 비우고 note 없이 빈 목록으로 답하세요."""


def search(client, model_name: str, ai_model: str):
    """Claude 웹 검색으로 공식 설명서 PDF 후보 찾기."""
    messages = [{"role": "user", "content": SEARCH_PROMPT.format(model=model_name)}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
             {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 4, "max_content_tokens": 15000}]
    for _ in range(4):
        resp = client.beta.messages.create(
            model=ai_model, max_tokens=8000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "low"}, tools=tools, messages=messages)
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    text = "".join(b.text for b in resp.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except ValueError:
        data = {}
    out = []
    for r in (data.get("results") or [])[:5]:
        url = str(r.get("url", ""))
        if url.startswith(("http://", "https://")):
            out.append({"title": str(r.get("title", ""))[:120], "url": url, "kind": str(r.get("kind", ""))[:20],
                        "official": bool(r.get("official")), "note": str(r.get("note", ""))[:120],
                        "host": urlparse(url).hostname})
    return {"model": str(data.get("model") or model_name)[:60], "results": out}


# ---------------------------------------------------------------- 요약 만들기
BUILD_PROMPT = """아래는 음향 콘솔 "{model}" 의 공식 설명서입니다. ([p.숫자] 는 쪽 번호 표시입니다.)
이 설명서를 바탕으로, 교회 음향 봉사자를 돕는 AI가 늘 참고할 한국어 참고 자료를 만들어 주세요.

형식과 원칙:
- 마크다운. 첫 줄 "# {model} 콘솔 조작 참고 자료 (AI 콘솔메이트용)", 다음 줄에 출처(설명서 이름·판·쪽수)와
  "괄호 안 p.숫자는 설명서 쪽 번호입니다." 안내.
- "## 1. 신호의 흐름" 처럼 번호 붙은 절로 나누고, 각 절 제목 끝에 근거 쪽을 (p.6-8) 처럼 적으세요.
- 꼭 넣을 내용(설명서에 있는 만큼):
  1) 신호 흐름: 입력·채널·버스(모니터)·메인·매트릭스·DCA 수와 역할
  2) 콘솔 겉면: 화면·버튼·페이더 구역·레이어, 선택(SELECT)·뮤트·솔로
  3) 모니터 믹스 만들고 조절하는 방법 (단계별)
  4) 게인·팬텀(+48V)·로우컷·EQ·컴프·게이트 조절 방법
  5) 이펙트(리버브·딜레이) 넣고 보내는 방법
  6) 라우팅/패치: 입력 단자 → 채널, 버스·메인 → 출력 단자, 스테이지박스·USB 녹음
  7) 씬/스냅샷 저장·불러오기, 안전하게 불러오는 방법(Safe/Recall 범위)
  8) 네트워크·원격 조작(앱/OSC) 설정, 원격 잠금
  9) 자주 생기는 문제와 확인 순서(소리 안 남, 하울링, 모니터 안 나옴, USB 녹음 안 됨 등)
  10) 용어 풀이 (쉬운 말로 한 줄씩)
- 버튼·메뉴 이름은 콘솔에 보이는 영문 그대로 쓰고, 단계는 1) 2) 3) 으로.
- 설명서에 없는 내용은 지어내지 말고, 일반 지식으로 보충할 때는 "(설명서에서 확인 못 함)"이라고 표시하세요.
- 쉬운 말로, 짧은 줄 위주. 전체 길이는 한국어 약 1만~1만 5천 자.
- 답에는 참고 자료 본문만 쓰세요."""


class Builder:
    """오래 걸리는 작업(받기·요약)을 하나씩 처리하고 진행 상황을 알려 줍니다."""

    def __init__(self):
        self.lock = threading.Lock()
        self.prepared = {}       # token → {text, pdf, pages, name, source, model}
        self.job = None

    # 1단계: 파일을 읽고 비용을 미리 알려 줌
    def prepare(self, client, ai_model, data: bytes, name: str, source: str, model: str):
        text, pages, pdf = extract(data, name)
        if not text and not pdf:
            raise ValueError("파일에서 글자를 찾지 못했습니다.")
        token = uuid.uuid4().hex[:12]
        est = None
        if client is not None:
            try:
                content = self._content(text, pdf, model or "콘솔")
                n = client.messages.count_tokens(model=ai_model, messages=[{"role": "user", "content": content}]).input_tokens
                usd = n * 4 / 1e6 + 20000 * 20 / 1e6
                est = {"tokens": n, "usd": round(usd, 2), "krw": int(round(usd * USD_KRW, -2))}
            except Exception:
                est = None
        with self.lock:
            self.prepared = {token: {"text": text, "pdf": pdf, "pages": pages, "name": name, "source": source}}
        return {"token": token, "pages": pages, "chars": len(text), "scanned": pdf is not None, "name": name, "estimate": est}

    def _content(self, text, pdf, model):
        prompt = BUILD_PROMPT.format(model=model)
        if pdf is not None:
            import base64
            return [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                    "data": base64.standard_b64encode(pdf).decode()}},
                    {"type": "text", "text": prompt}]
        return [{"type": "text", "text": "<manual>\n" + text + "\n</manual>"}, {"type": "text", "text": prompt}]

    # 2단계: 요약 만들기 (백그라운드)
    def start(self, client, ai_model, token, title, model, on_done):
        with self.lock:
            if self.job and self.job["state"] == "running":
                raise ValueError("이미 만들고 있는 자료가 있습니다. 끝난 뒤 다시 해 주세요.")
            p = self.prepared.pop(token, None)
            if p is None:
                raise ValueError("파일을 다시 올려 주세요(준비된 파일이 없습니다).")
            self.job = {"state": "running", "step": "AI가 설명서를 읽고 정리하는 중… (보통 2~5분)", "started": time.time(),
                        "title": title, "id": None, "error": ""}
        threading.Thread(target=self._run, args=(client, ai_model, p, title, model, on_done), daemon=True).start()

    def _run(self, client, ai_model, p, title, model, on_done):
        try:
            with client.beta.messages.stream(
                    model=ai_model, max_tokens=64000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                    output_config={"effort": "medium"},
                    messages=[{"role": "user", "content": self._content(p["text"], p["pdf"], model)}]) as stream:
                n = 0
                for ev in stream:
                    if getattr(ev, "type", "") == "content_block_delta" and getattr(ev.delta, "type", "") == "text_delta":
                        n += len(ev.delta.text)
                        if n % 400 < len(ev.delta.text):
                            self.job["step"] = f"정리한 글을 쓰는 중… {n:,}자"
                msg = stream.get_final_message()
            if msg.stop_reason == "refusal":
                raise ValueError("AI가 이 문서를 처리하지 못했습니다.")
            body = "".join(b.text for b in msg.content if b.type == "text").strip()
            if len(body) < 500:
                raise ValueError("정리된 내용이 너무 짧습니다. 다른 설명서 파일로 다시 해 보세요.")
            u = msg.usage
            usd = (u.input_tokens + (u.cache_read_input_tokens or 0)) * 4 / 1e6 + u.output_tokens * 20 / 1e6
            mid = add(title or f"{model} 설명서 요약", model, body, p["source"] or p["name"], p["pages"])
            self.job.update(state="done", step="완료", id=mid, cost={"usd": round(usd, 2), "krw": int(round(usd * USD_KRW, -1))})
            on_done(mid)
        except Exception as e:
            msg = str(e)
            try:
                import anthropic
                if isinstance(e, anthropic.AuthenticationError):
                    msg = "API 키가 올바르지 않습니다."
                elif isinstance(e, anthropic.APIConnectionError):
                    msg = "인터넷 연결을 확인해 주세요."
                elif isinstance(e, anthropic.APIStatusError):
                    msg = f"Claude API 오류 ({e.status_code}): {e.message}"
            except ImportError:
                pass
            self.job.update(state="error", step="실패", error=msg)

    def status(self):
        j = self.job
        if not j:
            return {"state": "idle"}
        return dict(j, elapsed=int(time.time() - j["started"]))


BUILDER = Builder()
