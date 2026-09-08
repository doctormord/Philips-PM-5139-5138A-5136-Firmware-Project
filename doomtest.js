// Records the sequence of notes the melody routine plays.
//
// The routine sits two bytes behind the ROM checksum (see section 35) and
// is reached on the instrument through menu item 8 of the diagnostic
// program. That key press cannot be injected in the emulator, because
// ACC.0 of the status register is always set in the model - so the
// routine is called directly here.
//
//     node doomtest.js [rom.bin]
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const FILE=process.argv[2] || P+'M27512_PM5139_V20_melody.bin';
const ROM=new Uint8Array(fs.readFileSync(FILE));
const NV =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const EE =new Uint8Array(fs.readFileSync(P+'D310_image_V20.bin'));

// The melody entry point: read the end address out of the checksum
// routine (MOV 10h,#hi / MOV 11h,#lo), the routine starts at end+2.
let end=-1;
for(let a=0;a<0xFFFC;a++)
  if(ROM[a]===0x75&&ROM[a+1]===0x10&&ROM[a+3]===0x75&&ROM[a+4]===0x11){
    const v=(ROM[a+2]<<8)|ROM[a+5];
    if(v>=0x8000&&v<0x10000) end=v;
  }
if(end<0){ console.log('checksum routine not found in '+FILE); process.exit(1); }
const entry=end+2;
if(ROM[entry]!==0x90){ console.log('no melody at %s - build it with mkdoom.py first',
  entry.toString(16)); process.exit(1); }
console.log('%s: melody entry at %sh', FILE.replace(P,''), entry.toString(16).toUpperCase());

const c=new CPU(ROM); c.nv.set(NV); c.xram.set(EE); c.pc=0;
for(let i=0;i<11000000;i++) c.step();
c.push(0xFF); c.push(0xFF); c.pc=entry;
const notes=[]; let n=0, cycles0=c.cycles;
while(c.pc!==0xFFFF && n<200000000){
  if(c.pc===0x0A28){                       // entering OUT_FREQ
    const bcd=[c.ram[0x50],c.ram[0x51],c.ram[0x52]];
    const D=bcd[0]>>4;
    const M=((bcd[0]&15)*10000+(bcd[1]>>4)*1000+(bcd[1]&15)*100+
             (bcd[2]>>4)*10+(bcd[2]&15));
    const hz=M*Math.pow(10,D-8)*1000;
    notes.push({hz, at:(c.cycles-cycles0)});
    if(notes.length>=40) break;            // the loop is endless, show the start
  }
  c.step(); n++;
}
console.log('%d notes recorded, %d steps', notes.length, n);
const NAMES={82.41:'E2',73.42:'D2',65.41:'C2',61.74:'B1',58.27:'A#1',49:'G1'};
console.log('\nno  frequency  note  distance to the previous one');
notes.forEach((t,i)=>{
  const d=i? (t.at-notes[i-1].at)/1000 : 0;   // instruction count, not ms - see section 35
  const nm=NAMES[Math.round(t.hz*100)/100]||'';
  console.log('  '+String(i+1).padStart(2)+'  '+t.hz.toFixed(2).padStart(7)+' Hz  '+
    nm.padEnd(4)+(i?d.toFixed(1):''));
});
