// Machine cycles per opcode, indexed by opcode byte. One machine cycle is
// 12 oscillator periods, so at the 12 MHz of the PM5139 exactly 1 us.
// Mirrors mcs51.CYCLES; cyclecheck.py verifies that the two agree.
var MCYC=('1221111111111111222111111111111122211111111111112221111111111111'+
          '2212111111111111221211111111111122121111111111112222121111111111'+
          '2222422222222222222211111111111122124122222222222211222222222222'+
          '2211111111111111221112112222222222221111111111112222111111111111'
         ).split('').map(Number);
// ---- MCS-51 core + PM5139 peripherals ------------------------------------
function CPU(rom){
  this.rom=rom; this.ram=new Uint8Array(256); this.sfr=new Uint8Array(256);
  this.xram=new Uint8Array(0x8000); this.nv=new Uint8Array(256);
  this.pc=0; this.sfr[0x81]=0x6B; this.cycles=0; this.mcyc=0; this.inIsr=false;
  this.p33=0; this.ktg=0; this.wave=[]; this.wi=0; this.itg=1; this.idr=0; this.kn=[]; this.ki=0; this.strobe=0; this.tiAt=-1;
  this.sda=1; this.act=false; this.stage=null; this.dir='w'; this.nb=0; this.sh=0;
  this.ph='bits'; this.sel=false; this.mack=true; this.tx=0; this.ptr=0; this.dev=0;
  this.disp=new Uint8Array(20); this.frame=new Uint8Array(20); this.fbuf=[]; this.fn=0;
}
CPU.prototype.bank=function(){return (this.sfr[0xD0]>>3)&3;};
CPU.prototype.gR=function(n){return this.ram[this.bank()*8+n];};
CPU.prototype.sR=function(n,v){this.ram[this.bank()*8+n]=v&255;};
CPU.prototype.dg=function(a){
  if(a===0x90){var v=this.sfr[0x90]; if(!this.sda)v&=0x7F; v&=~0x1C&255; if(this.ktg)v|=4; if(this.idr)v|=8; if(this.itg)v|=0x10; return v;}
  if(a===0xB0){var v=this.sfr[0xB0]; v=this.p33?(v|8):(v&~8&255);
    // P3.2 = INT0: the interface card signals an event, active low
    v=this.ifaceInt?(v&~4&255):(v|4); return v;}
  return a>=0x80?this.sfr[a]:this.ram[a];
};
CPU.prototype.ds=function(a,v){ v&=255;
  if(a===0x90){var o=this.sfr[0x90]; this.sfr[0x90]=v; this.i2c(o,v); return;}
  if(a>=0x80){ this.sfr[a]=v; if(a===0x99)this.tiAt=this.cycles+12; } else this.ram[a]=v;
};
CPU.prototype.ba=function(b){return b>=0x80?[b&0xF8,b&7,1]:[0x20+(b>>3),b&7,0];};
CPU.prototype.bg=function(b){var t=this.ba(b);
  if(t[2]&&(t[0]===0x90||t[0]===0xB0))return (this.dg(t[0])>>t[1])&1;
  return ((t[2]?this.sfr[t[0]]:this.ram[t[0]])>>t[1])&1;};
CPU.prototype.bs=function(b,v){var t=this.ba(b);
  if(t[2]&&t[0]===0x90){var x=this.sfr[0x90]; x=v?(x|(1<<t[1])):(x&~(1<<t[1])&255); this.ds(0x90,x); return;}
  var A=t[2]?this.sfr:this.ram;
  if(v)A[t[0]]|=(1<<t[1]); else A[t[0]]&=~(1<<t[1])&255;};
CPU.prototype.A=function(){return this.sfr[0xE0];};
CPU.prototype.sA=function(v){v&=255; this.sfr[0xE0]=v; var p=0,x=v; while(x){p^=x&1;x>>=1;}
  this.sfr[0xD0]=(this.sfr[0xD0]&0xFE)|p;};
CPU.prototype.C=function(){return (this.sfr[0xD0]>>7)&1;};
CPU.prototype.sC=function(v){if(v)this.sfr[0xD0]|=0x80; else this.sfr[0xD0]&=0x7F;};
CPU.prototype.dptr=function(){return (this.sfr[0x83]<<8)|this.sfr[0x82];};
CPU.prototype.sdptr=function(v){this.sfr[0x83]=(v>>8)&255; this.sfr[0x82]=v&255;};
CPU.prototype.push=function(v){this.sfr[0x81]=(this.sfr[0x81]+1)&255; this.ram[this.sfr[0x81]]=v&255;};
CPU.prototype.pop=function(){var v=this.ram[this.sfr[0x81]]; this.sfr[0x81]=(this.sfr[0x81]-1)&255; return v;};
CPU.prototype.xr=function(d){ if(d>=0x8000){this.strobe^=1;
  var v=this.strobe?0x11:0x01;
  if(this.ifaceInt) v|=0x08;          // bit 3: the interface signals an event
  return v;} return this.xram[d]; };
