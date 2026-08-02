import json
import os
import sys
from typing import List, Dict, Any

class PluginRegistry:
    def __init__(self, search_paths: List[str]):
        self.search_paths = search_paths
        self.plugins: List[Dict[str, Any]] = []

    def discover(self):
        """Scans the search paths for marketplace.json files."""
        for path in self.search_paths:
            if not os.path.exists(path):
                continue
            
            # Search recursively for marketplace.json in the given path
            for root, dirs, files in os.walk(path):
                if 'marketplace.json' in files:
                    file_path = os.path.join(root, 'marketplace.json')
                    try:
                        with open(file_path, 'r') as f:
                            plugin_data = json.load(f)
                            # Add the path to the plugin data for reference
                            plugin_data['plugin_path'] = file_path
                            self.plugins.append(plugin_data)
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Error loading plugin at {file_path}: {e}")

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        return self.plugins

    def get_plugins_by_harness(self, harness: str) -> List[Dict[str, Any]]:
        return [p for p in self.plugins if harness in p.get('harnesses', [])]

if __name__ == "__main__":
    # Support passing paths via command line
    paths = sys.argv[1:] if len(sys.argv) > 1 else ['.']
    registry = PluginRegistry(paths)
    registry.discover()
    print(json.dumps(registry.get_all_plugins(), indent=2))
