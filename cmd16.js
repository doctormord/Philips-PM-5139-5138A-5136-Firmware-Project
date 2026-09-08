// Re-check section 16: which strobes are served after a command?
// The command token goes into 10h, then the command interpreter 71BFh,
// then the reload cycle 090Ch. The strobes and the request byte 29h are
// recorded.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));

// stub out I2C and the display, but let the strobe output 0E98h run
const STUBS=new Set([0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066,
                     0x645A,0x64F7,0x2DC1,0x2C55,0x517D]);
const h=x=>x.toString(16).padStart(2,'0').toUpperCase();

function call(c,addr,max,rec){
  c.push(0xFF); c.push(0xFF); c.pc=addr;
  let buf=[];
  for(let i=0;i<max;i++){
    if(c.pc===0xFFFF) return true;
    if(STUBS.has(c.pc)){ c.sA(0); const hi=c.pop(), lo=c.pop(); c.pc=(hi<<8)|lo; continue; }
    const op=ROM[c.pc];
    if(rec){
      if(op===0xF5 && ROM[c.pc+1]===0x99) buf.push(c.sfr[0xE0]);
      else if(op===0x85 && ROM[c.pc+2]===0x99) buf.push(c.ram[ROM[c.pc+1]]);
      else if(op===0x75 && ROM[c.pc+1]===0x99) buf.push(ROM[c.pc+2]);
      else if(op===0xF0){ const dph=c.sfr[0x83];
        if(dph>=0x81&&dph<=0x8F){ const k=dph&15;
          if(!rec.has(k)) rec.set(k,[]);
          rec.get(k).push(buf.map(h).join(' ')); }
        buf=[]; }
    }
    c.step();
  }
  return false;
}

let G=null;
function boot(){
  if(!G){ const c=new CPU(ROM); call(c,0x3C2E,3000000,null);
    G={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),xram:Uint8Array.from(c.xram)}; }
  const c=new CPU(ROM); c.ram.set(G.ram); c.sfr.set(G.sfr); c.xram.set(G.xram);
  return c;
}

// command table at 7752h: 14 bytes of name, then two tokens
const tab={};
for(let a=0x7752;;a+=16){
  let name='';
  for(let i=0;i<14 && ROM[a+i];i++) name+=String.fromCharCode(ROM[a+i]);
  if(!name) break;
  for(const t of [ROM[a+14],ROM[a+15]]) if(t && t!==0xFF && !(t in tab)) tab[t]=name;
}

console.log('token command       29h  strobes in the wake');
const rows=[];
for(const t of Object.keys(tab).map(Number).sort((a,b)=>a-b)){
  if(t>=0x40) continue;
  const c=boot();
  c.ram[0x10]=t; c.ram[0x11]=0; c.ram[0x15]=1; c.ram[0x16]=0;
  if(!call(c,0x71BF,300000,null)) { console.log(`  ${h(t)}  ${tab[t].padEnd(12)} (the interpreter does not run through)`); continue; }
  const req=c.ram[0x29];
  const rec=new Map();
  call(c,0x090C,300000,rec);       // runs into the main cycle, budget limited
  const str=[...rec.keys()].sort((a,b)=>a-b).map(k=>'STR'+k);
  rows.push([t,tab[t],req,str]);
  console.log(`  ${h(t)}  ${tab[t].padEnd(12)} ${h(req)}   ${str.join(' ')||'-'}`);
}

// groups as in section 16
console.log('\nsummary by token range:');
const grp=[['waveforms','11-1A',0x11,0x1A],['symmetry','1E-1F',0x1E,0x1F],
           ['modulation/sweep','20-2F',0x20,0x2F]];
for(const [name,range,lo,hi] of grp){
  const s=new Set(), req=new Set();
  for(const [t,,a,str] of rows) if(t>=lo&&t<=hi){ str.forEach(x=>s.add(x)); req.add(h(a)); }
  console.log(`  ${name.padEnd(18)} ${range}  29h={${[...req].sort().join(',')}}  ${[...s].sort().join(' ')}`);
}
const bu=rows.find(z=>z[0]===0x28);
if(bu) console.log(`  burst alone        28    29h=${h(bu[2])}  ${bu[3].join(' ')}`);
