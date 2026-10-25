const CANVAS_WIDTH = 1600;
const CANVAS_HEIGHT = 900;
const ANNOTATION_PADDING = 7;
const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

/** @type {Runtime|null} */
let activeRuntime = null;

/** @returns {Runtime} */
function getRuntime() {
  if (!activeRuntime) {
    throw new Error("教材が初期化されていません。");
  }
  return activeRuntime;
}

/** @typedef {{id:string,target:string,side:"left"|"right",title:string,body:string}} Note */
/** @typedef {{file:string,title:string,notes:Note[]}} Slide */
/** @typedef {{workspace:HTMLElement,stage:HTMLElement,frame:HTMLIFrameElement,overlay:SVGSVGElement,left:HTMLElement,right:HTMLElement,toggle:HTMLButtonElement,previous:HTMLButtonElement,next:HTMLButtonElement,status:HTMLElement,error:HTMLElement}} Elements */
/** @typedef {{elements:Elements,slides:Slide[],index:number,revision:number,isAnnotationsVisible:boolean,activeDocument:Document|null,animationFrame:number,cleanupDocument:()=>void,cards:Map<string,HTMLElement>}} Runtime */

/** @param {unknown} value @returns {value is Record<string,unknown>} */
function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** @param {unknown} value @param {string} field @returns {string} */
function readString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`教材データの ${field} が空か文字列以外です。`);
  }
  return value;
}

/** @param {unknown} value @returns {Note} */
function parseNote(value) {
  if (!isRecord(value)) {
    throw new Error("注目ポイントの形式が不正です。");
  }
  const id = readString(value.id, "note.id");
  const target = readString(value.target, "note.target");
  if (
    !/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/u.test(id) ||
    !/^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/u.test(target)
  ) {
    throw new Error("注目ポイントのIDと対象はkebab-caseで指定します。");
  }
  if (value.side !== "left" && value.side !== "right") {
    throw new Error("注目ポイントのsideはleftまたはrightです。");
  }
  return {
    id,
    target,
    side: value.side,
    title: readString(value.title, "note.title"),
    body: readString(value.body, "note.body"),
  };
}

/** @param {unknown} value @returns {Slide} */
function parseSlide(value) {
  if (!isRecord(value) || !Array.isArray(value.notes)) {
    throw new Error("スライドの形式が不正です。");
  }
  const file = readString(value.file, "slide.file");
  if (!/^deck\/slides\/[a-z0-9][a-z0-9-]*\.html$/u.test(file)) {
    throw new Error("スライドの参照先はdeck/slides内のHTMLに限定します。");
  }
  const notes = value.notes.map(parseNote);
  if (
    new Set(
      notes.map(function (note) {
        return note.id;
      }),
    ).size !== notes.length ||
    new Set(
      notes.map(function (note) {
        return note.target;
      }),
    ).size !== notes.length
  ) {
    throw new Error("同じスライド内の注目IDと対象は重複できません。");
  }
  return { file, title: readString(value.title, "slide.title"), notes };
}

/** @returns {Slide[]} */
function readSlides() {
  const element = document.getElementById("learning-data");
  if (!(element instanceof HTMLScriptElement) || element.type !== "application/json") {
    throw new Error("教材データが見つかりません。");
  }
  /** @type {unknown} */
  const value = JSON.parse(element.textContent ?? "");
  if (!isRecord(value) || !Array.isArray(value.slides) || value.slides.length === 0) {
    throw new Error("教材には1枚以上のスライドが必要です。");
  }
  return value.slides.map(parseSlide);
}

/** @param {string} id @returns {HTMLElement} */
function requireElement(id) {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`表示要素 #${id} が見つかりません。`);
  }
  return element;
}

/** @param {string} id @returns {HTMLButtonElement} */
function requireButton(id) {
  const element = requireElement(id);
  if (!(element instanceof HTMLButtonElement)) {
    throw new Error(`#${id} はbuttonで指定します。`);
  }
  return element;
}

