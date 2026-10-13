"""Command Line Interface for PropRisk Swarm."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from proprisk_swarm import __version__
from proprisk_swarm.config import get_settings

console = Console()


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show the version and exit.")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """PropRisk Swarm: Autonomous Multi-Agent Real Estate Underwriting & Risk Platform."""
    if version:
        console.print(f"[bold cyan]PropRisk Swarm[/bold cyan] version [green]{__version__}[/green]")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]PropRisk Swarm[/bold cyan] v{__version__}\n"
                "[white]Autonomous multi-agent real estate risk assessment & underwriting platform[/white]\n"
                "Use [yellow]--help[/yellow] for available commands.",
                title="PropRisk Swarm",
                border_style="cyan",
            )
        )


@cli.command("status")
def status_cmd() -> None:
    """Display current system status and active configuration."""
    settings = get_settings()

    table = Table(title="PropRisk Swarm Configuration", border_style="cyan")
    table.add_column("Subsystem", style="bold yellow")
    table.add_column("Key", style="dim")
    table.add_column("Value", style="green")

    table.add_row("Core", "Project Name", settings.project_name)
    table.add_row("Core", "Version", settings.version)
    table.add_row("Core", "Log Level", settings.log_level)
    table.add_row("Core", "Data Directory", str(settings.data_dir))

    table.add_row("MCP", "Deeds Endpoint", f"{settings.mcp.deeds_host}:{settings.mcp.deeds_port}")
    table.add_row("MCP", "SEC Endpoint", f"{settings.mcp.sec_host}:{settings.mcp.sec_port}")
    table.add_row(
        "MCP", "Zoning Endpoint", f"{settings.mcp.zoning_host}:{settings.mcp.zoning_port}"
    )

    table.add_row("RAG", "Vector Dimension", str(settings.rag.vector_dimension))
    table.add_row("RAG", "Embedding Model", settings.rag.embedding_model)
    table.add_row("RAG", "Hybrid Alpha", str(settings.rag.hybrid_alpha))
    table.add_row("RAG", "Graph Enabled", str(settings.rag.graph_enabled))

    table.add_row("Swarm", "Max Agents", str(settings.swarm.max_concurrent_agents))
    table.add_row("Swarm", "Timeout Sec", str(settings.swarm.task_timeout_seconds))
    table.add_row("Swarm", "Reflection Loops", str(settings.swarm.max_reflection_loops))
    table.add_row("Swarm", "Strict Audit", str(settings.swarm.strict_audit_mode))

    console.print(table)


@cli.command("mcp-servers")
def mcp_servers_cmd() -> None:
    """List registered Model Context Protocol (MCP) data source servers."""
    settings = get_settings()

    table = Table(title="Registered MCP Diligence Servers", border_style="cyan")
    table.add_column("Server", style="bold")
    table.add_column("Port", style="green")
    table.add_column("Endpoint", style="dim")
    table.add_column("Capability Scope", style="yellow")

    table.add_row(
        "Municipal Deeds",
        str(settings.mcp.deeds_port),
        f"http://{settings.mcp.deeds_host}:{settings.mcp.deeds_port}/mcp",
        "Conveyance history, transfer taxes, chain of title, metes and bounds",
    )
    table.add_row(
        "SEC EDGAR",
        str(settings.mcp.sec_port),
        f"http://{settings.mcp.sec_host}:{settings.mcp.sec_port}/mcp",
        "10-K, 10-Q, 8-K filings, tenant lease risks, credit events, REIT disclosures",
    )
    table.add_row(
        "Municipal Zoning",
        str(settings.mcp.zoning_port),
        f"http://{settings.mcp.zoning_host}:{settings.mcp.zoning_port}/mcp",
        "Floor Area Ratio (FAR), permissible uses, setback constraints, parking ratios",
    )

    console.print(table)


@cli.command("underwrite")
@click.option("--deal-id", required=True, help="Unique identifier for the property deal.")
@click.option("--asking-price", type=float, required=True, help="Initial asking price in USD.")
@click.option("--holding-period", type=int, default=5, help="Holding period in years.")
@click.option(
    "--execute", is_flag=True, default=False, help="Run live multi-agent diligence pipeline."
)
@click.option(
    "--store-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to DealStore persistence JSON.",
)
@click.option(
    "--export-sql",
    type=click.Path(path_type=Path),
    default=None,
    help="Export result to PostgreSQL SQL file.",
)
def underwrite_cmd(
    deal_id: str,
    asking_price: float,
    holding_period: int,
    execute: bool = False,
    store_path: Optional[Path] = None,
    export_sql: Optional[Path] = None,
) -> None:
    """Run an autonomous underwriting pipeline on a property deal."""
    console.print(
        f"[bold green]Starting underwriting pipeline for deal:[/bold green] [cyan]{deal_id}[/cyan]"
    )
    console.print(
        f"Target Price: [yellow]${asking_price:,.2f}[/yellow] | Period: [yellow]{holding_period} years[/yellow]"
    )
    console.print("[dim]Ingesting municipal deeds, SEC filings, and zoning restrictions...[/dim]")
    console.print("[dim]Synthesizing DCF cash flows and audit memo...[/dim]")

    if not execute:
        console.print(
            "[bold green]Scaffold pipeline execution initialized successfully.[/bold green]"
        )
        return

    from proprisk_swarm.agents.orchestrator import SwarmOrchestrator
    from proprisk_swarm.storage.deal_store import DealStore

    store = DealStore(persistence_path=store_path)
    if store_path and store_path.exists():
        try:
            store.load_from_disk()
        except Exception:
            pass

    orchestrator = SwarmOrchestrator(deal_store=store)
    result = orchestrator.run_diligence_pipeline(
        deal_id=deal_id,
        deal_payload={
            "deal_id": deal_id,
            "target_purchase_price": asking_price,
            "holding_period": holding_period,
            "in_place_noi": asking_price * 0.065,
        },
    )

    if result.get("is_valid"):
        pkg = result["package"]
        store.import_deal_package(pkg)
        if store_path:
            store.save_to_disk()

        rec = pkg.get("memo", {}).get("recommendation", "UNKNOWN")
        console.print(
            f"[bold green]Swarm underwriting completed successfully. Recommendation: [cyan]{rec}[/cyan][/bold green]"
        )

        if export_sql:
            sql = store.export_to_sql(deal_id)
            export_sql.write_text(sql, encoding="utf-8")
            console.print(
                f"[bold green]PostgreSQL SQL script exported to [yellow]{export_sql}[/yellow][/bold green]"
            )
    else:
        console.print(
            f"[bold red]Validation failed: {result.get('validation', {}).get('errors')}[/bold red]"
        )


@cli.command("export-sql")
@click.option("--deal-id", required=True, help="Unique identifier for the property deal.")
@click.option(
    "--store-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to DealStore persistence JSON.",
)
@click.option("--schema", default="public", help="PostgreSQL schema name.")
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), default=None, help="Output .sql file path."
)
def export_sql_cmd(
    deal_id: str,
    store_path: Optional[Path] = None,
    schema: str = "public",
    output: Optional[Path] = None,
) -> None:
    """Export deal underwriting package to PostgreSQL DDL and INSERT/UPSERT SQL script."""
    from proprisk_swarm.storage.deal_store import DealStore

    store = DealStore(persistence_path=store_path)
    if store_path and store_path.exists():
        try:
            store.load_from_disk()
        except Exception as exc:
            raise click.ClickException(f"Failed to load DealStore from {store_path}: {exc}")

    if not store.get_deal(deal_id):
        raise click.ClickException(f"Deal '{deal_id}' not found in DealStore.")

    try:
        sql = store.export_to_sql(deal_id, schema=schema)
    except Exception as exc:
        raise click.ClickException(f"Export to SQL failed: {exc}")

    if output:
        output.write_text(sql, encoding="utf-8")
        console.print(
            f"[bold green]Successfully exported PostgreSQL SQL script for deal [cyan]{deal_id}[/cyan] to [yellow]{output}[/yellow][/bold green]"
        )
    else:
        click.echo(sql)


@cli.command("validate-export")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional output path for cleaned JSON.",
)
def validate_export_cmd(input_file: Path, output: Optional[Path] = None) -> None:
    """Clean and validate raw deal export JSON against schema."""
    from proprisk_swarm.storage.deal_store import DealStore

    try:
        raw_data = json.loads(input_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise click.ClickException(f"Failed to read input JSON file: {exc}")

    res = DealStore.clean_and_validate_raw_export(raw_data)

    if not res["is_valid"]:
        console.print(f"[bold red]Validation failed with {len(res['errors'])} error(s):[/bold red]")
        for err in res["errors"]:
            console.print(f"[red]  • {err}[/red]")
        raise click.ClickException("Export validation failed.")

    console.print("[bold green]Export successfully cleaned and validated.[/bold green]")
    cleaned = res["cleaned_data"]
    table = Table(title="Cleaned Export Details", border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value", style="green")
    table.add_row("Deal ID", str(cleaned.get("deal_id")))
    table.add_row("Title", str(cleaned.get("deal", {}).get("title", "N/A")))
    table.add_row(
        "Target Price", f"${cleaned.get('deal', {}).get('target_purchase_price', 0):,.2f}"
    )
    table.add_row("Deeds Records", str(len(cleaned.get("deeds", []))))
    table.add_row("SEC Filings", str(len(cleaned.get("filings", []))))
    console.print(table)

    if res.get("warnings"):
        for warn in res["warnings"]:
            console.print(f"[yellow]Warning: {warn}[/yellow]")

    if output:
        output.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
        console.print(f"[dim]Cleaned data written to {output}[/dim]")
