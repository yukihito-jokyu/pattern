import { readFileSync, writeFileSync, readdirSync, mkdirSync, existsSync, lstatSync, realpathSync } from "node:fs";
import { resolve, dirname, basename, join } from "node:path";
import { fileURLToPath } from "node:url";

const skillRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const profiles = JSON.parse(readFileSync(join(skillRoot, "assets/profiles.json"), "utf8"));
export const recipes = JSON.parse(readFileSync(join(skillRoot, "assets/recipes.json"), "utf8"));
export const canonical = (value) => JSON.stringify(value, null, 2) + "\n";
const slug = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const fail = (id, message) => { throw new Error(`${id} ${message}`); };

function object(value, id, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(id, `${label}: オブジェクトが必要です`);
}

export function validate(spec) {
  object(spec, "ERR-01", "motion");
  const keys = ["id", "system", "recipe", "intent", "frequency", "delight", "labels"];
  if (Object.keys(spec).some((key) => !keys.includes(key)) || keys.some((key) => !(key in spec)))
    fail("ERR-01", "motion: 未定義キーまたは必須キーの欠落");
  if (typeof spec.id !== "string" || !slug.test(spec.id)) fail("NAM-01", "idは英字始まりのkebab-case");
  if (!Object.hasOwn(profiles.systems, spec.system)) fail("DEP-01", "systemはcobalt/new-yorkの一方");
  if (!Object.hasOwn(recipes, spec.recipe)) fail("CODE-01", "未定義のrecipe");
  if (typeof spec.intent !== "string" || !spec.intent.trim() || /[\r\n]/.test(spec.intent))
    fail("ERR-01", "intentは空でない1行の文字列");
  if (!["frequent", "infrequent"].includes(spec.frequency) || typeof spec.delight !== "boolean")
    fail("ERR-01", "frequency/delightの型または値が不正");
  if (spec.delight && (spec.frequency !== "infrequent" || !["save", "notify"].includes(spec.recipe)))
    fail("MOT-04", "delightは低頻度の確定済み成功だけに使う");
  object(spec.labels, "ERR-01", "labels");
  const labels = recipes[spec.recipe].labels;
  if (Object.keys(spec.labels).length !== labels.length || labels.some((key) =>
    typeof spec.labels[key] !== "string" || !spec.labels[key].trim() || /[\r\n]/.test(spec.labels[key])))
    fail("MOT-01", `labelsは${labels.join(", ")}の空でない1行文字列だけ`);
  if (new Set(Object.values(spec.labels)).size !== labels.length) fail("MOT-01", "異なる状態のラベルを区別する");
  return spec;
}

export function compile(spec) {
  validate(spec);
  const profile = profiles.systems[spec.system];
  const recipe = recipes[spec.recipe];
  const token = profile.tokens[profile.recipeTokens[spec.recipe]];
  return {
    id: spec.id, system: spec.system, recipe: spec.recipe,
    duration: token.name, easing: profile.easing.name,
    interruption: recipe.interruption, reduced: "instant-with-meaning",
    exit: spec.recipe === "disclosure" ? "animated-nonblocking" : "state-first",
    relation: recipe.relation, preference: profile.preference,
    delight: spec.delight, meaning: recipe.meaning,
  };
}

const md = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("|", "&#124;").replaceAll("`", "&#96;");

export function render(spec) {
  const plan = compile(spec);
  const profile = profiles.systems[spec.system];
  const markdown = `<!-- 生成物。motion.jsonから再生成する。 -->\n# ${spec.id}\n\n${md(spec.intent)}。${plan.meaning}を伝える。\n\n| 項目 | 決定 |\n|---|---|\n| システム | ${plan.system} |\n| 関係 | ${plan.relation} |\n| 時間 | \`var(${plan.duration})\` |\n| 曲線 | \`var(${plan.easing})\` |\n| 途中操作 | ${plan.interruption} |\n| 低減時 | ${plan.reduced} |\n| 閉鎖 | ${plan.exit} |\n| 遊び心 | ${plan.delight ? "確定済み成功時だけ" : "なし"} |\n\n状態は操作・処理結果で更新する。アニメーション完了を業務状態の条件にしない。\n\n| 状態 | 動きを止めても残すラベル |\n|---|---|\n${Object.entries(spec.labels).map(([k,v]) => `| ${k} | ${md(v)} |`).join("\n")}\n\n正本は取り込み先の\`${profile.stylePath}\`。このファイルは適用計画であり、UIへの導入・動作検証・人間の確認は未実施。\n`;
  const css = `/* 生成物。motion.jsonから再生成する。ホストの既存Tokenを参照する。 */\n[data-motion-contract="${spec.id}"] {\n  --pleasant-duration: var(${plan.duration});\n  --pleasant-easing: var(${plan.easing});\n}\n`;
  return { "motion.md": markdown, "motion.css": css };
}

