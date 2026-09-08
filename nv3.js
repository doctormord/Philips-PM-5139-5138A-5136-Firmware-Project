// Is the first 25-byte record a mirror of the RAM from 4Bh on?
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE =new Uint8Array(fs.readFileSync(P+'D310_image.bin'));
const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
for(let i=0;i<11000000;i++) c.step();
// after an adjustment, so that the record has just been written
c.tog^=1; c.key(0x08,c.tog);
let i=0; while((c.wi<c.wave.length||c.ki<c.kn.length)&&i<2000000){c.step();i++;}
for(let k=0;k<1500000;k++) c.step();
c.rad(0,3);
i=0; while((c.wi<c.wave.length||c.ki<c.kn.length)&&i<2000000){c.step();i++;}
for(let k=0;k<2000000;k++) c.step();
const hx=v=>v.toString(16).padStart(2,'0');
console.log('off  NVRAM  RAM   RAM addr  equal');
let hits=0;
for(let o=0;o<25;o++){
  const r=0x4B+o, eq=c.nv[o]===c.ram[r];
  if(eq) hits++;
  console.log('  '+hx(o)+'   '+hx(c.nv[o])+'     '+hx(c.ram[r])+'    '+hx(r)+'h      '+(eq?'yes':'-'));
}
console.log('\n%d of 25 bytes agree', hits);
