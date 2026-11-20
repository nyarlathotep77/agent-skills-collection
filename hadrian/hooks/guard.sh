#!/usr/bin/env bash
# Hadrian guard — PreToolUse rule engine (Claude Code hooks adapter).
# Rules: freeze .hadrian/contract.md; block git push while a goal contract exists without signoff;
# enforce worktree isolation (Hard Rule 12).
# stdin: JSON {tool_name, tool_input{file_path|command}, cwd}
# exit 0 = allow, exit 2 = block (stderr is fed back to the model).
set -u

input="$(cat)"

json_get() { # $1 = dotted path
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$input" | jq -r --arg p "$1" 'getpath($p | split(".")) // empty' 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$input" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for k in sys.argv[1].split("."):
    if not isinstance(d,dict): break
    d=d.get(k,"")
print(d if isinstance(d,str) else "")' "$1" 2>/dev/null
  fi
}

tool="$(json_get tool_name)"
case_path="$(json_get tool_input.file_path)"
command="$(json_get tool_input.command)"
cwd="$(json_get cwd)"
[ -n "$cwd" ] || cwd="$(pwd)"

block() { echo "HADRIAN GUARD: $1" >&2; exit 2; }

case "$tool" in
  Edit|Write|MultiEdit)
    case "$case_path" in
      *.hadrian/contract.md)
        target="$case_path"
        [ "${target:0:1}" = "/" ] || target="$cwd/$case_path"
        if [ -f "$target" ] || [ -f "$cwd/.hadrian/contract.md" ]; then
          block "the goal contract is frozen (L3 invariant). Propose amendments in the escalation report; a human applies them."
        fi
        ;;
      *)
        # Worktree write protection (Hard Rule 12)
        if [ -f "$cwd/.hadrian/contract.md" ] && [ -d "$cwd/.hadrian/worktrees" ]; then
          if [ -n "$(ls -A "$cwd/.hadrian/worktrees" 2>/dev/null)" ]; then
            case "$case_path" in
              *.hadrian/worktrees/*|*.hadrian/*|.hadrian/*) ;;
              *) block "Direct file modification in root repository checkout is blocked while worktree isolation is active (Hard Rule 12). Execute all edits inside .hadrian/worktrees/<slug>/." ;;
            esac
          fi
        fi
        ;;
    esac
    ;;
  Bash)
    if printf '%s' "$command" | grep -Eq '(^|[;&|]|[[:space:]])git[[:space:]]+push([[:space:]]|$)'; then
      if [ -f "$cwd/.hadrian/contract.md" ] && [ ! -f "$cwd/.hadrian/signoff" ]; then
        block "git push is blocked while a goal contract is active without acceptance. Review the diff; on approval create .hadrian/signoff (or stop the goal)."
      fi
    fi
    ;;
esac

exit 0
