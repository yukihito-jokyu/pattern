import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { once } from "node:events";
import { access, chmod, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const cli = join(root, ".claude/skills/learning-setup/scripts/learning.mjs");

/** @returns {import("../.claude/skills/learning-setup/scripts/types.js").Profile} */
function profileFixture() {
  return {
    schemaVersion: 1,
    id: "example",
    title: "Exampleの学習",
    technology: "Example",
    version: "1.0.0",
    goal: "値の流れを説明する",
    audience: "プログラミングを始める人",
    officialHosts: ["example.com"],
    sources: [
      {
        id: "official-guide",
        title: "Official guide",
        url: "https://example.com/guide",
        version: "1.0.0",
        checkedAt: "2026-10-24",
      },
    ],
    curriculum: [
      { id: "values", title: "値の受け渡し", goal: "値の流れを説明する", dependsOn: [] },
    ],
  };
}

/** @param {string} directory @returns {Promise<void>} */
async function writeFixture(directory) {
  const deck = join(directory, "lessons/values/deck");
  await mkdir(join(deck, "slides"), { recursive: true });
  await writeFile(join(directory, "profile.json"), JSON.stringify(profileFixture()));
  await writeFile(
    join(directory, "lessons/values/lesson.json"),
    JSON.stringify({
      schemaVersion: 1,
      id: "values",
      title: "値の受け渡し",
      goal: "値の流れを説明する",
      prerequisites: ["値と名前の関係を知っている"],
      explanation: [
        {
          title: "入力から結果へ",
          body: "入力した値が戻り値として渡ります。",
          code: "",
          output: "",
        },
      ],
      exercise: { prompt: "結果を予想してください。", answer: "入力と同じ値が返ります。" },
      sources: ["official-guide"],
      slides: [
        {
          file: "01.html",
          title: "入力と戻り値",
          notes: [
            {
              id: "value-note",
              target: "return-value",
              side: "left",
              title: "戻り値",
              body: "呼出し元へ渡す値です。",
            },
          ],
        },
      ],
    }),
  );
  await writeFile(join(deck, "deck.md"), "# Fixture\n");
  await writeFile(join(deck, "theme.css"), ".slide { width: 1600px; height: 900px; }\n");
  await writeFile(join(deck, "index.html"), "<!doctype html><title>Fixture</title>\n");
  await writeFile(
    join(deck, "slides/01.html"),
    '<!doctype html><article class="slide"><p data-learning-target="return-value">value</p></article>\n',
  );
}

/**
 * @param {string[]} args
 * @param {string} [executable]
 * @returns {import("node:child_process").SpawnSyncReturns<string>}
 */
function runCli(args, executable = cli) {
  return spawnSync(process.execPath, [executable, ...args], {
    cwd: root,
    encoding: "utf8",
    timeout: 30_000,
  });
}

/** @param {string} path @returns {Promise<boolean>} */
async function exists(path) {
  try {
    await access(path);
    return true;
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      return false;
    }
    throw error;
  }
}

