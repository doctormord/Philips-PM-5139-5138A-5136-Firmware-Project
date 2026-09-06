import analyze2, re, difflib
RE=re.compile(r'X[0-9A-F]{4}h')
def seq(p):
    S=sorted(p.insn); toks=[]; 
    for a in S:
        l,t,tg,k=p.insn[a][:4]
        if tg is not None:
            d=tg-a
            t=RE.sub('@%+d'%d if abs(d)<0x80 else '@ABS', t)
        if t.startswith('MOV   DPTR'): t='MOV   DPTR,#PTR'
        toks.append(t)
    return S,toks
A=analyze2.load('13'); B=analyze2.load('15')
SA,TA=seq(A); SB,TB=seq(B)
sm=difflib.SequenceMatcher(None,TA,TB,autojunk=False)
ops=sm.get_opcodes()
same=sum(j-i for tag,i,j,_,_ in ops if tag=='equal')
print('Instruktionen V13=%d V15=%d, identisch(strukturell)=%d (%.1f%%)'%(len(TA),len(TB),same,same*100/len(TA)))
blocks=[o for o in ops if o[0]!='equal']
print('Unterschiedliche Blöcke: %d'%len(blocks))
f=open('blockdiff.txt','w')
for tag,i1,i2,j1,j2 in blocks:
    a0=SA[i1] if i1<len(SA) else 0xFFFF; b0=SB[j1] if j1<len(SB) else 0xFFFF
    f.write('\n===== %s  V1.3 %04X..%04X (%d Instr.)  <->  V1.5 %04X..%04X (%d Instr.) =====\n'
            %(tag,a0,SA[i2-1] if i2>i1 else a0,i2-i1,b0,SB[j2-1] if j2>j1 else b0,j2-j1))
    for a in SA[i1:i2]: f.write('  - %04X: %s\n'%(a,A.insn[a][1]))
    for b in SB[j1:j2]: f.write('  + %04X: %s\n'%(b,B.insn[b][1]))
f.close()
big=sorted(blocks,key=lambda o:-(max(o[2]-o[1],o[4]-o[3])))
print('\ngrößte Blöcke:')
for tag,i1,i2,j1,j2 in big[:30]:
    print('  %-8s V13 %04X (%d Instr) <-> V15 %04X (%d Instr)'%(tag,SA[i1] if i1<len(SA) else 0,i2-i1,SB[j1] if j1<len(SB) else 0,j2-j1))
