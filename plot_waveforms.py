#!/usr/bin/env python3
"""Plots all waveform tables of a PM5139 ROM (as in PM5139_Waveforms.png).

    python3 plot_waveforms.py [image.bin] [output.png]

Without arguments: M27512_PM5139_V20.bin -> PM5139_Waveforms_V20.png
The tables are found by signature so that the same script runs on V1.3,
V1.5 and V2.0.
"""
import sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

SIG = {   # signatures, read off V1.3; they also hit in V1.5/V2.0
 'quarter': bytes.fromhex('000000c0018002400340'),
 'haver'  : bytes.fromhex('80008000800080008000'),
 'levels' : bytes.fromhex('00000009131c252e3740'),
 'perm'   : bytes.fromhex('2923be84e16c'),
 'arb1'   : bytes.fromhex('807b76716c67625d'),
}

def find(r, sig):
    p = r.find(sig)
    return p if p >= 0 else None

def main(argv):
    path   = argv[1] if len(argv) > 1 else 'M27512_PM5139_V20.bin'
    target = argv[2] if len(argv) > 2 else 'PM5139_Waveforms_V20.png'
    r = open(path, 'rb').read()

    p_lv = find(r, SIG['levels'])
    # The three arbitrary curves lie contiguously, 1024 bytes apart
    # (A047h, A447h, A847h in V1.3). Only curve 1 is located by
    # signature — in V2.0 curve 2 carries a chirp and no longer matches.
    p_a1 = find(r, SIG['arb1'])
    p_a2 = p_a1 + 1024
    p_a3 = p_a1 + 2048
    p_q  = find(r, SIG['quarter'])
    p_h  = find(r, SIG['haver'])
    p_pm = find(r, SIG['perm'])

    w16 = [(r[p_q+2*i] << 8) | r[p_q+2*i+1] for i in range(256)] if p_q else []
    # 12-bit values, left-aligned in 16-bit words: >>4 gives 0..2048
    w12 = [((r[p_h+2*i] << 8) | r[p_h+2*i+1]) >> 4 for i in range(512)] if p_h else []

    fig, ax = plt.subplots(4, 2, figsize=(14, 11))
    fig.suptitle('Philips PM5139 - waveform tables in the ROM (%s)' % path,
                 fontsize=13)

    ax[0][0].plot(w16); ax[0][0].set_title('quarter sine, 256 x 16 bit (0...7FC0h)')
    full = w16 + w16[::-1] + [-x for x in w16] + [-x for x in w16[::-1]]
    ax[0][1].plot(full, color='tab:orange')
    ax[0][1].set_title('mirrored from it: a full sine (1024 points)')

    ax[1][0].plot(w12, color='tab:green')
    ax[1][0].set_title('haversine edge, 512 x 12 bit (800h...0)')
    ax[1][1].plot(w12 + w12[::-1], color='tab:green')
    ax[1][1].set_title('mirrored: the full haversine')

    ax[2][0].plot(list(r[p_lv:p_lv+1024]), color='tab:red', lw=.8)
    ax[2][0].set_title('ten sine arcs, each 3.33 dB smaller (computed)')
    ax[2][1].plot(list(r[p_pm:p_pm+256]), '.', ms=2, color='tab:purple')
    ax[2][1].set_title('permutation of all 256 values (RAM test)')

    ax[3][0].plot(list(r[p_a1:p_a1+1024]), lw=1.4, label='curve 1')
    ax[3][0].plot(list(r[p_a2:p_a2+1024]), lw=.8, label='curve 2', alpha=.7)
    ax[3][0].legend(fontsize=8)
    ax[3][0].set_title('built-in arbitrary curves 1 and 2 (pulse train with needle pulses)')
    d3 = list(r[p_a3:p_a3+1024])
    changes = sum(1 for i in range(1, 1023) if (d3[i]-d3[i-1])*(d3[i+1]-d3[i]) < 0)
    ax[3][1].plot(d3, lw=.8, color='tab:brown')
    ax[3][1].set_title('built-in arbitrary curve 3 - %d direction changes' % changes)

    plt.tight_layout()
    plt.savefig(target, dpi=105)
    print('written: %s   (curve 3: %d direction changes)' % (target, changes))

if __name__ == '__main__':
    main(sys.argv)
