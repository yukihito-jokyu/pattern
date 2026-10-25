import { spawnSync } from "node:child_process";
import { mkdtemp, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readCourse } from "../.claude/skills/learning-setup/scripts/model.mjs";

/** @param {string} code @param {string} expected @param {string} temporary @returns {Promise<void>} */
async function verifyGo(code, expected, temporary) {
  await writeFile(join(temporary, "main.go"), code, "utf8");
  await writeFile(join(temporary, "go.mod"), "module learning.example\n\ngo 1.27.0\n", "utf8");
  const result = spawnSync("go", ["run", "."], {
    cwd: temporary,
    encoding: "utf8",
    timeout: 60_000,
    env: {
      ...process.env,
      GOTOOLCHAIN: "local",
      GOPROXY: "off",
      GOSUMDB: "off",
      GOCACHE: join(temporary, "cache"),
      GOMODCACHE: join(temporary, "modules"),
      GOPATH: join(temporary, "gopath"),
    },
  });
  if (result.error || result.status !== 0) {
    throw new Error("TEST-01: Go example failed: " + (result.error?.message ?? result.stderr));
  }
  if (result.stdout.trimEnd() !== expected.trimEnd()) {
    throw new Error(
      "PROC-02: Go example output mismatch: expected " +
        JSON.stringify(expected) +
        ", got " +
        JSON.stringify(result.stdout),
    );
  }
}

/** @param {string} directory @param {string} temporary @returns {Promise<number>} */
async function verifyCourse(directory, temporary) {
  const course = await readCourse(directory);
  if (course.profile.technology.toLowerCase() !== "go") {
    return 0;
  }
  let count = 0;
  for (const { lesson } of course.lessons) {
    for (const explanation of lesson.explanation) {
      if (explanation.code.trimStart().startsWith("package main")) {
        await verifyGo(explanation.code, explanation.output, temporary);
        count += 1;
      }
    }
  }
  return count;
}

const temporary = await mkdtemp(join(tmpdir(), "learning-go-"));
try {
  let count = 0;
  for (const entry of await readdir("courses", { withFileTypes: true })) {
    if (!entry.isDirectory()) {
      continue;
    }
    count += await verifyCourse(join("courses", entry.name), temporary);
  }
  if (count === 0) {
    throw new Error("TEST-01: no Go reference examples were executed");
  }
  console.log("Go examples: passed (" + count + ")");
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
} finally {
  await rm(temporary, { recursive: true, force: true });
}
