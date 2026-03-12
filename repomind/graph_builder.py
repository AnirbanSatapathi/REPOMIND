from pathlib import Path
from typing import List, Dict, Any

class GraphBuilder:

    def build_graph(self, parsed_files: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        graph = {}
        module_to_file = {}
        for item in parsed_files:
            file_path = Path(item["file"])

            module_name = file_path.stem
            module_to_file[module_name] = str(file_path)

            parent = file_path.parent.name
            module_to_file[f"{parent}.{module_name}"] = str(file_path)

        for item in parsed_files:

            file_path = item["file"]
            imports = item["imports"]

            graph[file_path] = []

            for imp in imports:

                if imp in module_to_file:
                    graph[file_path].append(module_to_file[imp])
                    continue

                base = imp.split(".")[0]

                if base in module_to_file:
                    graph[file_path].append(module_to_file[base])

        return graph
