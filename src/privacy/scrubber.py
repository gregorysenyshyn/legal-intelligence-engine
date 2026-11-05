"""
Local PII Scrubber, Chunked Pre-Scanner & Reversible Anonymizer for LSO Rule 3.3-1 Compliance.
Breaks documents into small fragments during pre-ingestion, scans each fragment for
potential PII (names, third parties, employers, schools, street addresses, SINs, phones,
emails, postal codes), flags only short 40-char fragments, and replaces sensitive entities
with reversible tokens BEFORE any text is indexed or sent to an LLM prompt.
"""

import re
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.table import Table

console = Console()

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent
sys_path = str(SCRIPT_DIR.parent)
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)

CASES_DIR = ROOT_DIR / "cases"
ACTIVE_CASE_FILE = ROOT_DIR / ".active_case"

# Common legal/structural words to ignore when scanning for proper-noun entities
LEGAL_STOPWORDS = {
    "ONTARIO", "COURT", "JUSTICE", "SUPERIOR", "FAMILY", "BETWEEN", "APPLICANT",
    "RESPONDENT", "FORM", "FINANCIAL", "STATEMENT", "SUPPORT", "CLAIMS", "PART",
    "ANNUAL", "INCOME", "EXPENSES", "TOTAL", "LINE", "NOTICE", "ASSESSMENT",
    "CANADA", "REVENUE", "AGENCY", "ENDORSEMENT", "INTERIM", "ORDER", "FINAL",
    "SCHEDULE", "EXHIBIT", "AFFIDAVIT", "MOTION", "BRIEF", "CONFERENCE", "PAGE",
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY",
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
    "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER", "FATHER", "MOTHER", "CHILD",
}


def _resolve_active_case(case_name: Optional[str] = None) -> Optional[str]:
    if case_name:
        return case_name
    if ACTIVE_CASE_FILE.exists():
        name = ACTIVE_CASE_FILE.read_text(encoding="utf-8").strip()
        if name and (CASES_DIR / name).is_dir():
            return name
    if CASES_DIR.exists():
        cases = [d.name for d in sorted(CASES_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".")]
        if cases:
            return cases[0]
    return None


def get_mapping_path(case_name: Optional[str] = None) -> Path:
    active = _resolve_active_case(case_name)
    if not active:
        raise ValueError("No active case selected.")
    case_dir = CASES_DIR / active
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir / "privacy_map.json"


