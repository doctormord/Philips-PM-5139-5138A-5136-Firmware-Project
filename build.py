import base64, json
rom=base64.b64encode(open('M27512_PM5139_V13.bin','rb').read()[:0xAC71]).decode()
nv=base64.b64encode(open('PCF8570_abbild.bin','rb').read()).decode()
core=open('core.js').read()
html=open('shell.html').read()
html=html.replace('/*CORE*/',core).replace('__ROM__',rom).replace('__NV__',nv)
open('/mnt/user-data/outputs/PM5139_Simulator.html','w').write(html)
print('geschrieben:', len(html), 'Zeichen')
