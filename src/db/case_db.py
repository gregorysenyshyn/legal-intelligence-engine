"""
Multi-Client Database Manager for Ontario Family Law Practices.
Manages per-case SQLite FTS5 databases, active case switching, and sub-second page-level search.
"""

import os
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
from rich.console import Console

console = Console()

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CASES_DIR = ROOT_DIR / "cases"
ACTIVE_CASE_FILE = ROOT_DIR / ".active_case"
SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"

def get_active_case_name() -> Optional[str]:
    """Returns the name of the currently selected client case."""
    if ACTIVE_CASE_FILE.exists():
        name = ACTIVE_CASE_FILE.read_text(encoding="utf-8").strip()
        if name and (CASES_DIR / name).is_dir():
            return name
    # Default to first non-template case if available
    cases = list_cases()
    if cases:
        set_active_case(cases[0])
        return cases[0]
    return None

def set_active_case(case_name: str) -> bool:
    """Sets the active client case."""
    case_dir = CASES_DIR / case_name
    if not case_dir.is_dir():
        console.print(f"[red]Error: Case '{case_name}' does not exist in cases/[/red]")
        return False
    ACTIVE_CASE_FILE.write_text(case_name, encoding="utf-8")
    return True

def list_cases() -> List[str]:
    """Lists all available client cases."""
    if not CASES_DIR.exists():
        return []
    return [d.name for d in sorted(CASES_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".")]

def create_case(case_name: str, court_file_no: str = "", applicant: str = "", respondent: str = "", child: str = "") -> Path:
    """Creates a new client case folder structure, seeds PII scrubber mappings, and initializes its SQLite database."""
    from privacy.scrubber import PrivacyScrubber
    safe_name = re.sub(r'[^\w\-_\. ]', '_', case_name).strip().replace(" ", "_")
    case_dir = CASES_DIR / safe_name
    
    (case_dir / "01_raw").mkdir(parents=True, exist_ok=True)
    (case_dir / "02_text").mkdir(parents=True, exist_ok=True)
    (case_dir / "events").mkdir(parents=True, exist_ok=True)
    (case_dir / "memos").mkdir(parents=True, exist_ok=True)

    scrubber = PrivacyScrubber(safe_name)
    scrubber.seed_case_parties(applicant=applicant, respondent=respondent, child=child)

    core_path = case_dir / "CASE_CORE.md"
    if not core_path.exists():
        core_path.write_text(
            f"# CASE CORE BEDROCK: {case_name.upper()}\n"
            f"**Court File No.:** {court_file_no or '[TBD]'}\n"
            f"**Applicant:** [CLIENT_APPLICANT]\n"
            f"**Respondent:** [RESPONDENT_PARTY]\n\n"
            "## 1. Key Dates & Operative Orders\n- [Add operative orders and key dates]\n\n"
            "## 2. Parenting Schedule & Logistics\n- [Add parenting schedule and exchange protocol]\n\n"
            "## 3. Financial & Child Support Metrics\n- [Add Line 15000 incomes, CSG table amounts, and Section 7 ratios]\n\n"
            "## 4. Core Evidentiary Pinpoints & Impeachments\n- [Add verified citations `[Document, Page X]`]\n",
            encoding="utf-8",
        )
    
    # Initialize DB
    db_path = case_dir / "case.db"
    conn = sqlite3.connect(str(db_path))
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    
    # Store case meta (masked tokens stored in DB; raw identities remain only in privacy_map.json)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO case_meta (key, value) VALUES ('case_name', ?)", (case_name,))
    cursor.execute("INSERT OR REPLACE INTO case_meta (key, value) VALUES ('court_file_no', ?)", (court_file_no,))
    cursor.execute("INSERT OR REPLACE INTO case_meta (key, value) VALUES ('applicant', ?)", ("[CLIENT_APPLICANT]",))
    cursor.execute("INSERT OR REPLACE INTO case_meta (key, value) VALUES ('respondent', ?)", ("[RESPONDENT_PARTY]",))
    conn.commit()
    conn.close()
    
    set_active_case(safe_name)
    return case_dir