def load_mapping(case_name: Optional[str] = None) -> Dict[str, str]:
    path = get_mapping_path(case_name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_mapping(mapping: Dict[str, str], case_name: Optional[str] = None):
    path = get_mapping_path(case_name)
    path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


class PrivacyScrubber:
    def __init__(self, case_name: Optional[str] = None):
        self.case_name = _resolve_active_case(case_name)
        self.mapping = load_mapping(self.case_name) if self.case_name else {}
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}

    def add_entity(self, original_text: str, token: str):
        """Registers a known sensitive entity (party name, child name, employer, school) for replacement."""
        if not original_text or not token:
            return
        self.mapping[original_text] = token
        self.reverse_mapping[token] = original_text
        if self.case_name:
            save_mapping(self.mapping, self.case_name)

    def _next_token(self, prefix: str) -> str:
        idx = len([v for v in set(self.mapping.values()) if v.startswith(f"[{prefix}_")]) + 1
        return f"[{prefix}_{idx}]"

    def seed_case_parties(self, applicant: str = "", respondent: str = "", child: str = ""):
        """Automatically seeds full names and first/last names into privacy_map.json on case creation."""
        if applicant:
            self.add_entity(applicant.strip(), "[CLIENT_APPLICANT]")
            parts = [p for p in applicant.strip().split() if len(p) >= 3]
            if len(parts) >= 2:
                self.add_entity(parts[0], "[APPLICANT_FIRST]")
                self.add_entity(parts[-1], "[APPLICANT_LAST]")
        if respondent:
            self.add_entity(respondent.strip(), "[RESPONDENT_PARTY]")
            parts = [p for p in respondent.strip().split() if len(p) >= 3]
            if len(parts) >= 2:
                self.add_entity(parts[0], "[RESPONDENT_FIRST]")
                self.add_entity(parts[-1], "[RESPONDENT_LAST]")
        if child:
            self.add_entity(child.strip(), "[CHILD_1]")
            parts = [p for p in child.strip().split() if len(p) >= 3]
            if parts:
                self.add_entity(parts[0], "[CHILD_1_FIRST]")

    def auto_detect_style_of_cause(self, text: str) -> Dict[str, str]:
        """Scans court document headers (BETWEEN: ... Applicant and ... Respondent) for unmapped party names."""
        detected = {}
        if not text:
            return detected
        header = text[:1500]
        app_match = re.search(r'BETWEEN:\s*\n+\s*([A-Z][A-Za-z ,.\'-]{3,40})\s*\n+\s*Applicant', header, re.IGNORECASE)
        resp_match = re.search(r'(?:AND|-\s*and\s*-)\s*:?\s*\n+\s*([A-Z][A-Za-z ,.\'-]{3,40})\s*\n+\s*Respondent', header, re.IGNORECASE)
        if app_match:
            name = app_match.group(1).strip()
            if not name.startswith("[") and name not in self.mapping:
                detected[name] = "[CLIENT_APPLICANT]"
        if resp_match:
            name = resp_match.group(1).strip()
            if not name.startswith("[") and name not in self.mapping:
                detected[name] = "[RESPONDENT_PARTY]"
        return detected

    def pre_scan_chunks(self, text: str, auto_register: bool = False, use_llm: bool = True) -> List[Dict[str, Any]]:
        """
        Splits a document into small page/paragraph chunks and scans each chunk offline
        for potential unmapped PII (employers, schools, daycares, street addresses,
        titled third parties, SINs, phones, emails).
        If LM Studio is running locally at http://localhost:1234/v1 (and use_llm=True),
        also runs contextual local LLM NER on each chunk to catch first names, nicknames,
        and informal workplaces that regexes miss.
        Returns only a tiny 40-char redacted context fragment per flag so a full page
        never needs to be exposed during pre-ingestion review.
        """
        flags: List[Dict[str, Any]] = []
        if not text:
            return flags

        llm_active = False
        extract_llm_fn = None
        if use_llm:
            try:
                from tools.lmstudio_client import get_active_model, extract_contextual_pii_with_llm
                if get_active_model() is not None:
                    llm_active = True
                    extract_llm_fn = extract_contextual_pii_with_llm
            except Exception:
                llm_active = False

        # Split by page first
        page_blocks = re.split(r'(?=##\s*Page\s*\d+)', text)
        current_page = 1

        candidate_patterns = [
            ("EMPLOYER/ORG", "ORG", re.compile(
                r'\b([A-Z][A-Za-z0-9&\'-]+(?:\s+[A-Z][A-Za-z0-9&\'-]+){0,3}\s+(?:Inc\.?|Ltd\.?|Corp\.?|LLP|School|Daycare|Preschool|Hospital|Clinic|Centre|Center|Library))\b'
            )),
            ("STREET_ADDRESS", "ADDRESS", re.compile(
                r'\b(\d{1,5}\s+[A-Z][A-Za-z0-9.\'-]+(?:\s+[A-Z][A-Za-z0-9.\'-]+)?\s+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|Boulevard|Blvd\.?|Court|Ct\.?|Lane|Ln\.?|Way))\b'
            )),
            ("TITLED_PERSON", "PERSON", re.compile(
                r'\b((?:Dr\.|Mr\.|Mrs\.|Ms\.|Officer|Constable|Teacher)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
            )),
            ("LABELED_NAME", "PARTY", re.compile(
                r'(?:Applicant|Respondent|Sworn by(?:\s+Respondent|\s+Applicant)?)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
            )),
            ("SIN", "SIN", re.compile(r'\b(\d{3}[ -]\d{3}[ -]\d{3})\b')),
            ("EMAIL", "EMAIL", re.compile(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7})\b')),
            ("PHONE", "PHONE", re.compile(r'(\(?\b\d{3}\)?[-. ]?\d{3}[-. ]\d{4}\b)')),
            ("POSTAL_CODE", "POSTAL", re.compile(r'\b([A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d)\b')),
        ]

        seen_candidates = set()

        for p_block in page_blocks:
            p_match = re.search(r'##\s*Page\s*(\d+)', p_block)
            if p_match:
                current_page = int(p_match.group(1))

            # Break page into small paragraph/line chunks (max ~220 chars each)
            raw_Paras = [p.strip() for p in re.split(r'\n\s*\n|\n', p_block) if p.strip() and not p.strip().startswith(("## Page", "<!-- Page"))]
            for chunk_idx, chunk in enumerate(raw_Paras, 1):
                for category, prefix, pat in candidate_patterns:
                    for m in pat.finditer(chunk):
                        val = m.group(1).strip()
                        if val.startswith("[") or len(val) < 4:
                            continue
                        upper_words = {w.upper().strip(".,:") for w in val.split()}
                        if upper_words.issubset(LEGAL_STOPWORDS):
                            continue

                        already_mapped = val in self.mapping
                        token = self.mapping.get(val)
                        if not already_mapped:
                            if auto_register:
                                token = self._next_token(prefix)
                                self.add_entity(val, token)
                            else:
                                token = f"[? {prefix} ?]"

                        # Build a tiny 40-char isolated fragment around the match
                        start = max(0, m.start(1) - 18)
                        end = min(len(chunk), m.end(1) + 18)
                        prefix_ellipsis = "..." if start > 0 else ""
                        suffix_ellipsis = "..." if end < len(chunk) else ""
                        safe_fragment = (
                            prefix_ellipsis
                            + chunk[start:m.start(1)]
                            + f"«{token}»"
                            + chunk[m.end(1):end]
                            + suffix_ellipsis
                        ).replace("\n", " ")

                        key = (current_page, val)
                        if key not in seen_candidates:
                            seen_candidates.add(key)
                            flags.append({
                                "page": current_page,
                                "chunk": chunk_idx,
                                "category": category,
                                "candidate": val,
                                "token": token,
                                "status": "MAPPED" if (already_mapped or auto_register) else "UNMAPPED_FLAG",
                                "fragment": safe_fragment,
                            })

                # Stage 1B: Contextual Local LLM Chunk Scan via LM Studio (if active)
                if llm_active and extract_llm_fn:
                    for item in extract_llm_fn(chunk):
                        val = item["text"]
                        prefix = item["type"]
                        upper_words = {w.upper().strip(".,:") for w in val.split()}
                        if upper_words.issubset(LEGAL_STOPWORDS):
                            continue
                        pos = chunk.find(val)
                        if pos == -1:
                            continue
                        already_mapped = val in self.mapping
                        token = self.mapping.get(val)
                        if not already_mapped:
                            if auto_register:
                                token = self._next_token(prefix)
                                self.add_entity(val, token)
                            else:
                                token = f"[? {prefix} ?]"
                        start = max(0, pos - 18)
                        end = min(len(chunk), pos + len(val) + 18)
                        safe_fragment = (
                            ("..." if start > 0 else "")
                            + chunk[start:pos]
                            + f"«{token}»"
                            + chunk[pos + len(val):end]
                            + ("..." if end < len(chunk) else "")
                        ).replace("\n", " ")
                        key = (current_page, val)
                        if key not in seen_candidates:
                            seen_candidates.add(key)
                            flags.append({
                                "page": current_page,
                                "chunk": chunk_idx,
                                "category": f"LLM_{prefix}",
                                "candidate": val,
                                "token": token,
                                "status": "MAPPED" if (already_mapped or auto_register) else "UNMAPPED_FLAG",
                                "fragment": safe_fragment,
                            })
        return flags

    def mask_text(self, text: str) -> str:
        """Applies deterministic, reversible masking to PII before text is indexed or sent to an LLM prompt."""
        if not text:
            return text

        # Run fast regex chunk pre-scanner during on-the-fly masking (LLM scan runs during 'scrub scan' and 'ingest')
        self.pre_scan_chunks(text, auto_register=True, use_llm=False)

        masked = text

        # Apply registered entities (sorted longest-first to avoid partial prefix replacement)
        sorted_entities = sorted(self.mapping.keys(), key=len, reverse=True)
        for entity in sorted_entities:
            token = self.mapping[entity]
            pattern = re.compile(r'\b' + re.escape(entity) + r'\b', re.IGNORECASE)
            masked = pattern.sub(token, masked)

        return masked

    def unmask_text(self, text: str) -> str:
        """Restores original identities from anonymized tokens for final offline court filing."""
        if not text:
            return text
        unmasked = text
        sorted_tokens = sorted(self.reverse_mapping.keys(), key=len, reverse=True)
        for token in sorted_tokens:
            original = self.reverse_mapping[token]
            unmasked = unmasked.replace(token, original)
        return unmasked


