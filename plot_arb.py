#!/usr/bin/env python3
"""Plots the six curves of an arbitrary EEPROM image.

    python3 plot_arb.py [image.bin] [output.png]
"""
import sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

RECORD, DATA = 1280, 0x100

def unpack(d, at):
    w = []
    for i in range(0, RECORD, 5):
        b = d[at+i:at+i+5]
        for k in range(4):
            w.append((b[k] << 2) | ((b[4] >> (2*k)) & 3))
    return w

def main(argv):
    path   = argv[1] if len(argv) > 1 else 'D310_image_V20.bin'
    target = argv[2] if len(argv) > 2 else 'PM5139_ARB_V20.png'
    d = open(path, 'rb').read()
    n = d[0] & 0x0F
    fig, ax = plt.subplots(3, 2, figsize=(14, 8))
    fig.suptitle('Philips PM5139 - arbitrary memory (%s), %d slots'
                 % (path, n), fontsize=13)
    for k in range(1, n+1):
        a = ax[(k-1)//2][(k-1) % 2]
        w = unpack(d, DATA + (k-1)*RECORD)
        y = [v - 512 for v in w]              # 512 is the zero
        a.plot(y, lw=.8)
        a.set_title('slot %d   %+d ... %+d   (%.2f Vpp)'
                    % (k, min(y), max(y), (max(y)-min(y))/1022*20), fontsize=10)
        a.set_ylim(-560, 560); a.grid(alpha=.3); a.axhline(0, color='k', lw=.4)
    plt.tight_layout()
    plt.savefig(target, dpi=110)
    print('written:', target)

if __name__ == '__main__':
    main(sys.argv)
