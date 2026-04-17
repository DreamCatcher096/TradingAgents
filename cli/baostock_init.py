#!/usr/bin/env python3
"""BaoStock connectivity diagnostic tool.

Usage:
    python -m cli.baostock_init              # Run all checks
    python -m cli.baostock_init --test-only   # Test login only
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()


def test_connection():
    """Test BaoStock login/logout cycle."""
    console.print("[bold cyan]Testing BaoStock connection...[/bold cyan]")

    try:
        import baostock as bs

        console.print("  BaoStock module imported successfully")
    except ImportError:
        console.print("[red]  BaoStock not installed. Run: pip install baostock[/red]")
        return False

    try:
        result = bs.login()
        if result.error_code != "0":
            console.print(f"[red]  Login failed: {result.error_msg}[/red]")
            return False

        console.print("[green]  Login successful[/green]")

        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            rs = bs.query_history_k_data_plus(
                "sh.600036",
                "date,code,open,high,low,close,volume",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3",
            )

            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())

            if rows:
                console.print(
                    f"[green]  Data retrieval OK: {len(rows)} rows for 600036 (招商银行)[/green]"
                )
            else:
                console.print(
                    "[yellow]  Query returned no data (possibly market holiday)[/yellow]"
                )
                console.print(f"  Query error: {rs.error_msg}")
        finally:
            bs.logout()
            console.print("  Logout successful")

    except Exception as e:
        console.print(f"[red]  Connection test failed: {e}[/red]")
        return False

    return True


def check_stock_list():
    """Verify stock list retrieval."""
    console.print("\n[bold cyan]Checking stock list retrieval...[/bold cyan]")

    try:
        import baostock as bs

        bs.login()
        try:
            rs = bs.query_stock_basic()
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())

            if rows:
                console.print(f"[green]  Fetched {len(rows)} stock entries[/green]")

                table = Table(title="Sample Stocks")
                table.add_column("Code", style="cyan")
                table.add_column("Name", style="green")
                for row in rows[:5]:
                    code = row[0] if len(row) > 0 else ""
                    name = row[1] if len(row) > 1 else ""
                    table.add_row(str(code), str(name))
                console.print(table)
            else:
                console.print(f"[yellow]  Empty stock list: {rs.error_msg}[/yellow]")
        finally:
            bs.logout()

    except Exception as e:
        console.print(f"[red]  Stock list check failed: {e}[/red]")


def main():
    """Run BaoStock diagnostics."""
    console.print("[bold]BaoStock Connectivity Diagnostic[/bold]\n")

    test_only = "--test-only" in sys.argv

    connected = test_connection()
    if not connected:
        console.print("\n[red]BaoStock connection failed.[/red]")
        sys.exit(1)

    if not test_only:
        check_stock_list()

    console.print("\n[green]BaoStock diagnostic complete.[/green]")


if __name__ == "__main__":
    main()
