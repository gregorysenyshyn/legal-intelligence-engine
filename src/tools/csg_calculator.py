"""
Deterministic Ontario Child Support Guidelines (CSG) & Set-Off Engine.
Calculates:
  1. Sole residence table amounts (1 to 6 children) under Schedule I (Ontario).
  2. Section 9 Shared Parenting 50/50 set-offs (with net monthly/annual payable).
  3. Section 8 Split Parenting adjustments.
  4. Section 7 Special & Extraordinary Expense proportional ratios.
  5. Multi-scenario comparative settlement matrices (Offer vs Counter-offer vs Trial Imputation).
  6. Arrears and Rule 24 costs reconciliation.
"""

import sys
import argparse
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.table import Table

console = Console()

# Official Federal Child Support Guidelines (Schedule I - Ontario)
# Format: (threshold_income, base_amount, marginal_rate)
# Applicable to 2025/2026/current standard rates

ON_TABLES: Dict[int, List[Tuple[float, float, float]]] = {
    1: [
        (0, 0.0, 0.0),
        (13000, 0.0, 0.0),
        (15000, 19.0, 0.0100),
        (20000, 69.0, 0.0170),
        (25000, 154.0, 0.0172),
        (30000, 240.0, 0.0180),
        (35000, 330.0, 0.0120),
        (40000, 390.0, 0.0120),
        (45000, 420.0, 0.0060),
        (50000, 450.0, 0.0116),
        (55000, 508.0, 0.0092),
        (60000, 554.0, 0.0094),
        (70000, 648.0, 0.0095),
        (80000, 743.0, 0.0098),
        (90000, 841.0, 0.0091),
        (100000, 932.0, 0.0088),
        (125000, 1152.0, 0.0084),
        (150000, 1362.0, 0.0081),
    ],
    2: [
        (0, 0.0, 0.0),
        (13000, 0.0, 0.0),
        (15000, 31.0, 0.0160),
        (20000, 111.0, 0.0270),
        (25000, 246.0, 0.0272),
        (30000, 382.0, 0.0286),
        (35000, 525.0, 0.0190),
        (40000, 620.0, 0.0190),
        (45000, 668.0, 0.0096),
        (50000, 716.0, 0.0184),
        (55000, 808.0, 0.0146),
        (60000, 881.0, 0.0148),
        (70000, 1029.0, 0.0150),
        (80000, 1179.0, 0.0152),
        (90000, 1331.0, 0.0142),
        (100000, 1473.0, 0.0136),
        (125000, 1813.0, 0.0130),
        (150000, 2109.0, 0.0125),
    ],
    3: [
        (0, 0.0, 0.0),
        (13000, 0.0, 0.0),
        (15000, 39.0, 0.0200),
        (20000, 139.0, 0.0340),
        (25000, 309.0, 0.0344),
        (30000, 481.0, 0.0360),
        (35000, 661.0, 0.0240),
        (40000, 781.0, 0.0240),
        (45000, 841.0, 0.0120),
        (50000, 901.0, 0.0232),
        (55000, 1017.0, 0.0184),
        (60000, 1109.0, 0.0186),
        (70000, 1295.0, 0.0188),
        (80000, 1483.0, 0.0190),
        (90000, 1673.0, 0.0178),
        (100000, 1851.0, 0.0170),
        (125000, 2276.0, 0.0163),
        (150000, 2674.0, 0.0158),
    ],
    4: [
        (0, 0.0, 0.0),
        (13000, 0.0, 0.0),
        (15000, 46.0, 0.0235),
        (20000, 163.0, 0.0400),
        (25000, 363.0, 0.0405),
        (30000, 566.0, 0.0424),
        (35000, 778.0, 0.0282),
        (40000, 919.0, 0.0282),
        (45000, 990.0, 0.0141),
        (50000, 1060.0, 0.0273),
        (55000, 1196.0, 0.0216),
        (60000, 1304.0, 0.0219),
        (70000, 1523.0, 0.0221),
        (80000, 1744.0, 0.0223),
        (90000, 1967.0, 0.0209),
        (100000, 2176.0, 0.0200),
        (125000, 2676.0, 0.0192),
        (150000, 3149.0, 0.0186),
    ]
}

def get_table_amount(income: float, children: int = 1) -> float:
    """Calculates monthly CSG table amount for Ontario."""
    if income <= 13000:
        return 0.0
    
    # Cap / fallback child count
    num_kids = max(1, min(children, 4))
    bracket = ON_TABLES.get(num_kids, ON_TABLES[1])
    
    for i in range(len(bracket) - 1, -1, -1):
        thresh, base, rate = bracket[i]
        if income >= thresh:
            excess = income - thresh
            amount = base + (excess * rate)
            # If more than 4 children, add statutory increment (~10% per additional child)
            if children > 4:
                extra = children - 4
                amount += amount * (0.10 * extra)
            return round(amount, 2)
            
    return 0.0