/** @returns {Elements} */
function readElements() {
  const frame = requireElement("slide-frame");
  const overlay = document.querySelector("#annotation-overlay");
  if (!(frame instanceof HTMLIFrameElement) || !(overlay instanceof SVGSVGElement)) {
    throw new Error("スライドのiframeまたは注目表示のSVGが見つかりません。");
  }
  return {
    workspace: requireElement("lesson-workspace"),
    stage: requireElement("slide-stage"),
    frame,
    overlay,
    left: requireElement("notes-left"),
    right: requireElement("notes-right"),
    toggle: requireButton("annotation-toggle"),
    previous: requireButton("slide-previous"),
    next: requireButton("slide-next"),
    status: requireElement("slide-status"),
    error: requireElement("slide-error"),
  };
}

/** @param {string} message @returns {void} */
function showError(message) {
  const runtime = getRuntime();
  runtime.elements.error.textContent = message;
  runtime.elements.error.hidden = message === "";
}

/** @returns {number} */
function indexFromHash() {
  const runtime = getRuntime();
  const match = /^#slide-([1-9][0-9]*)$/u.exec(location.hash);
  const number = match ? Number(match[1]) : 1;
  if (!Number.isSafeInteger(number) || number > runtime.slides.length) {
    return 0;
  }
  return number - 1;
}

/** @param {Slide} slide @returns {void} */
function renderNotes(slide) {
  const runtime = getRuntime();
  runtime.cards.clear();
  runtime.elements.left.replaceChildren();
  runtime.elements.right.replaceChildren();
  slide.notes.forEach(function (note, index) {
    const card = document.createElement("article");
    card.className = "note-card";
    card.dataset.noteId = note.id;
    card.id = `note-${note.id}`;
    const title = document.createElement("h3");
    title.textContent = `${index + 1}. ${note.title}`;
    const body = document.createElement("p");
    body.textContent = note.body;
    card.append(title, body);
    const column = note.side === "left" ? runtime.elements.left : runtime.elements.right;
    column.append(card);
    runtime.cards.set(note.id, card);
  });
}

/** @returns {void} */
function applyVisibility() {
  const runtime = getRuntime();
  const isVisible = runtime.isAnnotationsVisible;
  runtime.elements.left.hidden = !isVisible;
  runtime.elements.right.hidden = !isVisible;
  runtime.elements.overlay.toggleAttribute("hidden", !isVisible);
  runtime.elements.workspace.dataset.annotations = isVisible ? "on" : "off";
  runtime.elements.toggle.setAttribute("aria-pressed", String(isVisible));
  runtime.elements.toggle.textContent = isVisible ? "注目ポイントを隠す" : "注目ポイントを表示";
  scheduleDraw();
}

/** @param {number} index @param {boolean} isUserNavigation @returns {void} */
function moveSlide(index, isUserNavigation) {
  const runtime = getRuntime();
  const slide = runtime.slides[index];
  if (!slide) {
    return;
  }
  const hash = `#slide-${index + 1}`;
  if (location.hash !== hash) {
    if (isUserNavigation) {
      history.pushState(null, "", hash);
    } else {
      history.replaceState(null, "", hash);
    }
  }
  if (runtime.index === index) {
    return;
  }
  runtime.revision += 1;
  runtime.cleanupDocument();
  runtime.activeDocument = null;
  runtime.index = index;
  runtime.elements.overlay.replaceChildren();
  showError("");
  renderNotes(slide);
  runtime.elements.previous.disabled = index === 0;
  runtime.elements.next.disabled = index === runtime.slides.length - 1;
  runtime.elements.status.textContent = `${index + 1} / ${runtime.slides.length} — ${slide.title}`;
  runtime.elements.frame.title = slide.title;
  const frameWindow = runtime.elements.frame.contentWindow;
  if (!frameWindow) {
    showError("スライドの表示領域を初期化できません。");
    return;
  }
  // iframe自身の履歴を増やすと、戻る操作が親のhashと分かれてしまう。
  frameWindow.location.replace(new URL(slide.file, location.href).href);
  applyVisibility();
}

