import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {project} from '../helpers/temporary-project.mjs';
const {searchDocuments} = createRequire(import.meta.url)('../../plugins/site-search/search-core.js');
const documents = [
  {title: 'パターンの追加', content: 'READMEとZIPを検証します。', permalink: '/docs/project/contributing'},
  {title: 'README', content: '他の文書です。', permalink: '/docs/project/other'},
];

test('日本語と英語の複数語を正規化して検索し、正しい移動先を返す', () => {
  assert.equal(searchDocuments(documents, '追加 ｒｅａｄｍｅ')[0].permalink, '/docs/project/contributing');
  assert.equal(searchDocuments(documents, 'ZIP')[0].title, 'パターンの追加');
  assert.match(searchDocuments(documents, 'README')[0].excerpt, /文書/);
});

test('空入力・該当なしは別文書を返さない', () => {
  assert.deepEqual(searchDocuments(documents, '  '), []);
  assert.deepEqual(searchDocuments(documents, '存在しない語'), []);
  assert.deepEqual(searchDocuments(documents, '追加 存在しない語'), []);
});

test('検索データ生成は公開文書とURLを対応付け、draft・unlistedを除外する', async t => {
  const root = await project(t);
  const plugin = createRequire(import.meta.url)('../../plugins/site-search/index.js')({siteDir: root});
  const doc = {title: 'Hello', source: '@site/docs/sample/basic/hello/index.md', permalink: '/preview/docs/sample/basic/hello'};
  let data;
  await plugin.allContentLoaded({
    allContent: {'docusaurus-plugin-content-docs': {default: {loadedVersions: [{docs: [doc, {...doc, draft: true}, {...doc, unlisted: true}]}]}}},
    actions: {setGlobalData(value) {data = value;}, async createData() {}},
  });
  assert.equal(data.documents.length, 1);
  assert.equal(searchDocuments(data.documents, 'Hello')[0].permalink, doc.permalink);
  assert.doesNotMatch(data.documents[0].content, /slug:|description:/);
});
