---
name: canlii-researcher
description: Researches and cites binding Canadian and Ontario family law case law and statutory tests (imputing income, retroactive child support, s.7 expenses, parenting status quo, review clauses, and Rule 24 costs).
---

# CanLII Legal Researcher Skill

Use this skill whenever drafting factums, conference briefs, legal memos, or settlement letters requiring binding Ontario Court of Appeal, Superior Court of Justice, or Supreme Court of Canada authorities.

## Core Rules & Execution

1. **CanLII "Fact-Twin" Matcher & Boolean Vector Generator (`./firm twin`):**
   - Automatically extracts the anonymized factual vectors of the active client case (`CASE_CORE.md` — zero PII transmitted) or takes custom fact patterns, matches them against parallel Ontario family law precedent archetypes ("Fact Twins"), and outputs both precision CanLII Boolean queries and side-by-side comparison tables:
     ```bash
     ./firm twin
     ./firm twin "curbside exchange conflict"
     ./firm twin --brief
     ```
2. **Local Precedent Lookup (Zero Token Cost):**
   - Run the precedent lookup tool:
     ```bash
     ./firm canlii "<topic_or_case_name>"
     ```
   - For court-ready brief format (with legal test and citation):
     ```bash
     ./firm canlii "<topic>" --brief
     ```
3. **Standard Topic Keywords:**
   - `imputing` -> *Drygala v. Pauli*, *Bak v. Dobell*, *Charron v. Carrière*, *Lavie v. Lavie*
   - `retroactive` -> *D.B.S. v. S.R.*, *Colucci v. Colucci*, *Michel v. Graydon*
   - `s7` -> *Park v. Thompson* (2005 CanLII 14132 ON CA)
   - `transitions` or `parenting` -> *Gordon v. Goertz*, *Barendregt v. Grebliunas*, *K.M. v. J.R.*, *Tremblay v. Tremblay*
   - `review` -> *Leskun v. Leskun*
   - `costs` or `bad faith` -> *Beaver v. Hill*, *Mattina v. Mattina*
3. **Citation Formatting Standard:**
   - Always include the neutral citation, official law report citation where available, and the core governing legal test.
   - Example:
     > *Drygala v. Pauli*, 2002 CanLII 41868 (ON CA), (2002), 61 O.R. (3d) 711 (C.A.): Sets out the 3-step test for imputing income under CSG s. 19(1)(a). Bad faith is not required; the test is whether the payor is earning what they are reasonably capable of earning.