/** @param {KeyboardEvent} event @returns {void} */
function onKey(event) {
  const runtime = getRuntime();
  const target = event.target;
  const isEditable =
    target instanceof HTMLElement &&
    (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/u.test(target.tagName));
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || isEditable) {
    return;
  }
  /** @type {Record<string,number>} */
  const destinations = {
    ArrowLeft: runtime.index - 1,
    ArrowRight: runtime.index + 1,
    Home: 0,
    End: runtime.slides.length - 1,
  };
  const destination = destinations[event.key];
  if (destination === undefined) {
    return;
  }
  event.preventDefault();
  moveSlide(destination, true);
}

/** @param {Document} frameDocument @param {number} revision @returns {boolean} */
function isCurrentDocument(frameDocument, revision) {
  const runtime = getRuntime();
  const slide = runtime.slides[runtime.index];
  return Boolean(
    slide &&
    runtime.revision === revision &&
    runtime.elements.frame.contentDocument === frameDocument &&
    frameDocument.URL === new URL(slide.file, location.href).href,
  );
}

/** @returns {Promise<void>} */
async function connectFrame() {
  const runtime = getRuntime();
  const revision = runtime.revision;
  let frameDocument = null;
  try {
    frameDocument = runtime.elements.frame.contentDocument;
  } catch {
    showError("注目表示には学習ページとスライドを同じHTTPサーバーで開く必要があります。");
    return;
  }
  if (!frameDocument) {
    showError("スライドを読み込めません。同じHTTPサーバーから開いてください。");
    return;
  }
  if (!isCurrentDocument(frameDocument, revision)) {
    return;
  }
  if (!frameDocument.querySelector(".slide")) {
    showError("スライドの本文を読み込めません。HTMLファイルを確認してください。");
    return;
  }
  runtime.activeDocument = frameDocument;
  bindFrameEvents(frameDocument, revision);
  scheduleDraw();
  await frameDocument.fonts.ready;
  if (isCurrentDocument(frameDocument, revision)) {
    scheduleDraw();
  }
}

/** @param {Document} frameDocument @param {number} revision @returns {void} */
function bindFrameEvents(frameDocument, revision) {
  const runtime = getRuntime();
  function update() {
    if (isCurrentDocument(frameDocument, revision)) {
      scheduleDraw();
    }
  }
  function key(/** @type {KeyboardEvent} */ event) {
    onKey(event);
  }
  frameDocument.addEventListener("animationend", update, true);
  frameDocument.addEventListener("transitionend", update, true);
  frameDocument.addEventListener("keydown", key);
  frameDocument.fonts.addEventListener("loadingdone", update);
  const observer = new ResizeObserver(update);
  const slide = runtime.slides[runtime.index];
  if (slide) {
    slide.notes.forEach(function (note) {
      const target = frameDocument.querySelector(`[data-learning-target="${note.target}"]`);
      if (target) {
        observer.observe(target);
      }
    });
  }
  runtime.cleanupDocument = function () {
    observer.disconnect();
    frameDocument.removeEventListener("animationend", update, true);
    frameDocument.removeEventListener("transitionend", update, true);
    frameDocument.removeEventListener("keydown", key);
    frameDocument.fonts.removeEventListener("loadingdone", update);
  };
}

/** @returns {void} */
function scheduleDraw() {
  const runtime = getRuntime();
  if (runtime.animationFrame) {
    cancelAnimationFrame(runtime.animationFrame);
  }
  const revision = runtime.revision;
  runtime.animationFrame = requestAnimationFrame(function () {
    runtime.animationFrame = 0;
    if (revision === runtime.revision) {
      drawAnnotations();
    }
  });
}