def get_case_connection(case_name: Optional[str] = None):
    """Returns a sqlite3 connection for the active or specified case."""
    active = case_name or get_active_case_name()
    if not active:
        raise ValueError("No active case selected. Run './firm use <case_name>' or './firm new <case_name>'.")
    db_path = CASES_DIR / active / "case.db"
    if not db_path.exists():
        # Initialize if missing
        conn = sqlite3.connect(str(db_path))
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()
        
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def sanitize_fts_query(q: str) -> str:
    """Escapes and structures search terms for SQLite FTS5."""
    q_strip = q.strip()
    if q_strip.startswith('"') and q_strip.endswith('"'):
        return q_strip
    cleaned = re.sub(r'[^\w\s*"]', ' ', q_strip).strip()
    words = [w for w in cleaned.split() if w]
    if not words:
        return '""'
    return ' '.join(f'"{w}"' for w in words)

def resolve_page_number(content: str, snippet: str) -> int:
    """Calculates the exact source page number from markdown ## Page X markers."""
    clean_snippet = re.sub(r'</?b>', '', snippet).strip('. \n\t')
    if not clean_snippet or not content:
        return 1
    
    search_sub = clean_snippet[:35].strip()
    pos = content.find(search_sub)
    if pos == -1 and len(clean_snippet) > 40:
        search_sub = clean_snippet[15:45].strip()
        pos = content.find(search_sub)
        
    if pos != -1:
        prefix = content[:pos]
        pages = re.findall(r'##\s*Page\s*(\d+)', prefix)
        if pages:
            return int(pages[-1])
            
    return 1

