# Agent Skills Collection

The master marketplace for agentic plugins and skills. This repository aggregates
[open-standard agent skills](https://agentskills.io) — markdown files (`SKILL.md`) that
ground LLMs with domain knowledge, workflows, and tooling — into a single installable
catalog for agentic harnesses (dcode, Claude Code, DeepAgents, generic).

Skills are discovered **live** by scanning `SKILL.md` frontmatter in the source trees, so
there is no intermediate registry artifact to keep in sync with upstream.

## Repository layout

| Path | What it is |
| --- | --- |
| `marketplace.json` | Root dcode plugin marketplace manifest (aggregated) |
| `.agents/plugins/marketplace.json` | Same manifest at the standard harness discovery path |
| `android-skills/` | Submodule — [Google Android skills](https://github.com/android/skills) |
| `scientific-agent-skills/` | Submodule — [k-dense-ai scientific agent skills](https://github.com/k-dense-ai/scientific-agent-skills) |
| `scientific-skills/` | Submodule — [Awesome Scientific Skills](https://github.com/InternScience/Awesome-Scientific-Skills) |
| `kotlin-kmp-claude-agent-skills/` | Submodule — [Kotlin KMP agent skills](https://github.com/mmiani/kotlin-kmp-claude-agent-skills) |
| `hadrian/` | First-party skill — L3 goal loop with quality gates, cycle budget, and human acceptance gate |
| `install_skills.py` | Marketplace CLI: list / search / install skills |
| `generate_metadata.py` | Generates a `metadata.json` per skill directory from frontmatter |
| `update_marketplace.py` | Re-aggregates all plugin manifests into the root marketplace manifest |
| `core/registry.py` | `PluginRegistry` — discovers `marketplace.json` files across search paths |
| `tools/scaffold_plugin.py` | Scaffolds a new plugin directory with a valid `marketplace.json` |
| `tools/validate_plugin.py` | Validates a `marketplace.json` against the schema (requires `jsonschema`) |
| `schema/plugin_schema.json` | JSON Schema (draft-07) for plugin manifests |

## Included plugins

| Plugin | Source | Description |
| --- | --- | --- |
| Android Skills | [android/skills](https://github.com/android/skills) | Google's official AI-optimized instructions and resources for Android development best practices. |
| Hadrian L3 Goal Loop | first-party (`hadrian/`) | Agentic L3 goal loop (ASDLC conditional autonomy): drive a bounded objective to verified completion with quality gates, a cycle budget, and a human acceptance gate. |
| Kotlin KMP Agent Skills | [mmiani/kotlin-kmp-claude-agent-skills](https://github.com/mmiani/kotlin-kmp-claude-agent-skills) | AI agent skills, orchestration pipeline, and workflows for Kotlin Multiplatform projects. |
| Scientific Agent Skills Plugin | [k-dense-ai/scientific-agent-skills](https://github.com/k-dense-ai/scientific-agent-skills) | A plugin for scanning and analyzing agent skills. |
| scientific-skills-plugin | [InternScience/Awesome-Scientific-Skills](https://github.com/InternScience/Awesome-Scientific-Skills) | A collection of scientific computing skills for agents. |

## Quickstart

Requires Python 3 (standard library only for the CLI).

```bash
# Clone with all skill sources checked out
git clone --recurse-submodules <this-repo-url>
cd agent-skills-collection

# List every discoverable skill
python3 install_skills.py list

# Search by name or description
python3 install_skills.py search compose

# Install a skill into ./installed_skills (default) or another target dir
python3 install_skills.py install camerax --target ~/.config/opencode/skills
```

`install_skills.py` walks the tree, parses each `SKILL.md` YAML frontmatter, and copies
the whole skill directory to the target. Duplicate skill IDs are skipped with a warning.

## Tooling

### Marketplace CLI (`install_skills.py`)

| Command | Description |
| --- | --- |
| `list` | List all available skills (id, version, description, source path) |
| `search <query>` | Case-insensitive match on skill id or description |
| `install <skill_id> [--target DIR]` | Copy a skill directory into the target (default `./installed_skills`) |

### Metadata generation (`generate_metadata.py`)

Scans one or more source directories, parses YAML frontmatter from every `SKILL.md`, and
writes a `metadata.json` next to it with fields: `id`, `name`, `version`, `description`,
`tags`, `dependencies`.

The per-skill `metadata.json` is a machine-readable sidecar of the skill's frontmatter.
Frontmatter lives inside markdown, so any tool that wants to index, search, or filter
skills (by id, version, tags, or dependencies) has to parse YAML out of prose first; the
generated JSON gives it a structured snapshot instead. The `SKILL.md` frontmatter remains
the single source of truth — regenerate after editing skills rather than hand-editing the
JSON:

```bash
python3 generate_metadata.py android-skills hadrian
```

### Marketplace aggregation (`update_marketplace.py`)

Scans top-level plugin directories for a manifest (in order of precedence):

1. `.claude-plugin/plugin.json`
2. `.codex-plugin/plugin.json`
3. local `marketplace.json`

…and rewrites the aggregated root manifest to both `marketplace.json` and
`.agents/plugins/marketplace.json`. Run this after adding or removing a plugin directory:

```bash
python3 update_marketplace.py .
```

### Plugin registry (`core/registry.py`)

Recursively discovers `marketplace.json` files under the given search paths and exposes
them as structured data (e.g. filtered by harness). Usable as a library or standalone:

```bash
python3 core/registry.py .
```

### Scaffolding & validation (`tools/`)

```bash
# Scaffold a new plugin directory with a valid marketplace.json
python3 tools/scaffold_plugin.py --name "My Plugin" --author "You" \
    --harnesses dcode claude-code generic --capabilities camera navigation

# Validate any manifest against the schema (pip install jsonschema)
python3 tools/validate_plugin.py my-plugin/marketplace.json
```

## Plugin manifest schema

`marketplace.json` files are validated against `schema/plugin_schema.json`
(JSON Schema draft-07). Required fields:

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string | Plugin/skill name |
| `version` | string | Semantic version |
| `description` | string | Brief description |
| `harnesses` | array of strings | One or more of: `deepagents`, `dcode`, `claude-code`, `generic` |

Optional fields: `author` (string), `capabilities` (array of strings), `entry_points`
(object mapping capability names to implementation paths/commands).

## Adding a new plugin or skill

1. **First-party content** goes in a top-level directory (like `hadrian/`). Each skill is
   a directory containing a `SKILL.md` with YAML frontmatter:

   ```markdown
   ---
   name: my-skill            # required, unique across the whole tree
   description: What it does and when to use it.
   metadata:
     version: "1.0.0"
   ---
   ```

2. **Upstream content** is added as a git submodule (see `.gitmodules`) so updates track
   the source repository. Do not edit submodule contents in this repo — changes belong to
   the upstream project.

3. Give the plugin directory a manifest: either scaffold one with `tools/scaffold_plugin.py`
   or add a local `marketplace.json`. Validate it with `tools/validate_plugin.py`.

4. Regenerate the root manifest so the new plugin is discoverable by harnesses:

   ```bash
   python3 update_marketplace.py .
   ```

## Local state (gitignored)

- `installed_skills/` — output of `install_skills.py`
- `.agents/` — local agent-harness plugin cache
- `.hadrian/` — local Hadrian goal-loop state
- `__pycache__/`, `*.pyc`

## Licenses

Each submodule carries its own license (see the respective upstream repositories).
First-party tooling in this repository is provided as-is.
