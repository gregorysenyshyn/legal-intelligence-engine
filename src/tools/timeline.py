"""
Contemporaneous Case Timeline & Master Chronology Engine for Ontario Law Practices.
Records, searches, and exports court-admissible chronologies for Form 17C Settlement Conference Briefs,
Form 14 Motion Records, and Trial Briefs.
Operates on the currently active case database and maintains a local append-only JSONL ledger.
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.markup import escape

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from db.case_db import get_active_case_name, get_case_connection, CASES_DIR

def get_ledger_path(case_name: Optional[str] = None) -> Path:
    active = case_name or get_active_case_name()
    if not active:
        raise ValueError("No active case selected.")
    events_dir = CASES_DIR / active / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    return events_dir / "timeline.jsonl"

def log_event(
    event_date: str,
    title: str,
    description: str,
    category: str = "General",
    event_time: str = "",
    location: str = "",
    key_parties: str = "",
    child_impact: str = "",
    counsel_notes: str = "",
    source_citation: str = "",
    page_number: Optional[int] = None,
    case_name: Optional[str] = None
) -> int:
    """Inserts a contemporaneous event into SQLite and appends to the client's timeline.jsonl ledger."""
    conn = get_case_connection(case_name)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO timeline_events (
            event_date, event_time, title, location, key_parties,
            category, description, child_impact, counsel_notes,
            source_citation, page_number
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_date, event_time, title, location, key_parties,
        category, description, child_impact, counsel_notes,
        source_citation, page_number
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    # Append to ledger
    ledger_entry = {
        "id": new_id,
        "event_date": event_date,
        "event_time": event_time,
        "title": title,
        "location": location,
        "key_parties": key_parties,
        "category": category,
        "description": description,
        "child_impact": child_impact,
        "counsel_notes": counsel_notes,
        "source_citation": source_citation,
        "page_number": page_number,
        "recorded_at": datetime.now().isoformat()
    }
    ledger_file = get_ledger_path(case_name)
    with open(ledger_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")
        
    return new_id

def search_events(
    query: str = "",
    category: str = "",
    from_date: str = "",
    to_date: str = "",
    case_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Searches events using FTS5 or date/category filters."""
    conn = get_case_connection(case_name)
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if from_date:
        conditions.append("event_date >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("event_date <= ?")
        params.append(to_date)
    if category:
        conditions.append("category LIKE ?")
        params.append(f"%{category}%")
        
    if query:
        # FTS5 search
        sql = """
            SELECT e.*
            FROM timeline_events e
            JOIN timeline_events_fts fts ON e.id = fts.rowid
            WHERE timeline_events_fts MATCH ?
        """
        params.insert(0, query)
        if conditions:
            sql += " AND " + " AND ".join(conditions)
        sql += " ORDER BY event_date ASC, event_time ASC"
    else:
        sql = "SELECT * FROM timeline_events"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY event_date ASC, event_time ASC"
        
    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def export_chronology(
    output_path: Optional[str] = None,
    from_date: str = "",
    to_date: str = "",
    category: str = "",
    case_name: Optional[str] = None
) -> str:
    """Exports a formatted markdown chronology suitable for a Court Brief exhibit."""
    active = case_name or get_active_case_name()
    events = search_events("", category, from_date, to_date, active)
    
    if not events:
        return "No events found matching the criteria."
        
    md = [
        f"# Master Chronological Timeline: {active.replace('_', ' ').title()}",
        f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} for Ontario Family Court Brief*\n",
        "| Date / Time | Category | Factual Narrative | Child Impact / Demeanour | Supporting Source / Exhibit |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for e in events:
        dt = e['event_date']
        if e.get('event_time'):
            dt += f"<br>*{e['event_time']}*"
            
        desc = e['description'].replace("\n", " ")
        child = (e.get('child_impact') or 'N/A').replace("\n", " ")
        
        cite = e.get('source_citation') or 'Contemporaneous notes'
        if e.get('page_number'):
            cite += f" (Page {e['page_number']})"
            
        md.append(f"| **{dt}** | `{e['category']}` | **{e['title']}**<br>{desc} | {child} | *{cite}* |")
        
    content = "\n".join(md)
    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        console.print(f"[green]✓ Chronology exported to:[/green] [cyan]{output_path}[/cyan]")
        
    return content

def display_events(events: List[Dict[str, Any]], detail: bool = False):
    """Prints events in a formatted rich table."""
    if not events:
        console.print("[yellow]No timeline events found.[/yellow]")
        return
        
    t = Table(title=f"Active Case Timeline ({len(events)} Events)", show_header=True)
    t.add_column("ID", style="dim", width=4)
    t.add_column("Date/Time", style="cyan", width=14)
    t.add_column("Category", style="yellow", width=16)
    t.add_column("Title & Summary", style="white")
    t.add_column("Citation / Page", style="green", width=18)
    
    for e in events:
        dt = e['event_date']
        if e.get('event_time'):
            dt += f"\n{e['event_time']}"
        cite = e.get('source_citation') or ''
        if e.get('page_number'):
            cite += f" (p. {e['page_number']})"
            
        desc = e['description'][:120] + ("..." if len(e['description']) > 120 else "")
        summary = f"[bold]{escape(e['title'])}[/bold]\n{escape(desc)}"
        if detail and e.get('child_impact'):
            summary += f"\n[dim]Child: {escape(e['child_impact'])}[/dim]"
        if detail and e.get('counsel_notes'):
            summary += f"\n[dim][italic]Counsel: {escape(e['counsel_notes'])}[/italic][/dim]"
            
        t.add_row(str(e['id']), dt, escape(e['category']), summary, escape(cite))
        
    console.print(t)

def main():
    parser = argparse.ArgumentParser(description="Ontario Family Law Case Timeline Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    # Log event
    p_log = subparsers.add_parser("log", help="Record a contemporaneous event")
    p_log.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    p_log.add_argument("--time", default="", help="Time (e.g. 5:00 PM)")
    p_log.add_argument("--title", required=True, help="Short descriptive title")
    p_log.add_argument("--desc", required=True, help="Objective factual description")
    p_log.add_argument("--category", default="General", help="Event category")
    p_log.add_argument("--location", default="", help="Location or medium (Email, OFW, School)")
    p_log.add_argument("--parties", default="", help="Individuals present")
    p_log.add_argument("--child-impact", default="", help="Child demeanour and presentation")
    p_log.add_argument("--counsel-notes", default="", help="Counsel tactical notes")
    p_log.add_argument("--citation", default="", help="Document citation or exhibit")
    p_log.add_argument("--page", type=int, default=None, help="Document page number")

    # List / search
    p_list = subparsers.add_parser("list", help="List or search events")
    p_list.add_argument("--search", default="", help="Full-text search keywords")
    p_list.add_argument("--category", default="", help="Filter by category")
    p_list.add_argument("--from-date", default="", help="Start date (YYYY-MM-DD)")
    p_list.add_argument("--to-date", default="", help="End date (YYYY-MM-DD)")
    p_list.add_argument("--detail", action="store_true", help="Show extended details")

    # Export
    p_export = subparsers.add_parser("export", help="Export chronology to Markdown")
    p_export.add_argument("--out", required=True, help="Output file path (e.g. chronology.md)")
    p_export.add_argument("--category", default="", help="Filter by category")
    p_export.add_argument("--from-date", default="", help="Start date (YYYY-MM-DD)")
    p_export.add_argument("--to-date", default="", help="End date (YYYY-MM-DD)")

    args = parser.parse_args()
    
    if args.command == "log":
        eid = log_event(
            args.date, args.title, args.desc, args.category,
            args.time, args.location, args.parties,
            args.child_impact, args.counsel_notes,
            args.citation, args.page
        )
        console.print(f"[bold green]✓ Event #{eid} successfully logged to active case.[/bold green]")
    elif args.command == "list" or not args.command:
        events = search_events(
            getattr(args, "search", ""),
            getattr(args, "category", ""),
            getattr(args, "from_date", ""),
            getattr(args, "to_date", "")
        )
        display_events(events, getattr(args, "detail", False))
    elif args.command == "export":
        export_chronology(args.out, args.from_date, args.to_date, args.category)

if __name__ == "__main__":
    main()
