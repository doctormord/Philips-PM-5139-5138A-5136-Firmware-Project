// When does the frequency limit check 11CCh run in normal operation?
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
  c.xram.set(B.xram); c.nv.set(B.nv); c.pc=0x0006; c.tog=0; return c;
}
function count(name, steps){
  const c=boot(); let n11CC=0, n1216=0, n1228=0;
  const idle=()=>c.wi>=c.wave.length && c.ki>=c.kn.length;
  const tick=k=>{ for(let i=0;i<k;i++){
      if(c.pc===0x11CC)n11CC++; if(c.pc===0x1216)n1216++; if(c.pc===0x1228)n1228++;
      c.step(); } };
  for(const s of steps){
    if(s[0]==='key'){ c.tog^=1; c.key(s[1],c.tog); } else c.rad(s[1],s[2]);
    let i=0; while(!idle()&&i<2500000){ tick(1); i++; }
    tick(400000);
  }
  const f=[0x50,0x51,0x52].map(a=>c.ram[a].toString(16).padStart(2,'0')).join(' ');
  console.log(`${name.padEnd(34)} 11CCh:${String(n11CC).padStart(4)}  table 1216h:${String(n1216).padStart(4)}  correction 1228h:${String(n1228).padStart(3)}   50h-52h=${f}`);
}
count('cold start only', []);
count('rotary knob +1 detent', [['rad',0,1]]);
count('rotary knob +20 detents', [['rad',0,20]]);
count('waveform key 11h', [['key',0x11]]);
count('waveform 11h, then turn', [['key',0x11],['rad',0,20]]);
count('MODE 29h, then turn', [['key',0x29],['rad',0,20]]);
count('key 19h, then turn', [['key',0x19],['rad',0,20]]);
