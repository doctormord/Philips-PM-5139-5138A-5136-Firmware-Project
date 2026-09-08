// Decodes the digit row 3Eh..43h of the display image that is sent.
// The base encoding was measured in section 15; bit 1 (02h) is an extra
// segment (the separator), and 02h on its own is an empty position.
const DIGIT={0xED:'0',0x0C:'1',0x79:'2',0x3D:'3',0x9C:'4',
              0xB5:'5',0xF5:'6',0x2C:'7',0xFD:'8',0xBD:'9'};
function digit(b){
  if(b===0x00) return ' ';
  if(b===0x02) return ' ';                  // empty, only the extra segment
  const z=DIGIT[b & ~0x02 & 0xFF];
  const p=(b & 0x02) ? '.' : '';
  return z===undefined ? '?'+b.toString(16) : z+p;
}
function row(frame){                         // frame = 20 bytes from c.frame
  return Array.from(frame.slice(14,19)).map(digit).join('');
}
module.exports={digit,row,DIGIT};
if(require.main===module){
  const samples=[['decade 5',[0x00,0x0e,0xed,0xed,0x02]],
                 ['decade 6',[0x00,0x0c,0xef,0xed,0xef]],
                 ['decade 7',[0x0c,0xed,0xef,0xed,0xef]],
                 ['decade 8',[0x0e,0xed,0xed,0xed,0xed]],
                 ['decade 9',[0x0c,0xef,0xed,0xed,0xed]]];
  for(const [n,b] of samples)
    console.log(n+':  '+b.map(x=>x.toString(16).padStart(2,'0')).join(' ')+
                '   ->   "'+b.map(digit).join('')+'"');
}