/** @returns {SVGDefsElement} */
function createArrow() {
  const definitions = document.createElementNS(SVG_NAMESPACE, "defs");
  const marker = document.createElementNS(SVG_NAMESPACE, "marker");
  marker.id = "annotation-arrow";
  marker.setAttribute("viewBox", "0 0 10 10");
  marker.setAttribute("refX", "9");
  marker.setAttribute("refY", "5");
  marker.setAttribute("markerWidth", "7");
  marker.setAttribute("markerHeight", "7");
  marker.setAttribute("orient", "auto");
  const arrow = document.createElementNS(SVG_NAMESPACE, "path");
  arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
  arrow.setAttribute("fill", "context-stroke");
  marker.append(arrow);
  definitions.append(marker);
  return definitions;
}

/** @typedef {{x:number,y:number,width:number,height:number}} Rectangle */
/** @param {Document} frameDocument @returns {Rectangle[]} */
function textRectangles(frameDocument) {
  const range = frameDocument.createRange();
  // SHOW_TEXT=4。iframe内の実際の文字行だけを衝突判定に使う。
  const walker = frameDocument.createTreeWalker(frameDocument.body, 4);
  /** @type {Rectangle[]} */
  const rectangles = [];
  let node = walker.nextNode();
  while (node) {
    if (node.textContent?.trim()) {
      range.selectNodeContents(node);
      for (const rectangle of range.getClientRects()) {
        if (rectangle.width > 0 && rectangle.height > 0) {
          rectangles.push(translateRectangle(rectangle));
        }
      }
    }
    node = walker.nextNode();
  }
  return rectangles;
}

/** @param {DOMRect} target @returns {Rectangle} */
function translateRectangle(target) {
  const runtime = getRuntime();
  const frame = runtime.elements.frame.getBoundingClientRect();
  const overlay = runtime.elements.overlay.getBoundingClientRect();
  const scaleX = frame.width / CANVAS_WIDTH;
  const scaleY = frame.height / CANVAS_HEIGHT;
  return {
    x: frame.left - overlay.left + target.left * scaleX,
    y: frame.top - overlay.top + target.top * scaleY,
    width: target.width * scaleX,
    height: target.height * scaleY,
  };
}

/** @param {Rectangle} left @param {Rectangle} right @returns {boolean} */
function rectanglesOverlap(left, right) {
  return (
    left.x < right.x + right.width &&
    left.x + left.width > right.x &&
    left.y < right.y + right.height &&
    left.y + left.height > right.y
  );
}

/** @param {number} origin @param {number} minimum @param {number} maximum @returns {number[]} */
function labelCoordinates(origin, minimum, maximum) {
  const positions = [Math.max(minimum, Math.min(maximum, origin)), maximum];
  // CSSピクセルで探すため、縮小したコードの行間に番号を押し込まない。
  for (let position = minimum; position <= maximum; position += 8) {
    positions.push(position);
  }
  return [...new Set(positions)].sort(function (left, right) {
    return Math.abs(left - origin) - Math.abs(right - origin);
  });
}

/** @param {SVGTextElement} label @param {Rectangle} target @param {"left"|"right"} side @param {Rectangle[]} obstacles @returns {Rectangle|null} */
function placeLabel(label, target, side, obstacles) {
  const runtime = getRuntime();
  const frame = runtime.elements.frame.getBoundingClientRect();
  const overlay = runtime.elements.overlay.getBoundingClientRect();
  const bounds = label.getBBox();
  // 白い縁取りも含めて文字から離し、番号全体をスライド内へ収める。
  const width = bounds.width + 4;
  const height = bounds.height + 4;
  const originX =
    side === "left"
      ? target.x - ANNOTATION_PADDING - 4 - width
      : target.x + target.width + ANNOTATION_PADDING + 4;
  const columns = labelCoordinates(
    originX,
    frame.left - overlay.left + 2,
    frame.right - overlay.left - width - 2,
  );
  const rows = labelCoordinates(
    target.y + (target.height - height) / 2,
    frame.top - overlay.top + 2,
    frame.bottom - overlay.top - height - 2,
  );
  for (const y of rows) {
    for (const x of columns) {
      const candidate = { x, y, width, height };
      if (
        !obstacles.some(function (obstacle) {
          return rectanglesOverlap(candidate, obstacle);
        })
      ) {
        label.setAttribute("x", String(x - bounds.x + 2));
        label.setAttribute("y", String(y - bounds.y + 2));
        return candidate;
      }
    }
  }
  return null;
}

