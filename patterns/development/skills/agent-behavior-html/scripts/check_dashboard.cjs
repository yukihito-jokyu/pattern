"use strict";

// Run the shipped dashboard against a small DOM fake, without a browser or network.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, ".claude/skills/agent-behavior-html/assets/dashboard.html"), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];
const example = JSON.parse(fs.readFileSync(path.join(root, "examples/demo.json"), "utf8"));

class FakeNode {
  constructor(tag) { this.tag = tag; this.children = []; this.listeners = new Map(); this.style = {}; this.value = ""; this.disabled = false; this.text = ""; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(""); }
  append(...nodes) { for (const node of nodes) this.children.push(node instanceof FakeNode ? node : Object.assign(new FakeNode("text"), {text:String(node)})); }
  replaceChildren(...nodes) { this.text = ""; this.children = []; this.append(...nodes); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  click() { if (!this.disabled) this.listeners.get("click")?.(); }
  dispatch(name) { this.listeners.get(name)?.(); }
  set innerHTML(value) { throw new Error("OPS-04 unsafe HTML sink"); }
}

function boot(data) {
  const nodes = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new FakeNode("div")]));
  nodes.get("report-data").textContent = JSON.stringify(data);
  nodes.get("timezone").value = "Asia/Tokyo";
  let download;
  const document = {getElementById:id => {assert(nodes.has(id), "unknown DOM element " + id); return nodes.get(id);}, createElement:tag => new FakeNode(tag)};
  const context = {document, Node:FakeNode, Blob, Intl, URL:{createObjectURL:blob => {download=blob;return "blob:fixture";},revokeObjectURL:() => {}},setTimeout:callback => callback()};
  vm.runInNewContext(script, context, {timeout:3000});
  return {get:id => nodes.get(id), select:(id,value) => {nodes.get(id).value=value;nodes.get(id).dispatch("input");},download:() => download};
}

async function main() {
  const ui = boot(example);
  assert.equal(ui.get("calls").textContent, "12", "initial call count");
  assert.equal(ui.get("errors").textContent, "2", "initial errors");
  assert.equal(ui.get("repeats").textContent, "2", "repeated inputs");
  assert.equal(ui.get("call-rows").children.length, 12, "call rows");
  assert.equal(ui.get("action-list").children.length, 12, "operation cards");
  assert(ui.get("action-list").textContent.includes("認証を通る原因"), "declared purpose visible");
  assert(ui.get("action-list").textContent.includes("期待した結果"), "expected result visible");
  assert(ui.get("action-list").textContent.includes("未記録"), "missing purposes explicit");
  assert(ui.get("action-list").textContent.includes("12 tests passed"), "observed result visible");
  ui.select("source", "claude");
  assert.equal(ui.get("calls").textContent, "6", "source filter");
  ui.select("tool", "Bash");
  assert.equal(ui.get("calls").textContent, "3", "tool filter");
  ui.select("status", "error");
  assert.equal(ui.get("calls").textContent, "1", "status filter");
  ui.get("call-rows").children[0].children[8].children[0].click();
  assert(ui.get("evidence-details").open, "evidence panel opens");
  assert(ui.get("evidence").textContent.includes("check-1"), "evidence is linked to the call");
  ui.get("export").click();
  const exported = JSON.parse(await ui.download().text());
  assert.equal(exported.calls.length, 1, "export follows filters");
  assert.equal(exported.events.length, 2, "export contains evidence");
  ui.select("status", "");
  ui.select("search", "check-2");
  assert.equal(ui.get("calls").textContent, "1", "call ID search");
  ui.select("session", JSON.stringify(["codex","demo-codex"]));
  assert.equal(ui.get("calls").textContent, "0", "cross-source session filter");
  assert(ui.get("call-rows").textContent.includes("ありません"), "empty state");
  ui.select("session", "");ui.select("source", "");ui.select("tool", "");ui.select("search", "");
  ui.select("source", "claude");ui.select("search", "認証を通る原因");
  assert.equal(ui.get("calls").textContent, "1", "purpose search");
  ui.get("call-rows").children[0].children[8].children[0].click();
  assert(ui.get("evidence").textContent.includes("ActionIntent"), "purpose evidence visible");
  ui.get("export").click();
  const purposeExport = JSON.parse(await ui.download().text());
  assert.equal(purposeExport.events.length, 3, "purpose event retained in export");
  ui.select("search", "src/auth.ts");
  assert.equal(ui.get("calls").textContent, "2", "target search");
  ui.select("search", "12 tests passed");
  assert.equal(ui.get("calls").textContent, "1", "result search");
  ui.select("source", "");ui.select("search", "");
  ui.select("timezone", "UTC");
  assert(ui.get("call-rows").children[0].children[0].textContent.includes("00:00"), "UTC display");
  assert(ui.get("quality").textContent.includes("終了記録なし2 件"), "quality remains global");
  const large = structuredClone(example);
  large.calls = Array.from({length:250}, (_,i) => ({...example.calls[0],tool_use_id:"fixture-"+i}));
  const paged = boot(large);
  assert.equal(paged.get("call-rows").children.length, 100, "page size");
  paged.get("next").click();
  assert(paged.get("page-label").textContent.startsWith("2 / 3"), "next page");
  paged.get("next").click();
  assert.equal(paged.get("call-rows").children.length, 50, "last page size");
  assert(paged.get("next").disabled, "last page disables next");
  paged.get("previous").click();
  assert(paged.get("page-label").textContent.startsWith("2 / 3"), "previous page");
  console.log("dashboard: actions, purposes, results, search, evidence, export and pagination OK (DOM fake)");
}

main().catch(error => {console.error(error);process.exitCode=1;});
