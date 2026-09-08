// Which key code triggers which handler of the jump table 0301h?
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
const HANDLER={0x0502:1,0x0504:2,0x0553:3,0x059F:4,0x05AC:5,0x06BA:7,0x0663:8,
               0x05F7:9,0x0626:10,0x0748:11,0x06C0:12,0x06FE:13,0x04E7:14,0x031F:15};
const hits={};
for(let code=0;code<256;code++){
  const c=boot(); c.tog^=1; c.key(code,c.tog);
  const idle=()=>c.wi>=c.wave.length && c.ki>=c.kn.length;
  let i=0, h=new Set(), n11CC=0;
  while((!idle()||i<300000) && i<1200000){
    if(c.pc in HANDLER) h.add(HANDLER[c.pc]);
    if(c.pc===0x11CC) n11CC++;
    c.step(); i++;
  }
  if(h.size||n11CC){
    const k=[...h].sort((a,b)=>a-b).join(',');
    (hits[k+(n11CC?'  +11CCh':'')] ||= []).push(code);
  }
}
console.log('handler (index in 0301h)   triggered by key code');
for(const [k,v] of Object.entries(hits))
  console.log('  %s %s', k.padEnd(24), v.map(x=>'0x'+x.toString(16)).join(' '));
