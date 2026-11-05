"""
Git Submodule & Cloud Intake Sync Manager for Ontario Law Practices.
Coordinates client multi-tenancy:
  1. Adding client repositories as isolated Git submodules.
  2. Pulling remote client updates (Jules commits, mobile uploads).
  3. Incrementally ingesting new raw documents via native macOS OCR.
  4. Syncing the append-only timeline.jsonl ledger directly into SQLite FTS5.
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from db.case_db import get_active_case_name, set_active_case, get_case_connection, CASES_DIR, SCHEMA_FILE
from ingest.ingest_pipeline import ingest_source

def add_client_submodule(case_name: str, repo_url: str) -> bool:
    """Adds a remote client Git repository as a submodule under cases/<case_name>."""
    submodule_path = f"cases/{case_name}"
    target_dir = ROOT_DIR / submodule_path
    
    if target_dir.exists() and (target_dir / ".git").exists():
        console.print(f"[yellow]Client case directory '{case_name}' already exists.[/yellow]")
        return False

    console.print(f"[bold cyan]Adding client submodule from {repo_url}...[/bold cyan]")
    try:
        cmd = ["git", "submodule", "add", repo_url, submodule_path]
        subprocess.run(cmd, cwd=str(ROOT_DIR), check=True)
        
        # Initialize SQLite DB if not present in the submodule
        db_path = target_dir / "case.db"
        if not db_path.exists():
            conn = sqlite3.connect(str(db_path))
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.close()
            
        set_active_case(case_name)
        console.print(f"[bold green]✓ Successfully linked client '{case_name}' via Git submodule![/bold green]")
        
        # Initial sync
        sync_case(case_name)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error adding git submodule: {e}[/red]")
        return False

def sync_ledger_to_db(case_name: str) -> int:
    """Syncs any events from events/timeline.jsonl into the local SQLite database."""
    case_dir = CASES_DIR / case_name
    ledger_file = case_dir / "events" / "timeline.jsonl"
    if not ledger_file.exists():
        return 0
        
    conn = get_case_connection(case_name)
    cursor = conn.cursor()
    
    # Get existing event signatures: (event_date, event_time, title)
    cursor.execute("SELECT event_date, event_time, title FROM timeline_events")
    existing = set((r[0] or "", r[1] or "", r[2] or "") for r in cursor.fetchall())
    
    new_count = 0
    with open(ledger_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
                
            sig = (entry.get("event_date") or "", entry.get("event_time") or "", entry.get("title") or "")
            if sig not in existing:
                cursor.execute("""
                    INSERT INTO timeline_events (
                        event_date, event_time, title, location, key_parties,
                        category, description, child_impact, counsel_notes,
                        source_citation, page_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.get("event_date", ""),
                    entry.get("event_time", ""),
                    entry.get("title", ""),
                    entry.get("location", ""),
                    entry.get("key_parties", ""),
                    entry.get("category", "General"),
                    entry.get("description", ""),
                    entry.get("child_impact", ""),
                    entry.get("counsel_notes", ""),
                    entry.get("source_citation", ""),
                    entry.get("page_number")
                ))
                existing.add(sig)
                new_count += 1
                
    conn.commit()
    conn.close()
    return new_count

def sync_case(case_name: Optional[str] = None):
    """Pulls remote updates from GitHub, syncs ledger, and ingests unindexed documents."""
    active = case_name or get_active_case_name()
    if not active:
        console.print("[red]No active case selected for sync.[/red]")
        return
        
    case_dir = CASES_DIR / active
    console.print(f"[bold cyan]Synchronizing client case: '{active}'...[/bold cyan]")
    
    # 1. Pull Git submodule updates if it is a git repo
    is_submodule = (case_dir / ".git").exists() or (ROOT_DIR / ".gitmodules").exists()
    if is_submodule:
        try:
            cmd = ["git", "submodule", "update", "--remote", "--merge", f"cases/{active}"]
            subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
            console.print("  • [green]Git submodule pulled from remote GitHub repository.[/green]")
        except Exception as e:
            console.print(f"  • [yellow]Git submodule pull skipped: {e}[/yellow]")

    # 2. Sync timeline ledger to SQLite
    new_events = sync_ledger_to_db(active)
    if new_events > 0:
        console.print(f"  • [green]Imported {new_events} new contemporaneous event(s) into database.[/green]")
    else:
        console.print("  • [dim]Timeline events are up to date.[/dim]")
        
    # 3. Check for new raw documents needing ingestion
    raw_dir = case_dir / "01_raw"
    text_dir = case_dir / "02_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    existing_texts = {p.stem.lower() for p in text_dir.glob("*.md")}
    raw_files = [p for p in raw_dir.iterdir() if p.is_file() and not p.name.startswith(".")]
    unindexed = [p for p in raw_files if p.stem.lower() not in existing_texts]
    
    if unindexed:
        console.print(f"  • [yellow]Found {len(unindexed)} new raw document(s) uploaded by client. Running ingestion...[/yellow]")
        ingest_source(str(raw_dir), active)
    else:
        console.print("  • [dim]All documents in 01_raw/ are fully indexed.[/dim]")
        
    console.print(f"[bold green]✓ Client case '{active}' is fully synchronized![/bold green]\n")

