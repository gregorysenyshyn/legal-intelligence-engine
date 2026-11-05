# AGENTS.md - System Instructions for Legal Intelligence Engine

This repository is a local-first AI legal intelligence, client intake buffer, and litigation strategy platform engineered for family law practitioners.

All AI agents (Codex, Google Antigravity, Claude Code, Cursor) interacting with this repository MUST follow these rules.

---

## 0. First-Time User & Non-Technical Lawyer Onboarding (CRITICAL)

Many users opening this repository are **practicing lawyers, mediators, or paralegals who do not write code**.
Whenever the user greets you, asks *"What do I do?"*, *"How does this work?"*, or *"Give me a tour"*:

1. **Silent Environment Check:**
   - Check if `.venv/bin/python` exists. If it does not exist, create it and install `requirements.txt` automatically in the background (`python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt`) without bothering the user with technical jargon.
2. **Never Tell the User to Type Terminal Commands:**
   - Run `./firm` commands yourself on the user's behalf and present the results in clean, readable legal English.
3. **Offer the 3-Part Interactive Demo Tour (Using the Pre-Loaded *Smith v. Jones* File):**
   - **Demo 1 — The Client Submodule & Emotional Buffer:** Explain (or roleplay!) how a client uses `client-case-template/` on their phone to vent after a chaotic exchange or brag about a parenting milestone, and how the AI calms them down with a BIFF draft while committing a **cryptographically timestamped, court-admissible incident log** (`events/timeline.jsonl`)—so the lawyer never has to read 11 PM emotional emails.
   - **Demo 2 — Instant Financial "Lie Detector" (`./firm search` & `./firm page`):** Run `./firm use smith_v_jones` and show how the engine catches Respondent swearing to **$38,000** on Page 1 of her Form 13 while her own attached 2024 CRA Notice of Assessment on Page 4 proves she earned **$64,200** (`+$26,200` undisclosed variance).
   - **Demo 3 — Draft Neutrality Audit & Deterministic Calculators:** Offer to run an admissibility and neutrality audit on `cases/smith_v_jones/memos/SETTLEMENT_CONFERENCE_MEMO.md` (stripping out argument/hearsay and verifying pinpoint citations), or run `./firm calc` / `./firm holidays`.

---

## 1. Professional Conduct & Evidentiary Standard (Zero Hallucination)

### The Absolute Evidentiary Rule
- **Never guess, estimate, or invent dates, financial figures, or past statements.**
- **Exact Page Citations:** Every factual assertion in an affidavit, timeline, conference brief, or legal memo MUST cite the source document and page number:
  - Format: `[Document Name, Page X]` (e.g., `[Form_13_Financial_Statement_Respondent, Page 4]`).
  - Page numbers correspond directly to the embedded `## Page X` markers created by the ingestion pipeline.
- **Confidentiality & Pre-LLM PII Scrubbing (LSO Rule 3.3-1):**
  - Client files, financial disclosures, and children's details remain strictly on the local workstation in isolated per-client SQLite FTS5 databases (`cases/<case_name>/case.db`).
  - **MANDATORY PRE-INGESTION PROMPT:** Whenever a user asks to create a new case (`./firm new`) or ingest new documents (`./firm ingest`), you MUST **ask the user first**:
    > *"Before I ingest and index your documents, are there any specific names or sensitive values (e.g., Applicant name, Respondent name, children's names, employers, schools, or addresses) that you would like me to register in the local PII scrubber (`./firm scrub add`) so they are replaced with anonymous tokens before entering the AI prompt?"*
  - `./firm ingest`, `./firm search`, and `./firm page` **automatically scrub PII** (registered names, auto-detected style-of-cause party names, SINs, phone numbers, email addresses, and postal codes) into reversible tokens (`[CLIENT_APPLICANT]`, `[RESPONDENT_PARTY]`, `[CHILD_1]`, `[SIN_1]`) **before** any text enters the LLM prompt.
  - **STRICT PROHIBITION:** Never read `cases/*/privacy_map.json` or raw files inside `cases/*/01_raw/` directly. Always access case documents via `./firm search` and `./firm page`, and use `./firm scrub unmask <draft.md> --out <final.md>` to restore real names locally offline when exporting final court documents.

---

## 2. Token-Efficiency & 4-Tier Discovery Protocol

Continuing records, motion records, and financial disclosures often span hundreds or thousands of pages. **Exhausting context windows by loading entire files into the prompt is strictly prohibited.**

Follow this 4-tier token-conscious discovery workflow:
1. **Tier 1 (Case Bedrock & Sync Orientation — <1,000 tokens):**
   ```bash
   ./firm cases
   ./firm use <case_name>
   ./firm core
   ./firm map --headings
   ```
2. **Tier 2 (Keyword & Full-Text Search — <150 tokens):**
   ```bash
   ./firm search "<search query>"
   ```