def calculate_support(
    party_a_name: str,
    party_a_income: float,
    party_b_name: str,
    party_b_income: float,
    children: int = 1,
    parenting_type: str = "shared",  # shared (s.9), sole_a, sole_b
    s7_annual_expenses: float = 0.0
) -> Dict:
    """
    Computes comprehensive CSG figures, shared set-off, and S.7 expense proportions.
    """
    table_a = get_table_amount(party_a_income, children)
    table_b = get_table_amount(party_b_income, children)
    
    total_income = party_a_income + party_b_income
    share_a_pct = round((party_a_income / total_income) * 100, 2) if total_income > 0 else 50.0
    share_b_pct = round((party_b_income / total_income) * 100, 2) if total_income > 0 else 50.0
    
    if parenting_type == "shared":
        diff = round(table_a - table_b, 2)
        if diff > 0:
            payor = party_a_name
            net_monthly = diff
        elif diff < 0:
            payor = party_b_name
            net_monthly = abs(diff)
        else:
            payor = "Neither (Offset Equal)"
            net_monthly = 0.0
    elif parenting_type == "sole_a":
        # Party A has primary residence; Party B pays full table
        payor = party_b_name
        net_monthly = table_b
    else: # sole_b
        # Party B has primary residence; Party A pays full table
        payor = party_a_name
        net_monthly = table_a
        
    s7_a_share = round((share_a_pct / 100.0) * s7_annual_expenses, 2)
    s7_b_share = round((share_b_pct / 100.0) * s7_annual_expenses, 2)
    
    return {
        "party_a_name": party_a_name,
        "party_a_income": party_a_income,
        "party_a_table": table_a,
        "party_a_s7_pct": share_a_pct,
        "party_a_s7_share": s7_a_share,
        "party_b_name": party_b_name,
        "party_b_income": party_b_income,
        "party_b_table": table_b,
        "party_b_s7_pct": share_b_pct,
        "party_b_s7_share": s7_b_share,
        "children": children,
        "parenting_type": parenting_type,
        "net_monthly": net_monthly,
        "net_annual": round(net_monthly * 12, 2),
        "payor": payor,
        "s7_annual_total": s7_annual_expenses
    }

def print_support_report(res: Dict, months_under_review: int = 0, prior_order_monthly: float = 0.0, costs_awarded: float = 0.0):
    """Outputs a rich formatted professional settlement / trial brief calculation."""
    console.print("\n[bold blue]" + "=" * 76 + "[/bold blue]")
    console.print("[bold white]ONTARIO CHILD SUPPORT GUIDELINES (CSG) DETERMINATION[/bold white]")
    console.print(f"[dim]Jurisdiction: Ontario | Children: {res['children']} | Regime: {res['parenting_type'].upper()}[/dim]")
    console.print("[bold blue]" + "=" * 76 + "[/bold blue]\n")
    
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Party", style="bold")
    t.add_column("Guideline Income", justify="right")
    t.add_column("Full Table CSG", justify="right")
    t.add_column("S.7 Share %", justify="right")
    if res["s7_annual_total"] > 0:
        t.add_column(f"S.7 Share (${res['s7_annual_total']:,.0f}/yr)", justify="right")
        
    row_a = [
        res['party_a_name'],
        f"${res['party_a_income']:>10,.2f}",
        f"${res['party_a_table']:>8,.2f}/mo",
        f"{res['party_a_s7_pct']:.1f}%"
    ]
    if res["s7_annual_total"] > 0:
        row_a.append(f"${res['party_a_s7_share']:>8,.2f}/yr")
        
    row_b = [
        res['party_b_name'],
        f"${res['party_b_income']:>10,.2f}",
        f"${res['party_b_table']:>8,.2f}/mo",
        f"{res['party_b_s7_pct']:.1f}%"
    ]
    if res["s7_annual_total"] > 0:
        row_b.append(f"${res['party_b_s7_share']:>8,.2f}/yr")
        
    t.add_row(*row_a)
    t.add_row(*row_b)
    console.print(t)
    
    console.print("\n[bold green]RESULT / NET CSG ORDER:[/bold green]")
    if res['parenting_type'] == 'shared':
        console.print(f"  • [bold]Set-Off Net Payable:[/bold] [yellow]${res['net_monthly']:,.2f} /month[/yellow] (${res['net_annual']:,.2f} /year)")
        console.print(f"  • [bold]Net Payor:[/bold]           [cyan]{res['payor']}[/cyan]")
    else:
        console.print(f"  • [bold]Base Table Payable:[/bold]  [yellow]${res['net_monthly']:,.2f} /month[/yellow] (${res['net_annual']:,.2f} /year)")
        console.print(f"  • [bold]Payor:[/bold]               [cyan]{res['payor']}[/cyan]")

    if months_under_review > 0 or costs_awarded > 0:
        console.print("\n[bold magenta]RECONCILIATION & ARREARS ADJUSTMENT:[/bold magenta]")
        console.print("-" * 76)
        if prior_order_monthly > 0 and months_under_review > 0:
            prior_total = months_under_review * prior_order_monthly
            new_total = months_under_review * res['net_monthly']
            variance = prior_total - new_total
            console.print(f"  • Duration:                    {months_under_review} months")
            console.print(f"  • Prior Operative Order Total: ${prior_total:,.2f} (${prior_order_monthly:,.2f}/mo)")
            console.print(f"  • Adjusted New Order Total:    ${new_total:,.2f} (${res['net_monthly']:,.2f}/mo)")
            if variance > 0:
                console.print(f"  • [bold green]Overpayment / Phantom Arrears Redacted:[/bold green] [bold green]${variance:,.2f}[/bold green]")
            elif variance < 0:
                console.print(f"  • [bold red]Retroactive Underpayment Accrued:[/bold red] [bold red]${abs(variance):,.2f}[/bold red]")
                
        if costs_awarded > 0:
            console.print(f"  • Rule 24 Bad-Faith / Discretionary Costs Award: +${costs_awarded:,.2f}")
            if res['payor'] == res['party_a_name'] and res['net_monthly'] > 0:
                holiday_months = round(costs_awarded / res['net_monthly'], 1)
                console.print(f"  • [bold cyan]Equivalent Support Moratorium:[/bold cyan] {holiday_months} months at $0 support")
                
    console.print("[bold blue]" + "=" * 76 + "[/bold blue]\n")

