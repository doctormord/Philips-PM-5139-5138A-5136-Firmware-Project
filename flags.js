// P6: the effect of the state bits 20h-2Fh.
// Watches two quantities at once: the display buffer 30h-43h and the
// telegrams on the serial C-bus (MOV SBUF,... collects the bytes, a
// MOVX @DPTR with DPH=8nh terminates the telegram with strobe n). All five
// forms that can write SBUF have to be caught: the waveform download loop
// at 3D80h alternates MOV SBUF,R6 with MOV SBUF,A, so watching only the
// accumulator form halves every telegram it emits.
// At rest the firmware sends nothing, so every run gets a stimulus. And
// because a flag only takes effect in the matching operating mode, every
// flag runs through several profiles.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM =new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV  =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const D310=new Uint8Array(fs.readFileSync(P+'D310_image.bin'));

// MODE right steps 2Ch one-hot: 01 MOD-OFF, 02 AM, 04 FM, 08 PSK,
// 10 GATE, 20 SWP-LIN, 40 SWP-LOG, 80 BURST.
const PROFILE={
  base  : [['rad',0,1],['key',0x11],['key',0x19]],
  am    : [['key',0x29],['key',0x29],['rad',0,1],['key',0x21]],
  fm    : [['key',0x29],['key',0x29],['key',0x29],['rad',0,1],['key',0x21]],
  sweep : [['key',0x29],['key',0x29],['key',0x29],['key',0x29],
           ['key',0x29],['key',0x29],['rad',0,1]],
  burst : [['key',0x29],['key',0x29],['key',0x29],['key',0x29],
           ['key',0x29],['key',0x29],['key',0x29],['key',0x29],['rad',0,1]],
  memory:[['key',0x22],['key',0x23],['rad',0,1]],
};
const ONLY = process.env.PROFILE ? [process.env.PROFILE] : Object.keys(PROFILE);

function run(c,n){ for(let i=0;i<n;i++) c.step(); }
let B=null;
function boot(){
  if(!B){ const c=new CPU(ROM); c.nv.set(NV); c.xram.set(D310); c.pc=0;
    run(c,11000000);
    B={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),
       xram:Uint8Array.from(c.xram),nv:Uint8Array.from(c.nv),cy:c.cycles}; }
  const c=new CPU(ROM);
  c.ram.set(B.ram); c.sfr.set(B.sfr); c.xram.set(B.xram); c.nv.set(B.nv);
  c.cycles=B.cy; c.pc=0x0006; c.tog=0;
  return c;
}

// Shortens a telegram to a readable signature
function sig(v){
  const l=[...v].sort();
  const short=s=>{ const t=s.split(' '); return t.length>6 ? t.slice(0,6).join(' ')+`...(${t.length}B)` : s; };
  return l.length===1 ? short(l[0]) : `${l.length}x[${short(l[0])}...]`;
}
const showT=m=>[...m].sort().map(([k,v])=>k+'{'+sig(v)+'}').join('  ');
const hx=a=>Array.from(a).map(x=>x.toString(16).padStart(2,'0').toUpperCase()).join(' ');

// Runs one profile and returns the telegram signature and display buffer
function drive(c,steps){
  const rec=new Map(); let buf=[];
  const idle=()=>c.wi>=c.wave.length && c.ki>=c.kn.length;
  const tick=(n)=>{ for(let i=0;i<n;i++){
      const op=ROM[c.pc];
      if(op===0xF5 && ROM[c.pc+1]===0x99) buf.push(c.sfr[0xE0]);
      else if(op===0x85 && ROM[c.pc+2]===0x99) buf.push(c.ram[ROM[c.pc+1]]);
      else if(op===0x75 && ROM[c.pc+1]===0x99) buf.push(ROM[c.pc+2]);
      else if(op>=0x88 && op<=0x8F && ROM[c.pc+1]===0x99) buf.push(c.gR(op-0x88));
      else if((op===0x86||op===0x87) && ROM[c.pc+1]===0x99) buf.push(c.ram[c.gR(op-0x86)]);
      else if(op===0xF0){ const dph=c.sfr[0x83];
        if(dph>=0x81 && dph<=0x8F){ const k='STR'+(dph&15);
          if(!rec.has(k)) rec.set(k,new Set());
          rec.get(k).add(hx(buf)); }
        buf=[]; }
      c.step(); } };
  for(const s of steps){
    if(s[0]==='key'){ c.tog^=1; c.key(s[1],c.tog); }
    else c.rad(s[1],s[2]);
    let i=0; while(!idle()&&i<2500000){ tick(1); i++; }
    tick(500000);
  }
  return {t:showT(rec), d:hx(c.ram.slice(0x30,0x44))};
}

// reference run per profile
const REF={};
for(const p of ONLY) REF[p]=drive(boot(),PROFILE[p]);
console.log('reference runs:');
for(const p of ONLY) console.log(`  ${p.padEnd(9)} ${REF[p].t||'(no telegrams)'}`);
console.log();

const acts=new Map();
for(let b=0x20;b<0x30;b++) for(let n=0;n<8;n++){
  const name=b.toString(16).toUpperCase()+'h.'+n;
  const hits=[];
  for(const p of ONLY){
    const c=boot(); c.ram[b]^=(1<<n);
    let r; try{ r=drive(c,PROFILE[p]); }catch(e){ hits.push(p+':aborted'); continue; }
    const dt=(r.t!==REF[p].t), dd=(r.d!==REF[p].d);
    if(dt||dd) hits.push(p+(dt&&dd?'(T+D)':dt?'(T)':'(D)'));
  }
  if(hits.length){ acts.set(name,hits); console.log(`  ${name.padEnd(7)} ${hits.join(' ')}`); }
}
console.log(`\n${acts.size} of 128 flags show an effect in at least one profile.`);
const silent=[];
for(let b=0x20;b<0x30;b++) for(let n=0;n<8;n++){
  const name=b.toString(16).toUpperCase()+'h.'+n;
  if(!acts.has(name)) silent.push(name);
}
console.log(`without effect (${silent.length}): `+silent.join(' '));
