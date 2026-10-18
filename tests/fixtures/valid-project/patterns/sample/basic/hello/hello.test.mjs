import test from 'node:test';
import assert from 'node:assert/strict';
import {hello} from './hello.mjs';

test('名前に対応する挨拶を返す', () => {
  assert.equal(hello('world'), 'Hello, world!');
});
