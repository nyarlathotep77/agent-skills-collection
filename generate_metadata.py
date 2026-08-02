#!/usr/bin/env python3
"""
Scans all skill directories, parses YAML frontmatter from SKILL.md,
and generates a metadata.json in each skill directory.

Fields produced: id, name, version, description, tags, dependencies.
"""
import json
import os
import re
import sys


def parse_yaml_frontmatter(skill_md_path):
    """Extract the YAML frontmatter block from a SKILL.md file."""
    with open(skill_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match --- ... --- at the beginning of the file
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    yaml_block = match.group(1)
    return parse_simple_yaml(yaml_block)


def parse_simple_yaml(text):
    """Minimal YAML parser for the flat/nested structures we encounter."""
    result = {}
    current_key = None
    current_list = None
    indent_stack = []

    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Calculate indentation
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Pop indent stack for dedented sections
        while indent_stack and indent_stack[-1]["indent"] >= indent:
            indent_stack.pop()

        if stripped.startswith("- "):
            # List item
            value = stripped[2:].strip().rstrip(".")
            if current_list is not None:
                current_list.append(value)
            continue

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if value == "":
                # Could be a dict or list starting on next line
                result[key] = {}  # Placeholder; will be overwritten if it's a list
                current_key = key
                indent_stack.append({"indent": indent, "key": key})
            elif value.startswith("{") and value.endswith("}"):
                # Inline dict - skip for now
                pass
            else:
                # Simple key-value
                val = value.strip("\"'").rstrip(".")
                result[key] = val

    return result


def extract_fields(frontmatter):
    """Extract the required metadata fields from parsed frontmatter."""
    if not frontmatter:
        return None

    name = frontmatter.get("name", "unknown")
    description = frontmatter.get("description", "")
    # Clean up description - remove newlines and extra spaces
    description = " ".join(description.split())

    # Version from metadata.version or default
    version = "1.0.0"
    meta = frontmatter.get("metadata")
    if isinstance(meta, dict):
        version = str(meta.get("version", "1.0.0"))

    # Tags from keywords list or derived from name
    tags = []
    if isinstance(meta, dict):
        keywords = meta.get("keywords", [])
        if isinstance(keywords, list):
            tags = [k.strip().rstrip(".") for k in keywords]

    # If no keywords found, derive tags from the skill name
    if not tags:
        tags = [name.replace("-", " ").replace("_", " ").strip()]

    # Dependencies - check compatibility field for version requirements
    dependencies = []
    compat = frontmatter.get("compatibility", "")
    if compat:
        # Extract package names from compatibility string
        compat_clean = " ".join(compat.split())
        # Look for common dependency patterns
        dep_patterns = [
            r"(?:requires|need)[s]??\s+([\w\s,]+?)(?:\.|$)",
            r"Python\s+(\d+\.\d+)",
        ]
        for pattern in dep_patterns:
            matches = re.findall(pattern, compat_clean, re.IGNORECASE)
            if matches:
                dependencies.extend(matches)

    return {
        "id": name,
        "name": name.replace("-", " ").replace("_", " ").title(),
        "version": version,
        "description": description,
        "tags": tags,
        "dependencies": dependencies
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_metadata.py <source_dir> [source_dir2 ...]")
        sys.exit(1)

    total = 0
    skipped = 0

    for source_dir in sys.argv[1:]:
        if not os.path.isdir(source_dir):
            print(f"Warning: {source_dir} is not a directory, skipping.")
            continue

        for root, dirs, files in os.walk(source_dir):
            # Skip .git directories
            if ".git" in dirs:
                dirs.remove(".git")

            skill_md = os.path.join(root, "SKILL.md")
            if not os.path.exists(skill_md):
                continue

            frontmatter = parse_yaml_frontmatter(skill_md)
            if frontmatter is None:
                print(f"  [skip] No frontmatter in {skill_md}")
                skipped += 1
                continue

            fields = extract_fields(frontmatter)
            if fields is None:
                print(f"  [skip] Could not extract fields from {skill_md}")
                skipped += 1
                continue

            metadata_path = os.path.join(root, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(fields, f, indent=2)
                f.write("\n")

            print(f"  [ok] {fields['id']} -> {metadata_path}")
            total += 1

    print(f"\nGenerated {total} metadata.json files ({skipped} skipped).")


if __name__ == "__main__":
    main()