def search_case_documents(query_text: str, limit: int = 10, case_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Performs an FTS5 search across all extracted client documents with exact page numbers."""
    conn = get_case_connection(case_name)
    cursor = conn.cursor()
    safe_query = sanitize_fts_query(query_text)
    
    sql = """
        SELECT filename, content, snippet(document_fts, 1, '<b>', '</b>', '...', 30) as preview
        FROM document_fts
        WHERE document_fts MATCH ?
        LIMIT ?
    """
    try:
        cursor.execute(sql, (safe_query, limit))
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        # Fallback to simple LIKE search if syntax error in FTS
        like_sql = """
            SELECT filename, content, substr(content, 1, 200) as preview
            FROM document_fts
            WHERE content LIKE ?
            LIMIT ?
        """
        cursor.execute(like_sql, (f"%{query_text}%", limit))
        rows = cursor.fetchall()

    from privacy.scrubber import PrivacyScrubber
    active = case_name or get_active_case_name()
    scrubber = PrivacyScrubber(active)

    results = []
    for r in rows:
        fn = r["filename"]
        content = r["content"]
        snippet = r["preview"]
        page_num = resolve_page_number(content, snippet)
        results.append({
            "filename": fn,
            "page_number": page_num,
            "preview": scrubber.mask_text(snippet)
        })
    conn.close()
    return results

def get_page_content(filename: str, page: int, end_page: Optional[int] = None, case_name: Optional[str] = None) -> str:
    """Extracts exact pages from an indexed document markdown file."""
    active = case_name or get_active_case_name()
    if not active:
        return "Error: No active case selected."
    text_dir = CASES_DIR / active / "02_text"
    
    # Locate matching md file
    target = None
    for p in text_dir.glob("*.md"):
        if p.stem.lower() == filename.lower() or p.name.lower() == filename.lower():
            target = p
            break
            
    if not target:
        # Partial match fallback
        for p in text_dir.glob("*.md"):
            if filename.lower() in p.stem.lower():
                target = p
                break
                
    if not target:
        return f"Document '{filename}' not found in active case '{active}'."

    content = target.read_text(encoding="utf-8", errors="replace")
    
    # Split by ## Page X or <!-- Page X -->
    page_markers = list(re.finditer(r'(?:##\s*Page\s*(\d+)|<!--\s*Page\s*(\d+)\s*-->)', content, re.I))
    if not page_markers:
        return content # Return all if unpaged
        
    pages_dict = {}
    for i in range(len(page_markers)):
        m = page_markers[i]
        p_num = int(m.group(1) or m.group(2))
        start_idx = m.start()
        end_idx = page_markers[i+1].start() if i + 1 < len(page_markers) else len(content)
        pages_dict[p_num] = content[start_idx:end_idx]

    max_p = end_page if end_page else page
    extracted = []
    for p in range(page, max_p + 1):
        if p in pages_dict:
            extracted.append(pages_dict[p].strip())
            
    if not extracted:
        return f"Page {page} not found in '{filename}' (Document contains {len(pages_dict)} indexed pages)."
        
    from privacy.scrubber import PrivacyScrubber
    scrubber = PrivacyScrubber(active)
    return scrubber.mask_text("\n\n---\n\n".join(extracted))


def check_sync_drift(case_dir: Path, core_file: Path) -> List[Path]:
    """Returns strategic memos modified more recently than CASE_CORE.md."""
    if not core_file.exists():
        return []
    core_mtime = core_file.stat().st_mtime
    stale = []
    for sub in ("memos", "orders"):
        d = case_dir / sub
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            if f.stat().st_mtime > core_mtime + 2.0:
                stale.append(f.relative_to(case_dir))
    return stale


def show_case_core(case_name: Optional[str] = None):
    """Displays the active case's CASE_CORE.md bedrock and flags any sync drift."""
    from rich.markdown import Markdown
    active = case_name or get_active_case_name()
    if not active:
        console.print("[red]Error: No active case selected.[/red]")
        return
    case_dir = CASES_DIR / active
    core_file = case_dir / "CASE_CORE.md"
    if not core_file.exists():
        console.print(f"[yellow]No CASE_CORE.md found in cases/{active}/.[/yellow]")
        return
    console.print(Markdown(core_file.read_text(encoding="utf-8")))
    stale = check_sync_drift(case_dir, core_file)
    if stale:
        console.print(
            "\n[bold yellow]⚠ SYNC DRIFT NOTICE:[/bold yellow] The following files were modified more recently than CASE_CORE.md: "
            + ", ".join(str(p) for p in stale)
        )


def show_case_map(show_headings: bool = False, case_name: Optional[str] = None):
    """Prints a token-efficient coupled-graph map & sync drift check for the active case."""
    from datetime import datetime
    from rich.table import Table
    active = case_name or get_active_case_name()
    if not active:
        console.print("[red]Error: No active case selected.[/red]")
        return
    case_dir = CASES_DIR / active
    core_file = case_dir / "CASE_CORE.md"
    core_mtime = core_file.stat().st_mtime if core_file.exists() else 0

    t = Table(title=f"Coupled-Graph Strategic Map & Sync Check ({active})", show_header=True, header_style="bold magenta")
    t.add_column("Group", style="cyan", width=12)
    t.add_column("Relative Path", style="bold white", width=48)
    t.add_column("Lines", justify="right", width=7)
    t.add_column("Updated", style="dim", width=16)
    t.add_column("Sync Status", width=20)

    items = []
    if core_file.exists():
        items.append(("Core", core_file))
    for label, sub in [("Memos/Briefs", "memos"), ("Indexed Text", "02_text")]:
        d = case_dir / sub
        if d.exists():
            for f in sorted(d.glob("*.md")):
                items.append((label, f))

    for label, f in items:
        rel_path = str(f.relative_to(case_dir))
        text = f.read_text(encoding="utf-8", errors="ignore")
        lines = len(text.splitlines())
        mtime = f.stat().st_mtime
        dt_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        if f.resolve() == core_file.resolve():
            status = "[bold cyan]MASTER BEDROCK[/bold cyan]"
        elif label == "Indexed Text":
            status = "[dim]EVIDENCE INDEX[/dim]"
        elif mtime > core_mtime + 2.0:
            status = "[bold yellow]NEWER THAN CORE (!)[/bold yellow]"
        else:
            status = "[green]IN SYNC[/green]"
        t.add_row(label, rel_path, str(lines), dt_str, status)
        if show_headings and label != "Indexed Text":
            headings = [line.strip() for line in text.splitlines() if line.startswith("## ")][:5]
            if headings:
                t.add_row("", f"[dim]↳ {' | '.join(headings)}[/dim]", "", "", "")
    console.print(t)


