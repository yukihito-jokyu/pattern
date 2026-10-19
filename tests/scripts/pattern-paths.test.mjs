import test from 'node:test';
import assert from 'node:assert/strict';
import {assertPatternId, patternPaths} from '../../scripts/lib/patterns.mjs';
import {readPatternCI} from '../../scripts/pattern-ci.mjs';
import {verifyPatterns} from '../../scripts/verify-patterns.mjs';

test('同じIDから文書・実装・ZIPのパスを生成する', () => {
  assert.equal(assertPatternId('sample/basic/hello-v2'), 'sample/basic/hello-v2');
  assert.deepEqual(patternPaths('sample/basic/hello-v2'), {
    name: 'hello-v2', document: 'docs/sample/basic/hello-v2/index.md', implementation: 'patterns/sample/basic/hello-v2', archive: 'sample/basic/hello-v2.zip', download: '/downloads/patterns/sample/basic/hello-v2.zip',
  });
});

test('全入口で同じ不正IDをファイルアクセス前に拒否する', async () => {
  for (const id of ['sample/basic/hello--world', 'sample/basic/hello-', 'sample/basic/-hello', 'sample/basic/1hello', 'Sample/basic/hello', 'sample/basic', 'sample/basic/hello/extra', '../basic/hello', 'project/basic/hello', 'sample\\basic\\hello', undefined]) {
    assert.throws(() => patternPaths(id), /不正なパターンID/);
    await assert.rejects(readPatternCI('/missing', id), /不正なパターンID/);
    await assert.rejects(verifyPatterns('/missing', {id, command: ['node']}), id ? /不正なパターンID/ : /検証対象を指定/);
  }
});
