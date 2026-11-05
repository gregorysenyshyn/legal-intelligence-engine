"""
Ontario Family Law Practice Assistant - Master CLI Interface.
Dispatches subcommands for multi-client case management, document ingestion,
FTS5 evidence search, CSG support calculations, CanLII legal research,
timeline management, and PII anonymization.
"""

import sys
import os
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from db.case_db import (
    get_active_case_name, set_active_case, list_cases,
    create_case, search_case_documents, get_page_content,
    show_case_core, show_case_map
)
from ingest.ingest_pipeline import ingest_file, ingest_directory
import tools.csg_calculator as csg
import tools.canlii_precedents as canlii
import tools.timeline as timeline
import tools.holiday_solver as holiday_solver
import tools.lmstudio_client as lmstudio
import privacy.scrubber as scrubber
from tools.sync_manager import add_client_submodule, sync_case

def cmd_cases(args):
    cases = list_cases()
    active = get_active_case_name()
    if not cases:
        console.print("[yellow]No client cases found in cases/ directory.[/yellow]")
        console.print("Run: [cyan]./firm new <case_name>[/cyan] to create your first client case.")
        return
        
    t = Table(title="Client Cases", show_header=True)
    t.add_column("Active", justify="center", width=8)
    t.add_column("Case Name", style="bold")
    t.add_column("Directory", style="dim")
    
    for c in cases:
        is_active = "✓" if c == active else ""
        style = "green" if c == active else "white"
        t.add_row(f"[{style}]{is_active}[/{style}]", f"[{style}]{c}[/{style}]", f"cases/{c}")
    console.print(t)

def cmd_use(args):
    if set_active_case(args.case_name):
        console.print(f"[bold green]Active case set to:[/bold green] [cyan]{args.case_name}[/cyan]")

def cmd_new(args):
    case_dir = create_case(args.case_name, args.file_no, args.applicant, args.respondent, args.child)
    console.print(f"[bold green]✓ Created new client case:[/bold green] [cyan]{args.case_name}[/cyan]")
    console.print(f"  • Folder:  [dim]{case_dir}[/dim]")
    console.print(f"  • PII Map: [green]Seeded in privacy_map.json (auto-scrubs before LLM prompt)[/green]")
    console.print(f"\nPlace client PDFs into [cyan]{case_dir}/01_raw/[/cyan] and run [cyan]./firm ingest[/cyan].")

def cmd_ingest(args):
    active = get_active_case_name()
    if not active:
        console.print("[red]Error: No active case selected. Run './firm use <case>' first.[/red]")
        return
        
    target_path = Path(args.path) if args.path else (ROOT_DIR / "cases" / active / "01_raw")
    if target_path.is_file():
        ingest_file(target_path, active)
    elif target_path.is_dir():
        ingest_directory(target_path, active)
    else:
        console.print(f"[red]Path not found:[/red] {target_path}")

def cmd_search(args):
    active = get_active_case_name()
    if not active:
        console.print("[red]Error: No active case selected.[/red]")
        return
    results = search_case_documents(args.query, args.limit, active)
    if not results:
        console.print(f"[yellow]No records found matching '{args.query}' in case '{active}'.[/yellow]")
        return
        
    t = Table(title=f"Search Results in '{active}' for: '{args.query}' ({len(results)} matches)", show_header=True)
    t.add_column("Document", style="bold cyan", width=32)
    t.add_column("Page", justify="center", width=8)
    t.add_column("Extract / Context", style="white")
    
    for r in results:
        t.add_row(r["filename"], str(r["page_number"]), r["preview"])
    console.print(t)

def cmd_page(args):
    active = get_active_case_name()
    if not active:
        console.print("[red]Error: No active case selected.[/red]")
        return
    text = get_page_content(args.document, args.page, args.end_page, active)
    console.print(f"\n[bold blue]=== {args.document} (Page {args.page}) ===[/bold blue]\n")
    print(text)
    console.print(f"\n[bold blue]=== End Page {args.page} ===[/bold blue]\n")

