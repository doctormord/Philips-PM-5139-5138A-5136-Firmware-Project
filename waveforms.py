#!/usr/bin/env python3
"""Generates waveforms for the PM5139.

Two destinations with different formats:

* **ROM curves** (the three built-in arbitrary tables): 1024 points of
  8 bit, raw, one after another.
* **EEPROM curves** (arbitrary memory D310): 1024 points of 10 bit,
  packed four values into five bytes, 512 being the zero.

All curves close cyclically: the value after the last point equals the
first one again, so that no jump occurs when repeating.
"""
import math

N = 1024


def _quantise(values, lo, hi):
    """Scale symmetrically about the middle.

    Important: do not stretch min->lo and max->hi, or the zero line of
    the curve shifts. Instead the larger of the two magnitudes is put on
    full scale, so that the natural zero of the waveform also sits on the
    zero of the converter. An asymmetric curve then simply drives only
    one half-wave to full scale — the amplitude is set on the instrument
    anyway."""
    middle = (lo + hi) / 2
    peak = (hi - lo) / 2
    largest = max(abs(min(values)), abs(max(values)))
    if largest == 0:
        return [round(middle)] * len(values)
    f = peak / largest
    return [max(lo, min(hi, round(middle + v * f))) for v in values]


def chirp(p0=1.0, p1=40.0):
    """Logarithmic chirp: the instantaneous frequency grows from p0 to p1
    periods per pass. The final phase is rounded to a multiple of 2*pi so
    that the curve stays cyclic."""
    k = p1 / p0
    # The total number of periods is the integral over the instantaneous
    # frequency. To keep the curve cyclic, the phase is stretched
    # afterwards so that whole periods come out at the end.
    total = p0 * (k - 1) / math.log(k)
    corr = round(total) / total
    y = []
    for i in range(N):
        x = i / N
        phase = 2 * math.pi * p0 * (k ** x - 1) / math.log(k) * corr
        y.append(math.sin(phase))
    return y


def ringing(periods=12, q=6.0):
    """Step response of a resonant circuit: a step, then a decaying
    oscillation. The decay is chosen so that practically nothing is left
    at the end.

    The jump from the last to the first point is **intended** here — it
    is the step edge that triggers the ringing."""
    y = []
    for i in range(N):
        x = i / N
        envelope = math.exp(-q * x)
        y.append(envelope * math.cos(2 * math.pi * periods * x))
    return y


def ecg():
    """A schematic ECG trace: P wave, QRS complex, T wave. The positions
    are given as fractions of the cycle."""
    def gauss(x, middle, width, height):
        return height * math.exp(-((x - middle) / width) ** 2)
    y = []
    for i in range(N):
        x = i / N
        v  = gauss(x, 0.18, 0.030, 0.12)      # P wave
        v += gauss(x, 0.36, 0.008, -0.18)     # Q
        v += gauss(x, 0.39, 0.010,  1.00)     # R
        v += gauss(x, 0.42, 0.012, -0.28)     # S
        v += gauss(x, 0.58, 0.050,  0.28)     # T wave
        y.append(v)
    return y


def multitone(tones=(7, 11, 17, 23, 31)):
    """The sum of several sines with mutually prime period counts — for
    intermodulation and distortion measurements. Equal amplitudes, phases
    staggered so that the crest factor stays small (Schroeder phases)."""
    y = []
    for i in range(N):
        x = i / N
        s = 0.0
        for k, p in enumerate(tones):
            phi = math.pi * k * (k + 1) / len(tones)
            s += math.sin(2 * math.pi * p * x + phi)
        y.append(s)
    return y


# ----------------------------------------------------------------- output

def as_rom(values, stretch=False):
    """1024 bytes, 8 bit. Zero-centred like as_eeprom; see there."""
    if stretch:
        mn, mx = min(values), max(values)
        values = [2 * (v - mn) / (mx - mn) - 1 for v in values] if mx > mn else values
    return bytes(_quantise(values, 0, 255))


def as_eeprom(values, stretch=False):
    """1280 bytes: 1024 values of 10 bit, four packed into five bytes.
    Value range 1..1023, 512 being the zero (section 32).

    The default is **zero-centred**: the larger of the two magnitudes
    goes to full scale, and the natural zero of the waveform sits on the
    zero of the converter. That way the curve carries its DC reference
    within itself and stays right at every amplitude.

    `stretch=True` uses the full value range instead. For one-sided
    shapes that gives up to one bit more resolution, but it shifts the
    baseline by an amount that **scales with the amplitude** — while the
    offset control of the instrument adds a fixed voltage and would have
    to be readjusted on every change of amplitude. The loss from zero
    centring is 0.2 to 1 bit, i.e. about 1.6 quantisation steps; the
    noise of the analogue path already amounted to 16 steps in the
    original that was read out. So the zero centring costs practically
    nothing."""
    if stretch:
        mn, mx = min(values), max(values)
        values = [2 * (v - mn) / (mx - mn) - 1 for v in values] if mx > mn else values
    w = _quantise(values, 1, 1023)
    out = bytearray()
    for i in range(0, N, 4):
        group = w[i:i+4]
        extra = 0
        for k, v in enumerate(group):
            out.append((v >> 2) & 0xFF)
            extra |= (v & 3) << (2 * k)
        out.append(extra)
    return bytes(out)


def sinc(lobes=8):
    """A band-limited impulse, sin(x)/x. Shows the transmission bandwidth
    and overshoot; the main lobe sits in the middle of the cycle."""
    y = []
    for i in range(N):
        x = (i / N - 0.5) * 2 * lobes * math.pi
        y.append(1.0 if x == 0 else math.sin(x) / x)
    return y


def rectified():
    """A full-wave rectified sine — two half arcs per pass. The same
    shape that sat in slot 5 of the EEPROM that was read out, computed
    here instead of sampled."""
    return [abs(math.sin(2 * math.pi * i / N)) for i in range(N)]


def staircase(steps=16):
    """An even staircase from -1 to +1 and back, bipolar, so that the
    converter is driven in both directions. For linearity and resolution
    checks."""
    y = []
    for i in range(N):
        x = i / N
        k = int(x * 2 * steps)
        k = k if k < steps else (2 * steps - 1 - k)
        y.append(2 * k / (steps - 1) - 1)
    return y


CURVES = {'chirp': chirp, 'ringing': ringing, 'ecg': ecg, 'multitone': multitone,
          'sinc': sinc, 'rectified': rectified, 'staircase': staircase}

if __name__ == '__main__':
    for name, f in CURVES.items():
        v = f()
        r, e = as_rom(v), as_eeprom(v)
        edge = abs(r[0] - r[-1])
        print('%-10s ROM %d bytes (min %d max %d), EEPROM %d bytes, '
              'jump end->start %d of 255'
              % (name, len(r), min(r), max(r), len(e), edge))
