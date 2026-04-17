#!/usr/bin/env python3
"""AKShare connectivity diagnostic tool.

Usage:
    python -m cli.akshare_init              # Run all checks
    python -m cli.akshare_init --test-only   # Test connection only
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()


def test_connection():
    """Test basic AKShare connectivity."""
    console.print("[bold cyan]Testing AKShare connection...[/bold cyan]")

    try:
        import akshare as ak

        console.print("[green]  AKShare module imported successfully[/green]")
        console.print(f"  Version: {ak.__version__}")
    except ImportError:
        console.print("[red]  AKShare not installed. Run: pip install akshare[/red]")
        return False
    except Exception as e:
        console.print(f"[red]  Failed to import AKShare: {e}[/red]")
        return False

    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            count = len(df)
            console.print(
                f"[green]  Fetched A-share stock list: {count} stocks[/green]"
            )

            table = Table(title="Sample Stocks")
            table.add_column("Code", style="cyan")
            table.add_column("Name", style="green")
            for _, row in df.head(5).iterrows():
                code = row.get("代码", row.iloc[0] if len(row.iloc) > 0 else "")
                name = row.get("名称", row.iloc[1] if len(row.iloc) > 1 else "")
                table.add_row(str(code), str(name))
            console.print(table)
        else:
            console.print("[yellow]  Fetched empty stock list[/yellow]")
    except Exception as e:
        console.print(f"[red]  Failed to fetch stock list: {e}[/red]")
        return False

    return True


def check_apis():
    """Check availability of key AKShare APIs."""
    console.print("\n[bold cyan]Checking key AKShare APIs...[/bold cyan]")

    apis = [
        ("stock_zh_a_spot_em", "A-share real-time quotes"),
        ("stock_zh_a_hist", "A-share historical data"),
        ("stock_individual_info_em", "Stock info"),
        ("stock_financial_abstract_ths", "Financial abstract"),
    ]

    import akshare as ak

    table = Table(title="API Availability")
    table.add_column("API", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Status", style="yellow")

    for api_name, description in apis:
        func = getattr(ak, api_name, None)
        if func is not None:
            table.add_row(api_name, description, "[green]Available[/green]")
        else:
            table.add_row(api_name, description, "[red]Not found[/red]")

    console.print(table)


def main():
    """Run AKShare diagnostics."""
    console.print("[bold]AKShare Connectivity Diagnostic[/bold]\n")

    test_only = "--test-only" in sys.argv

    connected = test_connection()
    if not connected:
        console.print("\n[red]AKShare connection failed.[/red]")
        sys.exit(1)

    if not test_only:
        check_apis()

    console.print("\n[green]AKShare diagnostic complete.[/green]")


if __name__ == "__main__":
    main()
