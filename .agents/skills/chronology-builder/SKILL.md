---
name: chronology-builder
description: Formats, structures, logs, and exports contemporaneous Master Chronological Timelines for Ontario Family Court conference briefs (Rule 17), motion records (Rule 14), and trial briefs.
---

# Master Chronology Builder Skill

Use this skill to log incident details, query case events, and export court-ready chronological tables for conference briefs and trial records.

## Core Rules & Execution

1. **Logging Contemporaneous Incidents:**
   - Log each event with factual, objective language and verbatim quotes:
     ```bash
     ./firm log \
       --date "YYYY-MM-DD" \
       --time "HH:MM AM/PM" \
       --title "Short Title" \
       --desc "Objective factual description" \
       --category "Transition Conflict" \
       --location "Location / Platform" \
       --parties "Individuals present" \
       --child-impact "Child's demeanour" \
       --counsel-notes "Breach of order / evidentiary proof" \
       --citation "Exhibit / Occurrence #" \
       --page 2
     ```
2. **Querying Timeline Events:**
   - Search events by keyword: `./firm events --search "transition"`
   - Filter by category: `./firm events --category "Transition Conflict" --detail`
   - Filter by date range: `./firm events --from-date "2026-01-01" --to-date "2026-06-30"`
3. **Exporting Master Chronology for Court Filing:**
   - Export directly to markdown for inclusion into a Form 17C Brief or Motion Record:
     ```bash
     ./firm chronology --out cases/<case_name>/memos/MASTER_CHRONOLOGY.md
     ```
   - Features in export:
     - Formatted markdown table with Date/Time, Category, Factual Narrative, Child Impact, and Supporting Exhibit Citation.
     - Fully compliant with Ontario Court presentation standards.