export function units(root) {
  const folder = join(root, "motions");
  if (!existsSync(folder)) return [];
  return readdirSync(folder).sort().map((name) => {
    const dir = join(folder, name);
    if (!slug.test(name) || !lstatSync(dir).isDirectory() || lstatSync(dir).isSymbolicLink())
      fail("STR-01", `motions/${name}: 単位は通常ディレクトリ`);
    const names = readdirSync(dir).sort();
    if (names.some((file) => !["motion.json", "motion.css", "motion.md"].includes(file)) || !names.includes("motion.json"))
      fail("STR-01", `${dir}: motion.json/css/mdだけを置く`);
    if (names.some((file) => lstatSync(join(dir,file)).isSymbolicLink())) fail("STR-01", `${dir}: リンク禁止`);
    const spec = validate(JSON.parse(readFileSync(join(dir,"motion.json"), "utf8")));
    if (spec.id !== name) fail("NAM-01", `${dir}: idとディレクトリ名を一致させる`);
    return { dir, spec };
  });
}

export function check(root, { format = true, generated = true } = {}) {
  const items = units(root);
  if (!items.length) fail("STR-01", "motionsに1単位以上が必要");
  for (const { dir, spec } of items) {
    if (format && readFileSync(join(dir, "motion.json"), "utf8") !== canonical(spec)) fail("TOOL-01", `${dir}: fmtを実行する`);
    if (generated) for (const [name, content] of Object.entries(render(spec))) {
      if (!existsSync(join(dir,name)) || readFileSync(join(dir,name),"utf8") !== content)
        fail("CODE-02", `${dir}/${name}: buildで再生成する`);
    }
  }
  return items.length;
}

export function build(root) {
  for (const { dir, spec } of units(root)) for (const [name, content] of Object.entries(render(spec)))
    writeFileSync(join(dir,name), content);
}

export function scaffold(root, id, system, recipe) {
  if (!slug.test(id ?? "")) fail("NAM-01", "new ID SYSTEM RECIPE");
  if (!Object.hasOwn(recipes, recipe) || !Object.hasOwn(profiles.systems, system)) fail("ERR-01", "system/recipeを指定する");
  const dir = join(root, "motions", id);
  if (existsSync(dir)) fail("STR-01", `${id}は既に存在する`);
  const defaults = {idle:"実行する",pending:"処理中",success:"完了しました",error:"完了できませんでした",retry:"再試行",selected:"選択済み",open:"開く",close:"閉じる",changed:"順序を変更しました",previous:"前へ",next:"次へ",from:"一覧",to:"詳細"};
  const spec = { id, system, recipe, intent:`${id}の操作結果を伝える`, frequency:"frequent", delight:false, labels:Object.fromEntries(recipes[recipe].labels.map((key) => [key,defaults[key]])) };
  validate(spec);
  mkdirSync(dir, { recursive:true });
  writeFileSync(join(dir,"motion.json"), canonical(spec));
  for (const [name,content] of Object.entries(render(spec))) writeFileSync(join(dir,name),content);
}

export function auditTarget(root, system) {
  const profile = profiles.systems[system];
  if (!profile) fail("DEP-01", "audit SYSTEM TARGET_ROOT");
  const styles = JSON.parse(readFileSync(join(root,profile.stylePath),"utf8"));
  const item = styles.items?.find((item) => item.name === profile.item);
  if (!item) fail("DEP-01", "stylesの正本項目がない");
  const declarations = Object.values(item.css).filter((value) => value && typeof value === "object");
  for (const token of [...Object.values(profile.tokens), profile.easing]) {
    if (!declarations.some((value) => value[token.name] === token.value))
      fail("MOT-02", `${token.name}: 調査時点から変更されている。現行値と適用手順を再調査する`);
  }
  return { system, tokens:"match", runtime:"unverified", revision:profiles.revision };
}

function main(args) {
  const [command, ...rest] = args;
  const root = process.cwd();
  if (command === "new") scaffold(root,...rest);
  else if (command === "build") build(root);
  else if (command === "fmt") { for(const {dir,spec} of units(root)) writeFileSync(join(dir,"motion.json"),canonical(spec)); }
  else if (command === "fmt-file") {
    const path = resolve(rest[0] ?? "");
    const spec = validate(JSON.parse(readFileSync(path,"utf8")));
    if (basename(path) !== "motion.json") fail("STR-01", "motion.jsonだけを整形する");
    writeFileSync(path,canonical(spec));
  }
  else if (command === "check") console.log(`motion check: ${check(root)} units passed (host runtime unverified)`);
  else if (command === "audit") console.log(canonical(auditTarget(resolve(rest[1] ?? ""),rest[0])));
  else if (command === "list") console.log(canonical({ systems:Object.keys(profiles.systems), recipes:Object.keys(recipes) }));
  else fail("ERR-01", "使用: motion.mjs new ID SYSTEM RECIPE | fmt | build | check | audit SYSTEM TARGET_ROOT | list");
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) {
  try { main(process.argv.slice(2)); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
