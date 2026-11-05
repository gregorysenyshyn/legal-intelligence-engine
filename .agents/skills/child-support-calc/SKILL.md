---
name: child-support-calc
description: Calculates exact Ontario Child Support Guidelines (CSG) monthly table amounts, 50/50 shared parenting set-offs (CSG Section 9), Section 7 expense sharing ratios, and multi-scenario settlement comparison matrices.
---

# Child Support Guidelines (CSG) Calculator Skill

Use this skill whenever counsel or a client requests child support calculations, 50/50 shared parenting set-off amounts, Section 7 expense sharing percentages, or comparative settlement matrices for Ontario family law matters.

## Core Rules & Execution

1. **Deterministic Calculation Mandate:**
   - **NEVER** guess, calculate in your head, or hallucinate child support figures.
   - Always run the deterministic engine:
     ```bash
     ./firm calc --party-a "Client" --income-a 90000 --party-b "Other Party" --income-b 62190 --children 1
     ```
2. **50/50 Shared Parenting Set-Off (CSG Section 9):**
   - When each parent exercises at least 40% of the parenting time annually, calculate support under Section 9:
     - Determine Parent A's Table Amount based on their Guideline income.
     - Determine Parent B's Table Amount based on their Guideline income.
     - Net set-off = `|Parent A Table - Parent B Table|`.
     - The higher earner pays the net difference to the lower earner.
3. **Section 7 Special & Extraordinary Expenses:**
   - Calculate proportional sharing ratios based on the parties' respective Guideline incomes:
     - `Party A % = Party A Income / Total Income * 100`
     - `Party B % = Party B Income / Total Income * 100`
   - To include S.7 in the calculation:
     ```bash
     ./firm calc --party-a "Client" --income-a 90000 --party-b "Other Party" --income-b 62190 --children 1 --s7 4000
     ```
4. **Arrears Adjustment & Rule 24 Costs Offsetting:**
   - Where a prior interim order is being varied retroactively:
     ```bash
     ./firm calc --party-a "Client" --income-a 90000 --party-b "Other" --income-b 62190 --months-unpaid 12 --prior-rate 692 --costs 3500
     ```
   - Automatically computes overpayment / phantom arrears reduction and equivalent support moratorium periods.

