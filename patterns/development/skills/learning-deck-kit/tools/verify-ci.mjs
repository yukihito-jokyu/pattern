import { run } from "./process.mjs";
import { prepareUv, requireChrome, requirePython } from "./ci-runtime.mjs";

let prepared;
try {
  requireChrome();
  requirePython();
  prepared = await prepareUv();
  const options = { env: prepared.environment };
  run("npm", ["ci", "--no-audit", "--no-fund"], options);
  run(
    process.execPath,
    [
      "node_modules/@playwright/test/cli.js",
      "install",
      ...(process.platform === "linux" ? ["--with-deps"] : []),
      "chromium",
    ],
    options,
  );
  run("npm", ["run", "check"], options);
  run("npm", ["run", "verify:decks"], options);
  console.log("ZIP verification: passed (check, examples, original html-deck)");
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
} finally {
  await prepared?.cleanup();
}
