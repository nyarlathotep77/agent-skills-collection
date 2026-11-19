// Hadrian Engine Plugin for OpenCode
// Encapsulates deterministic L3 goal loop automation and security invariants.
import { existsSync, readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { tool } from "@opencode/plugin";

const CONTRACT = ".hadrian/contract.md";
const SIGNOFF = ".hadrian/signoff";
const WORKTREES = ".hadrian/worktrees";
const PUSH_RE = /(^|[;&|]\s*|\s)git\s+push(\s|$)/;

function getScriptPath(root) {
  // Try relative to skill directory first, then root fallback
  const candidate = join(root, ".agents", "skills", "hadrian", "scripts", "engine.py");
  if (existsSync(candidate)) return candidate;
  const devCandidate = join(root, "scripts", "engine.py");
  if (existsSync(devCandidate)) return devCandidate;
  return "/home/davide/dev/workspace/public/ai/agent-skills-collection/hadrian/scripts/engine.py";
}

function runEngineCommand(root, args) {
  const script = getScriptPath(root);
  const proc = spawnSync("python3", [script, ...args], {
    cwd: root,
    encoding: "utf-8",
  });
  if (proc.error) {
    return JSON.stringify({ status: "ERROR", message: proc.error.message });
  }
  return proc.stdout || proc.stderr;
}

export const HadrianPlugin = async (ctx) => {
  const root = ctx.directory || process.cwd();

  return {
    // 1. Native Tools exposed to the LLM
    tool: {
      hadrian_run_gates: tool({
        description: "Deterministically execute G1 (assembleDebug) and G2 (testDebugUnitTest) quality gates. Parses JUnit XML test reports, checks for zero compiler warnings, captures evidence files in .hadrian/evidence/, and updates .hadrian/state.md.",
        args: {
          cycle: tool.schema.number().optional().describe("Current cycle number (default: 1)"),
          worktree: tool.schema.string().optional().describe("Worktree path to test"),
        },
        async execute(args) {
          const cycle = String(args.cycle || 1);
          const cliArgs = ["run-gates", "--cycle", cycle];
          if (args.worktree) {
            cliArgs.push("--worktree", args.worktree);
          }
          return runEngineCommand(root, cliArgs);
        },
      }),

      hadrian_status: tool({
        description: "Get the current active status, contract MD5 verification, and cycle budget of the active Hadrian goal.",
        args: {},
        async execute() {
          return runEngineCommand(root, ["status"]);
        },
      }),

      hadrian_review_diff: tool({
        description: "Get the git diff against the base commit for the Review Gate.",
        args: {
          worktree: tool.schema.string().optional().describe("Worktree path"),
        },
        async execute(args) {
          const cliArgs = ["review-diff"];
          if (args.worktree) {
            cliArgs.push("--worktree", args.worktree);
          }
          return runEngineCommand(root, cliArgs);
        },
      }),

      hadrian_commit: tool({
        description: "Commit verified changes on the work branch following conventional commit format.",
        args: {
          type: tool.schema.enum(["feat", "fix", "docs", "refactor", "test"]).describe("Commit type"),
          message: tool.schema.string().describe("Commit message"),
          worktree: tool.schema.string().optional().describe("Worktree path"),
        },
        async execute(args) {
          const cliArgs = ["commit", args.type, args.message];
          if (args.worktree) {
            cliArgs.push("--worktree", args.worktree);
          }
          return runEngineCommand(root, cliArgs);
        },
      }),

      hadrian_intake: tool({
        description: "Phase 0: Scaffold a new L3 goal contract, state, and isolated worktree.",
        args: {
          objective: tool.schema.string().describe("Goal objective or ticket (e.g. US#326)"),
          budget: tool.schema.number().optional().describe("Max cycle budget (default: 10)"),
          spec: tool.schema.string().optional().describe("Path to spec file"),
        },
        async execute(args) {
          const cliArgs = ["intake", args.objective];
          if (args.budget) cliArgs.push("--budget", String(args.budget));
          if (args.spec) cliArgs.push("--spec", args.spec);
          return runEngineCommand(root, cliArgs);
        },
      }),

      hadrian_pause: tool({
        description: "Pause active Hadrian goal execution cleanly and log a PAUSE record.",
        args: {
          reason: tool.schema.string().optional().describe("Reason for pausing"),
        },
        async execute(args) {
          const cliArgs = ["pause"];
          if (args.reason) cliArgs.push("--reason", args.reason);
          return runEngineCommand(root, cliArgs);
        },
      }),

      hadrian_resume: tool({
        description: "Resume active Hadrian goal, validate contract MD5 integrity, and check verdict records.",
        args: {},
        async execute() {
          return runEngineCommand(root, ["resume"]);
        },
      }),

      hadrian_taiga_sync: tool({
        description: "Synchronize goal progress with Taiga PM tool (inspect tasks, close child tasks, or mark story Done).",
        args: {
          action: tool.schema.enum(["status", "close-tasks", "update-story", "finish"]).optional().describe("Sync action (default: status)"),
          ref: tool.schema.number().optional().describe("Story ref (e.g. 326)"),
          project: tool.schema.string().optional().describe("Taiga project slug (default: smartsparks)"),
          status: tool.schema.string().optional().describe("Target status name for update-story"),
          comment: tool.schema.string().optional().describe("Comment describing transition"),
        },
        async execute(args) {
          const cliArgs = ["taiga-sync"];
          if (args.action) cliArgs.push("--action", args.action);
          if (args.ref) cliArgs.push("--ref", String(args.ref));
          if (args.project) cliArgs.push("--project", args.project);
          if (args.status) cliArgs.push("--status", args.status);
          if (args.comment) cliArgs.push("--comment", args.comment);
          return runEngineCommand(root, cliArgs);
        },
      }),
    },

    // 2. Security Guardrails & Invariants
    "tool.execute.before": async (input) => {
      // Rule 3: Git push blocked without signoff
      if (input.tool === "bash") {
        const cmd = String(input.args?.command ?? "");
        if (PUSH_RE.test(cmd)) {
          const contractFile = join(root, CONTRACT);
          const signoffFile = join(root, SIGNOFF);
          if (existsSync(contractFile) && !existsSync(signoffFile)) {
            throw new Error(
              "HADRIAN GUARD: git push is blocked while a goal contract is active without acceptance (Hard Rule 3). Review the diff; on approval create .hadrian/signoff (or stop the goal)."
            );
          }
        }
      }

      if (["edit", "write"].includes(input.tool)) {
        const p = String(input.args?.filePath ?? "");
        const target = p.startsWith("/") ? p : join(root, p);

        // Rule 1: Contract freeze
        if (p.endsWith(CONTRACT)) {
          if (existsSync(target)) {
            throw new Error(
              "HADRIAN GUARD: the goal contract is frozen (L3 invariant). Propose amendments in the escalation report; a human applies them."
            );
          }
        }

        // Rule 12: Worktree write protection
        const wtDir = join(root, WORKTREES);
        const contractFile = join(root, CONTRACT);
        if (existsSync(contractFile) && existsSync(wtDir)) {
          try {
            const hasWorktrees = readdirSync(wtDir).length > 0;
            const isHadrianInternal = p.startsWith(".hadrian/") || p.includes("/.hadrian/");
            const isInWorktree = p.startsWith(".hadrian/worktrees/") || p.includes("/.hadrian/worktrees/");

            if (hasWorktrees && !isHadrianInternal && !isInWorktree) {
              throw new Error(
                "HADRIAN GUARD: Direct file modification in root repository checkout is blocked while worktree isolation is active (Hard Rule 12). Execute all edits inside .hadrian/worktrees/<slug>/."
              );
            }
          } catch {}
        }
      }
    },
  };
};

export default HadrianPlugin;
