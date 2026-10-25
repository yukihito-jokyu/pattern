import { fileURLToPath } from "node:url";
import { run } from "./process.mjs";

try {
  run(process.execPath, [
    fileURLToPath(
      new URL("../.claude/skills/learning-setup/scripts/learning.mjs", import.meta.url),
    ),
    ...process.argv.slice(2),
  ]);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
