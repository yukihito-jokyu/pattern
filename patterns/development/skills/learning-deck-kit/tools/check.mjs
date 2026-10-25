import { run } from "./process.mjs";

const commands = [
  ["python3", [".foundation/bin/guard.py", "--root", "."]],
  ["npm", ["run", "format"]],
  ["npm", ["run", "lint"]],
  ["npm", ["run", "typecheck"]],
  ["npm", ["run", "structure"]],
  ["npm", ["test"]],
  ["npm", ["run", "test:browser"]],
  ["npm", ["run", "verify:examples"]],
  ["python3", [".foundation/bin/rules_check.py", "--root", ".", "--no-write"]],
];
try {
  for (const [command, args] of commands) {
    if (typeof command !== "string" || !Array.isArray(args)) {
      throw new Error("invalid check command");
    }
    run(command, args);
  }
  console.log("check: passed");
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
