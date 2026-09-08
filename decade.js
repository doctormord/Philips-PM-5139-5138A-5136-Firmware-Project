// The real operating path: select a parameter, then step the decade up
// with key 0Bh until the firmware stops advancing.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE =new Uint8Array(fs.readFileSync(P+'D310_image.bin'));
const ADR={1:0x50,4:0x58,5:0x5A,11:0x66};
let B=null;
function boot(){
  if(!B){ const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
    for(let i=0;i<11000000;i++) c.step();
    B={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),
       xram:Uint8Array.from(c.xram),nv:Uint8Array.from(c.nv)}; }
  const c=new CPU(ROM); c.ram.set(B.ram); c.sfr.set(B.sfr);
  c.xram.set(B.xram); c.nv.set(B.nv); c.pc=0x0006; c.tog=0; return c;
}
const idle=c=>c.wi>=c.wave.length && c.ki>=c.kn.length;
function press(c,code){
  c.tog^=1; c.key(code,c.tog);
  let i=0; while(!idle(c)&&i<2000000){ c.step(); i++; }
  for(let i=0;i<500000;i++) c.step();
}
const hx=v=>v.toString(16).padStart(2,'0');
for(const [name,sel] of [['FREQUENCY',0x08],['DCOFFSET',0x18],['MODFREQ',0x20],['DUTYCYCLE',0x1a]]){
  const c=boot(); press(c,sel);
  const idx=c.ram[0x24]&0x0F, a=ADR[idx];
  if(!a){ console.log(name+': parameter index '+idx+' is not in the address list'); continue; }
  let seq=[];
  for(let k=0;k<9;k++){
    seq.push((c.ram[a]>>4)+"|"+(c.ram[a]&0x0F)+hx(c.ram[a+1])+hx(c.ram[a+2]));
    press(c,0x0B);
  }
  console.log('%s (index %d, RAM %sh)\n   decade|mantissa after one press on 0Bh each:\n   %s',
    name.padEnd(10), idx, a.toString(16), seq.join('  ->  '));
}
