// Calls the version indication of the reset sequence and reads it in plain text.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const {digit}=require(P+'readout.js');
const NV=new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE=new Uint8Array(fs.readFileSync(P+'D310_image.bin'));
function version(path){
  const ROM=new Uint8Array(fs.readFileSync(P+path));
  const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
  for(let i=0;i<11000000;i++) c.step();
  // find the place that loads 3Fh with the version byte
  let adr=-1;
  for(let a=0;a<0xFFFC;a++)
    if(ROM[a]===0x75&&ROM[a+1]===0x3F&&ROM[a+3]===0x75&&ROM[a+4]===0x40
       &&(ROM[a+2]===0x0E||ROM[a+2]===0x7B)) { adr=a; break; }
  c.push(0xFF); c.push(0xFF); c.pc=adr;
  let n=0; while(c.pc!==0xFFFF&&n<400000){ c.step(); n++; }
  return {adr, raw:[c.ram[0x3F],c.ram[0x40]],
          text:digit(c.ram[0x3F])+digit(c.ram[0x40])};
}
for(const f of ['M27512_PM5139_V13.bin','M27512_PM5139_V15.bin','M27512_PM5139_V20.bin']){
  const v=version(f);
  console.log('%s  routine %s  RAM 3Fh/40h = %s  ->  display "%s"',
    f.padEnd(24), v.adr.toString(16), v.raw.map(x=>x.toString(16)).join(' '), v.text);
}
