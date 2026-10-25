import { createHash } from "node:crypto";
import { lstat, mkdir, readFile, readdir, realpath, unlink, writeFile } from "node:fs/promises";
import { dirname, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { parseProfile, readCourse } from "./model.mjs";
import {
  renderCourse,
  renderLesson,
  renderSkill,
  renderSources,
  renderWorkflow,
} from "./render.mjs";

/** @typedef {import('./types.js').Profile} Profile */
/** @typedef {{schemaVersion: 1, id: string, files: Record<string, string>}} Ledger */

const SELF = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const MARKER = ".learning-generated.json";
const OMIT = new Set([".venv", ".loop", "__pycache__", "node_modules", ".DS_Store"]);

/** @param {unknown} error @returns {boolean} */
function isMissing(error) {
  return typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT";
}

/** @param {string} path @returns {Promise<boolean>} */
async function exists(path) {
  try {
    await lstat(path);
    return true;
  } catch (error) {
    if (isMissing(error)) {
      return false;
    }
    throw error;
  }
}

/** @param {string} path @returns {Promise<string>} 未作成の出力先も既存の親の実パスから正規化する。 */
async function location(path) {
  const absolute = resolve(path);
  if (await exists(absolute)) {
    return realpath(absolute);
  }
  return resolve(await location(dirname(absolute)), relative(dirname(absolute), absolute));
}

/** @param {Uint8Array} content @returns {string} */
function hash(content) {
  return createHash("sha256").update(content).digest("hex");
}

/** @param {string} root @param {string} leaf @returns {Promise<string>} 出力ルート内の通常ファイルパスだけを返す。 */
async function safePath(root, leaf) {
  const base = resolve(root);
  const path = resolve(base, leaf);
  if (!leaf || path === base || !path.startsWith(base + sep)) {
    throw new Error(`OPS-02 ${leaf}: 出力先の外は変更できません`);
  }
  let current = path;
  while (current === base || current.startsWith(base + sep)) {
    if (await exists(current)) {
      const info = await lstat(current);
      if (info.isSymbolicLink()) {
        throw new Error(`OPS-02 ${current}: 出力先にsymlinkは使えません`);
      }
    }
    if (current === base) {
      break;
    }
    current = dirname(current);
  }
  return path;
}

/** @param {string} root @returns {Promise<Map<string, Buffer>>} 自己完結する配布物をバイナリのまま読む。 */
async function tree(root) {
  /** @type {Map<string, Buffer>} */
  const files = new Map();
  /** @param {string} directory @returns {Promise<void>} */
  async function visit(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      if (OMIT.has(entry.name)) {
        continue;
      }
      const path = resolve(directory, entry.name);
      if (entry.isSymbolicLink()) {
        throw new Error(`OPS-02 ${path}: 配布物にsymlinkは使えません`);
      }
      if (entry.isDirectory()) {
        await visit(path);
      } else if (entry.isFile()) {
        files.set(relative(root, path), await readFile(path));
      }
    }
  }
  await visit(root);
  return files;
}

/** @param {Map<string, Buffer>} files @param {string} id @returns {Buffer} */
function ledgerContent(files, id) {
  return Buffer.from(
    JSON.stringify(
      {
        schemaVersion: 1,
        id,
        files: Object.fromEntries([...files].map(([path, content]) => [path, hash(content)])),
      },
      null,
      2,
    ) + "\n",
  );
}

/** @param {Profile} profile @returns {Map<string, Buffer>} */
function skillFiles(profile) {
  return new Map([
    ["SKILL.md", Buffer.from(renderSkill(profile))],
    ["references/profile.json", Buffer.from(JSON.stringify(profile, null, 2) + "\n")],
    ["references/sources.md", Buffer.from(renderSources(profile))],
    ["references/workflow.md", Buffer.from(renderWorkflow(profile))],
  ]);
}

