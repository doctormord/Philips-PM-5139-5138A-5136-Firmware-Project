// A dynamic execution trace: which ROM addresses really run?
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const D310=new Uint8Array(fs.readFileSync(P+'D310_image.bin'));

const visited=new Uint8Array(65536);
const c=new CPU(ROM);
if(c.nv) c.nv.set(NV);
c.xram.set(D310);
c.pc=0;

function run(n){ for(let i=0;i<n;i++){ visited[c.pc]=1; c.step(); } }
function idle(){ return c.wi>=c.wave.length && c.ki>=c.kn.length; }
function settle(){ let i=0; while(!idle()&&i<4000000){visited[c.pc]=1;c.step();i++;} run(400000); }

process.stderr.write('cold start (self-test) ...\n');
run(10000000);
let tog=0;
function press(k){ c.key(k,tog^=1); settle(); }

// all the front panel keys, several times over
const KEYS=[0x2A,0x08,0x09,0x10,0x11,0x0A,0x0B,0x18,0x19,
            0x20,0x21,0x28,0x29,0x1A,0x1B,0x2B,
            0x02,0x03,0x04,0x13,0x22,0x23,0x0C];
for(let round=0;round<3;round++){
  process.stderr.write('round '+(round+1)+' ...\n');
  for(const k of KEYS){ press(k); }
  // turn in between, both directions, with and without acceleration
  for(const [d,n] of [[0,1],[1,1],[0,5],[1,5],[0,20],[1,20]]){ c.rad(d,n); settle(); }
}
// operating modes on purpose: step MODE through and turn while doing it
for(let i=0;i<10;i++){ press(0x29); c.rad(0,3); settle(); c.rad(1,3); settle(); press(0x21); }
// step through the waveforms
for(let i=0;i<14;i++){ press(0x11); c.rad(0,2); settle(); }
run(4000000);

const n=visited.reduce((a,b)=>a+b,0);
process.stderr.write(`addresses executed: ${n}, cycles: ${c.cycles}\n`);
fs.writeFileSync(P+'visited.bin', Buffer.from(visited));   // one byte per ROM address
console.log('done: '+n+' addresses, '+c.cycles+' cycles');
