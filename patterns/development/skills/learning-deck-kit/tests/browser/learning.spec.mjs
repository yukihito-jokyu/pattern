/// <reference lib="dom" />

import { test, expect } from "@playwright/test";
import { readCourse } from "../../.claude/skills/learning-setup/scripts/model.mjs";

const referenceCourse = await readCourse("courses/go");

/** @typedef {import("@playwright/test").Page} Page */
/** @typedef {{id:string,target:string,side:"left"|"right",title:string,body:string}} Note */
/** @typedef {{file:string,title:string,notes:Note[]}} Slide */

/** @param {Page} page @returns {Promise<Slide[]>} */
async function readSlides(page) {
  const text = await page.locator("#learning-data").textContent();
  /** @type {{slides:Slide[]}} */
  const data = JSON.parse(text ?? "");
  return data.slides;
}

/** @param {Page} page @param {number} index @returns {Promise<Slide>} */
async function expectSlide(page, index) {
  const slides = await readSlides(page);
  const slide = slides[index];
  if (!slide) {
    throw new Error("テストが指定したスライドは存在しません。");
  }
  await expect(page).toHaveURL(new RegExp(`#slide-${index + 1}$`, "u"));
  await expect(page.locator("#slide-status")).toHaveText(
    `${index + 1} / ${slides.length} — ${slide.title}`,
  );
  await expect(page.locator("#slide-frame")).toHaveAttribute("title", slide.title);
  await expect(page.frameLocator("#slide-frame").locator(".slide")).toBeVisible();
  await expect(page.locator("#annotation-overlay g[data-note-id]")).toHaveCount(slide.notes.length);
  await expect(page.locator("#slide-error")).toBeHidden();
  return slide;
}

/** @param {Page} page @param {Note} note @returns {Promise<number>} */
async function annotationError(page, note) {
  const target = await page
    .frameLocator("#slide-frame")
    .locator(`[data-learning-target="${note.target}"]`)
    .evaluate(function (element) {
      const box = element.getBoundingClientRect();
      return { x: box.x, y: box.y, width: box.width, height: box.height };
    });
  const frame = await page.locator("#slide-frame").boundingBox();
  const overlay = await page.locator("#annotation-overlay").boundingBox();
  if (!frame || !overlay) {
    throw new Error("スライドまたは注目枠を計測できません。");
  }
  const actual = await page
    .locator(`#annotation-overlay g[data-note-id="${note.id}"] ellipse`)
    .evaluate(function (element) {
      return {
        x: Number(element.getAttribute("cx")),
        y: Number(element.getAttribute("cy")),
        rx: Number(element.getAttribute("rx")),
        ry: Number(element.getAttribute("ry")),
      };
    });
  const scaleX = frame.width / 1600;
  const scaleY = frame.height / 900;
  return Math.max(
    Math.abs(overlay.x + actual.x - (frame.x + (target.x + target.width / 2) * scaleX)),
    Math.abs(overlay.y + actual.y - (frame.y + (target.y + target.height / 2) * scaleY)),
    Math.abs(actual.rx - ((target.width * scaleX) / 2 + 7)),
    Math.abs(actual.ry - ((target.height * scaleY) / 2 + 7)),
  );
}

/** @param {Page} page @param {Slide} slide @returns {Promise<void>} */
async function expectAnnotations(page, slide) {
  for (const note of slide.notes) {
    await expect(page.locator(`article[data-note-id="${note.id}"]`)).toContainText(note.body);
    await expect
      .poll(function () {
        return annotationError(page, note);
      })
      .toBeLessThan(1);
    await expect(
      page.locator(`#annotation-overlay g[data-note-id="${note.id}"] > path`),
    ).toHaveAttribute("d", /^M /u);
  }
}

/** @param {Page} page @returns {Promise<boolean | null>} */
async function arrowTouchesNoteText(page) {
  return page.locator("body").evaluate(function (body) {
    const elements = body.ownerDocument.querySelectorAll(
      "#annotation-overlay g[data-note-id] > path",
    );
    if (elements.length === 0) {
      return null;
    }
    for (const element of elements) {
      const path = /** @type {SVGPathElement} */ (element);
      const svg = path.ownerSVGElement;
      if (!svg) {
        return null;
      }
      const viewport = svg.getBoundingClientRect();
      const bodies = [...path.ownerDocument.querySelectorAll(".note-card h3, .note-card p")].map(
        function (body) {
          return body.getBoundingClientRect();
        },
      );
      const length = path.getTotalLength();
      for (let position = 0; position <= length; position += 3) {
        const point = path.getPointAtLength(position);
        const x = viewport.left + point.x;
        const y = viewport.top + point.y;
        if (
          bodies.some(function (body) {
            return (
              x >= body.left - 2 && x <= body.right + 2 && y >= body.top - 2 && y <= body.bottom + 2
            );
          })
        ) {
          return true;
        }
      }
    }
    return false;
  });
}

