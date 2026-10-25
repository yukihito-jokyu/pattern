import { spawnSync } from "node:child_process";

/**
 * @param {string} command
 * @param {string[]} args
 * @param {{cwd?: string, env?: NodeJS.ProcessEnv}} [options]
 * @returns {void}
 */
export function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: "inherit",
    ...options,
  });
  if (result.error) {
    throw new Error(command + ": " + result.error.message);
  }
  if (result.status !== 0) {
    throw new Error(command + " failed (" + String(result.status ?? result.signal) + ")");
  }
}
