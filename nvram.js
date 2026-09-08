// Which NVRAM bytes change when a parameter is adjusted?
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
function stimulate(c,f,extra){ f(); let i=0; while(!idle(c)&&i<2000000){c.step();i++;}
  for(let i=0;i<(extra||1500000);i++) c.step(); }
const hx=v=>v.toString(16).padStart(2,'0');
// The stimuli need the CPU instance, so they are functions of c
function probe(name,act){
  const c=boot(); const before=Uint8Array.from(c.nv);
  act(c);
  const diff=[];
  for(let i=0;i<256;i++) if(c.nv[i]!==before[i])
    diff.push(hx(i)+'h:'+hx(before[i])+'->'+hx(c.nv[i]));
  console.log(name.padEnd(28)+(diff.length?diff.join('  '):'(no change)'));
}
const T=(c,k)=>stimulate(c,()=>{c.tog^=1; c.key(k,c.tog);});
const R=(c,n)=>stimulate(c,()=>c.rad(0,n));
probe('do nothing',        c=>{ stimulate(c,()=>{},2000000); });
probe('rotary knob +1',    c=>{ R(c,1); });
probe('rotary knob +20',   c=>{ R(c,20); });
probe('decade up (0Bh)',   c=>{ T(c,0x08); T(c,0x0B); });
probe('waveform (11h)',    c=>{ T(c,0x11); });
probe('MODE (29h)',        c=>{ T(c,0x29); });
