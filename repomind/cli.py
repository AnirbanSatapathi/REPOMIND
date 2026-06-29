import typer
from pathlib import Path
from repomind.loader import Loader
from repomind.scanner import Scanner
from repomind.parser import Parser
from repomind.graph_builder import GraphBuilder
from repomind.visualizer import Visualizer
from repomind.qa_engine import QAEngine
from repomind.call_graph import CallGraphExtractor, generate_call_graph_summary
from repomind.arch_summary import generate_architecture_summary

app = typer.Typer(help="RepoMind: AI Codebase Understanding & Visualization Engine")

loader = Loader()
scanner = Scanner()
parser = Parser()
graph_builder = GraphBuilder()
visualizer = Visualizer()

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
def analyze(
    repo_url: str = typer.Argument(..., help="URL of the repository to analyze"),
    graph: bool = typer.Option(False, "--graph", help="Generate a dependency graph visualization")
):
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
    graph_data = graph_builder.build_graph(parsed_data)
    edges_count = sum(len(deps) for deps in graph_data.values())
    typer.echo(f"Graph built with {len(graph_data)} nodes and {edges_count} edges.")
    
    if graph:
        typer.echo("\nGenerating visualization...")
        # Try SVG first
        svg_path = visualizer.generate_graph(graph_data, local_path)
        typer.echo(f"Graph representation: {svg_path}")
        
        # Always generate Mermaid for easy viewing in Markdown
        mermaid_path = visualizer.generate_mermaid(graph_data, local_path)
        typer.echo(f"Mermaid diagram saved to: {mermaid_path}")

    # Temp: Display sample of the graph
    # typer.echo("\n--- SAMPLE GRAPH ---")
    # for k, v in list(graph_data.items())[:10]:
    #     typer.echo(k)
    #     for dep in v:
    #         typer.echo(f"   -> {dep}")

@app.command()
def scan(
    local_path: str = typer.Argument(..., help="Path to the local repository"),
    graph: bool = typer.Option(False, "--graph", help="Generate a dependency graph visualization")
):
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
    graph_data = graph_builder.build_graph(parsed_data)
    edges_count = sum(len(deps) for deps in graph_data.values())
    typer.echo(f"Graph built with {len(graph_data)} nodes and {edges_count} edges.")

    if graph:
        typer.echo("\nGenerating visualization...")
        # Try SVG first
        svg_path = visualizer.generate_graph(graph_data, repo_path)
        typer.echo(f"Graph representation: {svg_path}")
        
        # Always generate Mermaid for easy viewing in Markdown
        mermaid_path = visualizer.generate_mermaid(graph_data, repo_path)
        typer.echo(f"Mermaid diagram saved to: {mermaid_path}")

    # Temp: Display sample of the graph
    # typer.echo("\n--- SAMPLE GRAPH ---")
    # for k, v in list(graph_data.items())[:10]:
    #     typer.echo(k)
    #     for dep in v:
    #         typer.echo(f"   -> {dep}")


@app.command()
def index(
    local_path: str = typer.Argument(..., help="Path to the local repository to index"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild the index from scratch"),
):
    """Index a repository for semantic code search. Chunks code, generates embeddings, and stores in FAISS."""
    try:
        repo_path = loader.load_local_repo(local_path)
    except Exception as e:
        typer.echo(f"Invalid repository path: {e}")
        raise typer.Exit(code=1)

    typer.echo("\nScanning repository...")
    result = scanner.scan_repo(repo_path)
    display_scan_results(result)

    typer.echo("\nParsing code files...")
    parsed_data = parser.parse_repo(result.get("code_files", []))
    typer.echo(f"Successfully parsed {len(parsed_data)} files.")

    qa = QAEngine()
    if rebuild:
        import shutil
        from pathlib import Path
        idx_path = Path(".repomind/indexes")
        if idx_path.exists():
            shutil.rmtree(idx_path)
            typer.echo("Removed existing index.")

    typer.echo("\nIndexing repository (this may take a few minutes)...")
    try:
        qa.index_repo(parsed_data)
        typer.echo("Indexing complete!")
    except Exception as e:
        typer.echo(f"Error indexing repository: {e}")
        raise typer.Exit(code=1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top-k", help="Number of results to return"),
):
    """Search the indexed codebase for relevant code chunks."""
    qa = QAEngine()
    try:
        results = qa.search(query, top_k=top_k)
    except RuntimeError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)

    if not results:
        typer.echo("No results found.")
        return

    typer.echo(f"\nTop {len(results)} results for: '{query}'\n")
    for i, r in enumerate(results, 1):
        typer.echo(f"{'='*60}")
        typer.echo(f"Result {i} (score: {r['score']:.4f})")
        typer.echo(f"File: {r['file_path']}")
        typer.echo(f"Type: {r['chunk_type']}: {r['name']}")
        typer.echo(f"Lines: {r['start_line']}-{r['end_line']}")
        typer.echo(f"{'─'*40}")
        # Show first few lines of context
        lines = r['text'].splitlines()
        preview = lines[:10]
        typer.echo("\n".join(preview))
        if len(lines) > 10:
            typer.echo(f"... ({len(lines) - 10} more lines)")
        typer.echo("")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about the codebase"),
    top_k: int = typer.Option(5, "--top-k", help="Number of context chunks to retrieve"),
):
    """Ask an AI question about the indexed codebase using RAG with Ollama."""
    qa = QAEngine()
    typer.echo(f"\nQuerying codebase for: '{question}'\n")

    try:
        answer = qa.ask(question, top_k=top_k)
        typer.echo(answer)
    except RuntimeError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Error querying Ollama: {e}")
        raise typer.Exit(code=1)



