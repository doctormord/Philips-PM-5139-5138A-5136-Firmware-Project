// Which address range of the EEPROM does the firmware read at all?
// Important for the question whether an 8 KB device has to be mirrored.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE=new Uint8Array(fs.readFileSync(P+'D310_image.bin'));

const wasRead=new Set();
const orig=CPU.prototype.xr;
CPU.prototype.xr=function(d){ if(d<0x8000) wasRead.add(d); return orig.call(this,d); };

function fresh(){
  const c=new CPU(ROM); c.nv.set(NV);
  // mirrored four times, like an 8 KB device in a 32 KB socket:
  for(let i=0;i<4;i++) c.xram.set(EE, i*8192);
  return c;
}
// 1. cold start
let c=fresh(); c.pc=0; for(let i=0;i<11000000;i++) c.step();
const afterBoot=new Set(wasRead);
// 2. press all the keys
for(const k of [0x11,0x19,0x21,0x22,0x23,0x29,0x31,0x39,0x12,0x1A,0x2A,0x32]){
  c.tog^=1; c.key(k,c.tog);
  for(let i=0;i<800000;i++) c.step();
}
// 3. the EEPROM routines directly
for(const adr of [0x9615,0x991F,0x3DAB,0x4003,0x3EFC,0x4425,0x9E37]){
  const d=fresh(); d.pc=0; for(let i=0;i<11000000;i++) d.step();
  d.push(0xFF); d.push(0xFF); d.pc=adr;
  let n=0; while(d.pc!==0xFFFF && n<2000000){ d.step(); n++; }
}
const a=[...wasRead].sort((x,y)=>x-y);
console.log('EEPROM addresses read: %d different ones', a.length);
const h=x=>x.toString(16).toUpperCase().padStart(4,'0')+'h';
console.log('  lowest %s, highest %s', h(a[0]), h(a[a.length-1]));
console.log('  of those >= 2000h: %d', a.filter(x=>x>=0x2000).length);
console.log('  during the cold start alone: %d%s', afterBoot.size,
            afterBoot.size ? ' (highest '+h(Math.max(...afterBoot))+')' : '');
// contiguous ranges
let r=[], s=a[0], p=a[0];
for(const x of a.slice(1)){ if(x>p+64){ r.push([s,p]); s=x; } p=x; }
r.push([s,p]);
console.log('  ranges: ' + r.map(([v,b])=>h(v)+'-'+h(b)).join('  '));