def main():
    parser = argparse.ArgumentParser(description="Ontario Family Law Practice Assistant (Firm CLI)")
    subparsers = parser.add_subparsers(dest="subcommand")
    
    # cases
    subparsers.add_parser("cases", help="List all client cases")

    # core
    subparsers.add_parser("core", help="Print executive CASE_CORE.md bedrock & sync check (<1,000 tokens)")

    # map
    p_map = subparsers.add_parser("map", help="Print token-efficient coupled-graph map & sync drift check")
    p_map.add_argument("--headings", action="store_true", help="Include H2 section headings for memos and briefs")
    
    # use
    p_use = subparsers.add_parser("use", help="Select active client case")
    p_use.add_argument("case_name", help="Case name")
    
    # new
    p_new = subparsers.add_parser("new", help="Create new local client case")
    p_new.add_argument("case_name", help="Case identifier (e.g. smith_v_jones)")
    p_new.add_argument("--file-no", default="", help="Court file number")
    p_new.add_argument("--applicant", default="", help="Applicant name")
    p_new.add_argument("--respondent", default="", help="Respondent name")
    p_new.add_argument("--child", default="", help="Child name")

    # add-client (submodule)
    p_add_client = subparsers.add_parser("add-client", help="Link remote client GitHub repo as a submodule")
    p_add_client.add_argument("case_name", help="Case identifier (folder name in cases/)")
    p_add_client.add_argument("repo_url", help="Git clone URL (e.g. git@github.com:firm/case-smith.git)")

    # sync
    p_sync = subparsers.add_parser("sync", help="Pull client updates from GitHub, sync timeline, and auto-ingest new files")
    p_sync.add_argument("case_name", nargs="?", default="", help="Case name (defaults to active case)")
    
    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest and OCR documents into active case")
    p_ingest.add_argument("path", nargs="?", default="", help="File or folder path (defaults to 01_raw/)")
    
    # search
    p_search = subparsers.add_parser("search", help="FTS5 search across active case documents")
    p_search.add_argument("query", help="Search keyword(s)")
    p_search.add_argument("--limit", type=int, default=10, help="Maximum results (default: 10)")
    
    # page
    p_page = subparsers.add_parser("page", help="Extract specific page from a document")
    p_page.add_argument("document", help="Document filename (or keyword match)")
    p_page.add_argument("page", type=int, help="Page number")
    p_page.add_argument("--end-page", type=int, default=None, help="Optional ending page")

    # ask (Air-Gapped Local LM Studio Q&A)
    p_ask = subparsers.add_parser("ask", help="Air-gapped offline local Q&A via LM Studio (localhost:1234)")
    p_ask.add_argument("question", help="Plain-English question to answer from local SQLite FTS5 index")
    
    # calc
    p_calc = subparsers.add_parser("calc", help="Ontario Child Support Guidelines (CSG) calculator")
    p_calc.add_argument("--party-a", default="Party A", help="Name of Party A")
    p_calc.add_argument("--income-a", type=float, required=True, help="Party A Line 15000 Guideline Income")
    p_calc.add_argument("--party-b", default="Party B", help="Name of Party B")
    p_calc.add_argument("--income-b", type=float, required=True, help="Party B Line 15000 Guideline Income")
    p_calc.add_argument("--children", type=int, default=1, help="Number of children")
    p_calc.add_argument("--parenting", choices=["shared", "sole_a", "sole_b"], default="shared", help="Parenting regime")
    p_calc.add_argument("--s7", type=float, default=0.0, help="Annual total S.7 special expenses")
    p_calc.add_argument("--months-unpaid", type=int, default=0, help="Months of retroactive adjustment")
    p_calc.add_argument("--prior-rate", type=float, default=0.0, help="Prior monthly support rate")
    p_calc.add_argument("--costs", type=float, default=0.0, help="Rule 24 costs award")
    
    # canlii
    p_canlii = subparsers.add_parser("canlii", help="Ontario family law case precedents")
    p_canlii.add_argument("query", nargs="?", default="", help="Legal topic or case name")
    p_canlii.add_argument("--brief", action="store_true", help="Format for court brief / factum")

    # twin (CanLII Fact-Twin Search)
    p_twin = subparsers.add_parser("twin", help="Find CanLII 'Fact-Twin' precedents matching the active case's fact pattern")
    p_twin.add_argument("facts", nargs="?", default="", help="Optional custom fact pattern (defaults to active CASE_CORE.md)")
    p_twin.add_argument("--brief", action="store_true", help="Output side-by-side Fact-Twin Markdown table for Court Brief")

    # holidays
    p_holidays = subparsers.add_parser("holidays", help="Audit & solve court-compliant holiday parenting schedules")
    p_holidays.add_argument("--year", type=int, default=2026, help="Holiday year (default: 2026)")
    p_holidays.add_argument("--party-a", default="Applicant", help="Party A name")
    p_holidays.add_argument("--party-b", default="Respondent", help="Party B name")
    p_holidays.add_argument("--max-nights", type=int, default=2, help="Consecutive overnight cap (default: 2)")
    p_holidays.add_argument("--break", dest="break_type", default="christmas", choices=["christmas", "march_break", "summer"], help="Holiday type")

    # events / log / chronology
    p_log = subparsers.add_parser("log", help="Log a contemporaneous event")
    p_log.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    p_log.add_argument("--time", default="", help="Time (e.g. 5:00 PM)")
    p_log.add_argument("--title", required=True, help="Title")
    p_log.add_argument("--desc", required=True, help="Description")
    p_log.add_argument("--category", default="General", help="Category")
    p_log.add_argument("--location", default="", help="Location/platform")
    p_log.add_argument("--parties", default="", help="Parties present")
    p_log.add_argument("--child-impact", default="", help="Child presentation")
    p_log.add_argument("--counsel-notes", default="", help="Counsel notes")
    p_log.add_argument("--citation", default="", help="Citation/exhibit")
    p_log.add_argument("--page", type=int, default=None, help="Page number")
    
    p_events = subparsers.add_parser("events", help="List or search events in active case")
    p_events.add_argument("--search", default="", help="Search query")
    p_events.add_argument("--category", default="", help="Category filter")
    p_events.add_argument("--from-date", default="", help="Start date (YYYY-MM-DD)")
    p_events.add_argument("--to-date", default="", help="End date (YYYY-MM-DD)")
    p_events.add_argument("--detail", action="store_true", help="Show full details")

    p_chron = subparsers.add_parser("chronology", help="Export Master Chronology for Court Brief")
    p_chron.add_argument("--out", required=True, help="Output markdown path")
    p_chron.add_argument("--category", default="", help="Category filter")
    p_chron.add_argument("--from-date", default="", help="Start date (YYYY-MM-DD)")
    p_chron.add_argument("--to-date", default="", help="End date (YYYY-MM-DD)")

    # scrubber
    p_scrub = subparsers.add_parser("scrub", help="PII scrubber & chunked pre-scanner for LSO Rule 3.3-1")
    p_scrub.add_argument("action", choices=["scan", "mask", "unmask", "add", "list"], help="Scrubber action")
    p_scrub.add_argument("arg1", nargs="?", default="", help="Input text / file or original string")
    p_scrub.add_argument("arg2", nargs="?", default="", help="Output path or token string")

    args = parser.parse_args()
    
    if args.subcommand == "cases":
        cmd_cases(args)
    elif args.subcommand == "core":
        show_case_core()
    elif args.subcommand == "map":
        show_case_map(args.headings)
    elif args.subcommand == "use":
        cmd_use(args)
    elif args.subcommand == "new":
        cmd_new(args)
    elif args.subcommand == "add-client":
        add_client_submodule(args.case_name, args.repo_url)
    elif args.subcommand == "sync":
        sync_case(args.case_name or None)
    elif args.subcommand == "ingest":
        cmd_ingest(args)
    elif args.subcommand == "search":
        cmd_search(args)
    elif args.subcommand == "page":
        cmd_page(args)
    elif args.subcommand == "ask":
        lmstudio.ask_local_case_assistant(args.question)
    elif args.subcommand == "calc":
        res = csg.calculate_support(
            args.party_a, args.income_a,
            args.party_b, args.income_b,
            args.children, args.parenting,
            args.s7
        )
        csg.print_support_report(res, args.months_unpaid, args.prior_rate, args.costs)
    elif args.subcommand == "canlii":
        canlii.display_precedents(args.query, args.brief)
    elif args.subcommand == "twin":
        canlii.run_fact_twin_search(args.facts, args.brief)
    elif args.subcommand == "holidays":
        res = holiday_solver.solve_christmas_schedule(
            args.year, args.party_a, args.party_b, args.max_nights
        )
        holiday_solver.print_holiday_audit(res)
    elif args.subcommand == "log":
        eid = timeline.log_event(
            args.date, args.title, args.desc, args.category,
            args.time, args.location, args.parties,
            args.child_impact, args.counsel_notes,
            args.citation, args.page
        )
        console.print(f"[bold green]✓ Event #{eid} successfully logged to active case.[/bold green]")
    elif args.subcommand == "events":
        events = timeline.search_events(args.search, args.category, args.from_date, args.to_date)
        timeline.display_events(events, args.detail)
    elif args.subcommand == "chronology":
        timeline.export_chronology(args.out, args.from_date, args.to_date, args.category)
    elif args.subcommand == "scrub":
        s = scrubber.PrivacyScrubber()
        if args.action == "list":
            console.print(f"[bold cyan]Active Privacy Tokens for: {s.case_name or 'None'} ({len(s.mapping)} entities masked)[/bold cyan]")
            for tok in sorted(set(s.mapping.values())):
                console.print(f"  • [green]{tok}[/green]")
        elif args.action == "scan":
            target_path = Path(args.arg1) if args.arg1 else (ROOT_DIR / "cases" / (s.case_name or "") / "01_raw")
            targets = [target_path] if target_path.is_file() else sorted(target_path.glob("*.*"))
            for t_file in targets:
                content = t_file.read_text(encoding="utf-8", errors="ignore")
                flags = s.pre_scan_chunks(content, auto_register=True)
                scrubber.print_scan_report(t_file, flags, show_raw_candidates=False)
        elif args.action == "add":
            s.add_entity(args.arg1, args.arg2)
            console.print(f"[green]✓ Entity mapped:[/green] '{args.arg1}' -> '{args.arg2}'")
        elif args.action == "mask":
            in_path = Path(args.arg1)
            content = in_path.read_text(encoding="utf-8") if in_path.is_file() else args.arg1
            res = s.mask_text(content)
            if args.arg2:
                Path(args.arg2).write_text(res, encoding="utf-8")
                console.print(f"[green]✓ Masked output written to:[/green] {args.arg2}")
            else:
                print(res)
        elif args.action == "unmask":
            in_path = Path(args.arg1)
            content = in_path.read_text(encoding="utf-8") if in_path.is_file() else args.arg1
            res = s.unmask_text(content)
            if args.arg2:
                Path(args.arg2).write_text(res, encoding="utf-8")
                console.print(f"[green]✓ Unmasked output written to:[/green] {args.arg2}")
            else:
                print(res)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

