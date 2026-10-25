import { createServer } from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { extname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".woff2", "font/woff2"],
]);

/** @param {string} root @param {string} target @returns {boolean} */
function isInside(root, target) {
  const path = relative(root, target);
  return path === "" || (!path.startsWith(".." + sep) && path !== ".." && !isAbsolute(path));
}

/**
 * @param {string} root
 * @param {string} requestPath
 * @returns {Promise<string>}
 */
async function requestedFile(root, requestPath) {
  const decoded = decodeURIComponent(requestPath.split("?")[0] ?? "/");
  if (decoded.includes("\0") || decoded.includes("\\") || decoded.split("/").includes("..")) {
    throw new Error("OPS-02: invalid path");
  }
  const target = resolve(root, "." + decoded);
  if (!isInside(root, target)) {
    throw new Error("OPS-02: path outside site");
  }
  const info = await stat(target);
  const file = await realpath(info.isDirectory() ? join(target, "index.html") : target);
  if (!isInside(root, file)) {
    throw new Error("OPS-02: symlink outside site");
  }
  return file;
}

/**
 * @param {string} directory
 * @param {number} port
 * @returns {Promise<import("node:http").Server>}
 */
export async function startServer(directory, port) {
  const root = await realpath(directory);
  const server = createServer((request, response) => {
    if (request.method !== "GET" && request.method !== "HEAD") {
      response.writeHead(405, { Allow: "GET, HEAD" });
      response.end("Method not allowed");
      return;
    }
    requestedFile(root, request.url ?? "/")
      .then(async (file) => {
        const data = await readFile(file);
        response.writeHead(200, {
          "Content-Type": contentTypes.get(extname(file)) ?? "application/octet-stream",
          "X-Content-Type-Options": "nosniff",
          "Cache-Control": "no-store",
        });
        response.end(request.method === "HEAD" ? undefined : data);
      })
      .catch((error) => {
        const isBoundary = error instanceof Error && error.message.startsWith("OPS-02:");
        response.writeHead(isBoundary ? 403 : 404, { "Content-Type": "text/plain; charset=utf-8" });
        response.end(isBoundary ? "Forbidden" : "Not found");
      });
  });
  await new Promise((accept, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      server.off("error", reject);
      accept(undefined);
    });
  });
  return server;
}

if (
  process.argv[1] &&
  (await realpath(process.argv[1])) === (await realpath(fileURLToPath(import.meta.url)))
) {
  try {
    const directory = process.argv[2];
    const port = Number(process.argv[3] ?? 4187);
    if (!directory || !Number.isInteger(port) || port < 0 || port > 65535) {
      throw new Error("Usage: node tools/serve.mjs <site-dir> [port]");
    }
    const server = await startServer(directory, port);
    const address = server.address();
    if (address && typeof address === "object") {
      console.log("http://127.0.0.1:" + address.port + "/");
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
