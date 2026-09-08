// Re-check of the display bitmap (section 15) with the corrected JS core.
// Equivalent to sweep.py and sweep3.py, but fast enough for the pair search.
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM=new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const STUBS=new Set([0x5187,0x51A1,0x51C1,0x5194,0x37DB,0x392F,0x5061,0x5066]);

function call(c,addr,max){
  c.push(0xFF); c.push(0xFF); c.pc=addr;
  for(let i=0;i<max;i++){
    if(c.pc===0xFFFF) return true;
    if(STUBS.has(c.pc)){ const h=c.pop(), l=c.pop(); c.pc=(h<<8)|l; continue; }
    c.step();
  }
  return false;
}
let GROUND=null;
function base(){
  if(!GROUND){ const c=new CPU(ROM); call(c,0x3C2E,3000000);
    GROUND={ram:Uint8Array.from(c.ram),sfr:Uint8Array.from(c.sfr),xram:Uint8Array.from(c.xram)}; }
  const c=new CPU(ROM); c.ram.set(GROUND.ram); c.sfr.set(GROUND.sfr); c.xram.set(GROUND.xram);
  return c;
}
function build(flip){
  const c=base();
  for(const [b,n] of flip) c.ram[b]^=(1<<n);
  if(!call(c,0x3381,400000)) return null;
  return Array.from(c.ram.slice(0x30,0x44));
}
const equal=(a,b)=>a&&b&&a.every((v,i)=>v===b[i]);
const hex=a=>a.map(x=>x.toString(16).padStart(2,'0').toUpperCase()).join(' ');
function diff(a,b){ const r=[];
  for(let i=0;i<20;i++) if(a[i]!==b[i]) r.push(`${(0x30+i).toString(16).toUpperCase()}: ${a[i].toString(16).padStart(2,'0').toUpperCase()}->${b[i].toString(16).padStart(2,'0').toUpperCase()}`);
  return r.join('  '); }

const BASE=build([]);
console.log('base state after 3C2Eh:');
console.log('  '+hex(BASE));
console.log('  section 15 gives: 02 00 00 02 00 A0 28 0C 0E ED 00 00 00 00 00 0E ED ED EF 40');
console.log();

// --- part 1: flags that act on their own (equivalent to sweep.py)
const solo=[], silent=[];
console.log('=== flags with an immediate effect ===');
for(let b=0x20;b<0x30;b++) for(let n=0;n<8;n++){
  const o=build([[b,n]]);
  if(o===null){ console.log(`  ${b.toString(16).toUpperCase()}h.${n}  -> timeout`); continue; }
  if(!equal(o,BASE)){ solo.push([b,n]); console.log(`  ${b.toString(16).toUpperCase()}h.${n}  ${diff(BASE,o)}`); }
  else silent.push([b,n]);
}
console.log(`\n${solo.length} of 128 flags act immediately, ${silent.length} stay silent.`);

// --- part 2: preconditions (equivalent to sweep3.py)
console.log('\n=== silent flags that a precondition unlocks ===');
const all=[]; for(let b=0x20;b<0x30;b++) for(let n=0;n<8;n++) all.push([b,n]);
const found=new Map();
for(const pre of all){
  const pb=build([pre]); if(pb===null) continue;
  for(const t of silent){
    if(t[0]===pre[0]&&t[1]===pre[1]) continue;
    const o=build([pre,t]); if(o===null) continue;
    if(!equal(o,pb)){
      const k=`${t[0].toString(16).toUpperCase()}h.${t[1]}`;
      if(!found.has(k)) found.set(k,{n:0,first:pre,d:diff(pb,o)});
      found.get(k).n++;
    }
  }
}
for(const [k,v] of [...found].sort())
  console.log(`  ${k}  (unlocked by ${v.first[0].toString(16).toUpperCase()}h.${v.first[1]}, ${v.n} preconditions)  ${v.d}`);
console.log(`\n${found.size} further flags act only with a precondition, ${silent.length-found.size} not at all.`);