// ---- I2C slaves: PCF8576 (70h) and PCF8570 RAM (A0h) ----------------------
CPU.prototype.rx=function(b){
  if(this.stage==='addr'){ var base=b&0xFE;
    this.sel=(base===0x70||base===0xA0||(this.iface&&base===0x5E));
    this.dir=(b&1)?'r':'w'; this.dev=base;
    this.stage=(base===0xA0&&this.dir==='w')?'word':'data';
    // Only for the interface card: the ACK directly after the read address
    // comes from the slave, not from the master, and must not overwrite
    // mack - otherwise no byte is ever fetched. The display and the NVRAM
    // stay untouched so that the earlier measurements remain valid.
    if(this.dir==='r'&&base===0x5E&&this.iface){ this.mack=true; this.adrAck=true; }
    if(base===0x70)this.fbuf=[];
    if(this.iface&&base===0x5E) this.iface.start(this.dir);
    return; }
  if(this.dev===0x5E){ if(this.iface)this.iface.wr(b); return; }
  if(this.dev===0xA0){ if(this.stage==='word'){this.ptr=b; this.stage='data';}
    else {this.nv[this.ptr]=b; this.ptr=(this.ptr+1)&255;} return; }
  this.fbuf.push(b);
  if(this.fbuf.length===25){ for(var i=0;i<20;i++)this.frame[i]=this.fbuf[5+i]; this.fn++; }
};
CPU.prototype.i2c=function(o,n){
  var so=(o>>6)&1, ao=(o>>7)&1, s=(n>>6)&1, a=(n>>7)&1;
  if(s&&so&&ao&&!a){this.act=true;this.stage='addr';this.dir='w';this.dev=0;this.nb=0;this.sh=0;this.ph='bits';this.sel=false;this.sda=1;return;}
  if(s&&so&&!ao&&a){this.act=false;this.stage=null;this.sda=1;return;}
  if(!this.act)return;
  if(s&&!so){ if(this.ph==='bits'){ if(this.dir==='w')this.sh=((this.sh<<1)|a)&255; this.nb++; }
              else if(this.dir==='r'&&!this.adrAck)this.mack=(a===0); return; }
  if(so&&!s){
    if(this.ph==='bits'&&this.nb===8){ this.nb=0; var vm=(this.dir==='w'); if(vm)this.rx(this.sh);
      this.ph='ack'; this.sda=(vm&&this.sel)?0:1; return; }
    if(this.ph==='ack'){ this.ph='bits'; this.nb=0; this.adrAck=false;
      if(this.dir==='r'&&this.sel&&this.mack){
        this.tx=(this.dev===0x5E&&this.iface)?this.iface.rd():this.nv[this.ptr];
        if(this.dev!==0x5E)this.ptr=(this.ptr+1)&255;
        this.sda=(this.tx>>7)&1; }
      else this.sda=1; return; }
    if(this.dir==='r'&&this.sel&&this.nb<8) this.sda=(this.tx>>(7-this.nb))&1;
  }
};
// ---- keyboard -------------------------------------------------------------
CPU.prototype.key=function(code,tog){
  var H1=8000,H0=2500,G=900, w=[[0,6000]];
  this.sfr[0x88]|=8;                       // set IE1 instead of a start pulse
  var word=((tog&1)<<10)|(code&0x3F);   // toggle bit: bit 10
  for(var i=11;i>=0;i--){ w.push([1,((word>>i)&1)?H1:H0]); w.push([0,G]); }
  w.push([1,H0]); w.push([0,G]);      // closing pulse: triggers the final evaluation
  w.push([0,4000]);
  this.wave=w; this.wi=0; this.ktg=1;
};
CPU.prototype.rad=function(dir,n){
  // A full quadrature cycle per detent, rest position (ITG,IDR)=(1,1)
  var fwd  = [[0,1],[0,0],[1,0],[1,1]];
  var back = [[1,0],[0,0],[0,1],[1,1]];
  var f = dir? fwd : back, w=[], T=2500;
  for(var i=0;i<(n||1);i++) for(var k=0;k<4;k++) w.push([f[k][0],f[k][1],T]);
  w.push([1,1,8000]);
  this.kn=w; this.ki=0;
};
CPU.prototype.tick=function(){
  this.cycles++;
  while(this.ki<this.kn.length){ var e=this.kn[this.ki];
    if(e[2]<=0){this.ki++;continue;} this.itg=e[0]; this.idr=e[1]; e[2]--; break; }
  if(this.ki>=this.kn.length) this.itg=1;
  var t=this.sfr[0x88];
  if(t&0x10){ var v=((this.sfr[0x8C]<<8)|this.sfr[0x8A])+1; if(v>0xFFFF){v=0;this.sfr[0x88]|=0x20;}
    this.sfr[0x8C]=(v>>8)&255; this.sfr[0x8A]=v&255; }
  t=this.sfr[0x88];
  if(t&0x40){ var v=((this.sfr[0x8D]<<8)|this.sfr[0x8B])+1; if(v>0xFFFF){v=0;this.sfr[0x88]|=0x80;}
    this.sfr[0x8D]=(v>>8)&255; this.sfr[0x8B]=v&255; }
  if(this.tiAt>=0&&this.cycles>=this.tiAt){this.sfr[0x98]|=2; this.tiAt=-1;}
  while(this.wi<this.wave.length){ var e=this.wave[this.wi];
    if(e[1]<=0){this.wi++;continue;} this.p33=e[0]; e[1]--; break; }
  if(this.wi>=this.wave.length){this.p33=0;this.ktg=0;}
};
CPU.prototype.irq=function(){
  if(this.inIsr)return; var ie=this.sfr[0xA8]; if(!(ie&0x80))return;
  var t=this.sfr[0x88], src=-1, clr=0;
  if((ie&1)&&(t&2)){src=0x0003;clr=2;} else if((ie&2)&&(t&0x20)){src=0x000B;clr=0x20;}
  else if((ie&4)&&(t&8)){src=0x0013;clr=8;} else if((ie&8)&&(t&0x80)){src=0x001B;clr=0x80;}
  if(src<0)return;
  this.sfr[0x88]&=~clr&255;
  this.push(this.pc&255); this.push((this.pc>>8)&255); this.pc=src; this.inIsr=true;
  this.mcyc+=2;      // the vector fetch costs as much as an LCALL
};
// ---- instruction execution ------------------------------------------------
CPU.prototype.step=function(){
  var m=this.rom, pc=this.pc, op=m[pc];
  if(op===0x32) this.inIsr=false;
  var b1=m[(pc+1)&0xFFFF], b2=m[(pc+2)&0xFFFF];
  var rel=function(x){return x>127?x-256:x;};
  var lo=op&0x0F, hi=op&0xF0, lo5=op&0x1F, A=this.A();
  var self=this;
  function src(l){ if(l===4)return [b1,2]; if(l===5)return [self.dg(b1),2];
    if(l===6||l===7)return [self.ram[self.gR(l-6)],1]; return [self.gR(l-8),1]; }
  if(op===0x00){this.pc=pc+1;}
  else if(lo5===0x01){ this.pc=((pc+2)&0xF800)|((op&0xE0)<<3)|b1; }
  else if(lo5===0x11){ var t=((pc+2)&0xF800)|((op&0xE0)<<3)|b1;
    this.push((pc+2)&255); this.push(((pc+2)>>8)&255); this.pc=t; }
  else if(op===0x02){ this.pc=(b1<<8)|b2; }
  else if(op===0x12){ this.push((pc+3)&255); this.push(((pc+3)>>8)&255); this.pc=(b1<<8)|b2; }
  else if(op===0x22||op===0x32){ var h=this.pop(), l=this.pop(); this.pc=(h<<8)|l; }
  else if(op===0x03){this.sA(((A>>1)|(A<<7))&255);this.pc=pc+1;}
  else if(op===0x23){this.sA(((A<<1)|(A>>7))&255);this.pc=pc+1;}
  else if(op===0x13){var c=this.C();this.sC(A&1);this.sA((A>>1)|(c<<7));this.pc=pc+1;}
  else if(op===0x33){var c=this.C();this.sC((A>>7)&1);this.sA(((A<<1)|c)&255);this.pc=pc+1;}
  else if(op===0x04){this.sA(A+1);this.pc=pc+1;}
  else if(op===0x14){this.sA(A-1);this.pc=pc+1;}
  else if(op===0xE4){this.sA(0);this.pc=pc+1;}
  else if(op===0xF4){this.sA(~A);this.pc=pc+1;}
  else if(op===0xC4){this.sA(((A<<4)|(A>>4))&255);this.pc=pc+1;}
  else if(op===0xC3){this.sC(0);this.pc=pc+1;}
  else if(op===0xD3){this.sC(1);this.pc=pc+1;}
  else if(op===0xB3){this.sC(1-this.C());this.pc=pc+1;}
  else if(op===0xA3){this.sdptr((this.dptr()+1)&0xFFFF);this.pc=pc+1;}
  else if(op===0x90){this.sdptr((b1<<8)|b2);this.pc=pc+3;}
  else if(op===0x93){this.sA(m[(this.dptr()+A)&0xFFFF]);this.pc=pc+1;}
  else if(op===0x83){this.sA(m[(pc+1+A)&0xFFFF]);this.pc=pc+1;}
  else if(op===0x73){this.pc=(this.dptr()+A)&0xFFFF;}
  else if(op===0xE0){this.sA(this.xr(this.dptr()));this.pc=pc+1;}
  else if(op===0xF0){var d=this.dptr(); if(d<0x8000)this.xram[d]=A; this.pc=pc+1;}
  else if(op===0xE2||op===0xE3){this.sA(this.xr(this.gR(op-0xE2)));this.pc=pc+1;}
  else if(op===0xF2||op===0xF3){this.pc=pc+1;}
  else if(op===0xA4){var b=this.sfr[0xF0],r=A*b; this.sA(r&255); this.sfr[0xF0]=(r>>8)&255; this.sC(0); this.pc=pc+1;}
  else if(op===0x84){var b=this.sfr[0xF0]; if(b===0)this.sfr[0xD0]|=4; else {this.sA(Math.floor(A/b)); this.sfr[0xF0]=A%b;} this.sC(0); this.pc=pc+1;}
  else if(op===0xD4){var a=A; if((a&15)>9||((this.sfr[0xD0]>>6)&1))a+=6;
    if(((a>>4)&15)>9||this.C()){a+=0x60;this.sC(1);} this.sA(a); this.pc=pc+1;}
  else if(op===0x80){this.pc=pc+2+rel(b1);}
  else if(op===0x40||op===0x50){this.pc=(this.C()===(op===0x40?1:0))?pc+2+rel(b1):pc+2;}
  else if(op===0x60||op===0x70){var z=(A===0); this.pc=((op===0x60)?z:!z)?pc+2+rel(b1):pc+2;}
  else if(op===0x20||op===0x30){var v=this.bg(b1); this.pc=((op===0x20)?v:!v)?pc+3+rel(b2):pc+3;}
  else if(op===0x10){var v=this.bg(b1); if(v){this.bs(b1,0);this.pc=pc+3+rel(b2);}else this.pc=pc+3;}
  else this.g2(op,pc,b1,b2,rel,src,A,lo,hi);
  this.mcyc+=MCYC[op]; this.tick(); this.irq();
};
CPU.prototype.g2=function(op,pc,b1,b2,rel,src,A,lo,hi){
  var r;
  if((hi===0x20||hi===0x30||hi===0x90)&&lo>=4){ r=src(lo); var v=r[0],ln=r[1];
    var ci=(hi===0x30||hi===0x90)?this.C():0, x, ac;
    if(hi===0x90){ x=A-v-ci; this.sC(x<0?1:0); ac=((A&15)-(v&15)-ci)<0?1:0; }
    else { x=A+v+ci; this.sC(x>255?1:0); ac=((A&15)+(v&15)+ci)>15?1:0; }
    this.sfr[0xD0]=(this.sfr[0xD0]&~0x40)|(ac<<6);      // AC = auxiliary carry
    this.sA(x); this.pc=pc+ln; return; }
  if((hi===0x40||hi===0x50||hi===0x60)&&lo>=4&&[0x42,0x43,0x52,0x53,0x62,0x63].indexOf(op)<0){
    r=src(lo); var v=r[0]; this.sA(hi===0x40?(A|v):hi===0x50?(A&v):(A^v)); this.pc=pc+r[1]; return; }
  if(op===0x42||op===0x52||op===0x62){ var c=this.dg(b1);
    this.ds(b1, op===0x42?(c|A):op===0x52?(c&A):(c^A)); this.pc=pc+2; return; }
  if(op===0x43||op===0x53||op===0x63){ var c=this.dg(b1);
    this.ds(b1, op===0x43?(c|b2):op===0x53?(c&b2):(c^b2)); this.pc=pc+3; return; }
  if(hi===0xE0&&lo>=4){ r=src(lo); this.sA(r[0]); this.pc=pc+r[1]; return; }
  if(hi===0xF0&&lo>=5){ if(lo===5){this.ds(b1,A);this.pc=pc+2;}
    else if(lo<8){this.ram[this.gR(lo-6)]=A;this.pc=pc+1;}
    else {this.sR(lo-8,A);this.pc=pc+1;} return; }
  if(hi===0x70&&lo>=4){ if(lo===4){this.sA(b1);this.pc=pc+2;}
    else if(lo===5){this.ds(b1,b2);this.pc=pc+3;}
    else if(lo<8){this.ram[this.gR(lo-6)]=b1;this.pc=pc+2;}
    else {this.sR(lo-8,b1);this.pc=pc+2;} return; }
  if(hi===0x80&&lo>=5){ if(lo===5){this.ds(b2,this.dg(b1));this.pc=pc+3;}
    else if(lo<8){this.ds(b1,this.ram[this.gR(lo-6)]);this.pc=pc+2;}
    else {this.ds(b1,this.gR(lo-8));this.pc=pc+2;} return; }
  if(hi===0xA0&&lo>=6){ if(lo<8){this.ram[this.gR(lo-6)]=this.dg(b1);this.pc=pc+2;}
    else {this.sR(lo-8,this.dg(b1));this.pc=pc+2;} return; }
  if((hi===0x00||hi===0x10)&&lo>=5){ var d=(hi===0)?1:-1;
    if(lo===5){this.ds(b1,this.dg(b1)+d);this.pc=pc+2;}
    else if(lo<8){var a=this.gR(lo-6); this.ram[a]=(this.ram[a]+d)&255; this.pc=pc+1;}
    else {this.sR(lo-8,this.gR(lo-8)+d);this.pc=pc+1;} return; }
  if(hi===0xB0&&lo>=4){ var x,y;
    if(lo===4){x=A;y=b1;} else if(lo===5){x=A;y=this.dg(b1);}
    else if(lo<8){x=this.ram[this.gR(lo-6)];y=b1;} else {x=this.gR(lo-8);y=b1;}
    this.sC(x<y?1:0); this.pc=(x!==y)?pc+3+rel(b2):pc+3; return; }
  if(op===0xD5){ var v=(this.dg(b1)-1)&255; this.ds(b1,v); this.pc=v?pc+3+rel(b2):pc+3; return; }
  if(hi===0xD0&&lo>=8){ var v=(this.gR(lo-8)-1)&255; this.sR(lo-8,v); this.pc=v?pc+2+rel(b1):pc+2; return; }
  if(op===0xC0){this.push(this.dg(b1));this.pc=pc+2;return;}
  if(op===0xD0){this.ds(b1,this.pop());this.pc=pc+2;return;}
  if(hi===0xC0&&lo>=5){ var t;
    if(lo===5){t=this.dg(b1);this.ds(b1,A);this.sA(t);this.pc=pc+2;}
    else if(lo<8){var a=this.gR(lo-6);t=this.ram[a];this.ram[a]=A;this.sA(t);this.pc=pc+1;}
    else {t=this.gR(lo-8);this.sR(lo-8,A);this.sA(t);this.pc=pc+1;} return; }
  if(op===0xD6||op===0xD7){ var a=this.gR(op-0xD6),t=this.ram[a];
    this.ram[a]=(t&0xF0)|(A&15); this.sA((A&0xF0)|(t&15)); this.pc=pc+1; return; }
  if(op===0xC2){this.bs(b1,0);this.pc=pc+2;return;}
  if(op===0xD2){this.bs(b1,1);this.pc=pc+2;return;}
  if(op===0xB2){this.bs(b1,1-this.bg(b1));this.pc=pc+2;return;}
  if(op===0xA2){this.sC(this.bg(b1));this.pc=pc+2;return;}
  if(op===0x92){this.bs(b1,this.C());this.pc=pc+2;return;}
  if(op===0x72){this.sC(this.C()|this.bg(b1));this.pc=pc+2;return;}
  if(op===0xA0){this.sC(this.C()|(1-this.bg(b1)));this.pc=pc+2;return;}
  if(op===0x82){this.sC(this.C()&this.bg(b1));this.pc=pc+2;return;}
  if(op===0xB0){this.sC(this.C()&(1-this.bg(b1)));this.pc=pc+2;return;}
  this.pc=pc+1;
};
