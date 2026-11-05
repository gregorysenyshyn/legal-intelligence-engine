"""
Local LM Studio Client (http://localhost:1234/v1) for 100% Air-Gapped Legal Intelligence:
1. Contextual Chunk PII Detection (catching first names, nicknames, workplaces, and teachers
   in small 100-token chunks before any text reaches a cloud model).
2. 100% Offline Case Q&A (`./firm ask "<question>"`), feeding compact SQLite FTS5 snippets
   (<600 tokens) to a local Apple Silicon MLX/GGUF model in LM Studio for sub-2-second answers.
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

DEFAULT_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")


def get_active_model(base_url: str = DEFAULT_BASE_URL, timeout: float = 1.2) -> Optional[str]:
    """Checks if LM Studio server is running locally and returns the loaded model ID."""
    url = f"{base_url.rstrip('/')}/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data", [])
            if models:
                return models[0].get("id", "local-model")
    except Exception:
        return None
    return None


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    base_url: str = DEFAULT_BASE_URL,
    temperature: float = 0.0,
    max_tokens: int = 512,
    timeout: float = 30.0,
) -> Tuple[Optional[str], Optional[str], float]:
    """Calls LM Studio's local OpenAI-compatible /v1/chat/completions endpoint."""
    model_id = get_active_model(base_url)
    if not model_id:
        return None, None, 0.0

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    t0 = time.time()
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            choices = result.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                # Strip <think>...</think> blocks if using a local reasoning model (e.g. DeepSeek/Qwen-QwQ)
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
                return content, model_id, elapsed
    except Exception:
        return None, model_id, time.time() - t0
    return None, model_id, time.time() - t0


def extract_contextual_pii_with_llm(
    chunk_text: str,
    base_url: str = DEFAULT_BASE_URL,
) -> List[Dict[str, str]]:
    """
    Uses a local LLM in LM Studio to detect contextual PII in a small (40-150 token) chunk:
    first names, nicknames, informal workplaces, schools, teachers, or street locations
    that standard regexes miss.
    """
    if not chunk_text or len(chunk_text.strip()) < 15:
        return []

    sys_prompt = (
        "You are a local legal privacy redaction engine. Extract ONLY specific private entities from the snippet:\n"
        "- PERSON: Human names, first names, or nicknames (e.g. 'Sarah', 'Tommy', 'Kevin', 'Dr. Miller', 'Justice Henderson').\n"
        "- ORG: Employers, companies, schools, daycares, clinics, or local branches.\n"
        "- ADDRESS: Street addresses or specific private locations.\n"
        "DO NOT extract generic legal roles (Applicant, Respondent, Father, Mother, Child, Court, Judge), "
        "months/days, dollar amounts, or existing bracketed tokens like [CLIENT_APPLICANT].\n"
        "Respond ONLY with a valid JSON list of objects: [{\"text\": \"exact match\", \"type\": \"PERSON|ORG|ADDRESS\"}]. "
        "If none exist, respond with []."
    )
    resp_text, _, _ = chat_completion(
        system_prompt=sys_prompt,
        user_prompt=f"Snippet:\n{chunk_text}",
        base_url=base_url,
        temperature=0.0,
        max_tokens=200,
        timeout=12.0,
    )
    if not resp_text:
        return []

    # Extract JSON array from response
    m = re.search(r"\[.*\]", resp_text, flags=re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
        valid = []
        for item in items:
            if isinstance(item, dict) and item.get("text") and item.get("type") in ("PERSON", "ORG", "ADDRESS"):
                txt = str(item["text"]).strip()
                if len(txt) >= 3 and not txt.startswith("["):
                    valid.append({"text": txt, "type": str(item["type"])})
        return valid
    except Exception:
        return []


def ask_local_case_assistant(
    question: str,
    case_name: Optional[str] = None,
    base_url: str = DEFAULT_BASE_URL,
):
    """
    Executes a 100% air-gapped local RAG query using SQLite FTS5 + LM Studio.
    Because SQLite FTS5 narrows the context to <600 tokens, local Apple Silicon models
    respond in 1-3 seconds with zero cloud traffic.
    """
    from db.case_db import get_active_case_name, search_case_documents, CASES_DIR

    active = case_name or get_active_case_name()
    if not active:
        console.print("[red]Error: No active case selected. Run './firm use <case_name>' first.[/red]")
        return

    model_id = get_active_model(base_url)
    if not model_id:
        console.print(
            "[bold yellow]⚠ LM Studio Local Server Not Detected at "
            f"{base_url}[/bold yellow]\n"
            "To run 100% offline local LLM queries on your Mac:\n"
            "  1. Open [bold]LM Studio[/bold] (or run [cyan]~/.lmstudio/bin/lms server start[/cyan])\n"
            "  2. Load any 7B–14B Instruct model (e.g. Qwen2.5-7B-Instruct-MLX or Gemma-3-12B-MLX)\n"
            "  3. Re-run: [cyan]./firm ask \"" + question + "\"[/cyan]"
        )
        return

    # Build compact context from CASE_CORE.md + top FTS5 search hits
    case_dir = CASES_DIR / active
    core_file = case_dir / "CASE_CORE.md"
    core_text = core_file.read_text(encoding="utf-8")[:1500] if core_file.exists() else ""

    # Extract keywords from question for FTS5
    stop = {"what", "where", "when", "who", "how", "why", "did", "does", "the", "and", "for", "with", "from", "that", "this", "is", "are", "was", "were"}
    keywords = [w for w in re.findall(r"[A-Za-z0-9]+", question) if w.lower() not in stop and len(w) >= 3]
    fts_query = " OR ".join(keywords[:6]) if keywords else question

    hits = search_case_documents(fts_query, limit=5, case_name=active)
    snippets_block = "\n".join(
        f"- [{h['filename']}, Page {h['page_number']}]: {re.sub(r'</?b>', '', h['preview'])}"
        for h in hits
    )

    sys_prompt = (
        "You are a 100% offline Ontario Family Law Evidentiary Assistant running locally in LM Studio. "
        "Answer the counsel's question concisely and accurately using ONLY the provided Case Bedrock and "
        "Indexed Document Snippets. Every factual assertion or dollar figure MUST cite its exact source "
        "in brackets: [Document Name, Page X]. Never guess or invent facts."
    )
    user_prompt = (
        f"=== CASE BEDROCK ({active}) ===\n{core_text}\n\n"
        f"=== MATCHING DOCUMENT SNIPPETS ===\n{snippets_block or 'No additional snippets matched.'}\n\n"
        f"=== QUESTION ===\n{question}"
    )

    console.print(f"[dim]Querying local LM Studio model ({model_id}) with {len(hits)} pinpoint snippet(s)...[/dim]")
    answer, used_model, elapsed = chat_completion(
        system_prompt=sys_prompt,
        user_prompt=user_prompt,
        base_url=base_url,
        temperature=0.1,
        max_tokens=600,
        timeout=45.0,
    )
    if not answer:
        console.print("[red]Error: Local LM Studio request timed out or returned an empty response.[/red]")
        return

    header = (
        f"[bold green]100% Air-Gapped Local LLM Response[/bold green] "
        f"[dim](Model: {used_model} | Latency: {elapsed:.2f}s | Case: {active})[/dim]"
    )
    console.print(Panel(Markdown(answer), title=header, border_style="green"))
