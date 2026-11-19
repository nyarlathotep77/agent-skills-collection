// Hadrian guard — OpenCode v2 plugin adapter for the L3 goal loop.
import { existsSync, readdirSync } from "node:fs";
import { Plugin } from "@opencode/plugin";

const CONTRACT = ".hadrian/contract.md";
const SIGNOFF = ".hadrian/signoff";
const WORKTREES = ".hadrian/worktrees";
const PUSH_RE = /(^|[;&|]\s*|\s)git\s+push(\s|$)/;

export default Plugin.define({
  id: "hadrian.guard",
  async setup(ctx) {
    const root = ctx.location?.directory;

    await ctx.tool.hook("execute.before", (event) => {
      if (!root) return;
      if (["edit", "write"].includes(event.tool)) {
        const p = String(event.input?.filePath ?? "");
        const target = p.startsWith("/") ? p : `${root}/${p}`;

        // Rule 1: Contract freeze
        if (p.endsWith(CONTRACT)) {
          if (existsSync(target)) {
            throw new Error(
              "HADRIAN GUARD: the goal contract is frozen (L3 invariant). Propose amendments in the escalation report; a human applies them."
            );
          }
        }

        // Rule 12: Worktree write protection
        const wtDir = `${root}/${WORKTREES}`;
        const contractFile = `${root}/${CONTRACT}`;
        if (existsSync(contractFile) && existsSync(wtDir)) {
          let hasWorktrees = false;
          try {
            hasWorktrees = readdirSync(wtDir).length > 0;
          } catch {}

          if (hasWorktrees) {
            const isHadrianInternal = p.startsWith(".hadrian/") || p.includes("/.hadrian/");
            const isInWorktree = p.startsWith(".hadrian/worktrees/") || p.includes("/.hadrian/worktrees/");

            if (!isHadrianInternal && !isInWorktree) {
              throw new Error(
                "HADRIAN GUARD: Direct file modification in root repository checkout is blocked while worktree isolation is active (Hard Rule 12). Execute all edits inside .hadrian/worktrees/<slug>/."
              );
            }
          }
        }
      }
    });

    await ctx.shell.hook("create.before", (event) => {
      const cmd = String(event.command ?? "");
      if (PUSH_RE.test(cmd)) {
        const base = event.cwd || root;
        if (existsSync(`${base}/${CONTRACT}`) && !existsSync(`${base}/${SIGNOFF}`)) {
          throw new Error(
            "HADRIAN GUARD: git push is blocked while a goal contract is active without acceptance (Hard Rule 3). Review the diff; on approval create .hadrian/signoff (or stop the goal)."
          );
        }
      }
    });
  },
});
