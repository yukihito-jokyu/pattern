export const namePattern = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;

export function assertPatternId(id) {
  if (typeof id !== 'string' || id.split('/').length !== 3 || !id.split('/').every(part => namePattern.test(part)) || id.split('/')[0] === 'project') throw new Error(`不正なパターンIDです: ${id}`);
  return id;
}

export function patternPaths(id) {
  assertPatternId(id);
  return {
    name: id.split('/')[2],
    document: `docs/${id}/index.md`,
    implementation: `patterns/${id}`,
    archive: `${id}.zip`,
    download: `/downloads/patterns/${id}.zip`,
  };
}
