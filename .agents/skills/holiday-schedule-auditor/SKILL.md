---
name: holiday-schedule-auditor
description: Audits, models, and solves Ontario holiday and parenting schedules (Christmas/Winter Break, March Break, Summer) against governing court orders, enforcing consecutive-overnight caps, alternating year rotations, and 50/50 hourly equality.
---

# Holiday & Parenting Schedule Auditor (`holiday-schedule-auditor`)

Use this skill whenever opposing counsel or an opposing party submits a proposed holiday parenting schedule (Christmas break, March Break, or Summer vacation), or when counsel needs to generate a balanced, court-compliant holiday counter-proposal.

## Deterministic CLI Tool

Always run the deterministic solver via `./firm holidays` to calculate exact hours, check consecutive-overnight caps, and verify court-order compliance:

```bash
# Audit an Even-Year Christmas schedule with a 2-overnight cap:
./firm holidays --year 2026 --party-a "Smith" --party-b "Jones" --max-nights 2

# Project an Odd-Year Christmas schedule:
./firm holidays --year 2027 --party-a "Smith" --party-b "Jones" --max-nights 2
```

## Audit Checklist for Holiday Proposals

1. **Core Holiday Rotation Check:**
   - Verify whether the governing order alternates Christmas Eve (Dec 24 at 12:00 PM to Dec 25 at 12:00 PM) and Christmas Day (Dec 25 at 12:00 PM to Dec 26 at 12:00 PM) between even and odd years.
2. **Consecutive Overnight Cap Check:**
   - For young children (preschool / early primary), check whether the governing order imposes a consecutive-overnight cap (e.g., maximum 2 or 3 consecutive overnights during holiday breaks).
   - Flag any proposed multi-day block that breaches the cap without mutual written consent.
3. **100% Hourly Equality Check:**
   - Across a 14-day (336-hour) Winter Break, verify that total hours and overnights divide equally (168 hours / 7 overnights per parent) so neither parent can accuse the other of "time-skimming."
4. **School-Bell vs. Curbside Transitions:**
   - Wherever possible, anchor holiday start and end transitions to school dismissal (e.g., Friday 3:15 PM school bell) and school return (Monday 8:45 AM drop-off) to eliminate face-to-face curbside friction.
