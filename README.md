# RepoMind 🧠

**AI-Powered Codebase Understanding & Visualization Engine**

RepoMind is a local, privacy-first tool that analyzes, visualizes, and answers questions about any codebase — entirely offline. It uses Tree-sitter for multi-language parsing, FAISS for semantic search, and Ollama for AI-powered Q&A.

---

## ✨ Features

### Phase 1 — Core Analysis
| Feature | Description |
|---------|-------------|
| **Repository Scanning** | Clone or scan local repos with gitignore-aware file filtering |
| **Multi-Language Parsing** | Extract symbols (classes, functions, imports) from **8 languages** |
| **Dependency Graphing** | Build import-level dependency graphs with Graphviz/Mermaid |
| **Call Graph Extraction** | Trace function-to-function calls across files (Python AST + Tree-sitter for JS/TS/C/C++/Java/C#/Rust/Go) |
| **Architecture Summary** | Generate high-level reports: modules, hubs, callers, language breakdown |

### Phase 2 — AI Retrieval
| Feature | Description |
|---------|-------------|
| **Code Chunking** | Tree-sitter-aware chunking — extracts functions, classes, methods as logical units |
| **Semantic Embeddings** | Local embedding generation via sentence-transformers |
| **Vector Search** | FAISS-powered similarity search for code |
| **AI Q&A (RAG)** | Ask questions about your codebase — Ollama + RAG pipeline |

### Supported Languages
Python · JavaScript · TypeScript · C · C++ · Java · C# · Rust · Go

---

## 🚀 Quick Start

### Prerequisites

| Tool | Required For | Install |
|------|-------------|---------|
| **Python 3.10+** | Core engine | [python.org](https://www.python.org/downloads/) |
| **Git** | Cloning repositories | [git-scm.com](https://git-scm.com/downloads) |
| **Ollama** | AI Q&A (`ask` command) | [ollama.ai/download](https://ollama.ai/download) |
| **Graphviz** | SVG graph export (optional) | [graphviz.org](https://graphviz.org/download/) |

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/AnirbanSatapathi/repomind.git
cd repomind

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Install RepoMind (core — parsing, graphing, call graph)
pip install -e .

# 4. Install AI dependencies (for search & Q&A)
pip install -e ".[ai]"

# 5. Pull an LLM for Q&A (choose based on your hardware — see table below)
ollama pull llama3.2
```

### Configuration

Copy `.env.example` to `.env` and customize models based on your hardware:

```bash
cp .env.example .env      # Linux/Mac
copy .env.example .env     # Windows
```

Edit `.env` to set your preferred models:

```env
# Choose an embedding model (see recommendations below)
REPOMIND_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Choose an LLM model (must be pulled via: ollama pull <model_name>)
REPOMIND_LLM_MODEL=llama3.2

# Ollama server URL (change if running remotely)
REPOMIND_OLLAMA_HOST=http://localhost:11434
```

All settings are optional — sensible defaults are used if `.env` is not present.

| Variable | Default | Description |
|----------|---------|-------------|
| `REPOMIND_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model for embeddings |
| `REPOMIND_LLM_MODEL` | `llama3.2` | Ollama model for AI Q&A |
| `REPOMIND_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `REPOMIND_INDEX_DIR` | `.repomind/indexes` | FAISS index storage path |
| `REPOMIND_MAX_CHUNK_LINES` | `100` | Max lines per code chunk |
| `REPOMIND_TOP_K` | `5` | Default search result count |
| `REPOMIND_DEVICE` | auto | `cpu` or `cuda` for GPU acceleration |

---

## 📖 Analyzing a New GitHub Repository (Step-by-Step Guide)

This walkthrough shows the full workflow for analyzing any GitHub repository.

### Step 1: Analyze a Remote Repo (Clone + Parse + Graph)

```bash
# Analyze and generate a dependency graph
repomind analyze https://github.com/user/repo.git --graph
```

This will:
- Clone the repo into `.repomind/repos/`
- Scan all source files (ignoring `.git`, `node_modules`, `vendor`, etc.)
- Parse symbols (functions, classes, imports) using Tree-sitter
- Build a dependency graph from import relationships
- Generate Mermaid + Graphviz visualizations in `.repomind/graphs/`

### Step 2: Extract Call Graph

```bash
# Use the cloned path from Step 1, or a local repo path
repomind callgraph .repomind/repos/repo
```

Output: `.repomind/graphs/call_graph.md` — shows which functions call which other functions.

### Step 3: Generate Architecture Summary

```bash
repomind arch .repomind/repos/repo
```

Output: `.repomind/architecture_summary.md` — a high-level report with:
- Module breakdown (directories, file counts, function/class counts)
- Dependency hubs (most imported files)
- Call graph statistics (top callers)
- Language breakdown

### Step 4: Index for AI Search

```bash
# Index the repository (generates embeddings — may take a few minutes)
repomind index .repomind/repos/repo

# To rebuild the index from scratch:
repomind index .repomind/repos/repo --rebuild
```

This creates a FAISS vector index in `.repomind/indexes/`.

### Step 5: Search the Codebase

```bash
repomind search "how is authentication handled"
repomind search "database connection pooling" --top-k 10
```

### Step 6: Ask AI Questions

```bash
# Make sure Ollama is running first!
repomind ask "explain the dependency injection pattern used here"
repomind ask "what does the Parser class do?" --top-k 3
```

### Working with Local Repos

You can also scan a local repository directly (no cloning):

```bash
# Scan a local project
repomind scan ./my-project --graph

# Full pipeline on a local project
repomind scan ./my-project --graph
repomind callgraph ./my-project
repomind arch ./my-project
repomind index ./my-project
repomind search "error handling"
repomind ask "how does the caching layer work?"
```

---

## 🧠 Model Recommendations

### Embedding Models (for `REPOMIND_EMBEDDING_MODEL`)

These models run locally via `sentence-transformers`. They are downloaded automatically on first use.

| Model | Dimensions | Download Size | Quality | Min RAM |
|-------|-----------|--------------|---------|---------|
| `BAAI/bge-small-en-v1.5` | 384 | ~35MB | Good | 2GB+ |
| **`all-MiniLM-L6-v2`** ⭐ | **384** | **~90MB** | **Good** | **2GB+** |
| `all-MiniLM-L12-v2` | 384 | ~120MB | Better | 2GB+ |
| `BAAI/bge-base-en-v1.5` | 768 | ~130MB | Better | 4GB+ |
| `all-mpnet-base-v2` | 768 | ~440MB | Best | 4GB+ |

> **💡 Recommendation:** Start with `all-MiniLM-L6-v2` (default). It's fast, lightweight, and works well on any machine. Upgrade to `all-mpnet-base-v2` if you have 4GB+ RAM and want better search quality.

### LLM Models (for `REPOMIND_LLM_MODEL` via Ollama)

These models must be pulled before use: `ollama pull <model_name>`

| Model | Parameters | Download | Min RAM | Quality | Best For |
|-------|-----------|----------|---------|---------|----------|
| `qwen2.5:1.5b` | 1.5B | ~1GB | 4GB+ | Basic | Quick answers, low-end hardware |
| `phi3:3.8b` | 3.8B | ~2.2GB | 4GB+ | Good | Balanced speed/quality |
| **`llama3.2:3b`** ⭐ | **3B** | **~2GB** | **4GB+** | **Good** | **⭐ Best starting point** |
| `mistral:7b` | 7B | ~4.1GB | 8GB+ | Better | Detailed code explanations |
| `deepseek-coder:6.7b` | 6.7B | ~3.8GB | 8GB+ | Better | Best for code-specific tasks |
| `llama3.1:8b` | 8B | ~4.7GB | 8GB+ | Excellent | Complex reasoning |
| `codellama:34b` | 34B | ~19GB | 32GB+ | Best | Most accurate code analysis |

> **💡 Hardware Guide:**
> - **4GB RAM laptop:** Use `llama3.2:3b` + `all-MiniLM-L6-v2`
> - **8GB RAM laptop:** Use `mistral:7b` or `deepseek-coder:6.7b` + `all-MiniLM-L6-v2`
> - **16GB+ RAM / GPU:** Use `llama3.1:8b` + `all-mpnet-base-v2`
> - **32GB+ RAM / powerful GPU:** Use `codellama:34b` for best results

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_chunker.py -v

# Run a specific test
pytest tests/test_go_parser.py::TestGoParser::test_go_parser_extracts_functions_imports_and_types -v
```

**Current test coverage: 42 tests** covering:
- Architecture summary generation (7 tests)
- C include resolution & graph building
- Call graph extraction — Python, Go, JavaScript, Java, cross-file (8 tests)
- Code chunking — Python AST, Tree-sitter JS/Go, multi-language, line-based (9 tests)
- FAISS vector store — add, search, save, load, clear, edge cases (9 tests)
- Tree-sitter parsing — JS imports/classes/functions
- Go parser — functions, imports, type declarations
- Python relative imports
- Graph builder resolution

---

## 📁 Output Files

All generated files are stored in `.repomind/`:

```
.repomind/
├── repos/                    # Cloned repositories
├── graphs/
│   ├── dependency_graph.md   # Mermaid diagram
│   ├── dependency_graph.dot  # Raw Graphviz data
│   └── call_graph.md         # Call graph summary
├── indexes/
│   ├── index.faiss           # FAISS vector index
│   └── chunks.json           # Chunk metadata
└── architecture_summary.md   # Architecture report
```

---

## 🏗️ Architecture

```
CLI (typer)
  ├── Loader      → Clone/load repos (GitPython)
  ├── Scanner     → Walk files, filter by gitignore
  ├── Parser      → Tree-sitter AST parsing (8 languages)
  │   ├── PythonParser      (AST)
  │   ├── JavaScriptParser  (Tree-sitter)
  │   ├── CFamilyParser     (Tree-sitter)
  │   ├── JavaParser        (Tree-sitter)
  │   ├── CSharpParser      (Tree-sitter)
  │   ├── RustParser        (Tree-sitter)
  │   └── GoParser          (Tree-sitter)
  ├── GraphBuilder → Import resolution + dependency graph
  │   └── Resolvers (Python, JS, C/C++, Java, C#, Rust, Go)
  ├── Visualizer  → Graphviz SVG + Mermaid diagrams
  ├── Chunker     → Tree-sitter-aware code splitting (all languages)
  ├── EmbeddingEngine → sentence-transformers
  ├── VectorStore → FAISS search + persistence
  ├── QAEngine    → RAG pipeline + Ollama LLM
  ├── CallGraphExtractor → Multi-language function call analysis
  └── ArchSummary → High-level architecture reports
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ollama: command not found` | Install Ollama from [ollama.ai/download](https://ollama.ai/download) |
| `Error querying Ollama` | Make sure Ollama is running: `ollama serve` |
| `model not found` | Pull the model first: `ollama pull llama3.2` |
| `No index found` | Run `repomind index <path>` before `search` or `ask` |
| `FAISS import error` | Install AI deps: `pip install -e ".[ai]"` |
| `tree-sitter error` | Ensure `tree-sitter==0.21.3` and `tree-sitter-languages` are installed |
| `Git clone fails` | Check the URL and ensure Git is installed |
| Slow indexing | Use a lighter embedding model or reduce `REPOMIND_MAX_CHUNK_LINES` |
| Out of memory | Use a smaller LLM model (see hardware guide above) |

---

## 🔒 Privacy

RepoMind runs **100% locally**. No data leaves your machine:
- All parsing happens on your CPU
- Embeddings are generated locally via sentence-transformers
- Vector search uses local FAISS index
- LLM inference runs on your machine via Ollama
- No API calls, no telemetry, no cloud dependencies

---

## 📝 License

MIT

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Add more language parsers (Kotlin, Swift, Ruby, PHP)
- Improve cross-file call graph resolution
- Add Go module-aware import resolution (`go.mod` parsing)
- Web UI for interactive graph exploration
- Support for multi-repo analysis
