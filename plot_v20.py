#!/usr/bin/env python3
"""Compares the built-in arbitrary curves of V1.5 and V2.0.

Shows what the correction from section 34 achieves: the third curve was a
noisy sampling of the same waveform that already sits in the ROM as a
computed table.

    python3 plot_v20.py     ->  PM5139_Waveform3_V15_vs_V20.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LENGTH = 1024
SIG_ARB3  = bytes.fromhex('020205090d22202c374547')   # noisy, in V1.5
SIG_CLEAN = bytes.fromhex('00000009131c252e3740')     # the computed level table

def fetch(path, sig):
    r = open(path, 'rb').read()
    p = r.find(sig)
    return list(r[p:p+LENGTH]) if p >= 0 else None

def direction_changes(v):
    return sum(1 for i in range(1, len(v)-1)
               if (v[i]-v[i-1]) * (v[i+1]-v[i]) < 0)

old = fetch('M27512_PM5139_V15.bin', SIG_ARB3)      # noisy
ref = fetch('M27512_PM5139_V15.bin', SIG_CLEAN)     # the template
new = fetch('M27512_PM5139_V20.bin', SIG_CLEAN)     # in V2.0 also curve 3

fig, ax = plt.subplots(3, 2, figsize=(15, 10))
fig.suptitle('Philips PM5139 - built-in arbitrary curve 3: V1.5 against V2.0',
             fontsize=14)

ax[0][0].plot(old, lw=0.7, color='tab:red')
ax[0][0].set_title('V1.5 - noisy sampling\n%d direction changes'
                   % direction_changes(old))
ax[0][1].plot(new, lw=0.7, color='tab:green')
ax[0][1].set_title('V2.0 - computed curve\n%d direction changes'
                   % direction_changes(new))
for a in ax[0]:
    a.set_ylim(-10, 265); a.set_xlim(0, LENGTH)

# the detail in which the noise is most visible
LO, HI = 180, 320
ax[1][0].plot(range(LO, HI), old[LO:HI], lw=1.1, color='tab:red', marker='.', ms=3)
ax[1][0].set_title('detail %d...%d - V1.5' % (LO, HI))
ax[1][1].plot(range(LO, HI), new[LO:HI], lw=1.1, color='tab:green', marker='.', ms=3)
ax[1][1].set_title('the same detail - V2.0')
for a in ax[1]:
    a.set_xlim(LO, HI); a.grid(alpha=.3)

# deviation from the computed template
d_old = [old[i]-ref[i] for i in range(LENGTH)]
ax[2][0].plot(d_old, lw=0.6, color='tab:red')
ax[2][0].set_title('V1.5: deviation from the computed table '
                   '(min %d, max %d)' % (min(d_old), max(d_old)))
ax[2][0].set_ylim(-25, 25); ax[2][0].axhline(0, color='k', lw=.5)
ax[2][1].plot([0]*LENGTH, lw=0.6, color='tab:green')
ax[2][1].set_title('V2.0: deviation zero throughout')
ax[2][1].set_ylim(-25, 25); ax[2][1].axhline(0, color='k', lw=.5)
for a in ax[2]:
    a.set_xlim(0, LENGTH); a.grid(alpha=.3)

plt.tight_layout()
plt.savefig('PM5139_Waveform3_V15_vs_V20.png', dpi=110)
print('written: PM5139_Waveform3_V15_vs_V20.png')
print('V1.5: %d direction changes, deviation %d..%d'
      % (direction_changes(old), min(d_old), max(d_old)))
print('V2.0: %d direction changes, deviation 0..0' % direction_changes(new))
