// Mapping NVRAM offset <-> parameter: select each parameter and turn the knob.
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
const idle=c=>c.wi>=c.wave.length && c.ki>=c.kn.length;
function stimulate(c,f,x){ f(); let i=0; while(!idle(c)&&i<2000000){c.step();i++;}
  for(let i=0;i<(x||1500000);i++) c.step(); }
const hx=v=>v.toString(16).padStart(2,'0');
const T=(c,k)=>stimulate(c,()=>{c.tog^=1;c.key(k,c.tog);});
const R=(c,n)=>stimulate(c,()=>c.rad(0,n));
// Reference: only select, without turning
function base(sel){ const c=boot(); T(c,sel); return {c,nv:Uint8Array.from(c.nv)}; }
const ADR={0x08:[1,0x50],0x18:[4,0x58],0x20:[5,0x5A],0x1a:[11,0x66]};
console.log('key    param  RAM   NVRAM bytes that change while turning');
for(const [k,[idx,ram]] of Object.entries(ADR)){
  const sel=Number(k);
  const a=base(sel); R(a.c,15);
  const diff=[];
  for(let i=0;i<32;i++) if(a.c.nv[i]!==a.nv[i]) diff.push(hx(i)+'h');
  console.log('  '+hx(sel)+'    '+String(idx).padStart(2)+'    '+hx(ram)+'h   '+
    (diff.join(' ')||'-')+'      expected at RAM-4Bh: '+hx(ram-0x4b)+'h');
}
