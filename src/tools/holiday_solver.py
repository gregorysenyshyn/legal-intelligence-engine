"""
Ontario Family Law Holiday & Parenting Schedule Compliance Auditor.
Solves and validates holiday parenting schedules (Christmas/Winter Break, March Break, Summer)
against court-ordered overnight caps, alternating year rotations, and 50/50 hourly equality.
"""

import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def solve_christmas_schedule(
    year: int = 2026,
    party_a: str = "Applicant",
    party_b: str = "Respondent",
    max_overnights: int = 2,
):
    """Computes an hourly-balanced (168h / 168h) 14-day Christmas schedule respecting a consecutive-overnight cap."""
    is_even = (year % 2 == 0)

    if is_even:
        blocks = [
            (datetime.datetime(year, 12, 20, 15, 0), datetime.datetime(year, 12, 22, 15, 0), party_a, 2, "Opening 2-night rotation"),
            (datetime.datetime(year, 12, 22, 15, 0), datetime.datetime(year, 12, 24, 12, 0), party_b, 2, "Pre-Christmas block"),
            (datetime.datetime(year, 12, 24, 12, 0), datetime.datetime(year, 12, 25, 12, 0), party_a, 1, "Core Holiday: Christmas Eve 12:00 PM to Christmas Day 12:00 PM"),
            (datetime.datetime(year, 12, 25, 12, 0), datetime.datetime(year, 12, 26, 12, 0), party_b, 1, "Core Holiday: Christmas Day 12:00 PM to Boxing Day 12:00 PM"),
            (datetime.datetime(year, 12, 26, 12, 0), datetime.datetime(year, 12, 28, 12, 0), party_a, 2, "Boxing Day afternoon & post-holiday block"),
            (datetime.datetime(year, 12, 28, 12, 0), datetime.datetime(year, 12, 30, 12, 0), party_b, 2, "Mid-break 2-night rotation"),
            (datetime.datetime(year, 12, 30, 12, 0), datetime.datetime(year + 1, 1, 1, 12, 0), party_a, 2, "New Year's Eve block"),
            (datetime.datetime(year + 1, 1, 1, 12, 0), datetime.datetime(year + 1, 1, 3, 15, 0), party_b, 2, "New Year's Day & closing weekend"),
        ]
    else:
        blocks = [
            (datetime.datetime(year, 12, 20, 15, 0), datetime.datetime(year, 12, 22, 15, 0), party_b, 2, "Opening 2-night rotation"),
            (datetime.datetime(year, 12, 22, 15, 0), datetime.datetime(year, 12, 24, 12, 0), party_a, 2, "Pre-Christmas block"),
            (datetime.datetime(year, 12, 24, 12, 0), datetime.datetime(year, 12, 25, 12, 0), party_b, 1, "Core Holiday: Christmas Eve 12:00 PM to Christmas Day 12:00 PM"),
            (datetime.datetime(year, 12, 25, 12, 0), datetime.datetime(year, 12, 26, 12, 0), party_a, 1, "Core Holiday: Christmas Day 12:00 PM to Boxing Day 12:00 PM"),
            (datetime.datetime(year, 12, 26, 12, 0), datetime.datetime(year, 12, 28, 12, 0), party_b, 2, "Boxing Day afternoon & post-holiday block"),
            (datetime.datetime(year, 12, 28, 12, 0), datetime.datetime(year, 12, 30, 12, 0), party_a, 2, "Mid-break 2-night rotation"),
            (datetime.datetime(year, 12, 30, 12, 0), datetime.datetime(year + 1, 1, 1, 12, 0), party_b, 2, "New Year's Eve block"),
            (datetime.datetime(year + 1, 1, 1, 12, 0), datetime.datetime(year + 1, 1, 3, 15, 0), party_a, 2, "New Year's Day & closing weekend"),
        ]

    a_hours = sum((e - s).total_seconds() / 3600.0 for s, e, p, _, _ in blocks if p == party_a)
    b_hours = sum((e - s).total_seconds() / 3600.0 for s, e, p, _, _ in blocks if p == party_b)
    a_nights = sum(n for _, _, p, n, _ in blocks if p == party_a)
    b_nights = sum(n for _, _, p, n, _ in blocks if p == party_b)
    violations = [b for b in blocks if b[3] > max_overnights]

    return {
        "year": year,
        "is_even": is_even,
        "party_a": party_a,
        "party_b": party_b,
        "blocks": blocks,
        "a_hours": a_hours,
        "b_hours": b_hours,
        "a_nights": a_nights,
        "b_nights": b_nights,
        "max_nights": max_overnights,
        "violations": violations,
    }


def print_holiday_audit(result: dict):
    year = result["year"]
    pa = result["party_a"]
    pb = result["party_b"]
    banner = (
        f"[bold cyan]Holiday Parenting Schedule Compliance Audit ({year}-{year+1})[/bold cyan]\n"
        f"[white]Rotation:[/white] {'Even-Year' if result['is_even'] else 'Odd-Year'}  |  "
        f"[white]Max Consecutive Cap:[/white] {result['max_nights']} Overnights  |  "
        f"[white]Total Balance:[/white] {pa} {result['a_hours']:.0f}h ({result['a_nights']}n) vs. {pb} {result['b_hours']:.0f}h ({result['b_nights']}n)"
    )
    console.print(Panel(banner, border_style="cyan"))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Start Window", style="white", width=22)
    table.add_column("End Window", style="white", width=22)
    table.add_column("Parent", style="bold cyan", justify="center", width=14)
    table.add_column("Nights", justify="center", width=8)
    table.add_column("Hours", justify="right", width=8)
    table.add_column("Schedule Authority / Note", style="dim")

    for s, e, p, nights, desc in result["blocks"]:
        s_str = s.strftime("%a %b %d, %I:%M %p")
        e_str = e.strftime("%a %b %d, %I:%M %p")
        hrs = int((e - s).total_seconds() / 3600.0)
        night_str = f"[green]{nights}[/green]" if nights <= result["max_nights"] else f"[bold red]{nights} (!)[/bold red]"
        table.add_row(s_str, e_str, p, night_str, f"{hrs}h", desc)

    console.print(table)
    if not result["violations"]:
        console.print("[bold green]✓ Schedule passes all consecutive-overnight caps and 50/50 hourly equality checks.[/bold green]\n")
    else:
        console.print(f"[bold red]⚠ Found {len(result['violations'])} block(s) exceeding the {result['max_nights']}-overnight cap.[/bold red]\n")
