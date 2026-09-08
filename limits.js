// Y carries the entered parameter as BCD (PARAM_LOAD 080Bh).
// Find the switch-over point of 11CCh per waveform by bisection.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE =new Uint8Array(fs.readFileSync(P+'D310_image.bin'));
let B=null;
function boot(){
  if(!B){ const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
    for(let i=0;i<11000000;i++) c.step();
    B={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),
       xram:Uint8Array.from(c.xram),nv:Uint8Array.from(c.nv)}; }
  const c=new CPU(ROM); c.ram.set(B.ram); c.sfr.set(B.sfr);
  c.xram.set(B.xram); c.nv.set(B.nv); return c;
}
function bcd(c,value){                      // 8 BCD digits into Y (15h..19h)
  const z=String(value).padStart(10,'0');
  for(let i=0;i<5;i++) c.ram[0x15+i]=Number(z[2*i])*16+Number(z[2*i+1]);
}
function check(wf,decade,value){
  const c=boot();
  c.ram[0x24]=(c.ram[0x24]&0xF0)|wf;
  c.ram[0x50]=(decade<<4)|(c.ram[0x50]&0x0F);
  c.ram[0x23]&=~0x40;                       // 23h.6 off: otherwise another branch
  bcd(c,value);
  c.push(0xFF); c.push(0xFF); c.pc=0x11CC;
  let n=0; while(c.pc!==0xFFFF && n<200000){ c.step(); n++; }
  return (c.sfr[0xD0]>>7)&1;                // carry
}
function switchover(wf,dec){
  let lo=0, hi=99999;
  if(check(wf,dec,lo)===check(wf,dec,hi)) return null;
  while(hi-lo>1){ const m=(lo+hi)>>1; (check(wf,dec,m)===check(wf,dec,lo)?lo=m:hi=m); }
  return hi;
}
const NAMES={1:'sine',2:'triangle',3:'square',4:'pos.pulse',5:'neg.pulse',
             6:'pos.saw',7:'neg.saw',8:'haversine',9:'sine pulse',
             10:'triangle pulse',11:'arbitrary'};
console.log('waveform        decade<7   decade>=7');
for(let wf=1;wf<=11;wf++){
  const a=switchover(wf,5), b=switchover(wf,7);
  console.log('%s %s %s', (NAMES[wf]||('WF'+wf)).padEnd(15),
    String(a===null?'-':a).padStart(8), String(b===null?'-':b).padStart(11));
}