/** @param {Map<string, Buffer>} writes @returns {Promise<void>} 衝突を全件確認してから新規ファイルだけを書く。 */
async function createFiles(writes) {
  for (const [path, content] of writes) {
    if (await exists(path)) {
      if (!(await lstat(path)).isFile() || !(await readFile(path)).equals(content)) {
        throw new Error(`ERR-02 ${path}: 既存ファイルと衝突します`);
      }
    }
  }
  /** @type {string[]} */
  const created = [];
  try {
    for (const [path, content] of writes) {
      if (await exists(path)) {
        continue;
      }
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path, content, { flag: "wx" });
      created.push(path);
    }
  } catch (error) {
    for (const path of created.reverse()) {
      await unlink(path);
    }
    throw error;
  }
}

/** @param {string} root @param {Profile} profile @param {Map<string, Buffer>} files @returns {Promise<void>} */
async function writeManaged(root, profile, files) {
  const marker = await safePath(root, MARKER);
  /** @type {Ledger | undefined} */
  let previous;
  if (await exists(marker)) {
    const value = /** @type {unknown} */ (JSON.parse(await readFile(marker, "utf8")));
    if (
      typeof value !== "object" ||
      value === null ||
      !("schemaVersion" in value) ||
      value.schemaVersion !== 1 ||
      !("id" in value) ||
      value.id !== profile.id ||
      !("files" in value) ||
      typeof value.files !== "object" ||
      value.files === null ||
      Array.isArray(value.files)
    ) {
      throw new Error("ERR-02 所有マーカーが一致しません");
    }
    previous = /** @type {Ledger} */ (value);
  } else if ((await exists(root)) && (await readdir(root)).length !== 0) {
    throw new Error("ERR-02 空でない出力先に所有マーカーがありません");
  }
  for (const [leaf, expected] of Object.entries(previous?.files ?? {})) {
    const path = await safePath(root, leaf);
    if (
      !(await exists(path)) ||
      !(await lstat(path)).isFile() ||
      hash(await readFile(path)) !== expected
    ) {
      throw new Error(`ERR-02 ${leaf}: 生成後に変更されています。別の出力先へ生成してください`);
    }
  }
  for (const [leaf] of files) {
    const path = await safePath(root, leaf);
    if ((await exists(path)) && !Object.hasOwn(previous?.files ?? {}, leaf)) {
      throw new Error(`ERR-02 ${leaf}: 利用者ファイルと衝突します`);
    }
  }
  for (const [leaf, content] of files) {
    const path = await safePath(root, leaf);
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, content);
  }
  for (const leaf of Object.keys(previous?.files ?? {})) {
    if (!files.has(leaf)) {
      await unlink(await safePath(root, leaf));
    }
  }
  await mkdir(root, { recursive: true });
  await writeFile(marker, ledgerContent(files, profile.id));
}

/** @param {string} profilePath @param {string} courseDir @param {string} skillsDir @returns {Promise<void>} */
async function setup(profilePath, courseDir, skillsDir) {
  const profile = parseProfile(JSON.parse(await readFile(profilePath, "utf8")));
  /** @type {Map<string, Buffer>} */
  const writes = new Map();
  writes.set(
    await safePath(courseDir, "profile.json"),
    Buffer.from(JSON.stringify(profile, null, 2) + "\n"),
  );
  const generated = skillFiles(profile);
  generated.set(MARKER, ledgerContent(generated, profile.id));
  for (const [leaf, content] of generated) {
    writes.set(await safePath(resolve(skillsDir, `learn-${profile.id}`), leaf), content);
  }
  const setupDir = resolve(skillsDir, "learning-setup");
  const same = (await exists(setupDir)) && (await realpath(setupDir)) === (await realpath(SELF));
  if (!same) {
    for (const [leaf, content] of await tree(SELF)) {
      writes.set(await safePath(setupDir, leaf), content);
    }
  }
  await createFiles(writes);
  console.log(
    `setup: learn-${profile.id} と公式資料・取得手順を生成しました。教材本文は未作成です。`,
  );
}

