import { isBuiltin } from "node:module";
import { createHash } from "node:crypto";
import { access, readFile, readdir, realpath } from "node:fs/promises";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { Linter } from "eslint";
import { readCourse } from "../.claude/skills/learning-setup/scripts/model.mjs";
import { renderCourse, renderLesson } from "../.claude/skills/learning-setup/scripts/render.mjs";

const skill = ".claude/skills/learning-setup";
const requiredFiles = [
  "AGENTS.md",
  "CLAUDE.md",
  "README.md",
  "package.json",
  "package-lock.json",
  ".nvmrc",
  "ci.json",
  "vendor-lock.json",
  "tsconfig.node.json",
  "tsconfig.browser.json",
  "eslint.config.mjs",
  skill + "/SKILL.md",
  skill + "/references/authoring.md",
  skill + "/scripts/types.d.ts",
  skill + "/scripts/model.mjs",
  skill + "/scripts/render.mjs",
  skill + "/scripts/learning.mjs",
  skill + "/assets/web/learning.mjs",
  skill + "/assets/web/learning.css",
];
const ignoredNames = new Set(["node_modules", ".venv", "__pycache__", ".pytest_cache"]);

/** @param {unknown} value @param {string} label @returns {Record<string, unknown>} */
function record(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("TOOL-03: invalid " + label);
  }
  return /** @type {Record<string, unknown>} */ (value);
}

/** @param {string} path @returns {Promise<Record<string, unknown>>} */
async function readRecord(path) {
  const value = /** @type {unknown} */ (JSON.parse(await readFile(path, "utf8")));
  return record(value, path);
}

/** @param {string} path @returns {Promise<string[]>} */
async function filesIn(path) {
  const files = [];
  for (const entry of await readdir(path, { withFileTypes: true })) {
    if (ignoredNames.has(entry.name)) {
      continue;
    }
    const target = join(path, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await filesIn(target)));
    } else if (entry.isFile()) {
      files.push(target);
    } else {
      throw new Error("OPS-02: symlink is not a source file: " + target);
    }
  }
  return files.sort();
}

/** @param {string} root @returns {Promise<void>} */
async function checkLayout(root) {
  for (const file of requiredFiles) {
    try {
      await access(join(root, file));
    } catch {
      throw new Error("STR-01: missing " + file);
    }
  }
}

/** @param {string} root @returns {Promise<void>} */
async function checkVersions(root) {
  const packageData = await readRecord(join(root, "package.json"));
  const dependencies = record(packageData.devDependencies, "devDependencies");
  const lock = await readRecord(join(root, "package-lock.json"));
  const packages = record(lock.packages, "lock.packages");
  const lockedRoot = record(packages[""], "lock root");
  const lockedDependencies = record(lockedRoot.devDependencies, "locked devDependencies");
  for (const [name, version] of Object.entries(dependencies)) {
    const lockedPackage = record(packages["node_modules/" + name], "locked " + name);
    if (
      typeof version !== "string" ||
      !/^\d+\.\d+\.\d+$/.test(version) ||
      lockedDependencies[name] !== version ||
      lockedPackage.version !== version
    ) {
      throw new Error("TOOL-03: dependency must be fixed in package and lock: " + name);
    }
  }
  if (packageData.dependencies !== undefined) {
    throw new Error("DEP-01: runtime package dependencies are not allowed");
  }
  const nodeVersion = (await readFile(join(root, ".nvmrc"), "utf8")).trim();
  if (!/^22\.\d+\.\d+$/.test(nodeVersion) || !process.versions.node.startsWith("22.")) {
    throw new Error("TOOL-03: use the Node.js 22 runtime recorded in .nvmrc");
  }
  const ci = await readRecord(join(root, "ci.json"));
  if (ci.pythonVersion !== "3.14") {
    throw new Error("TOOL-03: ci.json must use Python 3.14");
  }
}

/** @param {string} root @returns {Promise<void>} */
async function checkVendor(root) {
  const lock = await readRecord(join(root, "vendor-lock.json"));
  if (
    lock.commit !== "2d638228f0104fa6ebfad6447bb1652379e1da78" ||
    lock.repository !== "https://github.com/nogikun/skills" ||
    lock.root !== skill + "/vendor/html-deck"
  ) {
    throw new Error("TOOL-03: unexpected upstream identity");
  }
  const hashes = record(lock.files, "vendor hashes");
  const vendorRoot = join(root, skill, "vendor/html-deck");
  const files = await filesIn(vendorRoot);
  const names = files.map((file) => relative(vendorRoot, file).split(sep).join("/"));
  if (names.length !== Object.keys(hashes).length) {
    throw new Error("TOOL-03: vendor file set changed");
  }
  for (const name of names) {
    const expected = hashes[name];
    const actual = createHash("sha256")
      .update(await readFile(join(vendorRoot, name)))
      .digest("hex");
    if (typeof expected !== "string" || !/^[a-f0-9]{64}$/.test(expected) || expected !== actual) {
      throw new Error("TOOL-03: vendor hash mismatch: " + name);
    }
  }
  for (const path of ["LICENSE", "tools/uv.lock", "tools/pyproject.toml"]) {
    if (!names.includes(path)) {
      throw new Error("TOOL-03: missing upstream runtime/license: " + path);
    }
  }
}

