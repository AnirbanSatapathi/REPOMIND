import typer
from repomind.loader import Loader
from repomind.scanner import Scanner
from repomind.parser import Parser
from repomind.graph_builder import GraphBuilder

app = typer.Typer(help="RepoMind: AI Codebase Understanding & Visualization Engine")

loader = Loader()
scanner = Scanner()
parser = Parser()
graph_builder = GraphBuilder()

def display_scan_results(result: dict):
    typer.echo("\nRepository Analysis")
    typer.echo("------------------")
    stats = result.get("stats", {})
    typer.echo(f"Code files: {stats.get('code_files', 0)}")
    typer.echo(f"Config files: {stats.get('config_files', 0)}")
    typer.echo(f"Infra files: {stats.get('infra_files', 0)}")
    typer.echo(f"Docs: {stats.get('docs', 0)}")

    if result["languages"]:
        typer.echo("\nLanguages:")
        for lang, count in result["languages"].items():
            typer.echo(f"  {lang}: {count}")
    else:
        typer.echo("\nNo code files found.")

@app.command()
def analyze(repo_url: str = typer.Argument(..., help="URL of the repository to analyze")):
    try:
        local_path = loader.clone_repo(repo_url)
        typer.echo("Repository cloned successfully")
    except Exception as e:
        typer.echo(f"Error cloning repository: {e}")
        raise typer.Exit(code=1)

    typer.echo("\nScanning repository...")
    try:
        result = scanner.scan_repo(local_path)
    except Exception as e:
        typer.echo(f"Error scanning repository: {e}")
        raise typer.Exit(code=1)
    
    display_scan_results(result)

    typer.echo("\nParsing code files...")
    parsed_data = parser.parse_repo(result.get("code_files", []))
    typer.echo(f"Successfully parsed {len(parsed_data)} files.")
    
    typer.echo("\nBuilding dependency graph...")
    graph = graph_builder.build_graph(parsed_data)
    edges_count = sum(len(deps) for deps in graph.values())
    typer.echo(f"Graph built with {len(graph)} nodes and {edges_count} edges.")

    # Temp: Display sample of the graph
    typer.echo("\n--- SAMPLE GRAPH ---")
    for k, v in list(graph.items())[:10]:
        typer.echo(k)
        for dep in v:
            typer.echo(f"   -> {dep}")

@app.command()
def scan(local_path: str = typer.Argument(..., help="Path to the local repository")):
    try:
        repo_path = loader.load_local_repo(local_path)
    except Exception as e:
        typer.echo(f"Invalid repository path: {e}")
        raise typer.Exit(code=1)
        
    typer.echo("\nScanning repository...")
    try:
        result = scanner.scan_repo(repo_path)
    except Exception as e:
        typer.echo(f"Error scanning repository: {e}")
        raise typer.Exit(code=1)

    display_scan_results(result)
    
    typer.echo("\nParsing code files...")
    parsed_data = parser.parse_repo(result.get("code_files", []))
    typer.echo(f"Successfully parsed {len(parsed_data)} files.")

    typer.echo("\nBuilding dependency graph...")
    graph = graph_builder.build_graph(parsed_data)
    edges_count = sum(len(deps) for deps in graph.values())
    typer.echo(f"Graph built with {len(graph)} nodes and {edges_count} edges.")

    # Temp: Display sample of the graph
    # typer.echo("\n--- SAMPLE GRAPH ---")
    # for k, v in list(graph.items())[:10]:
    #     typer.echo(k)
    #     for dep in v:
    #         typer.echo(f"   -> {dep}")


@app.command()
def info():
    typer.echo("RepoMind")
    typer.echo("AI Codebase Understanding & Visualization Engine")
    typer.echo("")
    typer.echo("Commands:")
    typer.echo("  repomind analyze <repo_url>")
    typer.echo("  repomind scan <local_path>")

if __name__ == "__main__":
    app()