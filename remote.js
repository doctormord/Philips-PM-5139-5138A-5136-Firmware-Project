// 1B37h -> REMOTE_SWITCH is reached when, in the wait loop 1B2Eh, either
// ACC.0 of the status register is 0 or P3.2 (INT0) becomes active.
// P3.2 hangs on the interface card -> ifaceInt.
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
  c.xram.set(B.xram); c.nv.set(B.nv); return c;
}
// A slave at 5Eh that answers E3h (REMOTE) when asked
function card(c,answer){
  c.iface = { queue:answer.slice(), wasRead:[], wasWritten:[],
    start(){}, wr(b){this.wasWritten.push(b);},
    rd(){ const b=this.queue.length?this.queue.shift():0xFF;
          this.wasRead.push(b); return b; } };
}
function run(name,{int0,cardOn,answer}){
  const c=boot();
  c.ram[0x25]|=0x80;                       // card detected
  if(cardOn) card(c,answer||[0xE3]);
  c.ifaceInt = !!int0;
  c.push(0xFF); c.push(0xFF); c.pc=0x1B0C;
  let n=0; const z={0x1B2E:0,0x1B37:0,0x666A:0,0x1B44:0};
  while(c.pc!==0xFFFF && n<1500000){ if(c.pc in z) z[c.pc]++; c.step(); n++; }
  const b=(a,k)=>(c.ram[a]>>k)&1;
  const p=(v,n)=>String(v).padStart(n);
  console.log(name.padEnd(28)+' 1B2E:'+p(z[0x1B2E],6)+'  1B37:'+p(z[0x1B37],4)+
    '  666A:'+p(z[0x666A],4)+'  1B44:'+p(z[0x1B44],6)+
    '   2Eh.3='+b(0x2E,3)+'  26h.1='+b(0x26,1)+'  2Fh.2='+b(0x2F,2));
}
run('without INT0, without card',  {int0:false,cardOn:false});
run('INT0 active, without card',   {int0:true, cardOn:false});
run('INT0 active, card says E3h',  {int0:true, cardOn:true, answer:[0xE3]});
run('INT0 active, card says E2h',  {int0:true, cardOn:true, answer:[0xE2]});
