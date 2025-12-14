"""
RUGA CLI - Command-line interface for RUGA server.
"""

import click
import os
import sys
from pathlib import Path
from typing import Optional
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.markdown import Markdown
import time

from .api_client import RugaAPIClient

console = Console()

# Default server URL from environment or default
DEFAULT_SERVER_URL = os.getenv("RUGA_SERVER_URL", "http://localhost:8000")


def get_client(server_url: Optional[str] = None) -> RugaAPIClient:
    """Get API client with configured server URL."""
    url = server_url or DEFAULT_SERVER_URL
    return RugaAPIClient(base_url=url)


def print_banner():
    """Print RUGA CLI banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██████╗ ██╗   ██╗ ██████╗  █████╗                         ║
║     ██╔══██╗██║   ██║██╔════╝ ██╔══██╗                        ║
║     ██████╔╝██║   ██║██║  ███╗███████║                        ║
║     ██╔══██╗██║   ██║██║   ██║██╔══██║                        ║
║     ██║  ██║╚██████╔╝╚██████╔╝██║  ██║                        ║
║     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝                        ║
║                                                               ║
║          Command-Line Interface v0.1.0                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


@click.group(invoke_without_command=True)
@click.option(
    "--server-url",
    default=None,
    envvar="RUGA_SERVER_URL",
    help="RUGA server URL (default: http://localhost:8000 or RUGA_SERVER_URL env var)",
)
@click.pass_context
def cli(ctx, server_url):
    """RUGA CLI - Command-line interface for RUGA file analysis and organization."""
    ctx.ensure_object(dict)
    ctx.obj["server_url"] = server_url or DEFAULT_SERVER_URL
    
    # Show banner and help if no command provided
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("\n[bold]Usage:[/bold] ruga [OPTIONS] COMMAND [ARGS]...\n")
        console.print("[bold]Commands:[/bold]")
        console.print("  [cyan]info[/cyan]              Show API information and available endpoints")
        console.print("  [cyan]files[/cyan]             File operations")
        console.print("  [cyan]analyze[/cyan]           Analysis operations")
        console.print("  [cyan]jobs[/cyan]              Job management operations")
        console.print("  [cyan]organize[/cyan]          Folder organization operations")
        console.print("  [cyan]chat[/cyan]              Chat with documents using RAG\n")
        console.print("[bold]Options:[/bold]")
        console.print("  [yellow]--server-url[/yellow] TEXT  RUGA server URL\n")
        console.print("[bold]Examples:[/bold]")
        console.print("  [green]ruga info[/green]")
        console.print("  [green]ruga files list ./examples/unstructured_folder[/green]")
        console.print("  [green]ruga analyze folder ./examples/unstructured_folder[/green]")
        console.print("  [green]ruga chat \"What documents discuss survival analysis?\"[/green]\n")
        console.print("Run [cyan]ruga COMMAND --help[/cyan] for more information on a command.\n")


@cli.command()
@click.pass_context
def info(ctx):
    """Show API information and available endpoints."""
    try:
        client = get_client(ctx.obj["server_url"])
        info_data = client.get_info()
        client.close()
        
        # ASCII Art Banner
        ascii_banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██████╗ ██╗   ██╗ ██████╗  █████╗                         ║
║     ██╔══██╗██║   ██║██╔════╝ ██╔══██╗                        ║
║     ██████╔╝██║   ██║██║  ███╗███████║                        ║
║     ██╔══██╗██║   ██║██║   ██║██╔══██║                        ║
║     ██║  ██║╚██████╔╝╚██████╔╝██║  ██║                        ║
║     ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝                        ║
║                                                               ║
║          File Analysis & Organization Platform                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
        console.print(ascii_banner, style="bold cyan")
        
        # Server info panel
        server_info = Panel(
            f"[bold]Version:[/bold] {info_data.get('version', 'unknown')}\n"
            f"[bold]Status:[/bold] [green]✓ Connected[/green]\n"
            f"[bold]Server:[/bold] {ctx.obj['server_url']}\n"
            f"[bold]Message:[/bold] {info_data.get('message', '')}",
            title="[bold cyan]Server Information[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(server_info)
        console.print()
        
        if "endpoints" in info_data:
            table = Table(title="[bold magenta]Available Endpoints[/bold magenta]", show_header=True, header_style="bold magenta")
            table.add_column("Endpoint", style="cyan", no_wrap=True)
            table.add_column("Description", style="green")
            
            for endpoint, description in info_data["endpoints"].items():
                table.add_row(endpoint, description)
            
            console.print(table)
            console.print()
    except Exception as e:
        console.print(f"\n[red]❌ Error:[/red] {e}")
        console.print(f"[yellow]Make sure the RUGA server is running at {ctx.obj['server_url']}[/yellow]")
        sys.exit(1)


@cli.group()
def files():
    """File operations."""
    pass


@files.command("list")
@click.argument("root_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.pass_context
def list_files(ctx, root_path):
    """List all files and folders recursively with .ruga status."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        with console.status(f"[bold green]Listing files in {root_path}..."):
            response = client.list_files(str(root_path.absolute()))
        
        client.close()
        
        files_list = response.get("files", [])
        root_path_str = response.get("root_path", str(root_path))
        
        console.print(f"\n[bold cyan]Files in {root_path_str}[/bold cyan]")
        console.print(f"Total items: {len(files_list)}\n")
        
        # Group by directory
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Path", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Has .ruga", style="green")
        table.add_column("Size", style="blue")
        
        for file_info in files_list:
            path = file_info.get("path", "")
            is_dir = file_info.get("is_directory", False)
            has_ruga = file_info.get("has_ruga", False)
            size = file_info.get("size")
            
            file_type = "📁 Directory" if is_dir else "📄 File"
            ruga_status = "✓" if has_ruga else "✗"
            size_str = f"{size:,} bytes" if size else "-"
            
            table.add_row(path, file_type, ruga_status, size_str)
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.group()
def analyze():
    """Analysis operations."""
    pass


