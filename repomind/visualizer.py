from pathlib import Path
from typing import Dict, List, Union
import graphviz
import os

class Visualizer:
    """
    Generates visual dependency graphs using Graphviz.
    """

    # Language-based color mapping
    COLORS = {
        ".py": "#3776AB",     # Python Blue
        ".js": "#F7DF1E",     # JS Yellow
        ".ts": "#3178C6",     # TS Blue
        ".java": "#ED8B00",   # Java Orange/Red
        ".rs": "#DEA584",     # Rust Brown
        ".go": "#00ADD8",     # Go Light Blue
        ".c": "#A8B9CC",      # C Gray
        ".cpp": "#00599C",    # C++ Blue
        ".h": "#A8B9CC",      # Header Gray
        ".cs": "#178600",     # C# Green
    }

    def __init__(self, output_dir: str = ".repomind/graphs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_node_style(self, file_path: str) -> Dict[str, str]:
        """Returns styling attributes for a node based on file extension."""
        ext = Path(file_path).suffix.lower()
        color = self.COLORS.get(ext, "#777777")  # Default gray
        
        return {
            "style": "filled",
            "fillcolor": color,
            "fontcolor": "#FFFFFF" if color != "#F7DF1E" else "#000000",
            "shape": "box",
            "fontname": "Helvetica",
        }

    def generate_mermaid(self, dependency_graph: Dict[str, List[str]], repo_root: Union[str, Path], output_name: str = "dependency_graph") -> str:
        """
        Creates a Mermaid diagram and saves it as a Markdown file.
        Returns the path to the generated file.
        """
        root_path = Path(repo_root).resolve()
        
        lines = ["```mermaid", "graph TD"]
        
        # Add edges
        for source, targets in dependency_graph.items():
            source_rel = os.path.relpath(source, root_path).replace("\\", "/")
            for target in targets:
                target_rel = os.path.relpath(target, root_path).replace("\\", "/")
                lines.append(f'    "{source_rel}" --> "{target_rel}"')
        
        lines.append("```")
        
        output_path = self.output_dir / f"{output_name}.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")
        
        return str(output_path)

    def generate_graph(self, dependency_graph: Dict[str, List[str]], repo_root: Union[str, Path], output_name: str = "dependency_graph") -> str:
        """
        Creates a directed graph and saves it as an SVG.
        Returns the path to the generated file.
        """
        dot = graphviz.Digraph(
            name=output_name,
            comment="RepoMind Dependency Graph",
            format="svg",
            engine="dot"
        )

        # Global graph attributes
        dot.attr(rankdir="LR", overlap="false", splines="true")
        dot.attr("node", fontsize="10", margin="0.1")

        root_path = Path(repo_root).resolve()

        # Add nodes
        for file_path in dependency_graph.keys():
            rel_path = os.path.relpath(file_path, root_path)
            style = self._get_node_style(file_path)
            dot.node(rel_path, rel_path, **style)

        # Add edges
        for source, targets in dependency_graph.items():
            source_rel = os.path.relpath(source, root_path)
            for target in targets:
                target_rel = os.path.relpath(target, root_path)
                dot.edge(source_rel, target_rel)

        output_path = self.output_dir / output_name
        
        try:
            # render() adds the format suffix (e.g. .svg)
            rendered_file = dot.render(str(output_path), cleanup=True)
            return rendered_file
        except graphviz.backend.ExecutableNotFound:
            pass
        except Exception:
            pass

        # Fallback: save .dot file for manual rendering
        try:
            dot_file = dot.save(str(output_path) + ".dot")
            return f"Raw DOT file saved to: {dot_file} (Install Graphviz to render as SVG)"
        except Exception:
            return "Failed to render graph. Install Graphviz (https://graphviz.org/download/) to enable SVG generation."