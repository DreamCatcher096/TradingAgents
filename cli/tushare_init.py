#!/usr/bin/env python3
"""Tushare token validation tool.

Usage:
    python -m cli.tushare_init              # Validate token
    python -m cli.tushare_init --test-only   # Test connection only
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()


def test_connection():
    """Test Tushare connection with token from environment."""
    console.print("[bold cyan]Testing Tushare connection...[/bold cyan]")

    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        console.print("[red]  TUSHARE_TOKEN not set in environment or .env file[/red]")
        console.print("  Get a token from https://tushare.pro and set TUSHARE_TOKEN")
        return False

    console.print(f"  Token found: {token[:8]}...{token[-4:]}")

    try:
        import tushare as ts

        console.print(f"  Tushare module imported (version: {ts.__version__})")
    except ImportError:
        console.print("[red]  Tushare not installed. Run: pip install tushare[/red]")
        return False

    try:
        ts.set_token(token)
        api = ts.pro_api()

        df = api.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry",
        )

        if df is not None and not df.empty:
            count = len(df)
            console.print(
                f"[green]  Token valid. Fetched {count} listed stocks[/green]"
            )

            from rich.table import Table

            table = Table(title="Sample Stocks")
            table.add_column("Code", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Industry", style="yellow")
            for _, row in df.head(5).iterrows():
                table.add_row(
                    str(row.get("ts_code", "")),
                    str(row.get("name", "")),
                    str(row.get("industry", "")),
                )
            console.print(table)
        else:
            console.print("[yellow]  Token accepted but returned empty data[/yellow]")
            return True

    except Exception as e:
        error_msg = str(e).lower()
        if "token" in error_msg or "auth" in error_msg or "limit" in error_msg:
            console.print(f"[red]  Token invalid or rate limited: {e}[/red]")
        else:
            console.print(f"[red]  API call failed: {e}[/red]")
        return False

    return True


def main():
    """Run Tushare diagnostics."""
    console.print("[bold]Tushare Token Validation[/bold]\n")

    connected = test_connection()
    if not connected:
        console.print("\n[red]Tushare connection failed.[/red]")
        sys.exit(1)

    console.print("\n[green]Tushare validation complete.[/green]")


if __name__ == "__main__":
    main()
