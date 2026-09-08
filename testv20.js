// Cold start with V2.0 against V1.5: display and state have to be equal.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE =new Uint8Array(fs.readFileSync(P+'D310_image.bin'));
const hx=a=>Array.from(a).map(x=>x.toString(16).padStart(2,'0')).join(' ');
function run(path){
  const ROM=new Uint8Array(fs.readFileSync(P+path));
  const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
  for(let i=0;i<11000000;i++) c.step();
  // a few keys, so that normal operation runs as well
  for(const k of [0x11,0x19,0x29,0x08]){
    c.tog^=1; c.key(k,c.tog);
    let i=0; while((c.wi<c.wave.length||c.ki<c.kn.length)&&i<2000000){c.step();i++;}
    for(let i=0;i<600000;i++) c.step();
  }
  return {pc:c.pc, disp:hx(c.frame), ram:hx(c.ram.slice(0x20,0x30)),
          err:(c.ram[0x24]>>3)&1};
}
const a=run('M27512_PM5139_V15.bin'), b=run('M27512_PM5139_V20.bin');
console.log('V1.5  PC=%s  error flag=%d', a.pc.toString(16), a.err);
console.log('      display %s', a.disp);
console.log('V2.0  PC=%s  error flag=%d', b.pc.toString(16), b.err);
console.log('      display %s', b.disp);
console.log('\ndisplay equal: %s', a.disp===b.disp);
console.log('flags 20h-2Fh equal: %s', a.ram===b.ram);
