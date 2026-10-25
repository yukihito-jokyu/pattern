import { access, cp, mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { run } from "./process.mjs";
import { hasRequiredUv, requireChrome, requirePython } from "./ci-runtime.mjs";
import { readCourse } from "../.claude/skills/learning-setup/scripts/model.mjs";

/** @returns {void} */
function preflight() {
  requireChrome();
  requirePython();
  if (!hasRequiredUv(process.env)) {
    throw new Error(
      "Preparation incomplete: uv 0.13.5 is required. Run node tools/verify-ci.mjs to prepare a temporary fixed version and verify the kit",
    );
  }
}

/** @param {string} temporary @returns {Promise<void>} */
async function verifyDecks(temporary) {
  const vendor = join(temporary, "html-deck");
  await cp(".claude/skills/learning-setup/vendor/html-deck", vendor, {
    recursive: true,
    filter: (source) => !source.split("/").some((part) => [".venv", "__pycache__"].includes(part)),
  });
  const entries = await readdir("courses", { withFileTypes: true });
  let count = 0;
  let reviewCount = 0;
  let infoCount = 0;
  for (const entry of entries.filter((value) => value.isDirectory())) {
    const course = await readCourse(join("courses", entry.name));
    for (const { lesson, deckDir } of course.lessons) {
      const deck = join(temporary, entry.name, lesson.id);
      const reportDirectory = join(deck, ".loop", "kit-verification");
      await cp(deckDir, deck, { recursive: true });
      try {
        run(
          "uv",
          [
            "run",
            "--locked",
            "--python",
            "3.14",
            "--project",
            join(vendor, "tools"),
            "html-deck-check",
            deck,
            "--out",
            reportDirectory,
          ],
          {
            env: {
              ...process.env,
              UV_CACHE_DIR: join(temporary, "uv-cache"),
              UV_PYTHON_DOWNLOADS: "never",
            },
          },
        );
      } finally {
        await copyReport(reportDirectory, join(temporary, "reports", entry.name, lesson.id));
      }
      const counts = await reportCounts(join(reportDirectory, "report.json"));
      if (counts.block !== 0) {
        throw new Error("html-deck reported blocking findings despite exit 0");
      }
      reviewCount += counts.review;
      infoCount += counts.info;
      count += 1;
    }
  }
  if (count === 0) {
    throw new Error("STR-01: no decks to verify");
  }
  console.log(
    "html-deck block gate: passed (" +
      count +
      " decks; block 0; review " +
      reviewCount +
      "; info " +
      infoCount +
      "; original source unchanged)",
  );
  console.log("review/info findings require review; exit 0 alone does not approve slide quality");
}

/** @param {string} source @param {string} destination @returns {Promise<void>} */
async function copyReport(source, destination) {
  try {
    await access(source);
  } catch {
    return;
  }
  await cp(source, destination, { recursive: true });
}

/** @param {string} path @returns {Promise<{block: number, review: number, info: number}>} */
async function reportCounts(path) {
  const report = /** @type {unknown} */ (JSON.parse(await readFile(path, "utf8")));
  if (!report || typeof report !== "object" || !("totals" in report)) {
    throw new Error("html-deck report has no totals");
  }
  const totals = report.totals;
  if (
    !totals ||
    typeof totals !== "object" ||
    !("block" in totals) ||
    typeof totals.block !== "number" ||
    !("review" in totals) ||
    typeof totals.review !== "number" ||
    !("info" in totals) ||
    typeof totals.info !== "number"
  ) {
    throw new Error("html-deck report totals are invalid");
  }
  return { block: totals.block, review: totals.review, info: totals.info };
}

/** @param {string} temporary @returns {Promise<void>} */
async function preserveReports(temporary) {
  const artifacts = process.env.CI_ARTIFACTS_DIR;
  if (!artifacts) {
    return;
  }
  const reports = join(temporary, "reports");
  try {
    await access(reports);
  } catch {
    return;
  }
  await cp(reports, join(artifacts, "html-deck"), { recursive: true });
  console.log("html-deck reports: " + join(artifacts, "html-deck"));
}

let temporary;
try {
  preflight();
  temporary = await mkdtemp(join(tmpdir(), "learning-decks-"));
  await verifyDecks(temporary);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
} finally {
  if (temporary) {
    await preserveReports(temporary);
    await rm(temporary, { recursive: true, force: true });
  }
}
