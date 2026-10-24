import { readFileSync, writeFileSync } from "node:fs";
const source = readFileSync("docs/design/rules.md","utf8");
const target = ".claude/skills/pleasant-ui-motion/references/rules.md";
if (process.argv.includes("--check")) {
  if (readFileSync(target,"utf8") !== source) { console.error("PROC-01 portable rules are stale"); process.exitCode=1; }
} else writeFileSync(target,source);
