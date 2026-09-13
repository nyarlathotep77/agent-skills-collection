#!/usr/bin/env python3
"""
Aggregates all marketplace.json files in the repository into a single compliant 
dcode plugin marketplace manifest.
"""
import json
import os
import sys

def aggregate_marketplace(root_dir):
    """Scans for plugin subdirectories and generates a compliant marketplace manifest."""
    plugins = []
    
    # We will search for plugin directories by scanning for subdirectories containing a manifest.
    for name in sorted(os.listdir(root_dir)):
        plugin_path = os.path.join(root_dir, name)
        if not os.path.isdir(plugin_path) or name.startswith('.'):
            continue
            
        # Check for plugin manifest
        manifest_found = False
        manifest_data = {}
        for rel_manifest in [
            os.path.join('.claude-plugin', 'plugin.json'),
            os.path.join('.codex-plugin', 'plugin.json')
        ]:
            manifest_file = os.path.join(plugin_path, rel_manifest)
            if os.path.isfile(manifest_file):
                manifest_found = True
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        manifest_data = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not parse manifest at {manifest_file}: {e}")
                break
                
        # Fallback to local marketplace.json in the plugin folder if no sub-plugin manifest found
        local_market = os.path.join(plugin_path, 'marketplace.json')
        if not manifest_found and os.path.isfile(local_market):
            try:
                with open(local_market, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                manifest_found = True
            except Exception:
                pass
                
        if manifest_found:
            # Map manifest details to a compliant MarketplacePluginEntry
            plugin_name = manifest_data.get("name", name)
            
            # Map author format (can be string or dict)
            author_data = manifest_data.get("author", "Unknown")
            
            plugins.append({
                "name": plugin_name,
                "source": f"./{name}",  # Relative path required by dcode
                "description": manifest_data.get("description", ""),
                "author": author_data,
                "displayName": manifest_data.get("displayName") or manifest_data.get("interface", {}).get("displayName")
            })
    
    # The master marketplace structure
    root_marketplace = {
        "name": "agent-skills-collection",  # Must be whitespace-free
        "version": "1.0.0",
        "description": "The master marketplace for all agentic plugins and skills.",
        "author": "Agent Skills Collection Team",
        "plugins": plugins
    }
    
    # Output to both root and standard dcode discovery path (.agents/plugins/marketplace.json)
    paths_to_write = [
        os.path.join(root_dir, 'marketplace.json'),
        os.path.join(root_dir, '.agents', 'plugins', 'marketplace.json')
    ]
    
    for out_path in paths_to_write:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(root_marketplace, f, indent=2)
            f.write("\n")
        print(f"Wrote marketplace manifest to {out_path}")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    aggregate_marketplace(os.path.abspath(target_dir))
