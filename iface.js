// P5: emulate the interface card at I2C address 5Eh and watch the traffic.
// core.js calls cpu.iface.start/wr/rd when cpu.iface is set; without iface
// the core behaves as before (no ACK on 5Eh).
const fs=require('fs'), P=__dirname+'/';
eval(fs.readFileSync(P+'core.js','utf8'));
const ROM =new Uint8Array(fs.readFileSync(P+'M27512_PM5139_V13.bin'));
const NV  =new Uint8Array(fs.readFileSync(P+'PCF8570_image.bin'));
const D310=new Uint8Array(fs.readFileSync(P+'D310_image.bin'));

// the rotating checksum of the firmware: r = ror8((byte + r) & 0xFF)
function checksum(bytes){
  let r=0;
  for(const b of bytes){ let a=(b+r)&0xFF; r=((a>>1)|((a&1)<<7))&0xFF; }
  return r;
}

function Card(answer){
  return {
    log:[], pending:[], queue:(answer||[]).slice(),
    start(dir){ this.dir=dir; if(dir==='w'&&this.pending.length){ this.log.push('W '+this.pending.join(' ')); this.pending=[]; } },
    wr(b){ this.pending.push(b.toString(16).padStart(2,'0').toUpperCase()); },
    rd(){ const b=this.queue.length?this.queue.shift():0xFF;
          this.log.push('R '+b.toString(16).padStart(2,'0').toUpperCase()); return b; },
    flush(){ if(this.pending.length){ this.log.push('W '+this.pending.join(' ')); this.pending=[]; } }
  };
}

function run(c,n){ for(let i=0;i<n;i++) c.step(); }
function idle(c){ return c.wi>=c.wave.length && c.ki>=c.kn.length; }
function settle(c){ let i=0; while(!idle(c)&&i<3000000){c.step();i++;} run(c,300000); }

function fresh(card){
  const c=new CPU(ROM); c.nv.set(NV); c.xram.set(D310); c.pc=0;
  if(card) c.iface=card;
  return c;
}
const h=x=>x.toString(16).padStart(2,'0').toUpperCase();

// ---------------------------------------------------------------- case A
console.log('=== A: without a card (the previous behaviour) ===');
{ const c=fresh(null); run(c,11000000);
  console.log('   25h.7 (card detected) = '+((c.ram[0x25]>>7)&1)+'   26h = '+h(c.ram[0x26]));
  console.log('   display buffer: '+Array.from(c.ram.slice(0x30,0x44)).map(h).join(' ')); }

// ---------------------------------------------------------------- case B
console.log('\n=== B: the card answers, but only with FFh (idle) ===');
{ const k=Card([]); const c=fresh(k); run(c,11000000); k.flush();
  console.log('   25h.7 = '+((c.ram[0x25]>>7)&1)+'   26h = '+h(c.ram[0x26])+'   4Bh = '+h(c.ram[0x4B]));
  console.log('   I2C traffic (the first 40 transactions):');
  for(const z of k.log.slice(0,40)) console.log('     '+z);
  console.log('   ... '+k.log.length+' transactions in total'); }

// ---------------------------------------------------------------- case C
// Inject a data packet. The format per 5FA9h: a status byte (bits 0..4 =
// length), then n data bytes, then the rotating checksum.
console.log('\n=== C: inject a data packet ===');
{
  const data=[0x41,0x42,0x43,0x44,0x45];             // "ABCDE"
  const status=data.length;                           // length, bits 7/6 = 0
  const packet=[status,...data];
  packet.push(checksum(packet));
  console.log('   packet: '+packet.map(h).join(' ')+'   (checksum '+h(packet[packet.length-1])+')');

  const k=Card(packet); const c=fresh(k);
  run(c,11000000);                                    // cold start, card detected
  k.log.length=0;
  c.ifaceInt=1;                                       // signal the interrupt
  run(c,2000000);
  c.ifaceInt=0;
  run(c,1000000); k.flush();
  console.log('   I2C traffic after the signal:');
  for(const z of k.log.slice(0,25)) console.log('     '+z);
  console.log('   receive buffer RAM 80h-8Fh: '+Array.from(c.ram.slice(0x80,0x90)).map(h).join(' '));
  console.log('   4Ah='+h(c.ram[0x4A])+'  4Bh='+h(c.ram[0x4B])+'  4Ch='+h(c.ram[0x4C])+
              '  25h='+h(c.ram[0x25])+'  26h='+h(c.ram[0x26]));
}

// ---------------------------------------------------------------- case D
console.log('\n=== D: a packet with a deliberately wrong checksum ===');
{
  const data=[0x41,0x42,0x43,0x44,0x45];
  const packet=[data.length,...data];
  packet.push((checksum(packet)^0xFF)&0xFF);
  const k=Card(packet); const c=fresh(k);
  run(c,11000000); k.log.length=0;
  c.ifaceInt=1; run(c,2000000); c.ifaceInt=0; run(c,1000000); k.flush();
  console.log('   receive buffer RAM 80h-8Fh: '+Array.from(c.ram.slice(0x80,0x90)).map(h).join(' '));
  console.log('   4Ah='+h(c.ram[0x4A])+'  4Bh='+h(c.ram[0x4B])+'  26h='+h(c.ram[0x26]));
  console.log('   last transactions: '+k.log.slice(-6).join(' | '));
}
