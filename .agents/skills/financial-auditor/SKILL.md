---
name: financial-auditor
description: Audits Ontario Form 13/13.1 Financial Statements, cross-references Line 15000 income against Notices of Assessment and paystubs, detects variances, identifies phantom Section 7 expenses, and generates cross-examination questions.
---

# Financial Disclosure Auditor Skill

Use this skill whenever auditing opposing party financial disclosure, reviewing Form 13/13.1 sworn statements, verifying income for child support, or preparing for cross-examination or a Settlement Conference.

## Audit Workflow

1. **Locate Financial Disclosures:**
   - Search for financial documents:
     ```bash
     ./firm search "Line 15000"
     ./firm search "Notice of Assessment"
     ./firm search "Paystub"
     ./firm search "Form 13"
     ```
2. **Three-Point Reconciliation Test:**
   - **Point 1 (Sworn Form 13):** Check Part 1 (Income) declared annual gross income.
   - **Point 2 (CRA Notice of Assessment):** Extract Line 15000 (Total Income) from the last 3 taxation years.
   - **Point 3 (YTD Paystubs):** Annualize year-to-date gross earnings (`(YTD Gross / Weeks Elapsed) * 52`).
   - If Paystub Annualized > Form 13 Declared: Flag hidden earnings.
   - If NOA includes non-taxable benefits, dividends, or self-employment gross-ups: Note adjustments under CSG Schedule III.
3. **Section 7 Expense Audit:**
   - Review claimed child care, medical/dental, tutoring, and extracurricular costs.
   - Cross-check whether:
     - Third-party receipts are provided for each line item.
     - Government child care subsidies (e.g. CWELCC $10/day daycare) or Canada Child Benefit deductions are netted out.
     - Expenses meet the *Park v. Thompson* threshold (both necessary and reasonable).
4. **Draft Cross-Examination & Disclosure Requests:**
   - For every discrepancy, formulate a precise Rule 13(11) disclosure demand and cross-examination question citing the exact page of the disclosure.

