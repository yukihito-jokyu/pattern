import { mkdtempSync, readFileSync, writeFileSync, existsSync, rmSync } from "node:fs";
import { resolve, join } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { auditTarget } from "../.claude/skills/pleasant-ui-motion/scripts/motion.mjs";
const target = resolve(process.argv[2] ?? ".");
const compiler = join(target,"node_modules/typescript/bin/tsc");
if (!existsSync(compiler)) { console.error("対象の一時コピーでnpm ciを先に実行してください"); process.exit(1); }
const work = mkdtempSync(join(tmpdir(),"pleasant-motion-api-"));
try {
  const sample = readFileSync(".claude/skills/pleasant-ui-motion/references/save-example.tsx","utf8");
  writeFileSync(join(work,"save-example.tsx"),sample);
  for (const system of ["new-york","cobalt"]) {
    console.log(auditTarget(target,system));
    const config = {compilerOptions:{target:"ES2022",module:"ESNext",moduleResolution:"Bundler",jsx:"react-jsx",strict:true,noEmit:true,skipLibCheck:true,esModuleInterop:true,lib:["ES2022","DOM"],types:[],paths:{"@/components/ui/button":[join(target,`registry/${system}/ui/button/button.tsx`)],"@/registry/*":[join(target,"registry/*")],"react":[join(target,"node_modules/@types/react/index.d.ts")],"react/jsx-runtime":[join(target,"node_modules/@types/react/jsx-runtime.d.ts")]}},files:[join(work,"save-example.tsx")]};
    const path = join(work,system + ".json");
    writeFileSync(path,JSON.stringify(config,null,2));
    const result=spawnSync(process.execPath,[compiler,"-p",path],{stdio:"inherit"});
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`${system}: 使用例の型検査失敗`);
    console.log(`${system}: SaveExample API typecheck passed (installed application runtime unverified)`);
  }
} catch(error) { console.error(error.message); process.exitCode=1; }
finally { rmSync(work,{recursive:true,force:true}); }
