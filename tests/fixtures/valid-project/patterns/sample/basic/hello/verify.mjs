import assert from 'node:assert/strict';
import {hello} from './hello.mjs';

assert.equal(hello('world'), 'Hello, world!');
console.log('Hello verification passed');