/** @param {DOMRect} card @param {Rectangle} target @param {DOMRect} overlay @param {"left"|"right"} side @returns {string} */
function arrowPath(card, target, overlay, side) {
  const centerY = target.y + target.height / 2;
  if (card.top - overlay.top > target.y + target.height) {
    const isLeft = side === "left";
    const startX = (isLeft ? card.left : card.right) - overlay.left;
    const startY = card.top - overlay.top + card.height / 2;
    const gutterX = isLeft ? 4 : overlay.width - 4;
    const endX = isLeft
      ? target.x - ANNOTATION_PADDING
      : target.x + target.width + ANNOTATION_PADDING;
    // 縦に並んだ他のカードへ線を通さず、左右の余白から対象へ戻す。
    return `M ${startX} ${startY} H ${gutterX} V ${centerY} H ${endX}`;
  }
  const isLeft = side === "left";
  const startX = (isLeft ? card.right : card.left) - overlay.left;
  const startY = card.top - overlay.top + card.height / 2;
  const endX = isLeft
    ? target.x - ANNOTATION_PADDING
    : target.x + target.width + ANNOTATION_PADDING;
  const middleX = (startX + endX) / 2;
  return `M ${startX} ${startY} C ${middleX} ${startY} ${middleX} ${centerY} ${endX} ${centerY}`;
}

/** @param {Note} note @param {Rectangle} target @param {number} index @returns {SVGGElement|null} */
function createAnnotation(note, target, index) {
  const runtime = getRuntime();
  const card = runtime.cards.get(note.id);
  if (!card) {
    return null;
  }
  const group = document.createElementNS(SVG_NAMESPACE, "g");
  group.dataset.noteId = note.id;
  const ellipse = document.createElementNS(SVG_NAMESPACE, "ellipse");
  ellipse.setAttribute("cx", String(target.x + target.width / 2));
  ellipse.setAttribute("cy", String(target.y + target.height / 2));
  ellipse.setAttribute("rx", String(target.width / 2 + ANNOTATION_PADDING));
  ellipse.setAttribute("ry", String(target.height / 2 + ANNOTATION_PADDING));
  const path = document.createElementNS(SVG_NAMESPACE, "path");
  path.setAttribute(
    "d",
    arrowPath(
      card.getBoundingClientRect(),
      target,
      runtime.elements.overlay.getBoundingClientRect(),
      note.side,
    ),
  );
  path.setAttribute("marker-end", "url(#annotation-arrow)");
  const label = document.createElementNS(SVG_NAMESPACE, "text");
  label.setAttribute("x", "0");
  label.setAttribute("y", "0");
  label.setAttribute("text-anchor", "middle");
  label.setAttribute("dominant-baseline", "middle");
  label.textContent = String(index + 1);
  group.append(path, ellipse, label);
  return group;
}

