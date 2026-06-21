"""
llm_io/llm.py
--------------
LLMプロバイダーを切り替えられる薄いラッパー。
"""

import os
from observation.logger import log

DEFAULT_MAX_TOKENS = 512

# =========================================================
# Anthropic
# =========================================================

_anthropic_client = None

def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY が設定されていません")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client

def _call_anthropic(system, messages, model, max_tokens):
    import anthropic
    client   = _get_anthropic_client()
    response = client.messages.create(
        model      = model or "claude-sonnet-4-6",
        max_tokens = max_tokens,
        system     = system,
        messages   = messages,
    )
    text = response.content[0].text if response.content else ""
    log(f"[LLM:anthropic] in={response.usage.input_tokens} out={response.usage.output_tokens}")
    return text


# =========================================================
# Gemini（新SDK: google-genai）
# =========================================================

_gemini_client = None

def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY が設定されていません")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client

def _call_gemini(system, messages, model, max_tokens):
    from google import genai
    from google.genai import types

    client     = _get_gemini_client()
    model_name = model or "gemini-2.5-flash-lite"

    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(
            role  = role,
            parts = [types.Part(text=m["content"])]
        ))

    config = types.GenerateContentConfig(
        system_instruction  = system,
        max_output_tokens   = max_tokens,
        temperature         = 1.5,   # 創造性を上げる（高いほど毎回違う返答）
        safety_settings     = [
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
        ],
    )

    # タイムアウト30秒で試行、失敗したらgemini-2.0-flash-liteで再試行
    try:
        response = client.models.generate_content(
            model    = model_name,
            contents = contents,
            config   = config,
        )
        text = response.text or ""
        log(f"[LLM:gemini] model={model_name}")
        return text
    except Exception as e:
        log(f"[LLM:gemini] {model_name} 失敗: {e} → fallback")
        # フォールバックモデルで再試行
        try:
            response = client.models.generate_content(
                model    = "gemini-2.5-flash",
                contents = contents,
                config   = config,
            )
            text = response.text or ""
            log(f"[LLM:gemini] fallback=gemini-2.5-flash")
            return text
        except Exception as e2:
            log(f"[LLM ERROR] {e2}")
            return ""


# =========================================================
# 統一インターフェース
# =========================================================

def call(
    system:     str,
    messages:   list,
    model:      str = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    provider = os.environ.get("CHRONOS_LLM_PROVIDER", "anthropic").lower()

    try:
        if provider == "gemini":
            return _call_gemini(system, messages, model, max_tokens)
        else:
            return _call_anthropic(system, messages, model, max_tokens)
    except Exception as e:
        log(f"[LLM ERROR] {e}")
        return ""


"""
llm_io/search.py
-----------------
DuckDuckGo Web検索の薄いラッパー。
ponが「調べてみる！」と言いながら使う。
"""

from observation.logger import log


def search(query: str, max_results: int = 3) -> list[dict]:
    """
    クエリでWeb検索して結果を返す。
    戻り値: [{"title": str, "body": str, "href": str}, ...]
    失敗時は空リストを返す。
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        log(f"[SEARCH] '{query}' → {len(results)}件")
        return results
    except ImportError:
        log("[SEARCH ERROR] ddgs 未インストール: pip install ddgs")
        return []
    except Exception as e:
        log(f"[SEARCH ERROR] {e}")
        return []


def search_summary(query: str, max_results: int = 3) -> str:
    """
    検索結果をLLMに渡しやすいテキストにまとめる。
    """
    results = search(query, max_results)
    if not results:
        return ""
    lines = []
    for r in results:
        title = r.get("title", "")
        body  = r.get("body", "")[:100]
        lines.append(f"・{title}: {body}")
    return "\n".join(lines)


def should_search(user_input: str, strengths: list) -> tuple[bool, str]:
    """
    検索が必要かどうかを判定して検索クエリを返す。
    得意話題 or 「最近」「新しい」「話題」などのキーワードがあれば検索する。

    戻り値: (検索するか, クエリ文字列)
    """
    SEARCH_TRIGGERS = ["最近", "新しい", "話題", "今", "最新", "新作", "流行", "人気"]

    # 検索トリガーワードがあれば検索
    for trigger in SEARCH_TRIGGERS:
        if trigger in user_input:
            return True, user_input

    # 得意話題なら検索
    for strength in strengths:
        keywords = [kw.strip() for kw in
                    strength.replace("（"," ").replace("）"," ").replace("、"," ").split()
                    if len(kw.strip()) >= 2]
        if any(kw in user_input for kw in keywords):
            return True, f"{strength} {user_input}"

    return False, ""
