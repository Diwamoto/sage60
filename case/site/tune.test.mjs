// Self-check for the serial demux in tune.html:  node case/site/tune.test.mjs
import assert from 'node:assert';
import {readFileSync} from 'node:fs';
const src = readFileSync(new URL('./tune.html', import.meta.url), 'utf8').split('// demux:start')[1].split('// demux:end')[0];
const makeDemux = new Function(src + 'return makeDemux;')();
const frames = [], lines = [];
const feed = makeDemux(b => frames.push(...b), l => lines.push(l));
feed(Uint8Array.from([0xAD, ...Buffer.from('rot 1 2')]));          // stray EOF, line split across chunks
feed(Uint8Array.from([...Buffer.from(' 3 4 5\r\n'), 0xAB, 1, 0xAC]));
feed(Uint8Array.from([0xAD, 2, 0xAD, ...Buffer.from('err\n')]));   // escaped EOF stays inside the frame
assert.deepEqual(lines, ['rot 1 2 3 4 5', 'err']);
assert.deepEqual(frames, [0xAB, 1, 0xAC, 0xAD, 2, 0xAD]);
console.log('ok');
