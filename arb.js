// Counts how often the error branch 963Bh in 9615h is taken.
// Counter-check: the same image with one flipped byte in the directory.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
let B=null;
function boot(xr){
  if(!B){ const c=new CPU(ROM); c.nv.set(NV); c.pc=0;
    for(let i=0;i<11000000;i++) c.step();
    B={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),nv:Uint8Array.from(c.nv)}; }
  const c=new CPU(ROM); c.ram.set(B.ram); c.sfr.set(B.sfr); c.nv.set(B.nv);
  c.xram.fill(0); c.xram.set(xr.subarray(0,Math.min(xr.length,c.xram.length)));
  return c;
}
function check(name, xr){
  const c=boot(xr);
  c.push(0xFF); c.push(0xFF); c.pc=0x9615;
  let n=0, bad=0, ok=0;
  while(c.pc!==0xFFFF && n<3000000){
    if(c.pc===0x963B) bad++;             // SETB 22h.7 - directory rejected
    if(c.pc===0x9645) ok++;              // the shared continuation, ALWAYS reached
    c.step(); n++;
  }
  // Only the error branch is meaningful; 9645h lies behind both paths.
  console.log(`  ${name.padEnd(32)} rejected: ${bad}x   (9645h ${ok}x)`);
}
const REAL=new Uint8Array(fs.readFileSync(P+'D310_image.bin'));   // the X28C64 as read out
const FLIPPED=Uint8Array.from(REAL); FLIPPED[5]^=0x01;    // one bit in the directory
const HEADER =Uint8Array.from(REAL); HEADER[1]^=0x01;     // the check byte itself
const SYN =new Uint8Array(fs.readFileSync(P+'D310_image_synthetic.bin'));
const EMPTY=new Uint8Array(8192).fill(0xFF);
check('real (D310_image.bin)', REAL);
check('real, one data bit flipped', FLIPPED);
check('real, check byte flipped', HEADER);
check('synthetic (counter-check)', SYN);
check('empty FFh', EMPTY);