/** @param {string} courseDir @returns {Promise<Profile>} */
async function readProfile(courseDir) {
  return parseProfile(JSON.parse(await readFile(resolve(courseDir, "profile.json"), "utf8")));
}

/** @param {string} courseDir @param {string} outputDir @returns {Promise<void>} */
async function build(courseDir, outputDir) {
  const input = await location(courseDir);
  const output = await location(outputDir);
  if (input === output || input.startsWith(output + sep) || output.startsWith(input + sep)) {
    throw new Error("ERR-02 入力コースと出力先を別の場所にしてください");
  }
  const course = await readCourse(courseDir);
  /** @type {Map<string, Buffer>} */
  const files = new Map([["index.html", Buffer.from(renderCourse(course.profile))]]);
  for (const [leaf, content] of await tree(resolve(SELF, "assets/web"))) {
    files.set(`assets/${leaf}`, content);
  }
  for (const { lesson, deckDir } of course.lessons) {
    files.set(`${lesson.id}/index.html`, Buffer.from(renderLesson(course.profile, lesson)));
    for (const [leaf, content] of await tree(deckDir)) {
      files.set(`${lesson.id}/deck/${leaf}`, content);
    }
  }
  await writeManaged(outputDir, course.profile, files);
  console.log(`build: ${course.lessons.length} 学習項目 → ${resolve(outputDir)}`);
}

/** @param {string[]} args @param {number} count @returns {string[]} */
function argumentsFor(args, count) {
  if (args.length !== count || args.some((arg) => !arg || arg.startsWith("--"))) {
    throw new Error("ERR-02 引数の数が違います。helpを参照してください");
  }
  return args;
}

/** @param {string[]} args @returns {Promise<void>} */
async function dispatch(args) {
  const [command, ...values] = args;
  if (!command || command === "help" || command === "--help") {
    console.log(
      "learning setup <profile.json> <course-dir> <skills-dir>\nlearning sync-skill <course-dir> <skills-dir>\nlearning check <course-dir>\nlearning build <course-dir> <output-dir>\nlearning sources <course-dir>\nlearning format-file <json>",
    );
    return;
  }
  const counts = new Map([
    ["setup", 3],
    ["sync-skill", 2],
    ["check", 1],
    ["build", 2],
    ["sources", 1],
    ["format-file", 1],
  ]);
  const count = counts.get(command);
  if (count === undefined) {
    throw new Error(`ERR-02 不明なコマンド: ${command}`);
  }
  const checked = argumentsFor(values, count);
  const first = checked[0];
  if (first === undefined) {
    throw new Error("ERR-02 入力がありません");
  }
  if (command === "setup") {
    return setup(first, checked[1] ?? "", checked[2] ?? "");
  }
  if (command === "build") {
    return build(first, checked[1] ?? "");
  }
  if (command === "check") {
    const course = await readCourse(first);
    console.log(`check: ${course.profile.id} / ${course.lessons.length} lessons passed`);
    return;
  }
  if (command === "format-file") {
    if (!first.endsWith(".json")) {
      throw new Error("ERR-02 format-fileはJSONファイルだけに使えます");
    }
    await writeFile(
      first,
      JSON.stringify(JSON.parse(await readFile(first, "utf8")), null, 2) + "\n",
    );
    return;
  }
  const profile = await readProfile(first);
  if (command === "sources") {
    console.log(renderSources(profile));
    return;
  }
  await writeManaged(
    resolve(checked[1] ?? "", `learn-${profile.id}`),
    profile,
    skillFiles(profile),
  );
  console.log(`sync-skill: learn-${profile.id}`);
}

/** @param {string[]} args @returns {Promise<void>} CLI境界だけで例外を終了コードへ変換する。 */
export async function main(args) {
  try {
    await dispatch(args);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}

if (
  process.argv[1] &&
  (await realpath(process.argv[1])) === (await realpath(fileURLToPath(import.meta.url)))
) {
  await main(process.argv.slice(2));
}
