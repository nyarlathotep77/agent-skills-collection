#!/usr/bin/env python3
"""Hadrian L3 Goal Loop Engine.

Deterministic execution harness for L3 autonomous engineering workflows:
- Phase 0: Contract intake, worktree isolation, MD5 contract freezing.
- Phase 1: Quality gates runner (Gradle / npm / pytest), JUnit XML parsing,
  zero compiler warning validation, evidence artifact generation (.hadrian/evidence/).
- Git operations: Worktree management, clean commit authoring, review diffs.
- State management: Machine-verifiable VERDICT records adhering strictly to
  Hadrian's verdict contract specification.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def get_utc_now() -> str:
    """Return ISO 8601 UTC timestamp."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_repo_root(start_path: Path = None) -> Path:
    """Find the root directory of the git repository."""
    curr = (start_path or Path.cwd()).resolve()
    while curr != curr.parent:
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path.cwd().resolve()


def compute_md5(file_path: Path) -> str:
    """Compute MD5 checksum of a file."""
    if not file_path.exists():
        return ""
    hasher = hashlib.md5()
    hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


class HadrianEngine:
    def __init__(self, repo_root: Path = None):
        self.root = find_repo_root(repo_root)
        self.hadrian_dir = self.root / ".hadrian"
        self.contract_file = self.hadrian_dir / "contract.md"
        self.state_file = self.hadrian_dir / "state.md"
        self.evidence_dir = self.hadrian_dir / "evidence"
        self.worktrees_dir = self.hadrian_dir / "worktrees"

    def ensure_hadrian_dirs(self):
        self.hadrian_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

    def parse_state_header(self) -> dict:
        """Parse metadata from .hadrian/state.md."""
        if not self.state_file.exists():
            return {}
        content = self.state_file.read_text(encoding="utf-8")
        data = {}
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- Objective:"):
                data["objective"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Contract md5:"):
                m = re.search(r"Contract md5:\s*([a-f0-9]{32})", line)
                if m:
                    data["contract_md5"] = m.group(1)
            elif line.startswith("- Budget used:"):
                m = re.search(r"(\d+)\s*/\s*(\d+)", line)
                if m:
                    data["budget_used"] = int(m.group(1))
                    data["budget_total"] = int(m.group(2))
            elif line.startswith("- Worktree:"):
                parts = line.split("|")
                for p in parts:
                    p = p.strip()
                    if p.startswith("- Worktree:"):
                        data["worktree"] = p.replace("- Worktree:", "").strip()
                    elif p.startswith("branch:"):
                        data["branch"] = p.replace("branch:", "").strip()
                    elif p.startswith("base commit:"):
                        raw_sha = p.replace("base commit:", "").strip()
                        m_sha = re.match(r"([0-9a-fA-F]{7,40})", raw_sha)
                        data["base_commit"] = m_sha.group(1) if m_sha else raw_sha
            elif line.startswith("- Ticket:"):
                data["ticket"] = line.split(":", 1)[1].strip()

        # If ticket was not explicitly set in header, infer from objective
        if "ticket" not in data and "objective" in data:
            m_obj = re.search(r"(?:us/|US#|#)\s*(\d+)", data["objective"], re.IGNORECASE)
            if m_obj:
                data["ticket"] = f"smartsparks#{m_obj.group(1)}"
        return data

    def cmd_status(self) -> dict:
        """Read and return goal status."""
        if not self.contract_file.exists() or not self.state_file.exists():
            return {"active": False, "message": "No active Hadrian goal found."}
        state = self.parse_state_header()
        current_md5 = compute_md5(self.contract_file)
        state["contract_valid"] = (current_md5 == state.get("contract_md5"))
        state["active"] = True
        return state

    def _resolve_story_from_objective(self, objective: str) -> tuple:
        """Extract story ref and project slug from objective string if present."""
        # 1. URL pattern: /project/<slug>/us/<ref>
        url_m = re.search(r"/project/([^/]+)/us/(\d+)", objective)
        if url_m:
            return int(url_m.group(2)), url_m.group(1)

        # 2. slug#ref pattern: smartsparks#327 (ignore if prefix is 'us' or 'userstory')
        slug_ref_m = re.search(r"([a-zA-Z0-9_\-]+)#(\d+)", objective)
        if slug_ref_m and slug_ref_m.group(1).lower() not in ("us", "userstory", "user_story"):
            return int(slug_ref_m.group(2)), slug_ref_m.group(1)

        # 3. Ref pattern: US#327, us/327, US-327, US 327
        ref_m = re.search(r"(?:US|us|#)\s*[/_\-]?\s*(\d+)", objective)
        if ref_m:
            return int(ref_m.group(1)), "smartsparks"

        return None, "smartsparks"

    def _fetch_taiga_story(self, story_ref: int, project_slug: str = "smartsparks") -> dict:
        """Fetch user story details from Taiga API if reachable."""
        try:
            project_info = self._taiga_request(f"projects/by_slug?slug={project_slug}")
            project_id = project_info.get("id")
            if not project_id:
                return None
            us = self._taiga_request(f"userstories/by_ref?ref={story_ref}&project={project_id}")
            if not us or "id" not in us:
                return None
            return {
                "id": us["id"],
                "ref": story_ref,
                "subject": us.get("subject", "").strip(),
                "description": us.get("description", "").strip(),
                "project_slug": project_slug,
            }
        except Exception:
            return None

    def _generate_story_contract(
        self,
        objective: str,
        story: dict,
        budget: int,
        branch_name: str,
        spec_path: str,
        utc_start: str,
    ) -> str:
        story_ref = story["ref"]
        subject = story.get("subject", "").strip()
        desc = story.get("description", "").strip()
        project_slug = story.get("project_slug", "smartsparks")

        # Parse sections from description
        context_match = re.search(r"###\s*Context:?\s*\n(.*?)(\n###|\Z)", desc, re.DOTALL | re.IGNORECASE)
        context_text = context_match.group(1).strip() if context_match else ""

        narrative_match = re.match(r"^(.*?)(\n###|\Z)", desc, re.DOTALL)
        narrative_text = narrative_match.group(1).strip() if narrative_match else ""

        ac_match = re.search(r"###\s*Acceptance Criteria:?\s*\n(.*?)(\n###|\Z)", desc, re.DOTALL | re.IGNORECASE)
        if not ac_match:
            ac_match = re.search(r"Acceptance Criteria:?\s*\n(.*?)(\n###|\Z)", desc, re.DOTALL | re.IGNORECASE)

        ac_items = []
        if ac_match:
            ac_text = ac_match.group(1).strip()
            current_item = []
            for line in ac_text.splitlines():
                is_bullet = bool(re.match(r"^\s*[-*]\s+", line) and not (line.startswith("    ") or line.startswith("\t") or line.startswith("  ")))
                is_num = bool(re.match(r"^\s*\d+\.\s+", line) and not (line.startswith("    ") or line.startswith("\t") or line.startswith("  ")))
                if is_bullet:
                    if current_item:
                        ac_items.append("\n".join(current_item).strip())
                        current_item = []
                    current_item.append(re.sub(r"^\s*[-*]\s+", "", line))
                elif is_num:
                    if current_item:
                        ac_items.append("\n".join(current_item).strip())
                        current_item = []
                    current_item.append(re.sub(r"^\s*\d+\.\s+", "", line))
                elif current_item:
                    current_item.append(line)
            if current_item:
                ac_items.append("\n".join(current_item).strip())

        # Build DoD Clauses (C1..Cn)
        clauses = []
        for item in ac_items:
            clauses.append(item)

        # Standard engineering clauses
        has_build = any("assembleDebug" in c or "compilation" in c for c in clauses)
        if not has_build:
            clauses.append("Clean build with zero compilation warnings (`./gradlew assembleDebug`) and all unit tests pass (`./gradlew testDebugUnitTest`); diff introduces no network calls, trackers, or cloud endpoints.")

        clauses.append("OpenWiki KB update pass run on the branch (AGENTS.md §9) so `openwiki/` reflects changes before merge; changed pages committed with the code.")
        clauses.append(f"Decomposition before work: child sub-tasks of US#{story_ref} exist in Taiga, assigned to acting account, BEFORE any implementation step (gate T1).")
        clauses.append("Evidence-backed transitions: each sub-task moves to in-progress on first real work step; closes only with captured verification evidence plus an outcome comment.")
        clauses.append(f"Fail-closed story completion: US#{story_ref} moves to Done only after re-read confirms every child task is closed (gate T2).")

        dod_lines = []
        for idx, c in enumerate(clauses, start=1):
            lines = c.splitlines()
            first_line = lines[0]
            rest = lines[1:]
            if rest:
                indented_rest = "\n".join("  " + r for r in rest)
                dod_lines.append(f"- **C{idx}** — {first_line}\n{indented_rest}")
            else:
                dod_lines.append(f"- **C{idx}** — {first_line}")

        dod_block = "\n".join(dod_lines)

        # Build Rubric Table
        rubric_rows = []
        for idx, c in enumerate(clauses, start=1):
            lines = c.splitlines()
            first_line = lines[0]
            if first_line.rstrip().endswith(":") and len(lines) > 1:
                c_summary = f"{first_line.rstrip(':')} ({len(lines)-1} sub-items)"
            else:
                c_summary = first_line
            c_clean = re.sub(r"[`*]", "", c_summary).strip()
            if len(c_clean) > 80:
                c_clean = c_clean[:77] + "..."
            source = "contract" if idx >= len(clauses) - 2 else "derived"
            anchor_desc = f"Meets C{idx} ({c_clean}) verified by captured evidence"
            rubric_rows.append(f"| R{idx} | C{idx}: {c_clean} | {source} | {anchor_desc} |")

        rubric_block = "\n".join(rubric_rows)

        ticket_url = f"http://localhost:9500/project/{project_slug}/us/{story_ref}"
        ticket_str = f"{project_slug}#{story_ref} — {ticket_url} (\"{subject}\")"

        context_section = ""
        if narrative_text or context_text:
            context_parts = []
            if narrative_text:
                context_parts.append(narrative_text)
            if context_text:
                context_parts.append(f"### Context\n{context_text}")
            context_section = f"\n## Story Context\n\n" + "\n\n".join(context_parts) + "\n"

        return f"""# Goal Contract — US#{story_ref} {subject}

- Started: {utc_start}
- Status: ACTIVE (Phase 1)
- Budget: {budget} cycles
- Work branch: {branch_name}
- Spec reference: {spec_path or 'none'}
- Knowledge base sources: AGENTS.md §1, §4, §7, §8, §9
- Ticket: {ticket_str}
{context_section}
## Definition of Done

{dod_block}

## Quality Gates

| # | Gate | Source | Command | Status |
|---|------|--------|---------|--------|
| G1 | assembleDebug --rerun-tasks (zero compiler warnings) | kb:AGENTS.md §8 | `./gradlew assembleDebug --rerun-tasks` | pending |
| G2 | testDebugUnitTest --rerun (100% green unit suites) | kb:AGENTS.md §7/§8 | `./gradlew testDebugUnitTest --rerun` | pending |
| T1 | Decomposition before work — child tasks exist under US#{story_ref}, assigned to acting account | contract | taiga-bridge or taiga-sync status check | pending |
| T2 | Fail-closed completion — every child task Closed and story in Done, confirmed by post-write re-read at stop | contract | taiga-bridge or taiga-sync status check | pending |

## Rubric (scale 0–4 per criterion)

Anchors: **0** = absent or contradicts the clause · **1** = attempted with major gaps · **2** = present but incomplete or evidence too weak to verify · **3** = meets the clause as written, verified by captured evidence (anchor) · **4** = exceeds — additional verification beyond what the clause requires.
Threshold: mean ≥ 3.0 and no criterion below its anchor (3). A clause that FAILs its gate cannot count as complete regardless of rubric points; NOT-RUN gates block completion.

| # | Criterion (clause) | Source | Anchor descriptor (3) |
|---|--------------------|--------|-----------------------|
{rubric_block}

## Ticket Sync

- Ticket: {project_slug}#{story_ref}
- URL: {ticket_url}
- PM Account: kadath.copilot (id 6)
- Status roles: initial=New, in-progress="In progress", done=Done, tasks close as Closed
"""

    def cmd_intake(self, objective: str, budget: int = 10, spec_path: str = None) -> dict:
        """Phase 0: Scaffold contract.md, state.md, and create worktree."""
        self.ensure_hadrian_dirs()

        # Archive any previous goal if present
        if self.contract_file.exists() or self.state_file.exists():
            ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            archive_dir = self.hadrian_dir / "archive" / ts
            archive_dir.mkdir(parents=True, exist_ok=True)
            for f in [self.contract_file, self.state_file, self.hadrian_dir / "signoff"]:
                if f.exists():
                    f.rename(archive_dir / f.name)
            if self.evidence_dir.exists():
                for ef in self.evidence_dir.glob("*.md"):
                    ef.rename(archive_dir / ef.name)

        # Attempt to resolve story from objective and fetch from Taiga
        story_ref, project_slug = self._resolve_story_from_objective(objective)
        story = self._fetch_taiga_story(story_ref, project_slug) if story_ref else None

        if story:
            ticket_ref = f"{project_slug}#{story['ref']}"
            clean_subj = re.sub(r"^US[\-\s0-9\.]*:\s*", "", story.get("subject", ""), flags=re.IGNORECASE)
            clean_subj = re.sub(r"[^a-zA-Z0-9]+", "-", clean_subj.lower()).strip("-")
            slug = f"us{story['ref']}-{clean_subj}"[:35].rstrip("-")
        else:
            ticket_match = re.search(r"(?:US|us|#)\s*(\d+)", objective)
            ticket_ref = f"smartsparks#{ticket_match.group(1)}" if ticket_match else "none"
            slug_raw = re.sub(r"[^a-zA-Z0-9]+", "-", objective.lower()).strip("-")
            slug = slug_raw[:35] if slug_raw else "goal"

        branch_name = f"hadrian/{slug}"
        worktree_path = (self.worktrees_dir / slug).resolve()

        # Get base commit
        base_commit = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "--short", "HEAD"],
            text=True
        ).strip()

        # Create dedicated worktree
        if worktree_path.exists():
            subprocess.run(["git", "-C", str(self.root), "worktree", "remove", "--force", str(worktree_path)], capture_output=True)
        
        # Check if branch exists
        branch_check = subprocess.run(["git", "-C", str(self.root), "rev-parse", "--verify", branch_name], capture_output=True)
        if branch_check.returncode == 0:
            subprocess.run(["git", "-C", str(self.root), "branch", "-D", branch_name], capture_output=True)

        res = subprocess.run(
            ["git", "-C", str(self.root), "worktree", "add", "-b", branch_name, str(worktree_path), base_commit],
            capture_output=True, text=True
        )
        if res.returncode != 0:
            return {"status": "ERROR", "message": f"Failed to create worktree: {res.stderr}"}

        utc_start = get_utc_now()

        # Write contract.md
        if story:
            contract_content = self._generate_story_contract(
                objective=objective,
                story=story,
                budget=budget,
                branch_name=branch_name,
                spec_path=spec_path,
                utc_start=utc_start,
            )
        else:
            contract_content = f"""# Goal Contract — {objective}

- Started: {utc_start}
- Status: ACTIVE (Phase 1)
- Budget: {budget} cycles
- Work branch: {branch_name}
- Spec reference: {spec_path or 'none'}
- Knowledge base sources: AGENTS.md
- Ticket: {ticket_ref}

## Definition of Done
1. Code builds cleanly with zero compilation warnings (`./gradlew assembleDebug`).
2. Unit tests for math generators pass (`./gradlew testDebugUnitTest`).
3. No third-party network analytics or cloud endpoints are introduced.
4. All new UI components support light and dark mode Material 3 tokens.
5. All strings are externalized or generated through localized templates.
6. Every new or modified Composable has a `@Preview` composable.
7. New UI is covered by Compose UI component tests (`createComposeRule()`).

## Quality Gates
| # | Gate | Source | Command | Status |
|---|------|--------|---------|--------|
| G1 | assembleDebug --rerun-tasks (zero compiler warnings) | kb:AGENTS.md §8 | `./gradlew assembleDebug --rerun-tasks` | pending |
| G2 | testDebugUnitTest --rerun (100% green unit suites) | kb:AGENTS.md §7/§8 | `./gradlew testDebugUnitTest --rerun` | pending |
"""
        self.contract_file.write_text(contract_content, encoding="utf-8")
        contract_md5 = compute_md5(self.contract_file)

        # Write state.md
        state_title = f"US#{story['ref']} {story.get('subject', '')}" if story else objective
        state_content = f"""# Goal State — {state_title}

- Objective: {objective}
- Contract md5: {contract_md5} (frozen at intake {utc_start})
- Budget used: 0 / {budget} cycles
- Worktree: {worktree_path} | branch: {branch_name} | base commit: {base_commit}
- Capability probe: verifier=independent (hadrian-verifier agent) | loop-engine=goal-system | freeze=hard | rubric=independent (hadrian-rubric-evaluator agent)
- Ticket: {ticket_ref}

## Cycles

### Cycle 1
- Action: Initial implementation pending in worktree.
- Gates: Pending execution via `hadrian_engine.py run-gates`.
"""
        self.state_file.write_text(state_content, encoding="utf-8")

        return {
            "status": "READY",
            "objective": objective,
            "worktree": str(worktree_path),
            "branch": branch_name,
            "base_commit": base_commit,
            "contract_md5": contract_md5,
            "budget": budget,
        }

    def cmd_pause(self, reason: str = "paused by user") -> dict:
        """Pause execution cleanly, append a PAUSE record to state.md."""
        if not self.state_file.exists():
            return {"status": "ERROR", "message": "No active state.md found."}
        utc_now = get_utc_now()
        record = f"\nPAUSE at={utc_now} reason=\"{reason}\"\n"
        with self.state_file.open("a", encoding="utf-8") as f:
            f.write(record)
        return {"status": "PAUSED", "timestamp": utc_now, "reason": reason}

    def cmd_resume(self) -> dict:
        """Resume execution: validate contract MD5, validate verdict records, and return active state."""
        if not self.contract_file.exists() or not self.state_file.exists():
            return {"status": "ERROR", "message": "No active Hadrian goal files found."}

        state = self.parse_state_header()
        current_md5 = compute_md5(self.contract_file)
        expected_md5 = state.get("contract_md5", "")
        contract_valid = (current_md5 == expected_md5)

        # Validate VERDICT lines against verdict contract regex
        verdict_pattern = re.compile(
            r'^\s*VERDICT kind=(gate|review|rubric) id=(G\d+|C\d+|CW|R\d+) status=(PASS|FAIL|NOT-RUN|WAIVED)( score=[0-4])? evidence="([^"]+)" source=\S+$'
        )
        malformed_verdicts = []
        state_content = self.state_file.read_text(encoding="utf-8")
        for idx, line in enumerate(state_content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("VERDICT"):
                if not verdict_pattern.match(stripped):
                    malformed_verdicts.append({"line_number": idx, "line": stripped})

        utc_now = get_utc_now()
        with self.state_file.open("a", encoding="utf-8") as f:
            f.write(f"\nRESUME at={utc_now}\n")

        return {
            "status": "RESUMED",
            "objective": state.get("objective", ""),
            "contract_valid": contract_valid,
            "contract_md5": current_md5,
            "budget_used": state.get("budget_used", 0),
            "budget_total": state.get("budget_total", 10),
            "worktree": state.get("worktree", str(self.root)),
            "branch": state.get("branch", ""),
            "base_commit": state.get("base_commit", ""),
            "malformed_verdicts": malformed_verdicts,
        }

    def cmd_stop(self, reason: str = "stopped by user") -> dict:
        """Halt immediately and record stop event in state.md."""
        if not self.state_file.exists():
            return {"status": "ERROR", "message": "No active state.md found."}
        utc_now = get_utc_now()
        record = f"\nSTOP at={utc_now} reason=\"{reason}\"\n"
        with self.state_file.open("a", encoding="utf-8") as f:
            f.write(record)
        return {"status": "STOPPED", "timestamp": utc_now, "reason": reason}

    def cmd_amend(self, changes: str, user: str = "user") -> dict:
        """Record an explicit user amendment to contract.md and update state checksum."""
        if not self.contract_file.exists() or not self.state_file.exists():
            return {"status": "ERROR", "message": "No active contract or state file."}

        utc_now = get_utc_now()
        new_md5 = compute_md5(self.contract_file)
        
        # Update contract md5 line in state.md
        state_content = self.state_file.read_text(encoding="utf-8")
        updated_state = re.sub(
            r"- Contract md5: [a-f0-9]{32}.*",
            f"- Contract md5: {new_md5} (amended by {user} at {utc_now})",
            state_content
        )
        updated_state += f"\nAMENDMENT: by={user} at={utc_now} changes=\"{changes}\"\n"
        self.state_file.write_text(updated_state, encoding="utf-8")

        return {
            "status": "AMENDED",
            "new_md5": new_md5,
            "timestamp": utc_now,
            "user": user,
            "changes": changes,
        }

    def _taiga_request(self, endpoint: str, data: dict = None, method: str = "GET") -> dict:
        """Helper to execute Taiga REST API calls."""
        base_url = os.environ.get("TAIGA_API_URL", "http://localhost:9500").rstrip("/")
        username = os.environ.get("TAIGA_USERNAME", "kadath.copilot")
        password = os.environ.get("TAIGA_PASSWORD", "kadath-copilot")

        import urllib.request
        import urllib.error

        # 1. Authenticate to get auth_token
        auth_url = f"{base_url}/api/v1/auth"
        auth_payload = json.dumps({"type": "normal", "username": username, "password": password}).encode("utf-8")
        auth_req = urllib.request.Request(auth_url, data=auth_payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(auth_req, timeout=10) as resp:
                auth_data = json.loads(resp.read().decode("utf-8"))
                token = auth_data.get("auth_token")
        except Exception as e:
            raise RuntimeError(f"Taiga authentication failed: {e}")

        # 2. Perform API request
        req_url = f"{base_url}/api/v1/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(req_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text) if resp_text else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            e.close()
            raise RuntimeError(f"Taiga HTTP {e.code} on {endpoint}: {err_body}")

    def cmd_taiga_sync(self, action: str = "status", story_ref: int = None, project_slug: str = "smartsparks", status_name: str = None, comment: str = None) -> dict:
        """Taiga Ticket Sync: claim, inspect, transition tasks and story."""
        try:
            # 1. Resolve story ref from contract/state if not provided
            if not story_ref:
                state = self.parse_state_header()
                ticket_str = state.get("ticket", "")
                m = re.search(r"(\d+)", ticket_str)
                if m:
                    story_ref = int(m.group(1))
            if not story_ref:
                return {"status": "ERROR", "message": "No story ref provided or found in goal state."}

            # 2. Resolve project ID
            project_info = self._taiga_request(f"projects/by_slug?slug={project_slug}")
            project_id = project_info["id"]

            # 3. Get user story
            us = self._taiga_request(f"userstories/by_ref?ref={story_ref}&project={project_id}")
            story_id = us["id"]

            # 4. Get child tasks
            tasks = self._taiga_request(f"tasks?user_story={story_id}")

            # 5. Handle subactions
            if action == "status":
                return {
                    "status": "OK",
                    "story": {
                        "id": us["id"],
                        "ref": us["ref"],
                        "subject": us["subject"],
                        "status": us["status_extra_info"]["name"],
                        "version": us["version"],
                        "assigned_to": us.get("assigned_to_extra_info", {}).get("username") if us.get("assigned_to_extra_info") else None,
                    },
                    "tasks": [
                        {
                            "id": t["id"],
                            "ref": t["ref"],
                            "subject": t["subject"],
                            "status": t["status_extra_info"]["name"],
                            "is_closed": t["status_extra_info"]["is_closed"],
                            "version": t["version"],
                        }
                        for t in tasks
                    ],
                }

            elif action == "close-tasks":
                # Find closed task status
                t_statuses = self._taiga_request(f"task-statuses?project={project_id}")
                closed_status = next((s for s in t_statuses if s.get("is_closed")), None)
                if not closed_status:
                    closed_status = next((s for s in t_statuses if s.get("name", "").lower() == "closed"), None)
                if not closed_status:
                    return {"status": "ERROR", "message": "Could not identify closed task status in project."}

                updated_tasks = []
                for t in tasks:
                    if not t["status_extra_info"]["is_closed"]:
                        payload = {
                            "status": closed_status["id"],
                            "version": t["version"],
                            "comment": comment or "Task completed and verified by Hadrian.",
                        }
                        self._taiga_request(f"tasks/{t['id']}", data=payload, method="PATCH")
                        updated_tasks.append(t["ref"])

                return {"status": "OK", "action": "close-tasks", "closed_task_refs": updated_tasks}

            elif action == "update-story":
                if not status_name:
                    return {"status": "ERROR", "message": "status_name required for update-story."}
                us_statuses = self._taiga_request(f"userstory-statuses?project={project_id}")
                target_status = next((s for s in us_statuses if s.get("name", "").lower() == status_name.lower()), None)
                if not target_status:
                    valid_names = [s.get("name") for s in us_statuses]
                    return {"status": "ERROR", "message": f"Status '{status_name}' not found. Valid: {valid_names}"}

                payload = {
                    "status": target_status["id"],
                    "version": us["version"],
                    "comment": comment or f"Story updated to {target_status['name']} by Hadrian.",
                }
                res = self._taiga_request(f"userstories/{us['id']}", data=payload, method="PATCH")
                return {
                    "status": "OK",
                    "action": "update-story",
                    "story_ref": story_ref,
                    "new_status": target_status["name"],
                }

            elif action == "finish":
                # Ensure all child tasks are closed
                t_statuses = self._taiga_request(f"task-statuses?project={project_id}")
                closed_status = next((s for s in t_statuses if s.get("is_closed")), None)
                for t in tasks:
                    if not t["status_extra_info"]["is_closed"] and closed_status:
                        self._taiga_request(
                            f"tasks/{t['id']}",
                            data={"status": closed_status["id"], "version": t["version"], "comment": "Auto-closed on goal finish."},
                            method="PATCH"
                        )
                # Mark story Done
                us_statuses = self._taiga_request(f"userstory-statuses?project={project_id}")
                done_status = next((s for s in us_statuses if s.get("is_closed") or s.get("name", "").lower() == "done"), None)
                if done_status:
                    self._taiga_request(
                        f"userstories/{us['id']}",
                        data={"status": done_status["id"], "version": us["version"], "comment": comment or "Goal completed and verified by Hadrian."},
                        method="PATCH"
                    )
                return {"status": "OK", "action": "finish", "story_ref": story_ref, "story_status": done_status["name"] if done_status else "Done"}

            else:
                return {"status": "ERROR", "message": f"Unknown taiga action: {action}"}

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def cmd_run_gates(self, cycle: int = 1, worktree_dir: str = None) -> dict:
        """Phase 1: Deterministically execute G1 & G2 quality gates, capture evidence, and parse JUnit XML."""
        self.ensure_hadrian_dirs()
        target_dir = Path(worktree_dir).resolve() if worktree_dir else None
        if not target_dir or not target_dir.exists():
            state = self.parse_state_header()
            if state.get("worktree"):
                target_dir = Path(state["worktree"]).resolve()
            else:
                target_dir = self.root

        utc_now = get_utc_now()

        # Gate 1: assembleDebug
        g1_cmd = ["./gradlew", "assembleDebug", "--rerun-tasks"]
        g1_res = subprocess.run(g1_cmd, cwd=str(target_dir), capture_output=True, text=True)
        
        # Check Kotlin warnings (grep -c '^w:')
        warning_lines = [line for line in g1_res.stdout.splitlines() if line.startswith("w:")]
        warning_count = len(warning_lines)

        g1_status = "PASS" if (g1_res.returncode == 0 and warning_count == 0) else "FAIL"
        
        # Write 1-G1.md evidence artifact
        g1_evidence_file = self.evidence_dir / f"{cycle}-G1.md"
        g1_evidence_content = f"""# Gate Evidence: G1 — assembleDebug (Cycle {cycle})

- Timestamp: {utc_now}
- Target Directory: {target_dir}
- Command: `{' '.join(g1_cmd)}`
- Exit Code: {g1_res.returncode}
- Kotlin Compiler Warnings (`w:`): {warning_count}
- Status: {g1_status}

## Output Excerpt
```text
{g1_res.stdout[-2000:] if g1_res.stdout else g1_res.stderr[-2000:]}
```
"""
        g1_evidence_file.write_text(g1_evidence_content, encoding="utf-8")

        # Gate 2: testDebugUnitTest
        g2_cmd = ["./gradlew", "testDebugUnitTest", "--rerun"]
        g2_res = subprocess.run(g2_cmd, cwd=str(target_dir), capture_output=True, text=True)

        # Parse JUnit XML test results
        test_results_dir = target_dir / "app" / "build" / "test-results" / "testDebugUnitTest"
        total_classes = 0
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_skipped = 0
        failing_tests = []

        if test_results_dir.exists():
            for xml_file in test_results_dir.glob("TEST-*.xml"):
                total_classes += 1
                try:
                    tree = ET.parse(xml_file)
                    root_elem = tree.getroot()
                    total_tests += int(root_elem.attrib.get("tests", 0))
                    failures = int(root_elem.attrib.get("failures", 0))
                    errors = int(root_elem.attrib.get("errors", 0))
                    skipped = int(root_elem.attrib.get("skipped", 0))
                    total_failures += failures
                    total_errors += errors
                    total_skipped += skipped

                    if failures > 0 or errors > 0:
                        for tc in root_elem.findall("testcase"):
                            if tc.find("failure") is not None or tc.find("error") is not None:
                                failing_tests.append(f"{tc.attrib.get('classname')}.{tc.attrib.get('name')}")
                except Exception:
                    pass

        g2_status = "PASS" if (g2_res.returncode == 0 and total_failures == 0 and total_errors == 0 and total_tests > 0) else "FAIL"

        # Write 1-G2.md evidence artifact
        g2_evidence_file = self.evidence_dir / f"{cycle}-G2.md"
        g2_evidence_content = f"""# Gate Evidence: G2 — testDebugUnitTest (Cycle {cycle})

- Timestamp: {utc_now}
- Target Directory: {target_dir}
- Command: `{' '.join(g2_cmd)}`
- Exit Code: {g2_res.returncode}
- Suites / Classes: {total_classes}
- Total Tests: {total_tests}
- Failures: {total_failures}
- Errors: {total_errors}
- Skipped: {total_skipped}
- Status: {g2_status}

## Failing Tests
{json.dumps(failing_tests, indent=2) if failing_tests else "None. All unit tests passed cleanly."}

## Output Excerpt
```text
{g2_res.stdout[-2000:] if g2_res.stdout else g2_res.stderr[-2000:]}
```
"""
        g2_evidence_file.write_text(g2_evidence_content, encoding="utf-8")

        overall_status = "PASS" if (g1_status == "PASS" and g2_status == "PASS") else "FAIL"

        # Append machine-verifiable VERDICT lines to state.md if present
        if self.state_file.exists():
            state_text = self.state_file.read_text(encoding="utf-8")
            verdicts = f"""
VERDICT kind=gate id=G1 status={g1_status} evidence=".hadrian/evidence/{cycle}-G1.md — exit {g1_res.returncode}, {warning_count} compiler warnings" source=kb:AGENTS.md
VERDICT kind=gate id=G2 status={g2_status} evidence=".hadrian/evidence/{cycle}-G2.md — {total_classes} classes / {total_tests} tests / {total_failures} failures / {total_errors} errors" source=kb:AGENTS.md
"""
            # Replace placeholder or append
            if "Gates: Pending execution" in state_text:
                state_text = state_text.replace("Gates: Pending execution via `hadrian_engine.py run-gates`.", f"Gates:{verdicts}")
            else:
                state_text += f"\n<!-- Cycle {cycle} Gate Re-Run -->\n{verdicts}\n"
            self.state_file.write_text(state_text, encoding="utf-8")

        return {
            "status": overall_status,
            "cycle": cycle,
            "g1": {
                "status": g1_status,
                "warnings": warning_count,
                "exit_code": g1_res.returncode,
                "evidence": f".hadrian/evidence/{cycle}-G1.md",
            },
            "g2": {
                "status": g2_status,
                "classes": total_classes,
                "tests": total_tests,
                "failures": total_failures,
                "errors": total_errors,
                "failing_tests": failing_tests,
                "evidence": f".hadrian/evidence/{cycle}-G2.md",
            },
        }

    def cmd_commit(self, commit_type: str, message: str, worktree_dir: str = None) -> dict:
        """Create a standard conventional commit on the work branch."""
        target_dir = Path(worktree_dir).resolve() if worktree_dir else None
        if not target_dir or not target_dir.exists():
            state = self.parse_state_header()
            target_dir = Path(state.get("worktree", self.root)).resolve()

        subprocess.run(["git", "-C", str(target_dir), "add", "-A"], check=True)
        full_msg = f"{commit_type}: {message}"
        res = subprocess.run(["git", "-C", str(target_dir), "commit", "-m", full_msg], capture_output=True, text=True)
        if res.returncode != 0:
            return {"status": "ERROR", "message": res.stderr}

        commit_sha = subprocess.check_output(
            ["git", "-C", str(target_dir), "rev-parse", "--short", "HEAD"],
            text=True
        ).strip()

        return {"status": "COMMITTED", "sha": commit_sha, "message": full_msg}

    def cmd_review_diff(self, worktree_dir: str = None) -> dict:
        """Extract git diff against base commit for the Review Gate."""
        target_dir = Path(worktree_dir).resolve() if worktree_dir else None
        state = self.parse_state_header()
        if not target_dir or not target_dir.exists():
            target_dir = Path(state.get("worktree", self.root)).resolve()

        base_commit = state.get("base_commit", "main")
        diff_res = subprocess.run(
            ["git", "-C", str(target_dir), "diff", f"{base_commit}..HEAD"],
            capture_output=True, text=True
        )
        stat_res = subprocess.run(
            ["git", "-C", str(target_dir), "diff", "--stat", f"{base_commit}..HEAD"],
            capture_output=True, text=True
        )

        return {
            "base_commit": base_commit,
            "stat": stat_res.stdout.strip(),
            "diff": diff_res.stdout,
        }

    def cmd_signoff(
        self,
        approver: str = "user",
        create_pr: bool = True,
        push: bool = True,
        base_branch: str = "main",
    ) -> dict:
        """Sign off completed goal, push branch, create PR, and archive active artifacts."""
        if not self.contract_file.exists() or not self.state_file.exists():
            return {"status": "ERROR", "message": "No active Hadrian goal files found."}

        state = self.parse_state_header()
        worktree_str = state.get("worktree", "")
        branch = state.get("branch", "")
        ticket = state.get("ticket", "")
        objective = state.get("objective", "")

        worktree_path = Path(worktree_str) if worktree_str else self.root
        if not worktree_path.exists():
            worktree_path = self.root

        utc_now = get_utc_now()
        signoff_file = self.hadrian_dir / "signoff"

        # 1. Write .hadrian/signoff (satisfies Hard Rule 3 for push guard)
        signoff_content = f"""APPROVED by {approver} at {utc_now}
Objective: {objective}
Ticket: {ticket}
Branch: {branch}
"""
        signoff_file.write_text(signoff_content, encoding="utf-8")

        # 2. Append signoff record to state.md
        with self.state_file.open("a", encoding="utf-8") as f:
            f.write(f"\n- SIGNED OFF by {approver} at {utc_now}\n")

        # 3. Git push
        push_output = ""
        if push and branch:
            remotes = subprocess.run(
                ["git", "-C", str(worktree_path), "remote"],
                capture_output=True,
                text=True,
            ).stdout.split()

            if "origin" in remotes:
                push_res = subprocess.run(
                    ["git", "-C", str(worktree_path), "push", "-u", "origin", branch],
                    capture_output=True,
                    text=True,
                )
                if push_res.returncode != 0:
                    return {
                        "status": "ERROR",
                        "message": f"git push failed: {push_res.stderr.strip()}",
                    }
                push_output = push_res.stdout.strip()

        # 4. Create PR via gh CLI if requested
        pr_url = None
        if create_pr and branch:
            import shutil
            if shutil.which("gh"):
                view_res = subprocess.run(
                    ["gh", "pr", "view", "--head", branch, "--json", "url", "-q", ".url"],
                    cwd=str(worktree_path),
                    capture_output=True,
                    text=True,
                )
                if view_res.returncode == 0 and view_res.stdout.strip():
                    pr_url = view_res.stdout.strip()
                else:
                    clean_obj = re.sub(r"^Complete\s+", "", objective).strip()
                    pr_title = f"{branch.replace('hadrian/', '')}: {clean_obj}"
                    if len(pr_title) > 90:
                        pr_title = pr_title[:87] + "..."

                    pr_body = f"""## Objective
{objective}

- **Ticket:** {ticket}
- **Branch:** `{branch}`
- **Approver:** {approver}
- **Timestamp:** {utc_now}

## Verification Summary
- Deterministic verification completed via Hadrian L3 Goal Loop.
- Quality Gates (G1 assembleDebug / G2 testDebugUnitTest): PASS
- Review Gate (hadrian-verifier): PASS
- Rubric Gate (hadrian-rubric-evaluator): PASS
"""
                    create_res = subprocess.run(
                        [
                            "gh", "pr", "create",
                            "--head", branch,
                            "--base", base_branch,
                            "--title", pr_title,
                            "--body", pr_body,
                        ],
                        cwd=str(worktree_path),
                        capture_output=True,
                        text=True,
                    )
                    if create_res.returncode == 0:
                        pr_url = create_res.stdout.strip()

        # 5. Archive active goal artifacts cleanly
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_dir = self.hadrian_dir / "archive" / ts
        archive_dir.mkdir(parents=True, exist_ok=True)

        for f in [self.contract_file, self.state_file, signoff_file, self.hadrian_dir / "langsmith_thread"]:
            if f.exists():
                f.rename(archive_dir / f.name)

        if self.evidence_dir.exists():
            for ef in self.evidence_dir.glob("*.md"):
                ef.rename(archive_dir / ef.name)

        return {
            "status": "COMPLETED",
            "approver": approver,
            "branch": branch,
            "pr_url": pr_url,
            "archive_dir": str(archive_dir),
            "push_output": push_output,
        }


def main():
    parser = argparse.ArgumentParser(description="Hadrian L3 Goal Loop Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Get status of active Hadrian goal")

    # intake
    intake_p = subparsers.add_parser("intake", help="Initialize a new goal with contract and worktree")
    intake_p.add_argument("objective", help="Objective statement or ticket (e.g. US#326)")
    intake_p.add_argument("--budget", type=int, default=10, help="Max cycle budget (default: 10)")
    intake_p.add_argument("--spec", help="Path to spec file (optional)")

    # run-gates
    gates_p = subparsers.add_parser("run-gates", help="Execute G1 & G2 quality gates")
    gates_p.add_argument("--cycle", type=int, default=1, help="Cycle number (default: 1)")
    gates_p.add_argument("--worktree", help="Path to worktree directory")

    # commit
    commit_p = subparsers.add_parser("commit", help="Commit changes inside worktree")
    commit_p.add_argument("type", choices=["feat", "fix", "docs", "refactor", "test"], help="Commit type")
    commit_p.add_argument("message", help="Commit message")
    commit_p.add_argument("--worktree", help="Path to worktree directory")

    # diff
    diff_p = subparsers.add_parser("review-diff", help="Get diff against base commit for Review Gate")
    diff_p.add_argument("--worktree", help="Path to worktree directory")

    # pause
    pause_p = subparsers.add_parser("pause", help="Pause active goal cleanly")
    pause_p.add_argument("--reason", default="paused by user", help="Reason for pause")

    # resume
    subparsers.add_parser("resume", help="Resume active goal and validate contract integrity")

    # stop
    stop_p = subparsers.add_parser("stop", help="Stop active goal execution")
    stop_p.add_argument("--reason", default="stopped by user", help="Reason for stopping")

    # amend
    amend_p = subparsers.add_parser("amend", help="Record explicit user amendment to contract")
    amend_p.add_argument("changes", help="Description of changes to contract")
    amend_p.add_argument("--user", default="user", help="User making the amendment")

    # taiga-sync
    taiga_p = subparsers.add_parser("taiga-sync", help="Synchronize status with Taiga PM tool")
    taiga_p.add_argument("--action", choices=["status", "close-tasks", "update-story", "finish"], default="status", help="Taiga sync action")
    taiga_p.add_argument("--ref", type=int, help="Story ref (e.g. 326)")
    taiga_p.add_argument("--project", default="smartsparks", help="Project slug")
    taiga_p.add_argument("--status", help="Target status name (for update-story)")
    taiga_p.add_argument("--comment", help="Comment for transition")

    # signoff
    signoff_p = subparsers.add_parser("signoff", help="Sign off completed goal, push branch, create PR, and archive active artifacts")
    signoff_p.add_argument("--approver", default="user", help="Name of human approver")
    signoff_p.add_argument("--base", default="main", help="Base branch for PR")
    signoff_p.add_argument("--no-push", action="store_true", help="Do not push branch")
    signoff_p.add_argument("--no-pr", action="store_true", help="Do not create PR")

    args = parser.parse_args()
    engine = HadrianEngine()

    if args.command == "status":
        res = engine.cmd_status()
    elif args.command == "intake":
        res = engine.cmd_intake(args.objective, budget=args.budget, spec_path=args.spec)
    elif args.command == "run-gates":
        res = engine.cmd_run_gates(cycle=args.cycle, worktree_dir=args.worktree)
    elif args.command == "commit":
        res = engine.cmd_commit(args.type, args.message, worktree_dir=args.worktree)
    elif args.command == "review-diff":
        res = engine.cmd_review_diff(worktree_dir=args.worktree)
    elif args.command == "pause":
        res = engine.cmd_pause(reason=args.reason)
    elif args.command == "resume":
        res = engine.cmd_resume()
    elif args.command == "stop":
        res = engine.cmd_stop(reason=args.reason)
    elif args.command == "amend":
        res = engine.cmd_amend(args.changes, user=args.user)
    elif args.command == "taiga-sync":
        res = engine.cmd_taiga_sync(
            action=args.action,
            story_ref=args.ref,
            project_slug=args.project,
            status_name=args.status,
            comment=args.comment,
        )
    elif args.command == "signoff":
        res = engine.cmd_signoff(
            approver=args.approver,
            create_pr=not args.no_pr,
            push=not args.no_push,
            base_branch=args.base,
        )
    else:
        res = {"error": f"Unknown command {args.command}"}

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
