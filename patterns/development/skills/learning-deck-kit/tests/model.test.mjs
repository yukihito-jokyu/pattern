import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import {
  parseLesson,
  parseProfile,
  readCourse,
} from "../.claude/skills/learning-setup/scripts/model.mjs";
import { renderCourse, renderLesson } from "../.claude/skills/learning-setup/scripts/render.mjs";

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

/** @returns {import("../.claude/skills/learning-setup/scripts/types.js").Lesson} */
function lessonFixture() {
  return {
    schemaVersion: 1,
    id: "values",
    title: "値の受け渡し",
    goal: "値の流れを説明する",
    prerequisites: ["値と名前の関係を知っている"],
    explanation: [
      { title: "入力から結果へ", body: "入力した値が戻り値として渡ります。", code: "", output: "" },
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
  };
}

/** @param {string} directory @returns {Promise<void>} */
async function writeFixture(directory) {
  const deck = join(directory, "lessons", "values", "deck");
  await mkdir(join(deck, "slides"), { recursive: true });
  await writeFile(join(directory, "profile.json"), JSON.stringify(profileFixture()));
  await writeFile(join(directory, "lessons/values/lesson.json"), JSON.stringify(lessonFixture()));
  await writeFile(join(deck, "deck.md"), "# Fixture\n");
  await writeFile(join(deck, "theme.css"), ".slide { width: 1600px; height: 900px; }\n");
  await writeFile(join(deck, "index.html"), "<!doctype html><title>Fixture</title>\n");
  await writeFile(
    join(deck, "slides/01.html"),
    '<!doctype html><article class="slide"><p data-learning-target="return-value">value</p></article>\n',
  );
}

test("closed profile and lesson preserve the declared curriculum and references", () => {
  const profile = parseProfile(profileFixture());
  const lesson = parseLesson(lessonFixture(), profile, "values");
  assert.equal(profile.curriculum[0]?.id, lesson.id);
  assert.deepEqual(lesson.sources, ["official-guide"]);
});

test("unknown keys and empty mandatory text fail at the JSON boundary", () => {
  assert.throws(() => parseProfile({ ...profileFixture(), extra: true }), /ERR-01/);
  assert.throws(() => parseProfile({ ...profileFixture(), goal: " " }), /ERR-01/);
  const lesson = lessonFixture();
  assert.throws(
    () =>
      parseLesson(
        { ...lesson, exercise: { ...lesson.exercise, extra: true } },
        profileFixture(),
        "values",
      ),
    /ERR-01/,
  );
});

test("a prerequisite must refer to an earlier unique curriculum item", () => {
  const profile = profileFixture();
  const unit = profile.curriculum[0];
  assert.ok(unit);
  assert.throws(
    () => parseProfile({ ...profile, curriculum: [{ ...unit, dependsOn: ["future"] }] }),
    /ERR-01.*dependsOn/,
  );
  assert.throws(() => parseProfile({ ...profile, curriculum: [unit, unit] }), /NAM-01/);
});

test("source hosts, protocol, credentials, date and version are validated", () => {
  const profile = profileFixture();
  const source = profile.sources[0];
  assert.ok(source);
  for (const url of [
    "http://example.com/guide",
    "https://example.com.evil.test/guide",
    "https://user:pass@example.com/guide",
    "https://example.com:8443/guide",
  ]) {
    assert.throws(() => parseProfile({ ...profile, sources: [{ ...source, url }] }), /OPS-01/);
  }
  assert.throws(
    () => parseProfile({ ...profile, sources: [{ ...source, checkedAt: "2026-02-30" }] }),
    /OPS-01/,
  );
  assert.throws(
    () => parseProfile({ ...profile, sources: [{ ...source, version: "latest" }] }),
    /OPS-01/,
  );
  assert.throws(() => parseProfile({ ...profile, version: "未確認" }), /OPS-01/);
});

test("lesson metadata and source references must match the profile", () => {
  const profile = profileFixture();
  const lesson = lessonFixture();
  assert.throws(() => parseLesson({ ...lesson, title: "別の題" }, profile, "values"), /ERR-01/);
  assert.throws(
    () => parseLesson({ ...lesson, sources: ["unknown-guide"] }, profile, "values"),
    /ERR-01/,
  );
});

test("slide paths and duplicate annotation targets cannot cross the declared boundary", () => {
  const profile = profileFixture();
  const lesson = lessonFixture();
  const slide = lesson.slides[0];
  assert.ok(slide);
  for (const file of [
    "../secret.html",
    "%2e%2e/secret.html",
    "/secret.html",
    "nested/01.html",
    "https://example.com/01.html",
    "01.html?unsafe=1",
  ]) {
    assert.throws(
      () => parseLesson({ ...lesson, slides: [{ ...slide, file }] }, profile, "values"),
      /OPS-02/,
    );
  }
  const note = slide.notes[0];
  assert.ok(note);
  assert.throws(
    () =>
      parseLesson(
        { ...lesson, slides: [{ ...slide, notes: [note, { ...note, id: "second-note" }] }] },
        profile,
        "values",
      ),
    /NAM-01/,
  );
});

test("HTML text and embedded annotation data cannot terminate their containers", () => {
  const attack = '</script><script id="unexpected">alert("x")</script>';
  const profile = { ...profileFixture(), title: attack };
  const lesson = lessonFixture();
  const slide = lesson.slides[0];
  assert.ok(slide);
  const note = slide.notes[0];
  assert.ok(note);
  const output = renderLesson(profile, {
    ...lesson,
    explanation: [{ title: "例", body: attack, code: attack, output: attack }],
    slides: [{ ...slide, notes: [{ ...note, body: attack }] }],
  });
  assert.ok(renderCourse(profile).includes("&lt;/script&gt;"));
  assert.ok(output.includes("&lt;/script&gt;"));
  assert.ok(!output.includes('<script id="unexpected">'));
  const data = output.match(
    /<script id="learning-data" type="application\/json">([\s\S]*?)<\/script>/,
  )?.[1];
  assert.ok(data);
  const decoded = /** @type {unknown} */ (JSON.parse(data));
  assert.ok(decoded && typeof decoded === "object" && "slides" in decoded);
  assert.ok(data.includes("\\u003c"));
});

test("readCourse resolves every declared slide and rejects missing or duplicate targets", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-model-"));
  try {
    await writeFixture(temporary);
    const course = await readCourse(temporary);
    assert.equal(course.lessons.length, 1);
    const slide = join(temporary, "lessons/values/deck/slides/01.html");
    await writeFile(slide, '<article class="slide"><p>missing</p></article>');
    await assert.rejects(readCourse(temporary), /NAM-01/);
    await writeFile(
      slide,
      '<article class="slide"><p data-learning-target="return-value"></p><p data-learning-target="return-value"></p></article>',
    );
    await assert.rejects(readCourse(temporary), /NAM-01/);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("readCourse ignores annotation-shaped markup inside comments and raw-text elements", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-html-tokens-"));
  try {
    await writeFixture(temporary);
    const slide = join(temporary, "lessons/values/deck/slides/01.html");
    const falseTarget = '<p data-learning-target="return-value">fake</p>';
    const candidates = [
      "<!-- " + falseTarget + " -->",
      "<script>const template = '" + falseTarget + "';</script>",
      "<style>.example::after { content: '" + falseTarget + "'; }</style>",
      "<title>" + falseTarget + "</title>",
      "<textarea>" + falseTarget + "</textarea>",
    ];
    for (const candidate of candidates) {
      await writeFile(slide, '<article class="slide">' + candidate + "</article>");
      await assert.rejects(readCourse(temporary), /NAM-01/, candidate);
    }
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("readCourse uses exact class tokens and accepts HTML attribute whitespace and single quotes", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-html-attributes-"));
  try {
    await writeFixture(temporary);
    const slide = join(temporary, "lessons/values/deck/slides/01.html");
    await writeFile(
      slide,
      '<article class="slide-preview"><p data-learning-target="return-value">value</p></article>',
    );
    await assert.rejects(readCourse(temporary), /STR-01/);
    await writeFile(
      slide,
      "<article class = 'slide layout'><p data-learning-target = 'return-value'>value</p></article>",
    );
    const course = await readCourse(temporary);
    assert.equal(course.lessons[0]?.lesson.slides[0]?.notes[0]?.target, "return-value");
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("readCourse rejects a symlink leading outside the course", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "learning-boundary-"));
  try {
    const course = join(temporary, "course");
    await writeFixture(course);
    const outside = join(temporary, "outside.json");
    await writeFile(outside, JSON.stringify(profileFixture()));
    await unlink(join(course, "profile.json"));
    await symlink(outside, join(course, "profile.json"));
    await assert.rejects(readCourse(course), /OPS-02/);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
