import { createSave, createIndicator, createDisclosure, resolveMotion } from "./runtime.mjs";
const profiles = await fetch("/.claude/skills/pleasant-ui-motion/assets/profiles.json").then((r) => r.json());
const $ = (id) => document.getElementById(id);
const query = matchMedia("(prefers-reduced-motion: reduce)");
let celebration;
let celebrated = false;
let enabled = true;
const profile = () => profiles.systems[$("system").value];
function timing(token) {
  const p = profile();
  const key = p.recipeTokens[token];
  return { duration:parseFloat(p.tokens[key].value), easing:p.easing.value };
}
const indicator = createIndicator($("indicator"), () => timing("selection"), () => enabled);
function updatePreference() {
  const p = profile();
  const cobalt = p.preference === "inherit-on-off";
  $("parent").disabled = !cobalt;
  $("local").disabled = !cobalt;
  const effective = resolveMotion(cobalt ? $("parent").value : "on", cobalt ? $("local").value : "inherit", query.matches);
  enabled = effective === "on";
  document.documentElement.dataset.motion = effective;
  document.documentElement.style.setProperty("--press", p.tokens[p.recipeTokens.press].value);
  document.documentElement.style.setProperty("--disclosure-duration",p.tokens[p.recipeTokens.disclosure].value);
  document.documentElement.style.setProperty("--ease",p.easing.value);
  if (!enabled) { indicator.stop(); celebration?.cancel(); }
  $("effective").textContent = `現在: ${effective.toUpperCase()}${query.matches ? "（OSの低減設定）" : ""}`;
}
query.addEventListener("change",updatePreference);
for (const id of ["parent","local","system"]) $(id).addEventListener("change",updatePreference);
updatePreference();
const labels = {pending:"保存中",success:"保存しました",error:"保存できませんでした。再試行できます"};
const save = createSave(async () => {
  const result = $("result").value;
  await new Promise((resolve) => setTimeout(resolve,450));
  if (result === "error") throw new Error("simulated failure");
},(state) => {
  $("save-status").textContent = labels[state];
  $("save-status").dataset.state = state;
  $("save").disabled = state === "pending";
  $("save").setAttribute("aria-busy",String(state === "pending"));
  $("success-mark").hidden = state !== "success";
  if (state === "success" && enabled && $("delight").checked && !celebrated && $("success-mark").animate) {
    celebrated = true;
    celebration = $("success-mark").animate([{scale:".9"},{scale:"1.08",offset:.65},{scale:"1"}],timing("notify"));
    void celebration.finished.catch(() => {});
  }
});
$("save").addEventListener("click",save);
for (const button of document.querySelectorAll("[data-choice]")) button.addEventListener("click",() => {
  for (const candidate of document.querySelectorAll("[data-choice]")) candidate.setAttribute("aria-pressed",String(candidate === button));
  indicator.move(Number(button.dataset.choice) * button.getBoundingClientRect().width);
});
const disclosure = createDisclosure($("panel"),$("open"),{open:"補足を開く",close:"補足を閉じる"});
$("open").addEventListener("click",disclosure.toggle);
$("close").addEventListener("click",disclosure.close);
$("panel").addEventListener("keydown",(event) => { if (event.key === "Escape") disclosure.close(); });
let nextActions = 0;
$("next-action").addEventListener("click",() => { $("next-status").textContent = `次の操作を受け付けました（${++nextActions}回）`; });
