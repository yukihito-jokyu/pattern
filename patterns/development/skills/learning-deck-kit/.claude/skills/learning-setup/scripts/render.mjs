/** @typedef {import('./types.js').Profile} Profile */
/** @typedef {import('./types.js').Lesson} Lesson */

/** @param {string} value @returns {string} HTMLテキストと属性をエスケープする。 */
function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/** @param {string} title @param {string} body @param {string} prefix @returns {string} */
function document(title, body, prefix) {
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self'; script-src 'self'; frame-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none'">
  <title>${escapeHtml(title)}</title>
  <link rel="stylesheet" href="${prefix}assets/learning.css">
</head>
<body>
  <a class="skip-link" href="#main-content">本文へ移動</a>
${body}
</body>
</html>
`;
}

/** @param {Profile} profile @returns {string} カリキュラム順の入口を生成する。 */
export function renderCourse(profile) {
  const items = profile.curriculum
    .map(
      (unit, index) =>
        `<li><a href="${unit.id}/"><span class="lesson-number">${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(unit.title)}</strong><span>${escapeHtml(unit.goal)}</span></a></li>`,
    )
    .join("\n");
  return document(
    profile.title,
    `<main id="main-content" class="course-page">
    <p class="eyebrow">LEARNING PATH · ${escapeHtml(profile.technology)} ${escapeHtml(profile.version)}</p>
    <h1>${escapeHtml(profile.title)}</h1>
    <p class="course-goal">${escapeHtml(profile.goal)}</p>
    <p>対象読者：${escapeHtml(profile.audience)}</p>
    <h2>前提を積み上げて学ぶ</h2>
    <ol class="curriculum">${items}</ol>
    <p>各ページはスライドで全体像をつかみ、下の説明と例で動作を確かめる構成です。左右の注目説明はボタンで表示を切り替えられます。</p>
    <section><h2>使用する公式資料</h2>${sources(
      profile,
      profile.sources.map((source) => source.id),
    )}</section>
  </main>`,
    "",
  );
}

/** @param {Profile} profile @param {string[]} refs @returns {string} */
function sources(profile, refs) {
  return `<ul class="source-list">${profile.sources
    .filter((source) => refs.includes(source.id))
    .map(
      (source) =>
        `<li><a href="${escapeHtml(source.url)}">${escapeHtml(source.title)}</a> — ${escapeHtml(source.version)}、確認日 ${escapeHtml(source.checkedAt)}</li>`,
    )
    .join("")}</ul>`;
}

/** @param {Profile} profile @param {Lesson} lesson @returns {string} 学習本文と独立スライドのホストを生成する。 */
export function renderLesson(profile, lesson) {
  const index = profile.curriculum.findIndex((unit) => unit.id === lesson.id);
  const previous = profile.curriculum[index - 1];
  const next = profile.curriculum[index + 1];
  const prerequisites = lesson.prerequisites
    .map((value) => `<li>${escapeHtml(value)}</li>`)
    .join("");
  const explanation = lesson.explanation
    .map(
      (section) =>
        `<section><h3>${escapeHtml(section.title)}</h3><p>${escapeHtml(section.body).replaceAll("\n", "<br>")}</p>${section.code ? `<pre><code>${escapeHtml(section.code)}</code></pre>` : ""}${section.output ? `<p class="output-label">期待する実行結果</p><pre class="expected-output"><code>${escapeHtml(section.output)}</code></pre>` : ""}</section>`,
    )
    .join("\n");
  const data = JSON.stringify({
    slides: lesson.slides.map((slide) => ({ ...slide, file: `deck/slides/${slide.file}` })),
  }).replaceAll("<", "\\u003c");
  return document(
    `${lesson.title} | ${profile.title}`,
    `<header class="lesson-header">
    <a href="../">← ${escapeHtml(profile.title)}</a>
    <p class="eyebrow">LESSON ${String(index + 1).padStart(2, "0")} / ${String(profile.curriculum.length).padStart(2, "0")} · ${escapeHtml(profile.technology)} ${escapeHtml(profile.version)}</p>
    <h1>${escapeHtml(lesson.title)}</h1>
    <p class="lesson-goal">${escapeHtml(lesson.goal)}</p>
  </header>
  <main id="main-content">
    <section class="slide-section" aria-label="スライドと注目説明">
      <div class="slide-toolbar">
        <button type="button" id="slide-previous" aria-label="前のスライド">← 前へ</button>
        <p id="slide-status" aria-live="polite"></p>
        <button type="button" id="slide-next" aria-label="次のスライド">次へ →</button>
        <button type="button" id="annotation-toggle" aria-pressed="true">注目説明</button>
      </div>
      <div id="lesson-workspace">
        <aside id="notes-left" aria-label="左の注目説明"></aside>
        <div id="slide-stage"><iframe id="slide-frame" width="1600" height="900" title="${escapeHtml(lesson.title)}のスライド" sandbox="allow-same-origin"></iframe></div>
        <aside id="notes-right" aria-label="右の注目説明"></aside>
        <svg id="annotation-overlay" aria-hidden="true"></svg>
      </div>
      <p id="slide-error" role="status"></p>
    </section>
    <article class="lesson-body">
      <section><h2>この学習で使う前提</h2><ul>${prerequisites}</ul></section>
      <section><h2>スライドから具体的な動作へ</h2>${explanation}</section>
      <section class="exercise"><h2>自分で確かめる</h2><p>${escapeHtml(lesson.exercise.prompt)}</p><details><summary>解説を読む</summary><p>${escapeHtml(lesson.exercise.answer)}</p></details></section>
      <section><h2>この学習の出典</h2>${sources(profile, lesson.sources)}</section>
    </article>
    <nav class="lesson-navigation" aria-label="学習項目の移動">${previous ? `<a href="../${previous.id}/">← ${escapeHtml(previous.title)}</a>` : "<span></span>"}${next ? `<a href="../${next.id}/">${escapeHtml(next.title)} →</a>` : `<a href="../">学習一覧へ戻る</a>`}</nav>
  </main>
  <script id="learning-data" type="application/json">${data}</script>
  <script type="module" src="../assets/learning.mjs"></script>`,
    "../",
  );
}

/** @param {Profile} profile @returns {string} 対象別スキルを入力から再現可能に生成する。 */
export function renderSkill(profile) {
  return `---
name: learn-${profile.id}
description: ${JSON.stringify(`${profile.technology} ${profile.version}を、${profile.goal}ために体系的に学ぶHTML教材を作成・更新する。対象の学習、教材追加、例の説明、資料更新の依頼で使う。`)}
---

# ${profile.technology}を体系的に学ぶ

到達目標：${profile.goal}
対象読者：${profile.audience}

このファイルはprofileからの生成物である。対象版と資料の正本は [profile.json](references/profile.json)、資料URLは [sources.md](references/sources.md)、取得と更新は [workflow.md](references/workflow.md) に置く。

1. workflow.mdを読み、登録された公式資料を実際に取得する。取得できた本文と対象版だけを根拠にし、未取得は確認済みと書かない。
2. 入力のprofileと同じidを持つコースディレクトリを利用先で特定する。候補が複数あれば依頼の対象を確定する。
3. profile.curriculumの前提と順序に従い、1学習項目1到達目標で作る。既に分かっている目標や前提を聞き直さない。
4. 兄弟のlearning-setupスキルの [教材作成手順](../learning-setup/references/authoring.md) に従い、同梱html-deckを使ってdeckを作る。スライドを短く保ち、前提・流れ・実行例・練習をlesson.jsonへ書く。
5. 注目対象はdata-learning-targetで特定し、左右の説明と対応させる。対象や例を変えたら本文・注目点・出力・出典も照合する。
6. learning-setup/scripts/learning.mjsのcheck/build、html-deckの実測検査、学習ページの表示を確認する。失敗、未実施、人間の確認待ちを分けて報告する。

スライドの制作と実測は兄弟のlearning-setup/vendor/html-deck/SKILL.mdを使う。外側の学習ページはそのスライドHTMLを同一originのiframeに埋め込む。
`;
}

/** @param {Profile} profile @returns {string} */
export function renderSources(profile) {
  return `# ${profile.technology}の公式資料\n\n対象版：${profile.version}。以下の確認日はprofileの入力値であり、この生成コマンドがネットワーク取得したという意味ではない。制作時にはworkflowの取得手順を実行する。\n\n${profile.sources.map((source) => `- **${source.id}** [${source.title}](${source.url}) — ${source.version}、確認日 ${source.checkedAt}`).join("\n")}\n`;
}

/** @param {Profile} profile @returns {string} */
export function renderWorkflow(profile) {
  return `# ${profile.technology}の情報取得と更新\n\n1. sources.mdのURLをWeb取得ツールまたはブラウザで開く。公式host（${profile.officialHosts.join(", ")}）と対象版（${profile.version}）を照合する。\n2. HTMLの外枠だけ、404、アクセス拒否を本文取得成功と扱わない。取得した節と教材に使う主張を対応付ける。取得不能なら別の公式URLを調べ、未取得を記録する。\n3. 言語仕様・API・Getting started・release notesを突き合わせ、前提から各到達目標までの順序をprofile.curriculumで確認する。\n4. codeを実行し、観測した結果と期待だけの結果を区別する。実行できない環境では未実施と明記する。\n5. 更新では同じURLとrelease notesを再取得し、資料の移転・対象版差分・例の変更を確認する。確認できた資料だけcheckedAtを更新する。\n6. profile、lesson.json、deck、注目対象、期待出力を照合してcheck/build/実測をやり直す。最後にsync-skillでこの参照一覧を再生成する。\n\nこれは資料を取得・確認するための手順であり、生成だけで最新情報の確認が済むことを意味しない。\n`;
}
