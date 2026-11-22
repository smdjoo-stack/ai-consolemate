"""Google AI Studio (Gemini) API 로 AI 대화하기.

- 키: https://aistudio.google.com/apikey 에서 만든 키 (AIza 로 시작)
- 외부 패키지 없이 표준 라이브러리(urllib)로 REST API 를 부릅니다.
- 콘솔 조작 도구(wing_tools.TOOLS)를 Gemini 의 function calling 형식으로 바꿔 씁니다.
"""

import json
import urllib.error
import urllib.request

BASE = "https://generativelanguage.googleapis.com/v1beta"
HOST = "generativelanguage.googleapis.com"
# 키 확인 때 쓸 수 있는 모델 중 이 순서로 고릅니다 (빠르고 저렴한 Flash 우선)
PREFERRED = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-pro-latest", "gemini-2.5-pro"]
KEEP = {"type", "description", "properties", "required", "enum", "items", "minimum", "maximum"}


class GeminiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _req(method, path, key, body=None, timeout=120):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        raise GeminiError(e.code, msg or e.reason)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GeminiError(0, f"연결 실패: {e}")


def _schema(s):
    """JSON Schema → Gemini 가 받는 부분만."""
    out = {k: v for k, v in s.items() if k in KEEP}
    if "properties" in out:
        out["properties"] = {k: _schema(v) for k, v in out["properties"].items()}
    if "items" in out:
        out["items"] = _schema(out["items"])
    if "enum" in out:
        out["enum"] = [str(x) for x in out["enum"]]
        out["type"] = "string"
    return out


def convert_tools(tools):
    return [{"functionDeclarations": [{"name": t["name"], "description": t.get("description", ""),
                                       "parameters": _schema(t["input_schema"])} for t in tools]}]


class GeminiClient:
    provider = "google"

    def __init__(self, api_key, model=""):
        self.key = api_key
        self.model = model or PREFERRED[1]

    def list_models(self):
        names = []
        page = ""
        for _ in range(5):
            r = _req("GET", "models?pageSize=200" + (f"&pageToken={page}" if page else ""), self.key, timeout=15)
            for m in r.get("models", []):
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    names.append(m["name"].split("/", 1)[-1])
            page = r.get("nextPageToken", "")
            if not page:
                break
        return names

    def pick_model(self):
        """키로 쓸 수 있는 모델 중 하나 고르기."""
        names = self.list_models()
        for p in PREFERRED:
            if p in names:
                return p
        flash = [n for n in names if "flash" in n and "lite" not in n and "image" not in n and "tts" not in n]
        return (flash or names or [self.model])[0]

    def generate(self, system, contents, tools=None):
        body = {"contents": contents, "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"temperature": 0.4}}
        if tools:
            body["tools"] = tools
            body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
        return _req("POST", f"models/{self.model}:generateContent", self.key, body)


def test_key(key):
    """(결과, 메시지, 고른 모델). 결과: ok / bad / offline. 모델 목록만 조회하므로 요금 없음."""
    c = GeminiClient(key)
    try:
        model = c.pick_model()
        return "ok", f"키가 확인되었습니다. ({model} 사용)", model
    except GeminiError as e:
        if e.status in (400, 401, 403):
            return "bad", "Google AI Studio 키가 올바르지 않거나 권한이 없습니다. aistudio.google.com 의 API 키를 다시 복사해 주세요.", ""
        if e.status == 0:
            return "offline", "인터넷에 연결되지 않아 키를 확인하지 못했습니다. 키는 저장했고, 인터넷이 되면 바로 쓸 수 있어요.", ""
        return "offline", f"Google 서버 응답 오류({e.status})로 확인하지 못했습니다. 키는 저장했습니다.", ""


def chat(client, system, history, tools_list, run_tool, user_text, max_steps=15):
    """한 번의 사용자 요청을 도구 호출까지 처리. history 는 이어지는 대화 목록(제자리에서 늘어남).
    돌려줌: {"reply", "actions", ("_error")}"""
    gtools = convert_tools(tools_list)
    actions = []
    start = len(history)
    history.append({"role": "user", "parts": [{"text": user_text}]})
    for _ in range(max_steps):
        try:
            r = client.generate(system, history, gtools)
        except GeminiError as e:
            del history[start:]
            if e.status in (400, 401, 403) and ("key" in e.message.lower() or "permission" in e.message.lower()):
                return {"reply": "Google AI Studio 키가 올바르지 않습니다. ⚙ 설정 → API 키를 확인해 주세요.", "actions": actions, "_error": "Google API 키가 올바르지 않음"}
            if e.status == 429:
                return {"reply": "요청이 너무 많거나 무료 사용량을 넘었습니다. 잠시 후 다시 시도해 주세요.", "actions": actions, "_error": "요청이 너무 많음 (Google 사용량 한도)"}
            if e.status == 0:
                return {"reply": "인터넷 연결을 확인해 주세요 (Google 서버에 접속할 수 없음).", "actions": actions, "_error": "인터넷 연결 안 됨"}
            return {"reply": f"Google API 오류 ({e.status}): {e.message}", "actions": actions, "_error": f"Google API 오류 {e.status}"}
        cands = r.get("candidates") or []
        if not cands or not cands[0].get("content"):
            reason = (r.get("promptFeedback") or {}).get("blockReason") or (cands[0].get("finishReason") if cands else "")
            del history[start:]
            return {"reply": f"이 요청은 처리할 수 없습니다. ({reason or '응답 없음'})", "actions": actions}
        content = cands[0]["content"]
        content.setdefault("role", "model")
        history.append(content)              # thoughtSignature 등 그대로 돌려줘야 함
        calls = [p["functionCall"] for p in content.get("parts", []) if "functionCall" in p]
        if not calls:
            text = "\n".join(p.get("text", "") for p in content.get("parts", []) if p.get("text") and not p.get("thought")).strip()
            return {"reply": text or "(응답 없음)", "actions": actions}
        parts = []
        for fc in calls:
            name, args = fc.get("name", ""), fc.get("args") or {}
            out, is_err = run_tool(name, args)
            actions.append({"tool": name, "input": args, "error": is_err, "result": out[:300]})
            resp = {"name": name, "response": {"error": out} if is_err else {"result": out}}
            if fc.get("id"):
                resp["id"] = fc["id"]
            parts.append({"functionResponse": resp})
        history.append({"role": "user", "parts": parts})
    return {"reply": "작업 단계가 너무 많아 멈췄습니다. 요청을 나눠서 다시 말씀해 주세요.", "actions": actions}
