import { spawnSync } from "node:child_process";
for (const [command,args] of [["npm",["ci"]],["npx",["--no-install","playwright","install",...(process.platform === "linux" ? ["--with-deps"] : []),"chromium"]],["npm",["run","check"]]]) {
  const result = spawnSync(command,args,{stdio:"inherit"});
  if (result.error) { console.error(result.error.message); process.exit(1); }
  if (result.status !== 0) process.exit(result.status ?? 1);
}