/** @param {string} file @param {string} source @returns {string[]} */
function moduleImports(file, source) {
  /** @type {string[]} */
  const imports = [];
  /** @param {import("estree").Node | null | undefined} node @returns {void} */
  function addLiteral(node) {
    if (!node || node.type !== "Literal" || typeof node.value !== "string") {
      throw new Error("DEP-01: module path must be literal: " + file);
    }
    imports.push(node.value);
  }
  /** @type {import("eslint").Rule.RuleModule} */
  const collector = {
    create() {
      return {
        ImportDeclaration(node) {
          addLiteral(node.source);
        },
        ExportNamedDeclaration(node) {
          if (node.source) {
            addLiteral(node.source);
          }
        },
        ExportAllDeclaration(node) {
          addLiteral(node.source);
        },
        ImportExpression(node) {
          addLiteral(node.source);
        },
        CallExpression(node) {
          if (node.callee.type === "Identifier" && node.callee.name === "require") {
            addLiteral(node.arguments[0]);
          }
        },
      };
    },
  };
  const messages = new Linter().verify(
    source,
    [
      {
        files: ["**/*.mjs"],
        plugins: { boundary: { rules: { imports: collector } } },
        rules: { "boundary/imports": "error" },
        languageOptions: { ecmaVersion: 2024, sourceType: "module" },
      },
    ],
    { filename: "module.mjs" },
  );
  if (messages.some((message) => message.fatal)) {
    throw new Error("DEP-01: source could not be parsed: " + file);
  }
  return imports;
}

/** @param {string} from @param {string} target @returns {boolean} */
function allowedLocalImport(from, target) {
  const scripts = skill + "/scripts/";
  const rules = new Map([
    [scripts + "model.mjs", []],
    [scripts + "render.mjs", []],
    [scripts + "learning.mjs", [scripts + "model.mjs", scripts + "render.mjs"]],
    [skill + "/assets/web/learning.mjs", []],
  ]);
  if (rules.has(from)) {
    return (rules.get(from) ?? []).includes(target);
  }
  if (from.startsWith("tools/")) {
    return target.startsWith("tools/") || target.startsWith(scripts);
  }
  if (from.startsWith("tests/")) {
    return target.startsWith("tests/") || target.startsWith(scripts);
  }
  return false;
}

/** @param {string} from @param {string} name @returns {boolean} */
function allowedExternalImport(from, name) {
  if (from === skill + "/scripts/model.mjs") {
    return name === "node:fs/promises" || name === "node:path";
  }
  if (from === skill + "/scripts/render.mjs" || from.includes("/assets/web/")) {
    return false;
  }
  if (isBuiltin(name)) {
    return true;
  }
  return (
    (from.startsWith("tools/") || from.startsWith("tests/")) &&
    ["typescript", "prettier", "eslint", "@playwright/test"].includes(name)
  );
}

/** @param {string} root @returns {Promise<void>} */
async function checkDependencies(root) {
  const directories = [skill + "/scripts", skill + "/assets/web", "tools", "tests"];
  for (const directory of directories) {
    for (const file of await filesIn(join(root, directory))) {
      if (!file.endsWith(".mjs")) {
        continue;
      }
      const from = relative(root, file).split(sep).join("/");
      for (const name of moduleImports(file, await readFile(file, "utf8"))) {
        const target = relative(root, resolve(dirname(file), name))
          .split(sep)
          .join("/");
        const isLocal = name.startsWith(".") || isAbsolute(name);
        if (
          (isLocal && !allowedLocalImport(from, target)) ||
          (!isLocal && !allowedExternalImport(from, name))
        ) {
          throw new Error("DEP-01: forbidden import " + from + " -> " + name);
        }
      }
    }
  }
}

/** @param {string} root @returns {Promise<number>} */
async function checkCourses(root) {
  const coursesDirectory = join(root, "courses");
  const directories = (await readdir(coursesDirectory, { withFileTypes: true })).filter((entry) =>
    entry.isDirectory(),
  );
  if (directories.length === 0) {
    throw new Error("STR-01: courses must contain a reference course");
  }
  for (const directory of directories) {
    const course = await checkedCourse(join(coursesDirectory, directory.name));
    const index = renderCourse(course.profile);
    if (!index.includes("assets/learning.css") || /<style[\s>]/i.test(index)) {
      throw new Error("CODE-04: course style must use assets/learning.css");
    }
    for (const { lesson } of course.lessons) {
      const page = renderLesson(course.profile, lesson);
      if (
        !page.includes("../assets/learning.css") ||
        !page.includes("../assets/learning.mjs") ||
        /<style[\s>]/i.test(page)
      ) {
        throw new Error("CODE-04: lesson style and behavior must use shared web assets");
      }
    }
  }
  return directories.length;
}

/** @param {string} directory @returns {Promise<import("../.claude/skills/learning-setup/scripts/types.js").Course>} */
async function checkedCourse(directory) {
  try {
    return await readCourse(directory);
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      throw new Error("STR-01: required course file is missing: " + directory);
    }
    throw error;
  }
}

/** @param {string} root @returns {Promise<void>} */
export async function checkStructure(root) {
  await checkLayout(root);
  await checkVersions(root);
  await checkVendor(root);
  await checkDependencies(root);
  const courseCount = await checkCourses(root);
  console.log(
    "structure: passed (" + courseCount + " courses; vendor hashes and imports verified)",
  );
}

if (
  process.argv[1] &&
  (await realpath(process.argv[1])) === (await realpath(fileURLToPath(import.meta.url)))
) {
  try {
    await checkStructure(fileURLToPath(new URL("../", import.meta.url)));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
