// Which 50h-52h give which note? Decode the display.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const {digit}=require(P+'readout.js');
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
// note in Hz -> BCD representation following f = M * 10^(D-8) kHz
function encode(hz){
  const khz=hz/1000;
  for(let D=1;D<=9;D++){
    const M=Math.round(khz/Math.pow(10,D-8));
    if(M>=1000 && M<=9999) return {D,M};
  }
  return null;
}
console.log('note     Hz      decade mantissa   50h 51h 52h   TWS word (11h..14h)');
for(const [name,hz] of [['E2',82.41],['D2',73.42],['C2',65.41],['A#1',58.27],
                        ['A1',55.00],['G1',49.00],['E1',41.20]]){
  const k=encode(hz);
  const c=boot();
  const z=String(k.M).padStart(5,'0');
  c.ram[0x50]=(k.D<<4)|Number(z[0]);
  c.ram[0x51]=Number(z[1])*16+Number(z[2]);
  c.ram[0x52]=Number(z[3])*16+Number(z[4]);
  c.push(0xFF); c.push(0xFF); c.pc=0x09BF;
  let n=0; while(c.pc!==0xFFFF && n<200000){ c.step(); n++; }
  const hx=a=>c.ram[a].toString(16).padStart(2,'0');
  console.log('%s %s  %d      %s      %s %s %s   %s',
    name.padEnd(4), String(hz).padStart(6), k.D, String(k.M).padStart(5),
    hx(0x50),hx(0x51),hx(0x52),
    [0x11,0x12,0x13,0x14].map(hx).join(' '));
}
