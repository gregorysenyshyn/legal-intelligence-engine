---
name: court-brief-drafter
description: Drafts Ontario Family Court materials (Form 17A Case Conference Briefs, Form 17C Settlement Conference Briefs, Form 14A Affidavits, and Rule 18 Offers to Settle) with exact page citations and zero hallucination.
---

# Court Brief & Pleading Drafter Skill

Use this skill to draft, update, or refine pleadings, conference briefs, and motion materials under the Ontario *Family Law Rules*.

## Mandatory Evidentiary Workflow

1. **Orientation:**
   - Confirm active case: `./firm cases`
   - Review case overview and parties.
2. **Document Discovery & Page Retrieval:**
   - Search relevant evidence: `./firm search "<keyword>"`
   - Pull exact page citations: `./firm page "<filename>" <page>`
   - **Zero Hallucination:** Every factual claim must include a verified citation: `[Document Name, Page X]`.
3. **Structure for Form 17C Settlement Conference Brief:**
   - **Part 1: Procedural History & Operative Orders** (Dates of separation, applications, interim orders).
   - **Part 2: Issues Resolved vs. Issues in Dispute** (Parenting time, decision-making, child support, S.7 expenses, equalization).
   - **Part 3: Applicant's / Respondent's Position & Settlement Offer** (Clear, numbered bullet points of exact orders sought).
   - **Part 4: Financial Analysis & CSG Table Figures** (Run `./firm calc` and embed the table).
   - **Part 5: Governing Legal Authorities** (Run `./firm canlii "<topic>" --brief`).
   - **Schedule A: Chronological Event Schedule** (Export via `./firm chronology`).
4. **Structure for Form 14A Affidavit:**
   - Numbered paragraphs in first-person voice.
   - Separate into descriptive headings:
     1. Background & Status of Proceedings
     2. Parenting Regime & Child's Needs
     3. Financial Disclosure & Child Support
     4. Grounds for Relief Sought
   - Direct exhibit citations: `(attached hereto as Exhibit "B" to this Affidavit, Page 3)`.