@analyze.command("folder")
@click.argument("root_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.pass_context
def analyze_folder(ctx, root_path):
    """Start analyzing all files in a folder."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        with console.status(f"[bold green]Starting folder analysis for {root_path}..."):
            response = client.analyze_folder(str(root_path.absolute()))
        
        client.close()
        
        job_id = response.get("job_id")
        message = response.get("message", "")
        files_queued = response.get("files_queued", 0)
        
        console.print(f"\n[bold green]✓ Analysis started[/bold green]")
        console.print(f"Job ID: [cyan]{job_id}[/cyan]")
        console.print(f"Message: {message}")
        console.print(f"Files queued: [yellow]{files_queued}[/yellow]")
        console.print(f"\nUse [cyan]ruga jobs list[/cyan] to check status")
        console.print(f"Use [cyan]ruga jobs get {job_id}[/cyan] for details")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@analyze.command("file")
@click.argument("file_path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
@click.option("--root-path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), help="Root directory (optional)")
@click.pass_context
def analyze_file(ctx, file_path, root_path):
    """Start analyzing a single file."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        root_path_str = str(root_path.absolute()) if root_path else None
        
        with console.status(f"[bold green]Starting file analysis for {file_path}..."):
            response = client.analyze_file(str(file_path.absolute()), root_path_str)
        
        client.close()
        
        job_id = response.get("job_id")
        message = response.get("message", "")
        
        console.print(f"\n[bold green]✓ Analysis started[/bold green]")
        console.print(f"Job ID: [cyan]{job_id}[/cyan]")
        console.print(f"Message: {message}")
        console.print(f"\nUse [cyan]ruga jobs get {job_id}[/cyan] for details")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.group()
def jobs():
    """Job management operations."""
    pass


@jobs.command("list")
@click.option("--include-file-statuses", is_flag=True, help="Include individual file statuses")
@click.pass_context
def list_jobs(ctx, include_file_statuses):
    """List all analysis jobs."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        with console.status("[bold green]Fetching jobs..."):
            response = client.list_jobs(include_file_statuses=include_file_statuses)
        
        client.close()
        
        jobs_list = response.get("jobs", [])
        
        if not jobs_list:
            console.print("\n[yellow]No jobs found[/yellow]")
            return
        
        console.print(f"\n[bold cyan]Analysis Jobs[/bold cyan]")
        console.print(f"Total jobs: {len(jobs_list)}\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Job ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Files", style="blue")
        table.add_column("Created", style="magenta")
        
        for job in jobs_list:
            job_id = job.get("job_id", "")[:8]  # Short ID
            job_type = job.get("job_type", "")
            status = job.get("status", "")
            files_queued = job.get("files_queued", 0)
            files_processed = job.get("files_processed", 0)
            files_failed = job.get("files_failed", 0)
            created_at = job.get("created_at", "")
            
            files_str = f"{files_processed}/{files_queued}"
            if files_failed > 0:
                files_str += f" ({files_failed} failed)"
            
            # Format created_at
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                created_str = created_at[:19] if len(created_at) > 19 else created_at
            
            # Color status
            status_color = {
                "analyzed": "green",
                "in_process": "yellow",
                "error": "red",
                "pending": "blue",
            }.get(status, "white")
            
            table.add_row(
                job_id,
                job_type,
                f"[{status_color}]{status}[/{status_color}]",
                files_str,
                created_str,
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@jobs.command("get")
@click.argument("job_id")
@click.pass_context
def get_job(ctx, job_id):
    """Get detailed information about a specific job."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        with console.status(f"[bold green]Fetching job {job_id}..."):
            job = client.get_job(job_id)
        
        client.close()
        
        console.print(f"\n[bold cyan]Job Details[/bold cyan]\n")
        
        # Basic info
        console.print(f"Job ID: [cyan]{job.get('job_id')}[/cyan]")
        console.print(f"Type: [yellow]{job.get('job_type')}[/yellow]")
        console.print(f"Status: [green]{job.get('status')}[/green]")
        console.print(f"Root Path: {job.get('root_path')}")
        console.print(f"Target Path: {job.get('target_path')}")
        console.print(f"Files Queued: {job.get('files_queued')}")
        console.print(f"Files Processed: {job.get('files_processed')}")
        console.print(f"Files Failed: {job.get('files_failed')}")
        console.print(f"Created: {job.get('created_at')}")
        
        if job.get("error_message"):
            console.print(f"\n[red]Error:[/red] {job.get('error_message')}")
        
        # File statuses
        file_statuses = job.get("file_statuses")
        if file_statuses:
            console.print(f"\n[bold cyan]File Statuses[/bold cyan]\n")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("File Path", style="cyan")
            table.add_column("Status", style="green")
            
            for file_path, status in file_statuses.items():
                status_color = {
                    "analyzed": "green",
                    "in_process": "yellow",
                    "error": "red",
                    "pending": "blue",
                }.get(status, "white")
                table.add_row(file_path, f"[{status_color}]{status}[/{status_color}]")
            
            console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.group()
def organize():
    """Folder organization operations."""
    pass


@organize.command("generate")
@click.argument("root_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.pass_context
def generate_structure(ctx, root_path):
    """Generate an organized folder structure suggestion."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        with console.status(f"[bold green]Generating folder structure for {root_path}..."):
            response = client.generate_structure(str(root_path.absolute()))
        
        client.close()
        
        structure_id = response.get("structure_id")
        structure = response.get("structure", {})
        total_files = response.get("total_files", 0)
        
        console.print(f"\n[bold green]✓ Structure generated[/bold green]")
        console.print(f"Structure ID: [cyan]{structure_id}[/cyan]")
        console.print(f"Total files: [yellow]{total_files}[/yellow]\n")
        
        # Show structure details
        console.print(f"[bold cyan]Root Folder:[/bold cyan] {structure.get('root_folder_name', '')}")
        console.print(f"[bold cyan]Rationale:[/bold cyan] {structure.get('organization_rationale', '')}\n")
        
        # Show folders to create
        folders = structure.get("folders", [])
        if folders:
            console.print(f"[bold cyan]Folders to create ({len(folders)}):[/bold cyan]")
            for folder in folders[:10]:  # Show first 10
                console.print(f"  • {folder}")
            if len(folders) > 10:
                console.print(f"  ... and {len(folders) - 10} more")
        
        # Show file moves
        file_moves = structure.get("file_moves", [])
        if file_moves:
            console.print(f"\n[bold cyan]File moves ({len(file_moves)}):[/bold cyan]")
            for move in file_moves[:5]:  # Show first 5
                console.print(f"  • {move.get('source_path')} → {move.get('destination_path')}")
            if len(file_moves) > 5:
                console.print(f"  ... and {len(file_moves) - 5} more")
        
        console.print(f"\nUse [cyan]ruga organize apply {structure_id}[/cyan] to apply this structure")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@organize.command("apply")
@click.argument("structure_id")
@click.option("--dry-run", is_flag=True, help="Show what would be done without actually copying files")
@click.pass_context
def apply_structure(ctx, structure_id, dry_run):
    """Apply a folder structure."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        action = "Previewing" if dry_run else "Applying"
        with console.status(f"[bold green]{action} folder structure {structure_id}..."):
            response = client.apply_structure(structure_id, dry_run=dry_run)
        
        client.close()
        
        new_root_path = response.get("new_root_path", "")
        files_copied = response.get("files_copied", 0)
        folders_created = response.get("folders_created", 0)
        errors = response.get("errors", [])
        
        if dry_run:
            console.print(f"\n[bold yellow]Preview (dry run)[/bold yellow]")
        else:
            console.print(f"\n[bold green]✓ Structure applied[/bold green]")
        
        console.print(f"New root path: [cyan]{new_root_path}[/cyan]")
        console.print(f"Files copied: [yellow]{files_copied}[/yellow]")
        console.print(f"Folders created: [yellow]{folders_created}[/yellow]")
        
        if errors:
            console.print(f"\n[red]Errors ({len(errors)}):[/red]")
            for error in errors[:10]:
                console.print(f"  • {error}")
            if len(errors) > 10:
                console.print(f"  ... and {len(errors) - 10} more")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@organize.command("all")
@click.argument("root_path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option("--no-wait", is_flag=True, help="Don't wait for analysis to complete")
@click.option("--max-wait-seconds", default=300, help="Maximum seconds to wait for analysis")
@click.pass_context
def organize_all(ctx, root_path, no_wait, max_wait_seconds):
    """Analyze, generate structure, and apply in one call."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        wait_for_analysis = not no_wait
        
        with console.status(f"[bold green]Organizing folder {root_path}..."):
            response = client.organize_all(
                str(root_path.absolute()),
                wait_for_analysis=wait_for_analysis,
                max_wait_seconds=max_wait_seconds,
            )
        
        client.close()
        
        analysis_job_id = response.get("analysis_job_id", "")
        structure_id = response.get("structure_id", "")
        new_root_path = response.get("new_root_path", "")
        files_analyzed = response.get("files_analyzed", 0)
        files_organized = response.get("files_organized", 0)
        folders_created = response.get("folders_created", 0)
        analysis_status = response.get("analysis_status", "")
        errors = response.get("errors", [])
        
        console.print(f"\n[bold green]✓ Organization complete[/bold green]")
        console.print(f"Analysis Job ID: [cyan]{analysis_job_id}[/cyan]")
        console.print(f"Structure ID: [cyan]{structure_id}[/cyan]")
        console.print(f"New root path: [cyan]{new_root_path}[/cyan]")
        console.print(f"Files analyzed: [yellow]{files_analyzed}[/yellow]")
        console.print(f"Files organized: [yellow]{files_organized}[/yellow]")
        console.print(f"Folders created: [yellow]{folders_created}[/yellow]")
        console.print(f"Analysis status: [green]{analysis_status}[/green]")
        
        if errors:
            console.print(f"\n[red]Errors ({len(errors)}):[/red]")
            for error in errors:
                console.print(f"  • {error}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("message")
@click.option("--history", help="Path to JSON file with conversation history")
@click.pass_context
def chat(ctx, message, history):
    """Chat with documents using RAG."""
    try:
        client = get_client(ctx.obj["server_url"])
        
        conversation_history = None
        if history:
            history_path = Path(history)
            if history_path.exists():
                with open(history_path, 'r') as f:
                    history_data = json.load(f)
                    conversation_history = history_data.get("messages", [])
        
        console.print(f"\n[bold cyan]You:[/bold cyan] {message}\n")
        console.print("[bold green]Assistant:[/bold green] ", end="")
        
        full_response = ""
        for chunk in client.chat(message, conversation_history):
            chunk_type = chunk.get("type", "")
            content = chunk.get("content", "")
            
            if chunk_type == "ai":
                console.print(content, end="", style="white")
                full_response += content
            elif chunk_type == "error":
                console.print(f"\n[red]Error:[/red] {content}")
            elif chunk_type == "done":
                console.print()  # New line
        
        client.close()
        
        if full_response:
            console.print()  # Final new line
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
