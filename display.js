// Display buffer 30h-43h at every decade step of the frequency.
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
function press(c,code){
  c.tog^=1; c.key(code,c.tog);
  let i=0; while(!idle(c)&&i<2000000){ c.step(); i++; }
  for(let i=0;i<500000;i++) c.step();
}
const hx=v=>v.toString(16).padStart(2,'0');
const buf=c=>Array.from(c.frame).map(hx).join(' ');   // the image sent to the PCF8576
const c=boot(); press(c,0x08);
let prev=null;
for(let k=0;k<6;k++){
  const d=c.ram[0x50]>>4, m=(c.ram[0x50]&15)+''+hx(c.ram[0x51])+hx(c.ram[0x52]);
  const p=buf(c);
  let diff='';
  if(prev){ const a=prev.split(' '), b=p.split(' ');
    diff=a.map((x,i)=>x!==b[i]?('%02X'.replace('%02X',(0x30+i).toString(16))+':'+x+'->'+b[i]):null)
          .filter(Boolean).join('  '); }
  console.log('decade '+d+' mantissa '+m+'  '+p+(diff?'\n         changed: '+diff:''));
  prev=p; press(c,0x0B);
}
