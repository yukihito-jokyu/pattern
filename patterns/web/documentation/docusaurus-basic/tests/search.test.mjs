import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const { searchDocuments } = createRequire(import.meta.url)('../plugins/site-search/search-core.js');
const docs = [{ title: '設定する', content: '日本語とNodeの設定を説明する。', permalink: '/preview/docs/config' }, { title: '記事を書く', content: '設定する手順とNODEを説明する。', permalink: '/preview/docs/writing' }];
test('日本語・全角英字・複数語を検索し、タイトル一致を優先する', () => { assert.equal(searchDocuments(docs, '設定 ＮＯＤＥ')[0].title, '設定する'); assert.equal(searchDocuments(docs, '日本語 記事').length, 0); });
test('空入力、該当なし、件数制限と抜粋設定を扱う', () => { assert.deepEqual(searchDocuments(docs, '  '), []); assert.deepEqual(searchDocuments(docs, '存在しない語'), []); assert.equal(searchDocuments(docs, '設定', { limit: 1 }).length, 1); assert.ok(searchDocuments(docs, '設定', { excerptLength: 5 })[0].excerpt.length <= 7); });
