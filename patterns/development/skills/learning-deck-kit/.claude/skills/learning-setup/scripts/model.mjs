import { readFile, realpath, stat } from "node:fs/promises";
import { resolve, sep } from "node:path";

/** @typedef {import('./types.js').Profile} Profile */
/** @typedef {import('./types.js').Lesson} Lesson */
/** @typedef {import('./types.js').Course} Course */

const ID = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const PROFILE_KEYS = [
  "schemaVersion",
  "id",
  "title",
  "technology",
  "version",
  "goal",
  "audience",
  "officialHosts",
  "sources",
  "curriculum",
];
const LESSON_KEYS = [
  "schemaVersion",
  "id",
  "title",
  "goal",
  "prerequisites",
  "explanation",
  "exercise",
  "sources",
  "slides",
];

/** @param {unknown} value @param {string[]} keys @param {string} at @returns {Record<string, unknown>} */
function object(value, keys, at) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`ERR-01 ${at}: オブジェクトが必要です`);
  }
  const data = /** @type {Record<string, unknown>} */ (value);
  const actual = Object.keys(data);
  if (actual.length !== keys.length || actual.some((key) => !keys.includes(key))) {
    throw new Error(`ERR-01 ${at}: キーは ${keys.join(", ")} です`);
  }
  return data;
}

/** @param {unknown} value @param {string} at @param {boolean} [allowEmpty] @returns {string} */
function text(value, at, allowEmpty = false) {
  if (typeof value !== "string" || (!allowEmpty && !value.trim())) {
    throw new Error(`ERR-01 ${at}: 文字列が必要です`);
  }
  return value;
}

/** @param {unknown} value @param {string} at @param {boolean} [allowEmpty] @returns {unknown[]} */
function array(value, at, allowEmpty = false) {
  if (!Array.isArray(value) || (!allowEmpty && value.length === 0)) {
    throw new Error(`ERR-01 ${at}: 配列が必要です`);
  }
  return /** @type {unknown[]} */ (value);
}

/** @param {unknown} value @param {string} at @returns {string} */
function id(value, at) {
  const result = text(value, at);
  if (!ID.test(result)) {
    throw new Error(`NAM-01 ${at}: 英字始まりkebab-caseが必要です`);
  }
  return result;
}

/** @param {string[]} values @param {string} at @returns {void} */
function unique(values, at) {
  if (new Set(values).size !== values.length) {
    throw new Error(`NAM-01 ${at}: IDが重複しています`);
  }
}

/** @param {unknown} value @param {string} at @returns {void} */
function version(value, at) {
  if (/^(?:latest|stable|current|unknown|未確認|最新版)$/i.test(text(value, at).trim())) {
    throw new Error(`OPS-01 ${at}: 対象版を特定してください`);
  }
}

/** @param {Record<string, unknown>} data @param {string[]} fields @param {string} at @returns {void} */
function texts(data, fields, at) {
  for (const key of fields) {
    text(data[key], `${at}.${key}`);
  }
}

/** @param {unknown} value @returns {Profile} 検証済みプロフィールを返す。 */
export function parseProfile(value) {
  const data = object(value, PROFILE_KEYS, "profile");
  if (data.schemaVersion !== 1) {
    throw new Error("ERR-01 schemaVersion: 1が必要です");
  }
  id(data.id, "profile.id");
  texts(data, ["title", "technology", "version", "goal", "audience"], "profile");
  version(data.version, "profile.version");
  const hosts = array(data.officialHosts, "officialHosts").map((host) => text(host, "host"));
  for (const host of hosts) {
    if (!/^[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}$/i.test(host)) {
      throw new Error("OPS-01 officialHosts: ホスト名だけを指定してください");
    }
  }
  const sourceIds = array(data.sources, "sources").map((item) => {
    const source = object(item, ["id", "title", "url", "version", "checkedAt"], "source");
    texts(source, ["title", "url", "version", "checkedAt"], "source");
    version(source.version, "source.version");
    const url = new URL(text(source.url, "source.url"));
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.port ||
      !hosts.includes(url.hostname)
    ) {
      throw new Error("OPS-01 source.url: 登録した公式hostのHTTPSが必要です");
    }
    const date = text(source.checkedAt, "source.checkedAt");
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      Number.isNaN(Date.parse(date)) ||
      new Date(date).toISOString().slice(0, 10) !== date
    ) {
      throw new Error("OPS-01 checkedAt: 実在するYYYY-MM-DDが必要です");
    }
    return id(source.id, "source.id");
  });
  unique(sourceIds, "sources");
  /** @type {string[]} */
  const earlier = [];
  for (const item of array(data.curriculum, "curriculum")) {
    const unit = object(item, ["id", "title", "goal", "dependsOn"], "curriculum");
    const unitId = id(unit.id, "curriculum.id");
    texts(unit, ["title", "goal"], "curriculum");
    const dependencies = array(unit.dependsOn, "dependsOn", true).map((itemId) =>
      id(itemId, "dependsOn"),
    );
    unique(dependencies, "dependsOn");
    if (dependencies.some((itemId) => !earlier.includes(itemId))) {
      throw new Error("ERR-01 dependsOn: 先行する学習項目だけを参照できます");
    }
    earlier.push(unitId);
  }
  unique(earlier, "curriculum");
  return /** @type {Profile} */ (value);
}

