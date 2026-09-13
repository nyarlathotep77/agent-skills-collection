#!/usr/bin/env python3

import json
import os
import argparse
import shutil
import sys

def load_registry(registry_path):
    if not os.path.exists(registry_path):
        return []
    with open(registry_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def list_skills(registry):
    if not registry:
        print("No skills available.")
        return
    for s in registry:
        tags = ", ".join(s.get('tags', []))
        print(f"[{s['id']}] {s['name']} - {s.get('description', '')} (Tags: {tags})")

def search_skills(registry, query):
    q = query.lower()
    res = [s for s in registry if q in s['name'].lower() or any(q in t.lower() for t in s.get('tags', []))]
    if not res:
        print(f"No matches for '{query}'")
    else:
        list_skills(res)

def install_skill(skill_id, registry, target_dir):
    s = next((x for x in registry if x['id'] == skill_id), None)
    if not s:
        print(f"Error: Skill '{skill_id}' not found.")
        return
    found = None
    for r, d, f in os.walk('.'):
        if 'metadata.json' in f:
            try:
                with open(os.path.join(r, 'metadata.json'), 'r') as f_in:
                    if json.load(f_in).get('id') == skill_id:
                        found = r
                        break
            except:
                continue
    if not found:
        print("Error: Source directory not found.")
        return
    dest = os.path.join(target_dir, skill_id)
    os.makedirs(target_dir, exist_ok=True)
    try:
        shutil.copytree(found, dest, dirs_exist_ok=True)
        print(f"Successfully installed '{s['name']}' to {dest}")
    except Exception as e:
        print(f"Error during installation: {e}")

def main():
    parser = argparse.ArgumentParser(description='Skill Marketplace CLI')
    parser.add_argument('--registry', default='registry.json', help='Path to registry.json')
    parser.add_argument('--target', default='./installed_skills', help='Directory to install skills into')
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.add_parser('list', help='List all available skills')
    search_p = subparsers.add_parser('search', help='Search skills by name or tag')
    search_p.add_argument('query', type=str, help='Search term')
    install_p = subparsers.add_parser('install', help='Install a skill by ID')
    install_p.add_argument('skill_id', type=str, help='ID of the skill to install')

    args = parser.parse_args()
    if not os.path.exists(args.registry):
        print(f"Error: Registry file '{args.registry}' not found.")
        return
    reg = load_registry(args.registry)
    if args.cmd == 'list':
        list_skills(reg)
    elif args.cmd == 'search':
        search_skills(reg, args.query)
    elif args.cmd == 'install':
        install_skill(args.skill_id, reg, args.target)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