/** @param {Page} page @returns {Promise<string[]>} */
async function labelsTouchSlideText(page) {
  return page.locator("body").evaluate(function (body) {
    const owner = body.ownerDocument;
    const frame = /** @type {HTMLIFrameElement | null} */ (owner.querySelector("#slide-frame"));
    const content = frame?.contentDocument;
    if (!frame || !content) {
      throw new Error("番号と本文の重なりを計測できません。");
    }
    const frameBox = frame.getBoundingClientRect();
    const range = content.createRange();
    // 4はNodeFilter.SHOW_TEXT。実際の文字の行矩形を取得する。
    const walker = content.createTreeWalker(content.body, 4);
    /** @type {{left:number,right:number,top:number,bottom:number}[]} */
    const boxes = [];
    let node = walker.nextNode();
    while (node) {
      if (node.textContent?.trim()) {
        range.selectNodeContents(node);
        for (const box of range.getClientRects()) {
          if (box.width > 0 && box.height > 0) {
            boxes.push({
              left: frameBox.left + (box.left * frameBox.width) / 1600,
              right: frameBox.left + (box.right * frameBox.width) / 1600,
              top: frameBox.top + (box.top * frameBox.height) / 900,
              bottom: frameBox.top + (box.bottom * frameBox.height) / 900,
            });
          }
        }
      }
      node = walker.nextNode();
    }
    return [...owner.querySelectorAll("#annotation-overlay g[data-note-id] > text")]
      .filter(function (label) {
        const number = label.getBoundingClientRect();
        return boxes.some(function (text) {
          return (
            number.left < text.right &&
            number.right > text.left &&
            number.top < text.bottom &&
            number.bottom > text.top
          );
        });
      })
      .map(function (label) {
        return label.parentElement?.getAttribute("data-note-id") ?? "unknown";
      });
  });
}

/** @param {Page} page @param {Slide} slide @returns {Promise<void>} */
async function expectLabelsInsideSlide(page, slide) {
  const { frame, numbers } = await page.locator("body").evaluate(function (body) {
    const owner = body.ownerDocument;
    const frame = owner.querySelector("#slide-frame")?.getBoundingClientRect();
    if (!frame) {
      throw new Error("番号の表示範囲を計測できません。");
    }
    const numbers = [...owner.querySelectorAll("#annotation-overlay g[data-note-id] > text")].map(
      function (label) {
        return {
          id: label.parentElement?.getAttribute("data-note-id"),
          text: label.textContent,
          box: label.getBoundingClientRect().toJSON(),
        };
      },
    );
    return { frame: frame.toJSON(), numbers };
  });
  expect(numbers).toHaveLength(slide.notes.length);
  const labels = [];
  for (const [index, note] of slide.notes.entries()) {
    const number = numbers.find(function (number) {
      return number.id === note.id;
    });
    if (!number) {
      throw new Error(`注目番号 ${note.id} を計測できません。`);
    }
    expect(number.text).toBe(String(index + 1));
    const box = number.box;
    // 2pxの白い縁もスライド内に収まり、他の番号と重ならない。
    const context = `${page.url()} ${note.id}`;
    expect(box.x - 2, context).toBeGreaterThanOrEqual(frame.x);
    expect(box.x + box.width + 2, context).toBeLessThanOrEqual(frame.x + frame.width);
    expect(box.y - 2, context).toBeGreaterThanOrEqual(frame.y);
    expect(box.y + box.height + 2, context).toBeLessThanOrEqual(frame.y + frame.height);
    for (const previous of labels) {
      const overlaps =
        box.x - 2 < previous.x + previous.width + 2 &&
        box.x + box.width + 2 > previous.x - 2 &&
        box.y - 2 < previous.y + previous.height + 2 &&
        box.y + box.height + 2 > previous.y - 2;
      expect(overlaps).toBe(false);
    }
    labels.push(box);
  }
}

test("注目番号は隣のコード行や図の文字を覆わない", async function ({ page }) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const { lesson } of referenceCourse.lessons) {
      for (let index = 0; index < lesson.slides.length; index += 1) {
        await page.goto(`/${lesson.id}/#slide-${index + 1}`);
        const slide = await expectSlide(page, index);
        await expect
          .poll(
            function () {
              return labelsTouchSlideText(page);
            },
            { message: `${lesson.id} slide ${index + 1}, width ${width}` },
          )
          .toEqual([]);
        await expectLabelsInsideSlide(page, slide);
      }
    }
  }
});