/** @param {Slide} slide @param {Document} frameDocument @returns {string[]} */
function drawNotes(slide, frameDocument) {
  const runtime = getRuntime();
  /** @type {string[]} */
  const errors = [];
  const obstacles = textRectangles(frameDocument);
  slide.notes.forEach(function (note, index) {
    const matches = frameDocument.querySelectorAll(`[data-learning-target="${note.target}"]`);
    const target = matches[0];
    if (matches.length !== 1 || !target) {
      errors.push(`注目対象「${note.target}」は1つ必要です（現在${matches.length}件）。`);
      return;
    }
    const rectangle = target.getBoundingClientRect();
    if (rectangle.width <= 0 || rectangle.height <= 0) {
      errors.push(`注目対象「${note.target}」を表示できません。`);
      return;
    }
    const targetRectangle = translateRectangle(rectangle);
    const annotation = createAnnotation(note, targetRectangle, index);
    if (annotation) {
      runtime.elements.overlay.append(annotation);
      const label = annotation.querySelector("text");
      if (label) {
        const placement = placeLabel(label, targetRectangle, note.side, obstacles);
        if (placement) {
          obstacles.push(placement);
        } else {
          annotation.remove();
          errors.push(`注目番号「${index + 1}」を置く余白がありません。文字量を減らしてください。`);
        }
      }
    }
  });
  return errors;
}

/** @returns {void} */
function drawAnnotations() {
  const runtime = getRuntime();
  const elements = runtime.elements;
  const scale = elements.stage.getBoundingClientRect().width / CANVAS_WIDTH;
  elements.frame.style.transform = `scale(${scale})`;
  if (!runtime.isAnnotationsVisible) {
    return;
  }
  const frameDocument = runtime.activeDocument;
  const slide = runtime.slides[runtime.index];
  if (!frameDocument || !slide || !isCurrentDocument(frameDocument, runtime.revision)) {
    return;
  }
  const rectangle = elements.overlay.getBoundingClientRect();
  elements.overlay.setAttribute("viewBox", `0 0 ${rectangle.width} ${rectangle.height}`);
  elements.overlay.replaceChildren(createArrow());
  showError(drawNotes(slide, frameDocument).join(" "));
}

/** @returns {void} */
function bindPageEvents() {
  const runtime = getRuntime();
  const elements = runtime.elements;
  elements.frame.addEventListener("load", function () {
    void connectFrame();
  });
  elements.previous.addEventListener("click", function () {
    moveSlide(runtime.index - 1, true);
  });
  elements.next.addEventListener("click", function () {
    moveSlide(runtime.index + 1, true);
  });
  elements.toggle.addEventListener("click", function () {
    runtime.isAnnotationsVisible = !runtime.isAnnotationsVisible;
    applyVisibility();
  });
  window.addEventListener("hashchange", function () {
    moveSlide(indexFromHash(), false);
  });
  window.addEventListener("resize", function () {
    scheduleDraw();
  });
  document.addEventListener("keydown", function (event) {
    onKey(event);
  });
  const observer = new ResizeObserver(function () {
    scheduleDraw();
  });
  observer.observe(elements.workspace);
  observer.observe(elements.stage);
  observer.observe(elements.left);
  observer.observe(elements.right);
}

/** @returns {void} */
function initialize() {
  if (!document.getElementById("lesson-workspace")) {
    return;
  }
  const elements = readElements();
  /** @type {Runtime} */
  const runtime = {
    elements,
    slides: readSlides(),
    index: -1,
    revision: 0,
    isAnnotationsVisible: true,
    activeDocument: null,
    animationFrame: 0,
    cleanupDocument: function () {},
    cards: new Map(),
  };
  activeRuntime = runtime;
  elements.frame.width = String(CANVAS_WIDTH);
  elements.frame.height = String(CANVAS_HEIGHT);
  elements.frame.setAttribute("sandbox", "allow-same-origin");
  elements.overlay.setAttribute("aria-hidden", "true");
  elements.overlay.setAttribute("focusable", "false");
  elements.error.setAttribute("role", "alert");
  elements.status.setAttribute("aria-live", "polite");
  bindPageEvents();
  moveSlide(indexFromHash(), false);
}

try {
  initialize();
} catch (error) {
  const element = document.getElementById("slide-error");
  if (element instanceof HTMLElement) {
    element.hidden = false;
    element.textContent = error instanceof Error ? error.message : "教材を表示できません。";
  } else {
    throw error;
  }
}

export {};