test("CLI reports invalid commands and malformed input as failure", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-cli-"));
  try {
    const unknown = runCli(["unknown"]);
    assert.equal(unknown.status, 1);
    assert.match(unknown.stderr, /ERR-02/);
    const input = join(temporary, "broken.json");
    await writeFile(input, "{");
    const malformed = runCli([
      "setup",
      input,
      join(temporary, "course"),
      join(temporary, "skills"),
    ]);
    assert.equal(malformed.status, 1);
    assert.ok(malformed.stderr.length > 0);
    assert.equal(await exists(join(temporary, "course")), false);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("setup copies a self-contained skill through paths with spaces and literal shell characters", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning setup $literal (学習)-"));
  try {
    const input = join(temporary, "profile inputs.json");
    const course = join(temporary, "course $literal");
    const skills = join(temporary, "skills ; $(literal)");
    await writeFile(input, JSON.stringify(profileFixture()));
    const setup = runCli(["setup", input, course, skills]);
    assert.equal(setup.status, 0, setup.stderr);
    assert.match(setup.stdout, /未作成/);
    const copied = join(skills, "learning-setup/scripts/learning.mjs");
    const sources = runCli(["sources", course], copied);
    assert.equal(sources.status, 0, sources.stderr);
    assert.match(sources.stdout, /https:\/\/example.com\/guide/);
    assert.ok(sources.stdout.includes("\n\n"));
    const generated = join(skills, "learn-example/SKILL.md");
    assert.match(await readFile(generated, "utf8"), /learn-example/);
    assert.equal(await exists(join(skills, "learn-example/references/workflow.md")), true);
    const repeated = runCli(["setup", input, course, skills]);
    assert.equal(repeated.status, 0, repeated.stderr);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("setup checks every destination before writing any course files", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-collision-"));
  try {
    const input = join(temporary, "profile.json");
    const course = join(temporary, "course");
    const skills = join(temporary, "skills");
    await writeFile(input, JSON.stringify(profileFixture()));
    await mkdir(join(skills, "learn-example"), { recursive: true });
    const protectedFile = join(skills, "learn-example/SKILL.md");
    await writeFile(protectedFile, "existing user skill\n");
    const result = runCli(["setup", input, course, skills]);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /ERR-02/);
    assert.equal(await exists(join(course, "profile.json")), false);
    assert.equal(await readFile(protectedFile, "utf8"), "existing user skill\n");
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("build updates owned output while preserving unrelated files and rejecting edited generated files", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-build-"));
  try {
    const course = join(temporary, "course");
    const output = join(temporary, "site");
    await writeFixture(course);
    const result = runCli(["build", course, output]);
    assert.equal(result.status, 0, result.stderr);
    const index = join(output, "index.html");
    assert.match(await readFile(index, "utf8"), /values\//);
    assert.equal(await exists(join(output, "values/deck/slides/01.html")), true);
    await writeFile(join(output, "personal-notes.txt"), "my notes\n");
    const repeated = runCli(["build", course, output]);
    assert.equal(repeated.status, 0, repeated.stderr);
    assert.equal(await readFile(join(output, "personal-notes.txt"), "utf8"), "my notes\n");
    const edited = (await readFile(index, "utf8")) + "<!-- user edit -->\n";
    await writeFile(index, edited);
    const refused = runCli(["build", course, output]);
    assert.equal(refused.status, 1);
    assert.match(refused.stderr, /ERR-02/);
    assert.equal(await readFile(index, "utf8"), edited);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("build refuses a nonempty unowned destination and output inside the input course", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-owned-"));
  try {
    const course = join(temporary, "course");
    const output = join(temporary, "existing");
    await writeFixture(course);
    await mkdir(output);
    await writeFile(join(output, "notes.txt"), "keep\n");
    const result = runCli(["build", course, output]);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /ERR-02/);
    assert.equal(await exists(join(output, "index.html")), false);
    assert.equal(await readFile(join(output, "notes.txt"), "utf8"), "keep\n");
    const nested = runCli(["build", course, join(course, "generated")]);
    assert.equal(nested.status, 1);
    assert.match(nested.stderr, /OPS-02|ERR-02/);
    assert.equal(await exists(join(course, "generated")), false);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("sync-skill rejects a changed generated skill without overwriting it", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-sync-"));
  try {
    const input = join(temporary, "profile.json");
    const course = join(temporary, "course");
    const skills = join(temporary, "skills");
    await writeFile(input, JSON.stringify(profileFixture()));
    const setup = runCli(["setup", input, course, skills]);
    assert.equal(setup.status, 0, setup.stderr);
    const sync = runCli(["sync-skill", course, skills]);
    assert.equal(sync.status, 0, sync.stderr);
    const target = join(skills, "learn-example/SKILL.md");
    await writeFile(target, "user changes\n");
    const result = runCli(["sync-skill", course, skills]);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /ERR-02/);
    assert.equal(await readFile(target, "utf8"), "user changes\n");
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("format-file changes only JSON and leaves a refused non-JSON file intact", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-format-"));
  try {
    const input = join(temporary, "input.json");
    await writeFile(input, '{"value":3}');
    const formatted = runCli(["format-file", input]);
    assert.equal(formatted.status, 0, formatted.stderr);
    assert.equal(await readFile(input, "utf8"), '{\n  "value": 3\n}\n');
    const script = join(temporary, "input.mjs");
    await writeFile(script, '{"value":3}');
    const refused = runCli(["format-file", script]);
    assert.equal(refused.status, 1);
    assert.equal(await readFile(script, "utf8"), '{"value":3}');
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

/** @param {import("node:child_process").ChildProcessWithoutNullStreams} child @returns {Promise<string>} */
function serverUrl(child) {
  return new Promise((accept, reject) => {
    let output = "";
    const timeout = setTimeout(() => reject(new Error("server did not start: " + output)), 10_000);
    child.once("error", reject);
    child.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error("server stopped before startup: " + String(code) + " " + output));
    });
    child.stdout.on("data", (chunk) => {
      output += String(chunk);
      const url = output.match(/http:\/\/127\.0\.0\.1:\d+\//)?.[0];
      if (url) {
        clearTimeout(timeout);
        accept(url);
      }
    });
    child.stderr.on("data", (chunk) => {
      output += String(chunk);
    });
  });
}

test("local serving rejects encoded traversal, external symlinks and unsupported methods", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-server-"));
  const site = join(temporary, "site");
  await mkdir(site);
  await writeFile(join(site, "index.html"), "<!doctype html><title>Example</title>");
  const secret = join(temporary, "secret.txt");
  await writeFile(secret, "private\n");
  await symlink(secret, join(site, "leak.txt"));
  const entry = join(temporary, "serve alias.mjs");
  await symlink(join(root, "tools/serve.mjs"), entry);
  const child = spawn(process.execPath, [entry, site, "0"], {
    stdio: "pipe",
  });
  try {
    const url = await serverUrl(child);
    const home = await fetch(url);
    assert.equal(home.status, 200);
    assert.match(await home.text(), /Example/);
    assert.equal((await fetch(url + "%2e%2e%2fsecret.txt")).status, 403);
    assert.equal((await fetch(url + "leak.txt")).status, 403);
    assert.equal((await fetch(url, { method: "POST" })).status, 405);
    assert.equal(await readFile(secret, "utf8"), "private\n");
  } finally {
    if (child.exitCode === null && child.signalCode === null) {
      const ended = once(child, "exit");
      child.kill("SIGTERM");
      await ended;
    }
    await rm(temporary, { recursive: true, force: true });
  }
});

/** @param {string} path @param {string} source @returns {Promise<void>} */
async function writeExecutable(path, source) {
  await writeFile(join(dirname(path), "package.json"), JSON.stringify({ type: "commonjs" }) + "\n");
  await writeFile(path, "#!" + process.execPath + "\n" + source);
  await chmod(path, 0o755);
}

/** @param {string} source @returns {Record<string, unknown>} */
function probeRecord(source) {
  const value = /** @type {unknown} */ (JSON.parse(source));
  assert.ok(value && typeof value === "object" && !Array.isArray(value));
  return /** @type {Record<string, unknown>} */ (value);
}

/** @param {NodeJS.ProcessEnv} environment @returns {import("node:child_process").SpawnSyncReturns<string>} */
function probeUv(environment) {
  const runtime = new URL("../tools/ci-runtime.mjs", import.meta.url).href;
  const source = [
    "import { prepareUv } from " + JSON.stringify(runtime) + ";",
    "import { spawnSync } from 'node:child_process';",
    "const originalPath = process.env.PATH;",
    "let prepared;",
    "try {",
    "  prepared = await prepareUv();",
    "  const child = spawnSync('uv', ['--version'], {env: prepared.environment, encoding: 'utf8'});",
    "  console.log(JSON.stringify({path: prepared.environment.PATH, pythonPath: prepared.environment.PYTHONPATH, originalPath, unchanged: process.env.PATH === originalPath, version: child.stdout.trim()}));",
    "  if (process.env.TEST_CHILD_FAILURE) throw new Error('intentional child failure');",
    "} catch (error) { console.error(error.message); process.exitCode = 1; }",
    "finally { await prepared?.cleanup(); }",
  ].join("\n");
  return spawnSync(process.execPath, ["--input-type=module", "-e", source], {
    cwd: root,
    encoding: "utf8",
    env: environment,
    timeout: 30_000,
  });
}

test("CI keeps an existing fixed uv without invoking pip or changing its environment", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-uv-existing-"));
  try {
    const uv = join(temporary, "uv");
    const original = "console.log('uv 0.13.5 (fixture)');\n";
    await writeExecutable(uv, original);
    await writeExecutable(join(temporary, "python3.14"), "process.exit(99);\n");
    const environment = { ...process.env, PATH: temporary + delimiter + process.env.PATH };
    const result = probeUv(environment);
    assert.equal(result.status, 0, result.stderr);
    const lastLine = result.stdout.trim().split("\n").at(-1);
    assert.ok(lastLine);
    const observed = probeRecord(lastLine);
    assert.equal(observed.path, environment.PATH);
    assert.equal(observed.unchanged, true);
    assert.ok(typeof observed.version === "string");
    assert.match(observed.version, /^uv 0\.13\.5 /);
    assert.equal(await readFile(uv, "utf8"), "#!" + process.execPath + "\n" + original);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("CI installs a fixed uv only into temporary storage and removes it after success or failure", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-uv-install-"));
  try {
    const uv = join(temporary, "uv");
    const original = "console.log('uv 0.13.4');\n";
    await writeExecutable(uv, original);
    await writeExecutable(
      join(temporary, "python3.14"),
      [
        "const fs = require('node:fs'); const path = require('node:path');",
        "const args = process.argv.slice(2);",
        "if (args[0] === '--version') { console.log('Python 3.14.9'); } else {",
        "  const target = args[args.indexOf('--target') + 1];",
        "  fs.writeFileSync(process.env.TEST_INSTALL_RECORD, JSON.stringify({args, target}));",
        "  if (process.env.TEST_INSTALL_FAILURE) process.exit(55);",
        "  const bin = path.join(target, 'bin'); fs.mkdirSync(bin, {recursive: true});",
        "  fs.writeFileSync(path.join(bin, 'uv'), '#!' + process.execPath + '\\nconsole.log(\"uv 0.13.5\");\\n', {mode: 0o755});",
        "}",
      ].join("\n"),
    );
    for (const failure of ["none", "child", "install"]) {
      const record = join(temporary, "install-" + failure + ".json");
      const environment = {
        ...process.env,
        PATH: temporary + delimiter + process.env.PATH,
        PYTHONPATH: "existing-python-path",
        TEST_INSTALL_RECORD: record,
        ...(failure === "child" ? { TEST_CHILD_FAILURE: "1" } : {}),
        ...(failure === "install" ? { TEST_INSTALL_FAILURE: "1" } : {}),
      };
      const result = probeUv(environment);
      assert.equal(result.status, failure === "none" ? 0 : 1, result.stderr);
      const installed = probeRecord(await readFile(record, "utf8"));
      assert.ok(typeof installed.target === "string");
      assert.ok(Array.isArray(installed.args));
      const args = /** @type {unknown[]} */ (installed.args);
      assert.ok(args.includes("uv==0.13.5"));
      assert.ok(args.includes("--isolated"));
      assert.ok(args.includes("--only-binary=:all:"));
      assert.ok(args.includes("--no-deps"));
      assert.equal(args[args.indexOf("--index-url") + 1], "https://pypi.org/simple");
      assert.equal(await exists(dirname(installed.target)), false);
      assert.equal(await readFile(uv, "utf8"), "#!" + process.execPath + "\n" + original);
      if (failure === "install") {
        assert.match(result.stderr, /python3\.14 failed \(55\)/);
        assert.doesNotMatch(result.stdout, /"version"/);
        continue;
      }
      const lastLine = result.stdout.trim().split("\n").at(-1);
      assert.ok(lastLine);
      const observed = probeRecord(lastLine);
      assert.ok(typeof observed.path === "string");
      assert.equal(observed.path.split(delimiter)[0], join(installed.target, "bin"));
      assert.equal(observed.pythonPath, installed.target + delimiter + "existing-python-path");
      assert.equal(observed.unchanged, true);
      assert.equal(observed.version, "uv 0.13.5");
    }
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("Chrome preflight preserves the existing executable and reports actionable missing preparation", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-chrome-"));
  try {
    const chrome = join(temporary, "Google Chrome");
    await writeExecutable(chrome, "console.log('Google Chrome 155.0.8059.39');\n");
    const original = await readFile(chrome, "utf8");
    const runtime = new URL("../tools/ci-runtime.mjs", import.meta.url).href;
    const source =
      "import {requireChrome} from " +
      JSON.stringify(runtime) +
      "; try {requireChrome(process.argv[1]);} catch(error) {console.error(error.message); process.exitCode = 1;}";
    const existing = spawnSync(process.execPath, ["--input-type=module", "-e", source, chrome], {
      encoding: "utf8",
    });
    assert.equal(existing.status, 0, existing.stderr);
    assert.match(existing.stdout, /Using existing Google Chrome/);
    assert.equal(await readFile(chrome, "utf8"), original);
    const missingPath = join(temporary, "missing-chrome");
    const missing = spawnSync(
      process.execPath,
      ["--input-type=module", "-e", source, missingPath],
      { encoding: "utf8" },
    );
    assert.equal(missing.status, 1);
    assert.match(missing.stderr, /Preparation incomplete/);
    assert.match(missing.stderr, /--version/);
    assert.match(missing.stderr, /node tools\/verify-ci\.mjs/);
    assert.equal(await exists(missingPath), false);
    assert.equal(await readFile(chrome, "utf8"), original);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