for (const {
  lesson: { id: lesson },
} of referenceCourse.lessons) {
  test(`${lesson}: 注目枠は独立した対象要素の位置と大きさに合う`, async function ({ page }) {
    await page.goto(`/${lesson}/`);
    const slide = await expectSlide(page, 0);
    await expectAnnotations(page, slide);
    await expect(page.locator("#annotation-overlay")).toHaveAttribute("aria-hidden", "true");
    const pointerEvents = await page.locator("#annotation-overlay").evaluate(function (element) {
      return element.ownerDocument.defaultView?.getComputedStyle(element).pointerEvents;
    });
    expect(pointerEvents).toBe("none");
  });
}

test("表示OFFは補足と枠を隠し、本文・現在枚・学習位置を保つ", async function ({ page }) {
  await page.goto("/variables/#slide-2");
  const slide = await expectSlide(page, 1);
  const textBefore = await page.locator(".lesson-body").textContent();
  const toggle = page.locator("#annotation-toggle");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator("#notes-left")).toBeHidden();
  await expect(page.locator("#notes-right")).toBeHidden();
  await expect(page.locator("#annotation-overlay")).toBeHidden();
  await expect(page).toHaveURL(/#slide-2$/u);
  expect(await page.locator(".lesson-body").textContent()).toBe(textBefore);
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await expectAnnotations(page, slide);
});

test("前後・hash・履歴とキーボードで同じ枚を復元する", async function ({ page }) {
  await page.goto("/variables/");
  await expectSlide(page, 0);
  await expect(page.getByRole("button", { name: "前のスライド" })).toBeDisabled();
  await page.getByRole("button", { name: "次のスライド" }).focus();
  await page.keyboard.press("Enter");
  await expectSlide(page, 1);
  await expect(page.getByRole("button", { name: "次のスライド" })).toBeDisabled();
  await page.goBack();
  await expectSlide(page, 0);
  await page
    .frameLocator("#slide-frame")
    .locator(".slide")
    .click({ position: { x: 20, y: 20 } });
  await page.keyboard.press("ArrowRight");
  await expectSlide(page, 1);
  await page.keyboard.press("Home");
  await expectSlide(page, 0);
  await page.keyboard.press("End");
  await expectSlide(page, 1);
});

