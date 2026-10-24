import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, extname } from "node:path";
const root = process.cwd();
const types = {".html":"text/html; charset=utf-8",".css":"text/css",".mjs":"text/javascript",".json":"application/json"};
const server = createServer(async (request,response) => {
  const path = new URL(request.url,"http://localhost").pathname;
  const file = path === "/" ? "/examples/demo.html" : path;
  if (!/^\/examples\/[a-z-]+\.(html|css|mjs)$/.test(file) && file !== "/.claude/skills/pleasant-ui-motion/assets/profiles.json") {
    response.writeHead(404); response.end(); return;
  }
  try {
    response.writeHead(200,{"Content-Type":types[extname(file)],"Cache-Control":"no-store"});
    response.end(await readFile(resolve(root,"." + file)));
  } catch { response.writeHead(404); response.end(); }
});
server.listen(Number(process.env.PORT ?? 4178),"127.0.0.1",() => console.log("Reference: http://127.0.0.1:" + server.address().port));
