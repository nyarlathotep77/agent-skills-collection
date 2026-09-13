import json
import argparse
import os
import sys

def scaffold_plugin(name, author, version, description, harnesses, capabilities, entry_points, output_dir):
    plugin_data = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "harnesses": harnesses,
        "capabilities": capabilities,
        "entry_points": entry_points
    }

    # Create plugin directory
    plugin_dir = os.path.join(output_dir, name.replace(" ", "_").lower())
    os.makedirs(plugin_dir, exist_ok=True)
    
    # Write marketplace.json
    marketplace_path = os.path.join(plugin_dir, "marketplace.json")
    with open(marketplace_path, 'w') as f:
        json.dump(plugin_data, f, indent=2)
    
    print(f"🚀 Plugin '{name}' scaffolded successfully at: {plugin_dir}")
    print(f"📄 Created: {marketplace_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new plugin directory with a valid marketplace.json")
    parser.add_argument("--name", required=True, help="Name of the plugin")
    parser.add_argument("--author", default="Unknown Author", help="Author name")
    parser.add_argument("--version", default="0.1.0", help="Plugin version")
    parser.add_argument("--description", default="A new agentic plugin.", help="Description of the plugin")
    parser.add_argument("--harnesses", nargs="+", default=["generic"], help="Compatible harnesses (e.g., dcode claude-code)")
    parser.add_argument("--capabilities", nargs="+", default=[], help="List of capabilities provided")
    parser.add_argument("--entry-points", nargs='*', help="Key-value pairs for entry points (e.g., capability=path)")
    parser.add_argument("--output", default=".", help="Output directory for the new plugin")

    args = parser.parse_args()

    # Parse entry points from list of strings like ['cmd=run', 'task=execute']
    entry_points_dict = {}
    if args.entry_points:
        for ep in args.entry_points:
            if '=' in ep:
                k, v = ep.split('=', 1)
                entry_points_dict[k] = v
            else:
                print(f"⚠️ Warning: Skipping invalid entry point format '{ep}'. Use 'key=value'.")

    scaffold_plugin(
        args.name,
        args.author,
        args.version,
        args.description,
        args.harnesses,
        args.capabilities,
        entry_points_dict,
        args.output
    )
