// Checks the polyphonic player built by mkpoly.py.
//
// The emulator models no waveform RAM, so the loader cannot be tested by
// listening. What can be tested — and is enough — is that it puts the
// same telegram sequence on the C-bus as the firmware's own waveform
// load, and that the 1024 points arriving there are the ones mkchord.py
// intended. If both hold, the loader is right by construction.
//
//   node polytest.js [image.bin]
const fs = require('fs'), P = __dirname + '/';
eval(fs.readFileSync(P + 'core.js', 'utf8'));

const img  = process.argv[2] || P + 'M27512_PM5139_V20_poly.bin';
const ROM  = new Uint8Array(fs.readFileSync(img));
const NV   = new Uint8Array(fs.readFileSync(P + 'PCF8570_image.bin'));
const D310 = new Uint8Array(fs.readFileSync(P + 'D310_image_V20.bin'));

// The player sits two bytes behind the checksum, whose end address the
// reset code loads with MOV 10h,#hi / MOV 11h,#lo.
let end = -1;
for (let i = 0; i + 5 < ROM.length; i++)
  if (ROM[i] === 0x75 && ROM[i+1] === 0x10 && ROM[i+3] === 0x75 && ROM[i+4] === 0x11) {
    const v = (ROM[i+2] << 8) | ROM[i+5];
    if (v >= 0x8000 && v < 0x10000) end = v;      // the last plausible hit wins
  }
if (end < 0) throw new Error('checksum end address not found');
const entry = end + 2;
console.log('checksum ends at ' + end.toString(16).toUpperCase() + 'h, player entry ' +
            entry.toString(16).toUpperCase() + 'h');

const c = new CPU(ROM); c.nv.set(NV); c.xram.set(D310); c.pc = 0;
for (let i = 0; i < 11000000; i++) c.step();
console.log('cold start done');

c.push(0xFF); c.push(0xFF); c.pc = entry;
c.wcount = 0;                      // only count what the player itself loads
let settle = 0;

// Record every telegram: the bytes written to SBUF, closed by a strobe.
const tele = [];
let buf = [], startM = 0;
const M0 = c.mcyc;
for (let i = 0; i < 40000000 && c.pc !== 0xFFFF; i++) {
  const op = ROM[c.pc], b1 = ROM[c.pc + 1];
  let v = null;
  if (op === 0xF5 && b1 === 0x99) v = c.sfr[0xE0];
  else if (op === 0x85 && ROM[c.pc + 2] === 0x99) v = c.ram[b1];
  else if (op === 0x75 && b1 === 0x99) v = ROM[c.pc + 2];
  else if (op >= 0x88 && op <= 0x8F && b1 === 0x99) v = c.gR(op - 0x88);
  if (v !== null) { if (!buf.length) startM = c.mcyc; buf.push(v); }
  if (op === 0xF0) {
    const dph = c.sfr[0x83];
    if (dph >= 0x81 && dph <= 0x8F) {
      tele.push({ str: dph & 15, bytes: buf, cyc: c.mcyc - startM });
      buf = [];
    }
  }
  c.step();
  // Stop once a full table has gone into the waveform RAM, but run on a
  // little so the strobe that terminates the stream is still recorded.
  // That is exact and does not depend on how many streams a build emits.
  if (c.wcount >= 1024 && ++settle > 30000) break;
}

const hx = a => a.map(x => x.toString(16).padStart(2, '0').toUpperCase()).join(' ');
console.log('\ntelegrams emitted by the loader:');
for (const t of tele)
  console.log('  STR' + t.str + String(t.bytes.length).padStart(6) + ' byte(s) ' +
              String(t.cyc).padStart(7) + ' machine cycles  ' +
              (t.bytes.length > 12 ? hx(t.bytes.slice(0, 8)) + ' ...' : hx(t.bytes)));

const bigs = tele.filter(t => t.bytes.length > 1000);
if (!bigs.length) { console.log('\nNO waveform stream was emitted'); process.exit(1); }
console.log('\n%d waveform streams: %s',
            bigs.length,
            bigs.length > 1 ? 'the first is the firmware\'s own table for the selected '
                            + 'waveform, the last is ours' : 'ours');