def print_scan_report(file_path: Path, flags: List[Dict[str, Any]], show_raw_candidates: bool = False):
    """Displays the chunked pre-scan PII report showing only tiny isolated fragments."""
    t = Table(
        title=f"Pre-Ingest Chunked PII Scan: {file_path.name} ({len(flags)} PII Fragments Flagged)",
        show_header=True,
        header_style="bold magenta",
    )
    t.add_column("Page:Chunk", style="cyan", justify="center", width=11)
    t.add_column("PII Category", style="yellow", width=16)
    t.add_column("Token Assigned", style="bold green", width=20)
    if show_raw_candidates:
        t.add_column("Raw Value (Local Only)", style="dim", width=24)
    t.add_column("Isolated 40-Char Fragment (Safe Preview)", style="white")

    for f in flags:
        loc = f"P{f['page']}:C{f['chunk']}"
        if show_raw_candidates:
            t.add_row(loc, f["category"], f["token"], f["candidate"], f["fragment"])
        else:
            t.add_row(loc, f["category"], f["token"], f["fragment"])
    console.print(t)


def main():
    parser = argparse.ArgumentParser(description="Ontario Law Practice PII Scrubber & Chunked Pre-Scanner")
    subparsers = parser.add_subparsers(dest="command")

    p_add = subparsers.add_parser("add", help="Register a sensitive entity (Name, Address, School)")
    p_add.add_argument("original", help="Real name or sensitive string")
    p_add.add_argument("token", help="Anonymized token (e.g. [PARTY_A], [CHILD_1])")

    p_scan = subparsers.add_parser("scan", help="Pre-scan a file in small chunks and flag PII fragments before ingesting")
    p_scan.add_argument("input", help="Path to file or folder to pre-scan")
    p_scan.add_argument("--auto-map", action="store_true", help="Automatically register detected PII into privacy_map.json")

    p_mask = subparsers.add_parser("mask", help="Mask text or a file")
    p_mask.add_argument("input", help="Text string or path to file")
    p_mask.add_argument("--out", help="Optional output file path")

    p_unmask = subparsers.add_parser("unmask", help="Unmask text or a file")
    p_unmask.add_argument("input", help="Text string or path to file")
    p_unmask.add_argument("--out", help="Optional output file path")

    subparsers.add_parser("list", help="Display current active case anonymization tokens")

    args = parser.parse_args()
    scrubber = PrivacyScrubber()

    if args.command == "add":
        scrubber.add_entity(args.original, args.token)
        console.print(f"[green]✓ Entity mapped:[/green] -> '{args.token}'")
    elif args.command == "scan":
        in_path = Path(args.input)
        targets = [in_path] if in_path.is_file() else sorted(in_path.glob("*.*"))
        for target in targets:
            content = target.read_text(encoding="utf-8", errors="ignore")
            flags = scrubber.pre_scan_chunks(content, auto_register=args.auto_map)
            print_scan_report(target, flags, show_raw_candidates=False)
    elif args.command == "mask":
        content = args.input
        in_path = Path(args.input)
        if in_path.exists() and in_path.is_file():
            content = in_path.read_text(encoding="utf-8")
        res = scrubber.mask_text(content)
        if args.out:
            Path(args.out).write_text(res, encoding="utf-8")
            console.print(f"[green]✓ Masked output written to:[/green] {args.out}")
        else:
            print(res)
    elif args.command == "unmask":
        content = args.input
        in_path = Path(args.input)
        if in_path.exists() and in_path.is_file():
            content = in_path.read_text(encoding="utf-8")
        res = scrubber.unmask_text(content)
        if args.out:
            Path(args.out).write_text(res, encoding="utf-8")
            console.print(f"[green]✓ Unmasked output written to:[/green] {args.out}")
        else:
            print(res)
    else:
        console.print(f"[bold cyan]Active Privacy Tokens for: {scrubber.case_name or 'None'} ({len(scrubber.mapping)} entities masked)[/bold cyan]")
        for tok in sorted(set(scrubber.mapping.values())):
            console.print(f"  • [green]{tok}[/green]")


if __name__ == "__main__":
    main()