@app.command()
def callgraph(
    local_path: str = typer.Argument(..., help="Path to the local repository"),
):
    """Extract function-to-function call relationships and generate a call graph."""
    try:
        repo_path = loader.load_local_repo(local_path)
    except Exception as e:
        typer.echo(f"Invalid repository path: {e}")
        raise typer.Exit(code=1)

    typer.echo("\nScanning repository...")
    result = scanner.scan_repo(repo_path)
    display_scan_results(result)

    typer.echo("\nParsing code files...")
    parsed_data = parser.parse_repo(result.get("code_files", []))
    typer.echo(f"Successfully parsed {len(parsed_data)} files.")

    typer.echo("\nExtracting call graph...")
    extractor = CallGraphExtractor()
    cg = extractor.extract_call_graph(parsed_data)

    summary = generate_call_graph_summary(cg)
    typer.echo(summary)

    # Save to file
    output_dir = Path(".repomind/graphs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "call_graph.md"
    output_path.write_text(summary, encoding="utf-8")
    typer.echo(f"Call graph saved to: {output_path}")


@app.command()
def arch(
    local_path: str = typer.Argument(..., help="Path to the local repository"),
):
    """Generate a high-level architecture summary of the repository."""
    try:
        repo_path = loader.load_local_repo(local_path)
    except Exception as e:
        typer.echo(f"Invalid repository path: {e}")
        raise typer.Exit(code=1)

    typer.echo("\nScanning repository...")
    result = scanner.scan_repo(repo_path)
    display_scan_results(result)

    typer.echo("\nParsing code files...")
    parsed_data = parser.parse_repo(result.get("code_files", []))
    typer.echo(f"Successfully parsed {len(parsed_data)} files.")

    typer.echo("\nBuilding dependency graph...")
    dep_graph = graph_builder.build_graph(parsed_data)
    typer.echo(f"Graph built with {len(dep_graph)} nodes.")

    typer.echo("\nExtracting call graph...")
    extractor = CallGraphExtractor()
    cg = extractor.extract_call_graph(parsed_data)
    typer.echo(f"Call graph: {len(cg)} files with calls.")

    typer.echo("\nGenerating architecture summary...")
    summary = generate_architecture_summary(parsed_data, dep_graph, cg)

    # Save to file
    output_dir = Path(".repomind")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "architecture_summary.md"
    output_path.write_text(summary, encoding="utf-8")
    typer.echo(f"\nArchitecture summary saved to: {output_path}")
    typer.echo("\n" + summary)


@app.command()
def info():
    typer.echo("RepoMind v0.1.0 — AI Codebase Understanding & Visualization Engine")
    typer.echo("")
    typer.echo("USAGE:")
    typer.echo("  repomind <command> [options] [arguments]")
    typer.echo("")
    typer.echo("PHASE 1 — CORE ANALYSIS:")
    typer.echo("  analyze   <repo_url>          Analyze a remote repository (clone + scan + parse + graph)")
    typer.echo("  scan      <local_path>        Scan a local repository")
    typer.echo("  callgraph <local_path>        Extract function-to-function call relationships")
    typer.echo("  arch      <local_path>        Generate architecture summary (modules, deps, calls)")
    typer.echo("")
    typer.echo("PHASE 2 — AI RETRIEVAL:")
    typer.echo("  index     <local_path>        Index repository for AI-powered code search")
    typer.echo("  search    <query>             Semantic code search against indexed codebase")
    typer.echo("  ask       <question>          AI Q&A about the codebase using RAG + Ollama")
    typer.echo("")
    typer.echo("OPTIONS:")
    typer.echo("  --graph         Generate dependency graph visualization (analyze/scan)")
    typer.echo("  --rebuild       Rebuild index from scratch (index)")
    typer.echo("  --top-k         Number of results to retrieve (search/ask)")
    typer.echo("")
    typer.echo("EXAMPLES:")
    typer.echo("  repomind scan . --graph")
    typer.echo("  repomind index ./my-project")
    typer.echo('  repomind search "how is auth handled"')
    typer.echo('  repomind ask "explain the dependency graph"')

if __name__ == "__main__":
    app()
