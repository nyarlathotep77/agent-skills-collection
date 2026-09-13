#!/usr/bin/env python3

import json
import os
import argparse

def load_metadata(skill_dir):
    metadata_path = os.path.join(skill_dir, 'metadata.json')
    if not os.path.exists(metadata_path):
        return None
    with open(metadata_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None

def generate_registry(root_dir):
    registry = []
    for root, _, files in os.walk(root_dir):
        if 'metadata.json' in files:
            metadata = load_metadata(root)
            if metadata:
                # Ensure we have all required fields for the registry
                entry = {
                    "id": metadata.get("id"),
                    "name": metadata.get("name"),
                    "version": metadata.get("version", "1.0.0"),
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", []),
                    "dependencies": metadata.get("dependencies", [])
                }
                if entry["id"]:
                    registry.append(entry)
    return registry

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate skill registry')
    parser.add_argument('--android', default='android-skills', help='Path to android skills')
    parser.add_argument('--scientific', default='scientific-agent-skills/skills', help='Path to scientific skills')
    parser.add_argument('--scientific-extra', default='scientific-skills/skills', help='Path to extra scientific skills')
    parser.add_argument('--kotlin', default='kotlin-kmp-claude-agent-skills/skills', help='Path to kotlin kmp skills')
    parser.add_argument('--output', default='registry.json', help='Output registry file')
    args = parser.parse_args()

    registry = []
    if os.path.exists(args.android):
        registry.extend(generate_registry(args.android))
    if os.path.exists(args.scientific):
        registry.extend(generate_registry(args.scientific))
    if os.path.exists(args.scientific_extra):
        registry.extend(generate_registry(args.scientific_extra))
    if os.path.exists(args.kotlin):
        registry.extend(generate_registry(args.kotlin))
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=4)
    print(f"Generated registry with {len(registry)} skills in {args.output}")
