import { spawnSync } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { run } from "./process.mjs";

const uvVersion = "0.13.5";

/** @param {NodeJS.ProcessEnv} environment @returns {boolean} */
export function hasRequiredUv(environment) {
  const result = spawnSync("uv", ["--version"], { env: environment, encoding: "utf8" });
  return (
    !result.error &&
    result.status === 0 &&
    new RegExp("^uv " + uvVersion.replaceAll(".", "\\.") + "(?:\\s|$)").test(result.stdout)
  );
}

/** @param {NodeJS.ProcessEnv} [environment] @returns {void} */
export function requirePython(environment = process.env) {
  const result = spawnSync("python3.14", ["--version"], { env: environment, encoding: "utf8" });
  if (result.error || result.status !== 0 || !result.stdout.startsWith("Python 3.14.")) {
    throw new Error(
      "Preparation incomplete: Python 3.14 is required. Run python3.14 --version, then node tools/verify-ci.mjs",
    );
  }
}

/**
 * @param {NodeJS.ProcessEnv} [environment]
 * @returns {Promise<{environment: NodeJS.ProcessEnv, cleanup: () => Promise<void>}>}
 */
export async function prepareUv(environment = process.env) {
  if (hasRequiredUv(environment)) {
    console.log("Using existing uv " + uvVersion);
    return { environment, cleanup: async () => {} };
  }
  requirePython(environment);
  const temporary = await mkdtemp(join(tmpdir(), "learning-uv-"));
  const target = join(temporary, "python");
  const prepared = {
    ...environment,
    PATH: [join(target, "bin"), environment.PATH].filter(Boolean).join(delimiter),
    PYTHONPATH: [target, environment.PYTHONPATH].filter(Boolean).join(delimiter),
  };
  try {
    run(
      "python3.14",
      [
        "-m",
        "pip",
        "--isolated",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--index-url",
        "https://pypi.org/simple",
        "--only-binary=:all:",
        "--no-deps",
        "--target",
        target,
        "uv==" + uvVersion,
      ],
      { env: environment },
    );
    if (!hasRequiredUv(prepared)) {
      throw new Error("Preparation incomplete: the temporary uv installation is not " + uvVersion);
    }
    console.log("Using temporary uv " + uvVersion + " (existing installation unchanged)");
    return {
      environment: prepared,
      cleanup: async () => {
        await rm(temporary, { recursive: true, force: true });
      },
    };
  } catch (error) {
    await rm(temporary, { recursive: true, force: true });
    throw error;
  }
}

/** @param {string} [executable] @returns {void} */
export function requireChrome(
  executable = process.platform === "darwin"
    ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    : "/opt/google/chrome/chrome",
) {
  const result = spawnSync(executable, ["--version"], { encoding: "utf8" });
  if (result.error || result.status !== 0 || !result.stdout.startsWith("Google Chrome ")) {
    throw new Error(
      "Preparation incomplete: Google Chrome is required at " +
        executable +
        ".\n" +
        "Install Google Chrome manually from https://www.google.com/chrome/; existing browsers are never replaced by this check.\n" +
        'Confirm: "' +
        executable +
        '" --version\n' +
        "Retry: node tools/verify-ci.mjs (or npm run verify:decks)",
    );
  }
  console.log("Using existing " + result.stdout.trim());
}
