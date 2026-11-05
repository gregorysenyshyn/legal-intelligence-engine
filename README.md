# Legal Intelligence Engine

**Privacy-First, Local AI Evidence Search & Financial Disclosure Auditing for Family Law Practices.**

*Run 100% air-gapped on a Mac with **LM Studio** + **Apple Vision OCR** + **SQLite FTS5**—or use the built-in **Local Privacy Firewall** to scrub client PII into reversible tokens before a single word ever touches a cloud LLM.*

---

## Why Most Lawyers Can't Use Standard AI (And How This Fixes It)

Family law files contain the most sensitive data imaginable: sworn Financial Statements (Form 13), CRA Notices of Assessment, SINs, bank records, police occurrence reports, and children's school/medical records.

Practitioners face a catch-22:
1. **Cloud AI is a Confidentiality Risk:** Uploading raw client disclosures to third-party servers creates immediate headaches under **Law Society Rule 3.3-1 (Confidentiality)** and solicitor-client privilege.
2. **Standard Local LLMs Are Too Slow on Large Files:** Dumping a 500-page Continuing Record into a local LLM on a laptop overwhelms the context window, takes minutes per prompt, and loses track of page numbers.

**Legal Intelligence Engine** solves both problems by pairing **sub-millisecond local SQLite indexing** with **small-context local AI (LM Studio)**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: 100% OFFLINE INGESTION & PINPOINT INDEXING (On Your Mac)       │
│  • Native macOS Vision OCR extracts text from scanned PDFs offline      │
│  • Every page is stamped (`## Page X`) and indexed into SQLite FTS5     │
│  • Searches 700+ pages in 0.002 seconds—narrows context to <400 tokens  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│ OPTION A: 100% AIR-GAPPED MODE  │     │ OPTION B: LOCAL PII FIREWALL    │
│ (`./firm ask` via LM Studio)    │     │ (LM Studio -> Cloud AI)         │
│                                 │     │                                 │
│ • Feeds only the top <400-token │     │ • Splits docs into 100-word     │
│   search hits to LM Studio on   │     │   chunks; local LLM + regex     │
│   `localhost:1234`.             │     │   scrub names, employers, SINs  │
│ • Fast 1–3 second answers on    │     │   & addresses into tokens       │
│   Apple Silicon Macs.           │     │   (`[CLIENT_APPLICANT]`, etc.). │
│ • ZERO bytes ever leave your    │     │ • Cloud AI drafts on tokens;    │
│   office network.               │     │   unmask 100% offline for court.│
└─────────────────────────────────┘     └─────────────────────────────────┘
```

---

## Core Capabilities

1. **Instant Pinpoint Evidence Search (`[Document Name, Page X]`):**
   * When standing in front of a judge or drafting an affidavit, summaries aren't enough—you need the exact quote and page number. Search across hundreds of PDFs in milliseconds and pull the exact source page on demand.
2. **Chunked Pre-Ingestion PII Scanner (`./firm scrub scan`):**
   * Before a document is indexed, it is broken into small paragraph chunks and scanned offline (via regex + local LM Studio NER) for party names, children, employers, schools, daycares, street addresses, SINs, phone numbers, and emails.
   * Displays **only an isolated 40-character preview fragment** (`...Employer: «[ORG_2]», Guelph...`) and maps sensitive strings to reversible tokens (`[CLIENT_APPLICANT]`, `[RESPONDENT_PARTY]`, `[ORG_2]`, `[SIN_1]`) in a local-only dictionary (`privacy_map.json`).
3. **Three-Point Financial Statement Auditing (Form 13 vs. NOA vs. Paystubs):**
   * Cross-reference a party's sworn Form 13 income and expenses against their attached CRA Line 15000 Notices of Assessment and year-to-date paystubs to surface undisclosed income or unreceipted Section 7 claims.
4. **CanLII "Fact-Twin" Precedent Matcher (`./firm twin`):**
   * Automatically extracts the anonymized factual vectors of the active client case (`CASE_CORE.md` — zero PII transmitted), matches them against parallel Ontario family law precedent archetypes (*"Fact Twins"*: e.g., hostile curbside exchanges $\rightarrow$ school-bell transitions; Form 13 vs. Line 15000 variance $\rightarrow$ *Drygala*/*Colucci* imputation; unreceipted daycare claims $\rightarrow$ *Park v. Thompson* net-of-subsidy disallowance), and generates precision CanLII Boolean queries + side-by-side brief tables.
5. **Deterministic Child Support & Holiday Schedule Calculators:**
   * Built-in Python engines calculate *Child Support Guidelines* Schedule I table amounts, Section 9 (50/50 shared parenting) set-offs, Section 7 proportional splits, and 14-day holiday parenting schedules with consecutive-overnight caps.
6. **Structured Client Document & Timeline Intake (Optional Git Submodule):**
   * Clients can upload disclosure PDFs and log contemporaneous parenting observations into a structured intake repository that syncs directly into your local database.

---

## Try the 2-Minute Demo (No Coding or Git Required)

The repository comes pre-loaded with a synthetic Ontario Court of Justice file (***Smith v. Jones***, *File No. FO-24-00123*) so you can test the PII scrubber, pinpoint search, and financial audit tools immediately.

### Step 1: Download the Folder
1. Click the green **`<> Code`** button at the top right of this page and select **`Download ZIP`** *(or [**click here to download the ZIP directly**](https://github.com/gregorysenyshyn/legal-intelligence-engine/archive/refs/heads/main.zip))*.
2. Double-click the downloaded ZIP file to unzip the `legal-intelligence-engine` folder onto your Desktop or Documents folder.
3. Open that folder inside **OpenAI Codex**, **Google Antigravity**, **Claude Code**, or **Cursor** *(and optionally open **LM Studio** on `localhost:1234` for 100% offline local inference)*.

### Step 2: Ask Any of These Plain-English Prompts
*(The agent will automatically configure the local Python environment in the background and run the database queries for you):*

1. **"Give me a tour of the Smith v. Jones demo file and show me how the PII scrubber protects client names."**
2. **"Run a chunked PII scan on the raw documents and show me the 40-character preview fragments."**
   *(Watch it flag and mask the party names, employer `[ORG_2]`, and preschool `[ORG_3]` without exposing the raw file).*
3. **"Search the Smith v. Jones records for Line 15000 and check if there is any discrepancy between the Respondent's sworn Form 13 and her 2024 CRA Notice of Assessment."**
   *(Watch it pull `[Form_13_Financial_Statement_Respondent, Page 1 vs. Page 4]` and flag a **$26,200 undisclosed income variance** using anonymized tokens).*
4. **"Find CanLII Fact-Twin precedents that match the facts of Smith v. Jones and generate a side-by-side comparison table for my Settlement Conference Brief."**
   *(Watch `./firm twin` extract the anonymized fact vectors from `CASE_CORE.md`, build exact CanLII Boolean search strings, and map each fact pattern to parallel Ontario appellate holdings).*
5. **"Calculate child support if Party A earns $92,000 and Party B earns $64,200 with 1 child in 50/50 shared care and $4,000 in annual net daycare."**
6. **"Audit the 2026 Christmas holiday schedule to ensure it respects a 2-consecutive-overnight cap and divides the 336 holiday hours 50/50."**

---

## DIY Open Source vs. Turnkey Practice Setup (Consulting)

### 1. Free / Open Source
Everything in this repository is open source and works out of the box. Download the ZIP (or clone it), test the *Smith v. Jones* demo file, and use it on your own workstation.

### 2. Turnkey Firm Setup & Local AI Deployment
For solo practitioners and boutique family law firms who want a **private, local-first AI workstation** configured on their office Macs/PCs without spending time on technical setup, I offer turnkey deployment and consulting:
* **Local Apple Silicon / LM Studio Setup:** Installing and tuning local MLX models, Apple Vision OCR, and the SQLite FTS5 indexing pipeline on counsel and clerk workstations.
* **Privacy & LSO Rule 3.3-1 Hardening:** Configuring automated pre-ingestion PII scrubbing and offline unmasking workflows tailored to your firm's document templates.
* **Custom Financial & Support Calculators:** Integrating regional union salary grids, pension/equalization helpers, or state/provincial support tables.
* **1-on-1 Staff Training:** A practical walkthrough showing counsel and clerks how to ingest a new motion record and run a Three-Point Form 13 financial audit in 5 minutes.

📬 **Interested in setting this up for your practice?** Visit **[gregorysenyshyn.com](https://gregorysenyshyn.com)** to get in touch.

---

<details>
<summary><b>🔧 Technical Reference & CLI Commands (For Developers & Power Users)</b></summary>

<br>

Behind the scenes, the AI workspace executes a deterministic Python CLI (`./firm`) so it never wastes context tokens or hallucinates math:

```bash
# Setup (run automatically by the AI agent if needed)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

