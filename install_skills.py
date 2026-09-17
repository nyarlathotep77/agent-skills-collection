#!/usr/bin/env python3
"""Skill Marketplace CLI.

Discovers skills by scanning SKILL.md frontmatter in the submodule trees,
so there is no intermediate registry artifact to keep in sync with the
sources. Works on a fresh clone as long as the submodules are checked out.
"""

import argparse
import os
import shutil
import sys

SKIP_DIRS = {'.git', 'installed_skills'}


def parse_frontmatter(text):
    """Minimal YAML frontmatter parser (stdlib only).

    Supports flat `key: value` pairs, indented continuation lines for
    folded scalars, and one level of nested mapping (e.g. `metadata:`).
    """
    data = {}
    nested_key = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ':' not in stripped:
            continue
        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if indent == 0:
            nested_key = None
            if value == '':
                # Start of a nested mapping (e.g. `metadata:`)
                data[key] = {}
                nested_key = key
            else:
                data[key] = value
        elif nested_key is not None and isinstance(data.get(nested_key), dict):
            data[nested_key][key] = value
    return data


def extract_frontmatter(text):
    """Return the frontmatter block of a SKILL.md, or {} if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return parse_frontmatter('\n'.join(lines[1:i]))
    return {}


def scan_skills(root='.'):
    """Walk the tree and build an in-memory registry from SKILL.md files."""
    skills = []
    seen = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        if 'SKILL.md' not in filenames:
            continue
        path = os.path.join(dirpath, 'SKILL.md')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                fm = extract_frontmatter(f.read())
        except (OSError, UnicodeDecodeError) as e:
            print(f"Warning: could not read {path}: {e}", file=sys.stderr)
            continue
        name = fm.get('name') or os.path.basename(dirpath)
        if name in seen:
            print(f"Warning: duplicate skill id '{name}' at {dirpath} (skipped)",
                  file=sys.stderr)
            continue
        seen.add(name)
        metadata = fm.get('metadata')
        if not isinstance(metadata, dict):
            metadata = {}
        version = fm.get('version') or metadata.get('version')
        skills.append({
            'id': name,
            'description': fm.get('description', ''),
            'version': version,
            'source': dirpath,
        })
    return sorted(skills, key=lambda s: s['id'])


def _format_skill(s):
    desc = s['description']
    if len(desc) > 100:
        desc = desc[:97] + '...'
    ver = f" v{s['version']}" if s.get('version') else ''
    return f"[{s['id']}]{ver} {desc}  ({s['source']})"


def list_skills(skills):
    if not skills:
        print("No skills found.")
        return
    for s in skills:
        print(_format_skill(s))


def search_skills(skills, query):
    q = query.lower()
    matches = [s for s in skills
               if q in s['id'].lower() or q in s['description'].lower()]
    if not matches:
        print(f"No skills matching '{query}'.")
        return
    for s in matches:
        print(_format_skill(s))


def install_skill(skill_id, skills, target_dir):
    skill = next((s for s in skills if s['id'] == skill_id), None)
    if not skill:
        print(f"Error: Skill '{skill_id}' not found.")
        return 1
    dest = os.path.join(target_dir, skill_id)
    try:
        shutil.copytree(skill['source'], dest, dirs_exist_ok=True)
    except Exception as e:
        print(f"Error during installation: {e}")
        return 1
    print(f"Successfully installed '{skill['id']}' to {dest}")
    return 0


def main():
    parser = argparse.ArgumentParser(description='Skill Marketplace CLI')
    parser.add_argument('--target', default='./installed_skills',
                        help='Directory to install skills into')
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.add_parser('list', help='List all available skills')
    search_p = subparsers.add_parser('search', help='Search skills by name or description')
    search_p.add_argument('query', type=str, help='Search term')
    install_p = subparsers.add_parser('install', help='Install a skill by ID')
    install_p.add_argument('skill_id', type=str, help='ID of the skill to install')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 0

    skills = scan_skills('.')
    if args.cmd == 'list':
        list_skills(skills)
        return 0
    elif args.cmd == 'search':
        search_skills(skills, args.query)
        return 0
    elif args.cmd == 'install':
        return install_skill(args.skill_id, skills, args.target)
    return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Output piped to head/less/etc.; exit quietly instead of traceback.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
