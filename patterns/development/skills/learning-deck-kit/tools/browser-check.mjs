import { createServer } from "node:net";
import { run } from "./process.mjs";

/** @returns {Promise<number>} */
async function freePort() {
  const server = createServer();
  await new Promise((accept, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => accept(undefined));
  });
  const address = server.address();
  await new Promise((accept) => server.close(() => accept(undefined)));
  if (!address || typeof address === "string") {
    throw new Error("Cannot allocate test port");
  }
  return address.port;
}

try {
  run(process.execPath, ["node_modules/@playwright/test/cli.js", "test"], {
    env: { ...process.env, LEARNING_TEST_PORT: String(await freePort()) },
  });
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