/** @param {unknown} value @param {Profile} profile @param {string} curriculumId @returns {Lesson} */
export function parseLesson(value, profile, curriculumId) {
  const data = object(value, LESSON_KEYS, "lesson");
  const unit = profile.curriculum.find((item) => item.id === curriculumId);
  if (
    !unit ||
    data.id !== unit.id ||
    data.title !== unit.title ||
    data.goal !== unit.goal ||
    data.schemaVersion !== 1
  ) {
    throw new Error("ERR-01 lesson: curriculumのid/title/goalとschemaVersionを一致させてください");
  }
  array(data.prerequisites, "prerequisites").forEach((item) => text(item, "prerequisite"));
  for (const item of array(data.explanation, "explanation")) {
    const section = object(item, ["title", "body", "code", "output"], "explanation");
    texts(section, ["title", "body"], "explanation");
    text(section.code, "code", true);
    text(section.output, "output", true);
  }
  const exercise = object(data.exercise, ["prompt", "answer"], "exercise");
  texts(exercise, ["prompt", "answer"], "exercise");
  const refs = array(data.sources, "lesson.sources").map((item) => id(item, "source"));
  unique(refs, "lesson.sources");
  if (refs.some((ref) => !profile.sources.some((source) => source.id === ref))) {
    throw new Error("ERR-01 sources: 未登録の出典です");
  }
  const files = array(data.slides, "slides").map((item) => validateSlide(item));
  unique(files, "slides.file");
  return /** @type {Lesson} */ (value);
}

/** @param {unknown} item @returns {string} */
function validateSlide(item) {
  const slide = object(item, ["file", "title", "notes"], "slide");
  text(slide.title, "slide.title");
  const file = text(slide.file, "slide.file");
  if (!/^[a-z0-9][a-z0-9-]*\.html$/.test(file)) {
    throw new Error("OPS-02 slide.file: slides内のHTMLファイル名だけを許可します");
  }
  /** @type {string[]} */
  const ids = [];
  /** @type {string[]} */
  const targets = [];
  for (const itemNote of array(slide.notes, "notes")) {
    const note = object(itemNote, ["id", "target", "side", "title", "body"], "note");
    ids.push(id(note.id, "note.id"));
    targets.push(id(note.target, "note.target"));
    texts(note, ["title", "body"], "note");
    if (note.side !== "left" && note.side !== "right") {
      throw new Error("ERR-01 note.side: left/rightが必要です");
    }
  }
  unique(ids, "notes.id");
  unique(targets, "notes.target");
  return file;
}

/** @param {string} html @returns {{tag: string, attributes: Map<string, string>}[]} 静的スライドの実要素から属性を読む。 */
function elementsIn(html) {
  // コメントとraw text内のタグ風文字列はDOM要素にはならない。
  const content = html
    .replace(/<!--[\s\S]*?(?:-->|$)/g, "")
    .replace(/<(script|style|textarea|title)\b[^>]*>[\s\S]*?(?:<\/\1\s*>|$)/gi, "");
  const elements = [];
  const tags = /<([a-z][a-z0-9:-]*)\b((?:"[^"]*"|'[^']*'|[^'">])*)>/gi;
  const attributes = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>=`]+)))?/g;
  for (const match of content.matchAll(tags)) {
    const tag = match[1]?.toLowerCase();
    const values = new Map();
    for (const attribute of (match[2] ?? "").matchAll(attributes)) {
      const name = attribute[1]?.toLowerCase();
      if (!name) {
        continue;
      }
      if (values.has(name)) {
        throw new Error(`ERR-01 HTML属性 ${name} が同じ要素で重複しています`);
      }
      values.set(name, attribute[2] ?? attribute[3] ?? attribute[4] ?? "");
    }
    if (tag) {
      elements.push({ tag, attributes: values });
    }
  }
  return elements;
}

/** @param {string} base @param {string} leaf @returns {Promise<string>} */
async function within(base, leaf) {
  const basePath = await realpath(base);
  const fullPath = await realpath(resolve(basePath, leaf));
  if (!fullPath.startsWith(basePath + sep)) {
    throw new Error(`OPS-02 ${leaf}: 配置先の外を参照できません`);
  }
  return fullPath;
}

/** @param {string} courseDir @returns {Promise<Course>} 全学習項目と注目対象を検証する。 */
export async function readCourse(courseDir) {
  const profile = parseProfile(
    JSON.parse(await readFile(await within(courseDir, "profile.json"), "utf8")),
  );
  /** @type {Course['lessons']} */
  const lessons = [];
  for (const unit of profile.curriculum) {
    const lessonDir = await within(courseDir, `lessons/${unit.id}`);
    const lesson = parseLesson(
      JSON.parse(await readFile(await within(lessonDir, "lesson.json"), "utf8")),
      profile,
      unit.id,
    );
    const deckDir = await within(lessonDir, "deck");
    for (const required of ["deck.md", "theme.css", "index.html", "slides"]) {
      await stat(await within(deckDir, required));
    }
    for (const slide of lesson.slides) {
      const html = await readFile(await within(deckDir, `slides/${slide.file}`), "utf8");
      const elements = elementsIn(html);
      const roots = elements.filter(
        (element) =>
          element.tag === "article" &&
          (element.attributes.get("class") ?? "").split(/\s+/).includes("slide"),
      );
      if (roots.length !== 1) {
        throw new Error(`STR-01 ${unit.id}/${slide.file}: article.slideが必要です`);
      }
      for (const note of slide.notes) {
        const matches = elements.filter(
          (element) => element.attributes.get("data-learning-target") === note.target,
        );
        if (matches.length !== 1) {
          throw new Error(`NAM-01 ${unit.id}/${slide.file}: target ${note.target} は1箇所必要です`);
        }
      }
    }
    lessons.push({ lesson, deckDir });
  }
  return { profile, lessons };
}
