import {catalog, cliOptions, main, requireValid} from './lib/project.mjs';

export async function checkDir(root) {
  return requireValid(await catalog(root));
}

main(import.meta.url, async () => {
  const {ids} = await checkDir(cliOptions().root);
  console.log(`配置確認: ${ids.length}パターン。違反なし。`);
});
