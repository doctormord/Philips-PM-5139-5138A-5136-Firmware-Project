// Measures the parameter limits through the complete handler 0663h.
// It loads the value itself with PARAM_LOAD out of the parameter RAM
// (address table 08F2h) and checks it through 1121h -> 11CCh.
// The indicator for "limit exceeded" is a pass through the correction
// point 1228h.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE =new Uint8Array(fs.readFileSync(P+'D310_image.bin'));
const ADR=[0,0x50,0x53,0x56,0x58,0x5A,0x5C,0x5E,0x60,0x62,0x64,0x66,0x68];
const LEN=i=>i<=2?3:2;
let B=null;
function boot(){
  if(!B){ const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
    for(let i=0;i<11000000;i++) c.step();
    B={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),
       xram:Uint8Array.from(c.xram),nv:Uint8Array.from(c.nv)}; }
  const c=new CPU(ROM); c.ram.set(B.ram); c.sfr.set(B.sfr);
  c.xram.set(B.xram); c.nv.set(B.nv); return c;
}
// The value as BCD into the parameter memory, the decade into the upper
// nibble of the first byte
function store(c,idx,dec,mant){
  const n=LEN(idx), digits=2*n-1;
  const z=String(mant).padStart(digits,'0');
  const a=ADR[idx];
  c.ram[a]=(dec<<4)|Number(z[0]);
  for(let k=1;k<n;k++) c.ram[a+k]=Number(z[2*k-1])*16+Number(z[2*k]);
}
function exceeds(idx,dec,mant){        // true = the limit bit
  const c=boot();
  c.ram[0x24]=(c.ram[0x24]&0xF0)|idx;
  store(c,idx,dec,mant);
  c.push(0xFF); c.push(0xFF); c.pc=0x0663;
  let n=0, corr=0;
  while(c.pc!==0xFFFF && n<300000){ if(c.pc===0x1228) corr++; c.step(); n++; }
  return corr>0;
}
function limit(idx,dec,max){
  let lo=0, hi=max;
  if(exceeds(idx,dec,lo)) return '(already at 0)';
  if(!exceeds(idx,dec,hi)) return '(free up to '+hi+')';
  while(hi-lo>1){ const m=(lo+hi)>>1; exceeds(idx,dec,m)?hi=m:lo=m; }
  return lo;                            // the largest permissible value
}
const NAMES=['','FREQUENCY','STOPFREQ','AMPLITUDE','DCOFFSET','MODFREQ','AMDEPTH',
             'FMDEVIATION','SWEEPTIME','ONPERIODS','STARTPHASE','DUTYCYCLE','RAM 68h'];
console.log('idx parameter      RAM   largest permissible mantissa per decade');
console.log('                         D=0      D=1      D=2      D=3      D=4      D=5');
for(let i=1;i<=12;i++){
  const max=LEN(i)===3?99999:999;
  const r=[0,1,2,3,4,5].map(d=>String(limit(i,d,max)).padStart(8));
  console.log(' %s %s %s %s', String(i).padStart(2),
    NAMES[i].padEnd(13), ADR[i].toString(16)+'h ', r.join(' '));
}