| Command | Usage | Description |
| :--- | :--- | :--- |
| `cases` | `./firm cases` | Lists all client cases and highlights the active workspace. |
| `use` | `./firm use <case_name>` | Switches the active workspace to a specific client file. |
| `core` | `./firm core` | Displays `CASE_CORE.md` executive index (<1,000 tokens) and checks for sync drift. |
| `map` | `./firm map [--headings]` | Prints token-efficient coupled-graph file map and sync status. |
| `new` | `./firm new <case_name>` | Initializes a new isolated client directory, `privacy_map.json`, and SQLite DB. |
| `add-client` | `./firm add-client <name> <url>` | Links a remote private client GitHub repository as a Git submodule. |
| `sync` | `./firm sync [case_name]` | Pulls client uploads, auto-ingests new PDFs, and updates SQLite FTS5. |
| `ingest` | `./firm ingest [path]` | Runs native macOS Vision OCR, chunked PII scrubbing, and FTS5 indexing. |
| `search` | `./firm search "<query>"` | Sub-second FTS5 search across all case documents with exact page numbers. |
| `page` | `./firm page "<doc>" <p>` | Extracts the exact PII-scrubbed page(s) from an indexed document. |
| `ask` | `./firm ask "<question>"` | 100% air-gapped local RAG Q&A via LM Studio (`localhost:1234`). |
| `calc` | `./firm calc ...` | Computes CSG table amounts, s.9 50/50 set-offs, s.7 ratios, and arrears. |
| `holidays` | `./firm holidays ...` | Solves and audits holiday schedules against overnight caps and 50/50 hours. |
| `twin` | `./firm twin [facts] [--brief]` | Matches anonymized case fact vectors to CanLII "Fact-Twin" precedents & Boolean queries. |
| `canlii` | `./firm canlii "<topic>"` | Retrieves curated family law appellate precedents (*Drygala*, *Colucci*, etc.). |
| `log` | `./firm log ...` | Records a contemporaneous event to SQLite and the Git `.jsonl` ledger. |
| `events` | `./firm events [--detail]` | Searches or filters client chronological timeline events. |
| `chronology` | `./firm chronology --out <f>` | Generates a formatted Markdown chronology table for Briefs or Affidavits. |
| `scrub` | `./firm scrub scan` / `unmask` | Pre-scans document chunks for PII fragments and masks/unmasks tokens offline. |

</details>
