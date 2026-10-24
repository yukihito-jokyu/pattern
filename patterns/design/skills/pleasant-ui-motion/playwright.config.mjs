import { defineConfig } from "@playwright/test";
import { createServer } from "node:net";
// 独立コピーの並列検証が同じポートを奪い合わないよう、OSに空きを選ばせる。
let port=Number(process.env.MOTION_TEST_PORT);
if (!port) {
  const listener=createServer();
  await new Promise((done) => listener.listen(0,"127.0.0.1",done));
  port=listener.address().port;
  await new Promise((done) => listener.close(done));
  process.env.MOTION_TEST_PORT=String(port);
}
const url=`http://127.0.0.1:${port}`;
export default defineConfig({
  testDir:"./tests/browser",fullyParallel:false,workers:1,
  use:{baseURL:url,browserName:"chromium",viewport:{width:1280,height:1000}},
  webServer:{command:"node tools/serve.mjs",url,env:{PORT:String(port)},reuseExistingServer:false},
});