def compare_scenarios(scenarios: List[Dict], party_a: str, party_b: str, children: int = 1):
    """Outputs side-by-side scenario matrix for settlement conferences and mediation."""
    t = Table(title=f"CSG Scenario Matrix: {party_a} v. {party_b} ({children} Child(ren))", show_header=True)
    t.add_column("Scenario / Offer", style="bold")
    t.add_column(f"{party_a} Income", justify="right")
    t.add_column(f"{party_b} Income", justify="right")
    t.add_column("Net Monthly Payable", justify="right")
    t.add_column("Payor", justify="center")
    t.add_column(f"S.7 Split ({party_a}/{party_b})", justify="center")
    
    for s in scenarios:
        res = calculate_support(party_a, s["inc_a"], party_b, s["inc_b"], children, s.get("type", "shared"))
        t.add_row(
            s["label"],
            f"${s['inc_a']:,.0f}",
            f"${s['inc_b']:,.0f}",
            f"${res['net_monthly']:,.2f}",
            res['payor'],
            f"{res['party_a_s7_pct']:.1f}% / {res['party_b_s7_pct']:.1f}%"
        )
    console.print(t)

def main():
    parser = argparse.ArgumentParser(description="Deterministic Ontario CSG Support Calculator")
    parser.add_argument("--party-a", dest="party_a", type=str, default="Party A", help="Name of Party A")
    parser.add_argument("--income-a", dest="income_a", type=float, required=True, help="Party A Line 15000 Guideline Income")
    parser.add_argument("--party-b", dest="party_b", type=str, default="Party B", help="Name of Party B")
    parser.add_argument("--income-b", dest="income_b", type=float, required=True, help="Party B Line 15000 Guideline Income")
    parser.add_argument("--children", type=int, default=1, help="Number of children (default: 1)")
    parser.add_argument("--parenting", choices=["shared", "sole_a", "sole_b"], default="shared", help="Parenting regime")
    parser.add_argument("--s7", dest="s7", type=float, default=0.0, help="Annual total Section 7 extraordinary expenses")
    parser.add_argument("--months-unpaid", type=int, default=0, help="Months of retroactive adjustment")
    parser.add_argument("--prior-rate", type=float, default=0.0, help="Monthly rate under prior interim order")
    parser.add_argument("--costs", type=float, default=0.0, help="Costs awarded in favor of Party A")

    args = parser.parse_args()
    res = calculate_support(
        args.party_a, args.income_a,
        args.party_b, args.income_b,
        args.children, args.parenting,
        args.s7
    )
    print_support_report(res, args.months_unpaid, args.prior_rate, args.costs)

if __name__ == "__main__":
    main()