const big = bigs[bigs.length - 1];

// The stream ends with the two bytes of the STR1 word, the rest is points.
const data = big.bytes.slice(0, 2048);
console.log('\nwaveform stream: ' + data.length + ' data bytes + ' +
            (big.bytes.length - 2048) + ' trailing (the STR1 word)');
console.log('  load took ' + big.cyc + ' machine cycles = ' +
            (big.cyc / 1000).toFixed(1) + ' ms at 12 MHz');

// Only 00h/44h/88h/CCh may appear as a low byte: the format carries ten
// bits per point, two of them duplicated across both nibbles.
const lows = new Set(), vals = [];
for (let i = 0; i < 2048; i += 2) { lows.add(data[i+1]); vals.push((data[i] << 2) | (data[i+1] >> 6)); }
console.log('  distinct low bytes: ' + [...lows].sort((a,b)=>a-b).map(x=>hx([x])).join(' '));
console.log('  points: ' + vals.length + ', range ' + Math.min(...vals) + '..' +
            Math.max(...vals) + ', ' + new Set(vals).size + ' distinct values');

let rev = 0, last = 0;
for (let i = 1; i < vals.length; i++) { const d = vals[i]-vals[i-1];
  if (!d) continue; if (last && (d>0)!==(last>0)) rev++; last = d; }
console.log('  direction changes: ' + rev);
console.log('\nfirst 16 points: ' + vals.slice(0, 16).join(' '));
fs.writeFileSync(P + 'poly_stream.txt', vals.join('\n') + '\n');
console.log('points written to poly_stream.txt for comparison with mkchord.py');

// --- what the analogue front end would actually be doing ---------------
// The emulator now models the waveform RAM (STR2 plus the DBK clock on
// P3.5) and the strobes whose meaning has been measured, so this can be
// checked here instead of on a scope. STR3, STR4 and STR5 are counted but
// not interpreted.
console.log('\nanalogue front end after the load:');
console.log('  ' + c.afeState());
const wr = Array.from(c.wram);
let wrev = 0, wlast = 0;
for (let i = 1; i < wr.length; i++) { const d = wr[i] - wr[i-1];
  if (!d) continue; if (wlast && (d > 0) !== (wlast > 0)) wrev++; wlast = d; }
console.log('  waveform RAM: %d..%d, mean %s, %d direction changes',
            Math.min(...wr), Math.max(...wr),
            (wr.reduce((a, b) => a + b, 0) / wr.length).toFixed(1), wrev);
fs.writeFileSync(P + 'poly_wram.txt', wr.join('\n') + '\n');
console.log('  contents written to poly_wram.txt — compare with mkchord.py');
console.log('  strobes seen: %s', JSON.stringify(c.afe.seen));

// --- and now the melody: every call of OUT_FREQ, decoded ---------------
const FREQ = end > 0xB000 ? 0x0A28 : 0x09BF;   // OUT_FREQ, V1.5/V2.0 or V1.3
const NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
function name(hz){ const n = Math.round(12 * Math.log2(hz / 440) + 69);
  return NAMES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 1); }
console.log('\nthe melody, as the player sets it (f0 = the table frequency):');
let seen = 0, prev = c.mcyc;
for (let i = 0; i < 30000000 && seen < 10; i++) {
  if (c.pc === FREQ) {
    const d = c.ram[0x50] >> 4;
    const m = ((c.ram[0x50] & 15) * 10000) + (c.ram[0x51] >> 4) * 1000 +
              (c.ram[0x51] & 15) * 100 + (c.ram[0x52] >> 4) * 10 + (c.ram[0x52] & 15);
    const f0 = m * Math.pow(10, d - 5);
    seen++;
    console.log('  note ' + String(seen).padStart(2) + '   f0 = ' +
                f0.toFixed(2).padStart(7) + ' Hz   chord 2:3:4 = ' +
                (2*f0).toFixed(1) + ' / ' + (3*f0).toFixed(1) + ' / ' + (4*f0).toFixed(1) +
                ' Hz   root ' + name(2*f0) +
                '   +' + ((c.mcyc - prev) / 1000).toFixed(0) + ' ms');
    prev = c.mcyc;
  }
  c.step();
}
