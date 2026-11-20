// Unit test for Hadrian guard hook
import assert from "node:assert";
import { existsSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

// Create temp workspace directory
const testDir = join(tmpdir(), `hadrian_guard_test_${Date.now()}`);
mkdirSync(join(testDir, ".hadrian", "worktrees", "test-wt"), { recursive: true });
writeFileSync(join(testDir, ".hadrian", "contract.md"), "# Contract\n");

// Mock context
let toolHook = null;
let shellHook = null;

const ctx = {
  location: { directory: testDir },
  tool: {
    hook: async (name, fn) => {
      if (name === "execute.before") toolHook = fn;
    },
  },
  shell: {
    hook: async (name, fn) => {
      if (name === "create.before") shellHook = fn;
    },
  },
};

// Import guard plugin
const { default: plugin } = await import("../plugins/hadrian-guard.js");
await plugin.setup(ctx);

assert(toolHook, "toolHook should be registered");
assert(shellHook, "shellHook should be registered");

console.log("Testing Rule 1: Contract freeze...");
assert.throws(
  () => {
    toolHook({
      tool: "edit",
      input: { filePath: ".hadrian/contract.md" },
    });
  },
  /the goal contract is frozen/
);

console.log("Testing Rule 12: Worktree write protection...");
assert.throws(
  () => {
    toolHook({
      tool: "edit",
      input: { filePath: "src/Main.kt" },
    });
  },
  /Direct file modification in root repository checkout is blocked/
);

console.log("Testing Rule 12 Allowed: Edits inside worktree...");
assert.doesNotThrow(() => {
  toolHook({
    tool: "edit",
    input: { filePath: ".hadrian/worktrees/test-wt/src/Main.kt" },
  });
});

console.log("Testing Rule 12 Allowed: Edits to .hadrian/state.md...");
assert.doesNotThrow(() => {
  toolHook({
    tool: "edit",
    input: { filePath: ".hadrian/state.md" },
  });
});

console.log("Testing Rule 3: Git push blocked without signoff...");
assert.throws(
  () => {
    shellHook({
      command: "git push origin main",
    });
  },
  /git push is blocked/
);

console.log("Testing Rule 3 Allowed: Git push with signoff...");
writeFileSync(join(testDir, ".hadrian", "signoff"), "APPROVED by human\n");
assert.doesNotThrow(() => {
  shellHook({
    command: "git push origin main",
  });
});

// Cleanup
rmSync(testDir, { recursive: true, force: true });
console.log("All 5 Hadrian guard security invariants PASS cleanly!");
