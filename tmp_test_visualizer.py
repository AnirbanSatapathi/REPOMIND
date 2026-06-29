import sys
import os
from pathlib import Path

# Add the project root to sys.path
sys.path.append(os.getcwd())

from repomind.visualizer import Visualizer

def test_visualizer():
    # Mock dependency graph
    mock_graph = {
        "d:/MyProjects/RepoMind/repomind/cli.py": [
            "d:/MyProjects/RepoMind/repomind/loader.py",
            "d:/MyProjects/RepoMind/repomind/scanner.py",
            "d:/MyProjects/RepoMind/repomind/visualizer.py"
        ],
        "d:/MyProjects/RepoMind/repomind/visualizer.py": [
            "d:/MyProjects/RepoMind/repomind/graph_builder.py"
        ],
        "d:/MyProjects/RepoMind/repomind/loader.py": [],
        "d:/MyProjects/RepoMind/repomind/scanner.py": [],
        "d:/MyProjects/RepoMind/repomind/graph_builder.py": []
    }
    
    repo_root = "d:/MyProjects/RepoMind"
    
    # Initialize visualizer with a temporary output dir inside the project's .repomind
    visualizer = Visualizer(output_dir=".repomind/graphs_test")
    
    print("Generating graph...")
    try:
        output_file = visualizer.generate_graph(mock_graph, repo_root, "test_graph")
        print(f"Graph generated successfully at: {output_file}")
        
        if os.path.exists(output_file):
            print("Verification: File exists.")
        else:
            print("Verification FAILED: File does not exist.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_visualizer()