3. **Tier 3 (Targeted Page Extraction — <300 tokens):**
   Extract *only* the specific 1–2 pages needed for evidentiary verification:
   ```bash
   ./firm page "<document_name>" <page_number>
   ```
4. **Tier 4 (Legal Authority, Fact-Twin Matching & Deterministic Calculators — <200 tokens):**
   ```bash
   ./firm twin --brief
   ./firm canlii "<topic>" --brief
   ./firm calc --party-a "Smith" --income-a 92000 --party-b "Jones" --income-b 64200 --children 1
   ./firm holidays --year 2026 --party-a "Smith" --party-b "Jones" --max-nights 2
   ```

---

## 3. Coupled-Graph Knowledge Synchronization Mandate

To prevent "brief drift" between executive summaries, conference briefs, and affidavits, treat all strategic documents inside `cases/<case_name>/` as a **coupled graph**:
- Whenever a financial figure, impeachment pinpoint, or chronological event is updated in *any* memo or brief (`cases/<case_name>/memos/`), update `cases/<case_name>/CASE_CORE.md` in the **same turn**.
- Always edit `CASE_CORE.md` **last** so its modification timestamp remains newer than or equal to all downstream memos (clearing `./firm map` drift checks).

---

## 4. Draft Neutrality, Admissibility & Tactical Sequencing

When asked to review a draft brief/affidavit or plan litigation strategy, invoke the [`draft-neutrality-auditor`](.agents/skills/draft-neutrality-auditor/SKILL.md) skill:
1. **Family Law Rules Admissibility & Neutrality Audit:**
   - Strip out emotional adjectives, argument, and hearsay; anchor every assertion to direct observation and `[Document Name, Page X]` pinpoints; and conclude with a concise 1–3 sentence summary of the exact order sought.
2. **Child-Centered Sequencing Playbook:**
   - **Foreground Discipline (Moving Materials):** Lead with calm, generous, child-centered logistics (school-bell transitions, commute minimization, developmental stability) and deterministic CSG tables.
   - **Background Discipline (Reply Affidavits):** Hold documentary impeachment tables for clean, clinical Reply Affidavits when responding to specific factual inaccuracies.

---

## 5. The Unified CLI Suite (`./firm`)

| Subcommand | Function | Example |
| :--- | :--- | :--- |
| `./firm cases` | List all client files in `cases/` | `./firm cases` |
| `./firm use <name>` | Switch active client case | `./firm use smith_v_jones` |
| `./firm core` | Print active case's `CASE_CORE.md` & sync check | `./firm core` |
| `./firm map` | Print coupled-graph map & sync drift check | `./firm map --headings` |
| `./firm new <name>` | Initialize a new client folder & SQLite DB | `./firm new taylor_v_taylor --file-no "FO-26-999"` |
| `./firm add-client` | Link a client's private GitHub repo as a submodule | `./firm add-client smith git@github.com:firm/smith.git` |
| `./firm sync` | Pull client's mobile logs & uploads into SQLite | `./firm sync smith_v_jones` |
| `./firm ingest [path]` | Ingest PDFs, Word files & apply macOS Vision OCR | `./firm ingest` (processes `01_raw/`) |
| `./firm search "<q>"` | FTS5 full-text search with exact page results | `./firm search "Line 15000"` |
| `./firm page "<doc>" <p>` | Extract exact page from indexed document | `./firm page "Form_13_Respondent" 4` |
| `./firm ask "<question>"` | 100% offline local Q&A via LM Studio (`localhost:1234`) | `./firm ask "What is the Line 15000 variance?"` |
| `./firm calc` | Deterministic Ontario CSG & Set-Off calculator | `./firm calc --party-a "Smith" --income-a 92000 --party-b "Jones" --income-b 64200` |
| `./firm holidays` | Audit & solve court-compliant holiday schedules | `./firm holidays --year 2026 --party-a "Smith" --party-b "Jones"` |
| `./firm twin [facts]` | CanLII "Fact-Twin" matcher & Boolean query generator | `./firm twin` / `./firm twin --brief` |
| `./firm canlii "<topic>"` | Retrieve Ontario family law benchmark precedents | `./firm canlii "imputing" --brief` |
| `./firm log` | Record contemporaneous event to SQLite & Git ledger | `./firm log --date "2026-10-20" --title "Exchange Delay" --desc "..."` |
| `./firm events` | Filter and query client timeline events | `./firm events --category "Transition Conflict" --detail` |
| `./firm chronology` | Export Master Chronology for Court Brief | `./firm chronology --out cases/smith_v_jones/memos/CHRONOLOGY.md` |
| `./firm scrub` | Chunked PII pre-scanner & reversible anonymizer | `./firm scrub scan` / `./firm scrub unmask "Draft.md" "Final.md"` |
