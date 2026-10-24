import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { check } from "../.claude/skills/pleasant-ui-motion/scripts/motion.mjs";
function run(command,args) {
  const result = spawnSync(command,args,{stdio:"inherit"});
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
function syntax(folder) {
  for (const entry of readdirSync(folder,{withFileTypes:true})) {
    const path = join(folder,entry.name);
    if (entry.isDirectory()) syntax(path);
    else if (entry.name.endsWith(".mjs")) run(process.execPath,["--check",path]);
  }
}
try {
  console.log(`schema/format/lint/generated: ${check(process.cwd())} units passed`);
  run(process.execPath,["tools/sync-rules.mjs","--check"]);
  for (const folder of ["examples","tools","tests",".claude/skills/pleasant-ui-motion/scripts"]) syntax(folder);
  run("python3",[".foundation/bin/guard.py","--root","."]);
  run("python3",[".foundation/bin/rules_check.py","--root",".","--no-write"]);
  run(process.execPath,["--test","--test-reporter=tap","tests/contracts.test.mjs"]);
  run("npm",["run","test:browser"]);
  const ruleText = readFileSync("docs/design/rules.md","utf8");
  const portableRules = readFileSync(".claude/skills/pleasant-ui-motion/references/rules.md","utf8");
  if (portableRules !== ruleText) throw new Error("PROC-01 portable rules are stale: npm run fix");
  console.log("check: passed (reference browser only; target UI and human comfort require separate review)");
} catch (error) { console.error(error.message); process.exitCode = 1; }
