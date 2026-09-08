var fs=require('fs'); eval(fs.readFileSync('core.js','utf8'));
var ROM=new Uint8Array(0x10000).fill(0xFF);
ROM.set(new Uint8Array(fs.readFileSync('M27512_PM5139_V13.bin')).slice(0,0xAC71),0);
function h(x){return x.toString(16).padStart(2,'0');}
var c=new CPU(ROM); c.nv.set(new Uint8Array(fs.readFileSync('PCF8570_image.bin')));
c.xram.set(new Uint8Array(fs.readFileSync('D310_image.bin')).slice(0,0x8000)); c.pc=0;
var buf=[]; c.log=[];
var ds=CPU.prototype.ds, st=CPU.prototype.step;
c.ds=function(a,v){ if(a===0x99) buf.push(v&255); ds.call(this,a,v); };
c.step=function(){ var op=this.rom[this.pc];
  if(op===0xF0){var d=this.dptr(); if(d>=0x8000){var n=(d>>8)&15; if(n&&buf.length)this.log.push([n,buf.slice()]); if(n)buf=[];}}
  st.call(this); };
for(var i=0;i<9000000;i++)c.step();
var tog=0;
function press(k){ tog^=1; c.log=[]; c.key(k,tog); for(var i=0;i<2200000;i++)c.step(); }
var F={0xED:'0',0x0C:'1',0x79:'2',0x3D:'3',0x9C:'4',0xB5:'5',0xF5:'6',0x2C:'7',0xFD:'8',0xBD:'9',0x00:' '};
function acf(){var s='';for(var k=7;k<9;k++){var b=c.frame[k];s+=(F[b&~2&255]||'?');if(b&2)s+='.';}return s;}
function row(t){
  var s9=c.log.filter(function(e){return e[0]===9;}).pop();
  var s7=c.log.filter(function(e){return e[0]===7;}).pop();
  console.log(t.padEnd(10)+' 56h/57h='+h(c.ram[0x56])+h(c.ram[0x57])+'  1Ch='+h(c.ram[0x1C])+
   ' 1Eh='+h(c.ram[0x1E])+'  AC field='+acf()+'  STR9='+(s9?s9[1].map(h).join(''):'--')+
   ' STR7='+(s7?s7[1].map(h).join(' '):'--'));
}
press(0x2A);            // knob unlocked
press(0x11);            // sine
press(0x19); press(0x19);   // select AC and switch it on
row('AC on');
for(var r=1;r<=8;r++){ c.log=[]; c.rad(1,1); for(i=0;i<2400000;i++)c.step(); row('knob '+r); }
