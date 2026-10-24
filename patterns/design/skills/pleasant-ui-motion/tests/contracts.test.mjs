import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, cpSync, symlinkSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { validate, compile, render, scaffold, check, auditTarget, profiles, recipes } from "../.claude/skills/pleasant-ui-motion/scripts/motion.mjs";
import { createSave, resolveMotion } from "../examples/runtime.mjs";
const sample = {id:"save-preferences",system:"cobalt",recipe:"save",intent:"設定を保存する",frequency:"frequent",delight:false,labels:{idle:"保存する",pending:"保存中",success:"保存しました",error:"保存できませんでした",retry:"再試行"}};
test("CLI: copied skill generates and checks through a directory alias",() => {
  const root = mkdtempSync(join(tmpdir(),"motion-portable-"));
  try {
    const real = join(root,"real");
    const alias = join(root,"alias");
    cpSync(new URL("../.claude/skills/pleasant-ui-motion/",import.meta.url),real,{recursive:true});
    symlinkSync(real,alias,process.platform === "win32" ? "junction" : "dir");
    const cli = join(alias,"scripts/motion.mjs");
    for (const args of [["new","portable-save","cobalt","save"],["check"]]) {
      const result = spawnSync(process.execPath,[cli,...args],{cwd:root,encoding:"utf8"});
      assert.equal(result.status,0,result.stderr);
    }
    assert.equal(existsSync(join(root,"motions/portable-save/motion.json")),true);
    assert.equal(check(root),1);
  } finally { rmSync(root,{recursive:true,force:true}); }
});
test("schema: bad types, unknown keys and misleading labels fail",() => {
  assert.throws(() => validate({...sample,duration:300}),/ERR-01/);
  assert.throws(() => validate({...sample,id:".."}),/NAM-01/);
  assert.throws(() => validate({...sample,system:"both"}),/DEP-01/);
  assert.throws(() => validate({...sample,recipe:"spin-everything"}),/CODE-01/);
  assert.throws(() => validate({...sample,delight:true}),/MOT-04/);
  assert.throws(() => validate({...sample,labels:{...sample.labels,pending:"保存しました"}}),/MOT-01/);
  assert.throws(() => validate({...sample,frequency:8}),/ERR-01/);
});
test("all recipes compile for both systems without fabricated tokens",() => {
  const root = mkdtempSync(join(tmpdir(),"motion-contracts-"));
  try {
    for (const system of Object.keys(profiles.systems)) for (const recipe of Object.keys(recipes)) scaffold(root,`${system}-${recipe}`,system,recipe);
    assert.equal(check(root),16);
    for (const system of Object.keys(profiles.systems)) {
      const result = compile({...sample,system});
      assert.ok(Object.values(profiles.systems[system].tokens).some((token) => token.name === result.duration));
      assert.equal(result.reduced,"instant-with-meaning");
    }
    assert.throws(() => scaffold(root,"../escape","cobalt","save"),/NAM-01/);
  } finally { rmSync(root,{recursive:true,force:true}); }
});
test("OPS-01: generated markdown escapes label markup and never claims host validation",() => {
  const result = render({...sample,intent:"<script>alert(1)</script>"});
  assert.ok(result["motion.md"].includes("&lt;script&gt;"));
  assert.ok(result["motion.md"].includes("未実施"));
  assert.equal(compile({...sample,recipe:"disclosure",labels:{open:"開く",close:"閉じる"}}).exit,"animated-nonblocking");
});
test("MOT-03: OS reduction wins over every parent and local preference",() => {
  for (const parent of ["on","off"]) for (const local of ["inherit","on","off"]) {
    assert.equal(resolveMotion(parent,local,true),"off");
    assert.equal(resolveMotion(parent,local,false),local === "inherit" ? parent : local);
  }
});
test("STATE-01: pending is immediate, duplicate submits blocked, actual result wins",async () => {
  let finish;
  let calls = 0;
  const states = [];
  const submit = createSave(() => {calls++; return new Promise((resolve) => {finish=resolve;});},(state) => states.push(state));
  const pending = submit();
  assert.deepEqual(states,["pending"]);
  await submit(); assert.equal(calls,1);
  finish(); await pending;
  assert.deepEqual(states,["pending","success"]);
  const failed = createSave(async () => {throw new Error("network");},(state) => states.push(state));
  await failed(); assert.equal(states.at(-1),"error");
});
test("target audit detects source drift and explicitly leaves runtime unverified",() => {
  const root = mkdtempSync(join(tmpdir(),"motion-target-"));
  try {
    const p = profiles.systems.cobalt;
    mkdirSync(join(root,"registry/cobalt/styles"),{recursive:true});
    const values = Object.fromEntries([...Object.values(p.tokens),p.easing].map((token) => [token.name,token.value]));
    const path = join(root,p.stylePath);
    writeFileSync(path,JSON.stringify({items:[{name:p.item,css:{":root":values}}]}));
    assert.equal(auditTarget(root,"cobalt").runtime,"unverified");
    values["--cobalt-duration-press"]="500ms";
    writeFileSync(path,JSON.stringify({items:[{name:p.item,css:{":root":values}}]}));
    assert.throws(() => auditTarget(root,"cobalt"),/MOT-02/);
  } finally { rmSync(root,{recursive:true,force:true}); }
});