test("リサイズと狭い画面で枠を再計測し、番号付きの説明を読める", async function ({ page }) {
  await page.goto("/variables/");
  const slide = await expectSlide(page, 0);
  await page.setViewportSize({ width: 1180, height: 900 });
  await expectAnnotations(page, slide);
  await page.setViewportSize({ width: 390, height: 844 });
  await expectAnnotations(page, slide);
  const stage = await page.locator("#slide-stage").boundingBox();
  const left = await page.locator("#notes-left").boundingBox();
  if (!stage || !left) {
    throw new Error("狭い画面の配置を計測できません。");
  }
  expect(left.y).toBeGreaterThanOrEqual(stage.y + stage.height);
  const overflow = await page.locator("body").evaluate(function (element) {
    return element.scrollWidth - element.ownerDocument.documentElement.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(1);
  const note = slide.notes[0];
  if (!note) {
    throw new Error("見本には注目ポイントが必要です。");
  }
  await expect(page.locator(`article[data-note-id="${note.id}"] h3`)).toContainText("1.");
  await page.getByRole("button", { name: "次のスライド" }).click();
  await expectAnnotations(page, await expectSlide(page, 1));
});

test("縦配置の矢印は説明カードの本文を通らずガターを通る", async function ({ page }) {
  await page.goto("/variables/");
  const slide = await expectSlide(page, 0);
  for (const width of [390, 768, 1100]) {
    await page.setViewportSize({ width, height: 900 });
    await expectAnnotations(page, slide);
    await expect
      .poll(function () {
        return arrowTouchesNoteText(page);
      })
      .toBe(false);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .locator(".note-card p")
    .first()
    .evaluate(function (element) {
      const content = (element.textContent ?? "").repeat(8);
      element.replaceChildren(element.ownerDocument.createTextNode(content));
    });
  await expect
    .poll(function () {
      return arrowTouchesNoteText(page);
    })
    .toBe(false);
  await page.getByRole("button", { name: "次のスライド" }).click();
  await expectAnnotations(page, await expectSlide(page, 1));
  await expect
    .poll(function () {
      return arrowTouchesNoteText(page);
    })
    .toBe(false);
});

test("通常motionのアニメーションとtransitionの終了後も対象へ追従する", async function ({ page }) {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/variables/");
  const slide = await expectSlide(page, 0);
  const note = slide.notes[0];
  if (!note) {
    throw new Error("見本には注目ポイントが必要です。");
  }
  const target = page
    .frameLocator("#slide-frame")
    .locator(`[data-learning-target="${note.target}"]`);
  await expect
    .poll(async function () {
      return page
        .frameLocator("#slide-frame")
        .locator(".slide")
        .evaluate(function (element) {
          return element.getAnimations({ subtree: true }).every(function (animation) {
            return animation.playState === "finished";
          });
        });
    })
    .toBe(true);
  const initialY = await target.evaluate(function (element) {
    return element.getBoundingClientRect().y;
  });
  await target.evaluate(function (element) {
    const sheet = element.ownerDocument.createElement("style");
    sheet.textContent = `
      @keyframes learning-test-arrive { from { transform: translateY(0); } to { transform: translateY(45px); } }
      [data-learning-test-animation] { animation: learning-test-arrive 90ms linear both !important; }
    `;
    element.ownerDocument.head.append(sheet);
    element.setAttribute("data-learning-test-animation", "");
  });
  await expect
    .poll(async function () {
      return target.evaluate(function (element) {
        return element.getAnimations().every(function (animation) {
          return animation.playState === "finished";
        });
      });
    })
    .toBe(true);
  const animatedY = await target.evaluate(function (element) {
    return element.getBoundingClientRect().y;
  });
  expect(animatedY - initialY).toBeCloseTo(45, 1);
  await expectAnnotations(page, slide);
  await target.evaluate(function (element) {
    const sheet = element.ownerDocument.createElement("style");
    sheet.textContent = `
      [data-learning-test-animation] { animation: none !important; transform: translateY(45px); }
      [data-learning-test-transition] { transition: transform 90ms linear !important; transform: translateY(90px); }
    `;
    element.ownerDocument.head.append(sheet);
    element.getBoundingClientRect();
    element.setAttribute("data-learning-test-transition", "");
  });
  await expect
    .poll(async function () {
      return target.evaluate(function (element) {
        return element.getAnimations().every(function (animation) {
          return animation.playState === "finished";
        });
      });
    })
    .toBe(true);
  const transitionedY = await target.evaluate(function (element) {
    return element.getBoundingClientRect().y;
  });
  expect(transitionedY - initialY).toBeCloseTo(90, 1);
  await expectAnnotations(page, slide);
});

test("古いスライドの遅い読込が現在枚の説明と枠を上書きしない", async function ({ page }) {
  const gate = { release: function () {} };
  const completed = { release: function () {} };
  /** @type {Promise<void>} */
  const held = new Promise(function (resolve) {
    gate.release = function () {
      resolve();
    };
  });
  /** @type {Promise<void>} */
  const oldRequestCompleted = new Promise(function (resolve) {
    completed.release = function () {
      resolve();
    };
  });
  let heldRequests = 0;
  await page.route("**/variables/deck/slides/01.html", async function (route) {
    heldRequests += 1;
    await held;
    await route.continue();
    completed.release();
  });
  await page.goto("/variables/", { waitUntil: "domcontentloaded" });
  await expect
    .poll(function () {
      return heldRequests;
    })
    .toBe(1);
  await page.getByRole("button", { name: "次のスライド" }).click();
  const second = await expectSlide(page, 1);
  gate.release();
  await oldRequestCompleted;
  await expectAnnotations(page, second);
  await expect(page.locator("#notes-left")).not.toContainText("名前で後から参照する");
});

test("対象欠損は誤った丸枠で隠さず、原因を表示する", async function ({ page }) {
  await page.route("**/variables/deck/slides/01.html", async function (route) {
    const response = await route.fetch();
    const html = await response.text();
    await route.fulfill({
      response,
      body: html.replace(/data-learning-target="[a-z0-9-]+"/u, 'data-learning-missing="removed"'),
    });
  });
  await page.goto("/variables/");
  const slides = await readSlides(page);
  const slide = slides[0];
  if (!slide) {
    throw new Error("見本にはスライドが必要です。");
  }
  await expect(page.locator("#slide-error")).toContainText("現在0件");
  await expect(page.locator("#annotation-overlay g[data-note-id]")).toHaveCount(
    slide.notes.length - 1,
  );
  await expect(page.locator(".lesson-body")).toBeVisible();
  await page.getByRole("button", { name: "次のスライド" }).click();
  await expectAnnotations(page, await expectSlide(page, 1));
});
