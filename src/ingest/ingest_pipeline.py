"""
Turnkey Document Ingestion & Native macOS OCR Pipeline for Ontario Law Practices.
Ingests PDFs, Word documents, and scanned disclosure files, applies page-by-page markers (## Page X),
and indexes them directly into the client's local SQLite FTS5 database.
"""

import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

import pypdf
import pdfplumber

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
SWIFT_OCR_BIN = SCRIPT_DIR / "ocr_mac"
SWIFT_OCR_SRC = SCRIPT_DIR / "ocr_mac.swift"

def ensure_ocr_binary():
    """Compiles the native macOS Vision Swift OCR script if needed."""
    if not SWIFT_OCR_BIN.exists() and SWIFT_OCR_SRC.exists():
        console.print("[dim]Compiling native macOS Vision OCR binary...[/dim]")
        cmd = ["swiftc", "-O", str(SWIFT_OCR_SRC), "-o", str(SWIFT_OCR_BIN)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            console.print(f"[yellow]Warning: Could not compile Swift OCR: {res.stderr}[/yellow]")

def run_native_mac_ocr(pdf_path: Path) -> Tuple[str, int, int]:
    """Runs native macOS Vision OCR on a scanned PDF."""
    ensure_ocr_binary()
    if not SWIFT_OCR_BIN.exists():
        return "", 0, 0
        
    cmd = [str(SWIFT_OCR_BIN), str(pdf_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return "", 0, 0
        
    raw_ocr = res.stdout
    # Process output into page-stamped markdown
    pages = raw_ocr.split("--- PAGE ")
    pages_text = []
    total_chars = 0
    p_count = 0
    for chunk in pages:
        if not chunk.strip():
            continue
        p_count += 1
        lines = chunk.strip().split("\n", 1)
        page_num = p_count
        body = lines[1] if len(lines) > 1 else lines[0]
        total_chars += len(body)
        pages_text.append(f"<!-- Page {page_num} -->\n## Page {page_num}\n\n{body}\n")
        
    return "\n".join(pages_text), p_count, total_chars

def extract_pdf(pdf_path: Path) -> Tuple[str, int, int, bool]:
    """Extracts digital text and tables from PDF; detects if OCR is needed."""
    pages_text = []
    total_chars = 0
    scanned_pages = 0
    page_count = 1

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for idx, page in enumerate(pdf.pages, 1):
                text = (page.extract_text() or "").strip()
                tables = page.extract_tables()
                
                table_md = ""
                if tables:
                    for table in tables:
                        clean_rows = [[cell or "" for cell in row] for row in table if any(row)]
                        if clean_rows and len(clean_rows) > 1:
                            header = clean_rows[0]
                            table_md += "\n\n| " + " | ".join(header) + " |\n"
                            table_md += "| " + " | ".join(["---"] * len(header)) + " |\n"
                            for row in clean_rows[1:]:
                                padded = row[:len(header)] + [""] * max(0, len(header) - len(row))
                                table_md += "| " + " | ".join([c.replace("\n", " ") for c in padded]) + " |\n"
                            table_md += "\n"

                clean_text = text
                if table_md:
                    clean_text += "\n" + table_md

                char_count = len(clean_text)
                total_chars += char_count

                if char_count < 40 and len(page.images) > 0:
                    scanned_pages += 1

                pages_text.append(f"<!-- Page {idx} -->\n## Page {idx}\n\n{clean_text}\n")

    except Exception:
        # Fallback to pypdf
        try:
            reader = pypdf.PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            pages_text = []
            total_chars = 0
            for idx, page in enumerate(reader.pages, 1):
                clean_text = (page.extract_text() or "").strip()
                total_chars += len(clean_text)
                pages_text.append(f"<!-- Page {idx} -->\n## Page {idx}\n\n{clean_text}\n")
        except Exception as e:
            return f"Error extracting text: {e}", 0, 0, True

    is_scanned = (scanned_pages > 0 and (total_chars / max(1, page_count)) < 150) or total_chars < 50
    return "\n".join(pages_text), page_count, total_chars, is_scanned

def infer_doc_type(filename: str) -> str:
    n = filename.lower()
    if any(k in n for k in ["affidavit", "14a", "35.1"]):
        return "Affidavit"
    if any(k in n for k in ["motion", "form 14", "15 motion"]):
        return "Motion / Pleading"
    if any(k in n for k in ["financial statement", "form 13"]):
        return "Financial Statement"
    if any(k in n for k in ["brief", "17a", "17c"]):
        return "Conference Brief"
    if any(k in n for k in ["endorsement", "order"]):
        return "Court Order"
    if any(k in n for k in ["noa", "t1", "tax", "paystub", "pay stub"]):
        return "Financial Disclosure"
    if any(k in n for k in ["email", "letter", "ltr", "ofw"]):
        return "Correspondence"
    return "Exhibit / General"

def ingest_source(source_path: str, case_name: Optional[str] = None):
    """
    Ingests files from source_path (file or directory) into the client's case directory
    and indexes them into SQLite FTS5.
    """
    try:
        from db.case_db import get_active_case_name, get_case_connection, CASES_DIR
        from privacy.scrubber import PrivacyScrubber, print_scan_report
    except ImportError:
        from ..db.case_db import get_active_case_name, get_case_connection, CASES_DIR
        from ..privacy.scrubber import PrivacyScrubber, print_scan_report
    
    active = case_name or get_active_case_name()
    if not active:
        console.print("[bold red]Error: No active case selected. Run './firm use <case_name>' first.[/bold red]")
        return
        
    src_p = Path(source_path).expanduser().resolve()
    if not src_p.exists():
        console.print(f"[bold red]Error: Source path '{source_path}' does not exist.[/bold red]")
        return
        
    case_dir = CASES_DIR / active
    raw_dir = case_dir / "01_raw"
    text_dir = case_dir / "02_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_process = []
    if src_p.is_file():
        files_to_process.append(src_p)
    else:
        for ext in ["*.pdf", "*.PDF", "*.docx", "*.DOCX", "*.txt", "*.TXT", "*.md", "*.MD", "*.png", "*.jpg"]:
            files_to_process.extend(src_p.rglob(ext))
            
    if not files_to_process:
        console.print(f"[yellow]No supported files found in '{source_path}'.[/yellow]")
        return
        
    console.print(f"[bold cyan]Found {len(files_to_process)} document(s) for client '{active}'...[/bold cyan]")
    
    conn = get_case_connection(active)
    cursor = conn.cursor()
    scrubber = PrivacyScrubber(active)
    if not scrubber.mapping:
        console.print(
            "[bold yellow]⚠ PII Notice:[/bold yellow] No custom party/child names are registered in privacy_map.json yet.\n"
            "  SINs, emails, phones, and postal codes will be scrubbed automatically, and style-of-cause headers will be auto-detected.\n"
            "  To register additional names/schools/employers, run: [cyan]./firm scrub add \"<Name>\" \"[TOKEN]\"[/cyan]\n"
        )
    
    processed_count = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Ingesting & Indexing...", total=len(files_to_process))
        
        for file in files_to_process:
            progress.update(task, description=f"[cyan]Processing {file.name[:35]}...")
            dest_raw = raw_dir / file.name
            if file != dest_raw:
                shutil.copy2(file, dest_raw)
                
            md_name = file.stem + ".md"
            dest_text = text_dir / md_name
            
            # Extract content
            doc_type = infer_doc_type(file.name)
            is_scanned = False
            page_count = 1
            
            if file.suffix.lower() == ".pdf":
                content, page_count, chars, is_scanned = extract_pdf(dest_raw)
                if is_scanned and SWIFT_OCR_SRC.exists():
                    ocr_content, ocr_p, ocr_chars = run_native_mac_ocr(dest_raw)
                    if ocr_chars > chars:
                        content = ocr_content
                        page_count = ocr_p
            else:
                try:
                    content = dest_raw.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    content = f"Binary content: {file.name}"
                    
            # Stage 1: Auto-detect style of cause & break document into small chunks for pre-ingestion PII scan
            detected_parties = scrubber.auto_detect_style_of_cause(content)
            for orig_name, tok in detected_parties.items():
                scrubber.add_entity(orig_name, tok)
            flags = scrubber.pre_scan_chunks(content, auto_register=True)
            if flags:
                print_scan_report(file, flags, show_raw_candidates=False)

            # Stage 2: Scrub all flagged PII fragments before saving to 02_text/ or indexing into SQLite FTS5
            content = scrubber.mask_text(content)

            # Write markdown file
            frontmatter = f"---\nsource_file: \"{file.name}\"\npage_count: {page_count}\nis_scanned: {str(is_scanned).lower()}\ndoc_type: \"{doc_type}\"\npii_scrubbed: true\n---\n\n"
            dest_text.write_text(frontmatter + content, encoding="utf-8")
            
            # Index into SQLite
            cursor.execute("""
                INSERT OR REPLACE INTO documents 
                (filename, title, doc_type, page_count, raw_path, text_path, is_scanned)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (file.stem, file.name, doc_type, page_count, str(dest_raw), str(dest_text), 1 if is_scanned else 0))
            
            # Index into FTS5
            cursor.execute("DELETE FROM document_fts WHERE filename = ?", (file.stem,))
            cursor.execute("INSERT INTO document_fts (filename, content) VALUES (?, ?)", (file.stem, content))
            
            processed_count += 1
            progress.advance(task)
            
    conn.commit()
    conn.close()
    console.print(f"[bold green]✓ Successfully ingested and indexed {processed_count} document(s) for client '{active}'![/bold green]")

def ingest_file(file_path: Path, case_name: Optional[str] = None):
    return ingest_source(str(file_path), case_name)

def ingest_directory(dir_path: Path, case_name: Optional[str] = None):
    return ingest_source(str(dir_path), case_name)
