import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { startServer } from "./serve.mjs";
import { run } from "./process.mjs";

const temporary = await mkdtemp(join(tmpdir(), "learning-browser-"));
try {
  const output = join(temporary, "site");
  run(process.execPath, ["tools/learning.mjs", "build", "courses/go", output]);
  const server = await startServer(output, Number(process.env.LEARNING_TEST_PORT ?? 4187));
  const address = server.address();
  console.log(
    "browser fixture: http://127.0.0.1:" +
      (address && typeof address === "object" ? address.port : "") +
      "/",
  );
  /** @returns {Promise<void>} */
  async function stop() {
    server.closeAllConnections();
    await new Promise((accept) => server.close(() => accept(undefined)));
    await rm(temporary, { recursive: true, force: true });
  }
  process.once("SIGTERM", () => void stop());
  process.once("SIGINT", () => void stop());
} catch (error) {
  await rm(temporary, { recursive: true, force: true });
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
