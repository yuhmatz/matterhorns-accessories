"""Pure-Python DSP primitives for ACHILLES.

Why pure Python?  The deployment box runs Python 3.14, where pip only accepts
version-independent wheels — numpy/scipy builds were the reason
openWakeWord/onnxruntime were abandoned.  Wake gating and speaker
verification only touch ~1-2 s of 16 kHz audio at a time, so an O(n log n)
pure-Python FFT is fast enough (a few hundred ms worst case) and keeps the
dependency surface at zero.
"""
from __future__ import annotations

import cmath
import math
from typing import Sequence


def rms(samples: Sequence[float]) -> float:
    """Root-mean-square level of a float sample block (range [-1, 1])."""
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def pcm16_to_float(data: bytes) -> list[float]:
    """Convert little-endian signed 16-bit PCM bytes to floats in [-1, 1]."""
    n = len(data) // 2
    out = [0.0] * n
    for i in range(n):
        lo = data[2 * i]
        hi = data[2 * i + 1]
        v = lo | (hi << 8)
        if v >= 0x8000:
            v -= 0x10000
        out[i] = v / 32768.0
    return out


def fft(x: Sequence[complex]) -> list[complex]:
    """Iterative radix-2 Cooley-Tukey FFT. len(x) must be a power of two."""
    n = len(x)
    if n & (n - 1):
        raise ValueError(f"FFT length must be a power of two, got {n}")
    a = list(x)
    # bit-reversal permutation
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wlen = cmath.exp(1j * ang)
        for start in range(0, n, length):
            w = 1.0 + 0.0j
            half = length >> 1
            for k in range(start, start + half):
                u = a[k]
                v = a[k + half] * w
                a[k] = u + v
                a[k + half] = u - v
                w *= wlen
        length <<= 1
    return a


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def power_spectrum(frame: Sequence[float], nfft: int) -> list[float]:
    """|FFT|^2 / nfft for the first nfft//2+1 bins of a (padded) frame."""
    padded = list(frame) + [0.0] * (nfft - len(frame))
    spec = fft([complex(s, 0.0) for s in padded])
    return [(abs(c) ** 2) / nfft for c in spec[: nfft // 2 + 1]]


def hz_to_mel(hz: float) -> float:
    return 2595.0 * math.log10(1.0 + hz / 700.0)


def mel_to_hz(mel: float) -> float:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def mel_filterbank(n_filters: int, nfft: int, sample_rate: int,
                   fmin: float = 0.0, fmax: float | None = None) -> list[list[float]]:
    """Triangular mel filterbank matrix: n_filters x (nfft//2+1)."""
    fmax = fmax or sample_rate / 2.0
    mel_points = [hz_to_mel(fmin) + i * (hz_to_mel(fmax) - hz_to_mel(fmin)) / (n_filters + 1)
                  for i in range(n_filters + 2)]
    bins = [int(math.floor((nfft + 1) * mel_to_hz(m) / sample_rate)) for m in mel_points]
    n_bins = nfft // 2 + 1
    fbank = [[0.0] * n_bins for _ in range(n_filters)]
    for m in range(1, n_filters + 1):
        left, center, right = bins[m - 1], bins[m], bins[m + 1]
        for k in range(left, center):
            if center != left and 0 <= k < n_bins:
                fbank[m - 1][k] = (k - left) / (center - left)
        for k in range(center, right):
            if right != center and 0 <= k < n_bins:
                fbank[m - 1][k] = (right - k) / (right - center)
    return fbank


def dct2(x: Sequence[float], n_out: int) -> list[float]:
    """Type-II DCT (orthogonalized), first n_out coefficients."""
    n = len(x)
    out = []
    for k in range(n_out):
        s = sum(x[i] * math.cos(math.pi * k * (2 * i + 1) / (2 * n)) for i in range(n))
        scale = math.sqrt(1.0 / (4 * n)) if k == 0 else math.sqrt(1.0 / (2 * n))
        out.append(2.0 * s * scale)
    return out


def mfcc(samples: Sequence[float], sample_rate: int = 16000,
         frame_ms: float = 25.0, hop_ms: float = 10.0,
         n_filters: int = 26, n_coeffs: int = 13) -> list[list[float]]:
    """MFCC frames for a mono float signal. Returns [n_frames][n_coeffs]."""
    frame_len = int(sample_rate * frame_ms / 1000.0)
    hop = int(sample_rate * hop_ms / 1000.0)
    if len(samples) < frame_len:
        return []
    nfft = _next_pow2(frame_len)
    fbank = mel_filterbank(n_filters, nfft, sample_rate)
    # pre-emphasis
    emphasized = [samples[0]] + [samples[i] - 0.97 * samples[i - 1] for i in range(1, len(samples))]
    hamming = [0.54 - 0.46 * math.cos(2 * math.pi * i / (frame_len - 1)) for i in range(frame_len)]
    frames_out: list[list[float]] = []
    for start in range(0, len(emphasized) - frame_len + 1, hop):
        frame = [emphasized[start + i] * hamming[i] for i in range(frame_len)]
        pspec = power_spectrum(frame, nfft)
        energies = []
        for filt in fbank:
            e = sum(f * p for f, p in zip(filt, pspec))
            energies.append(math.log(max(e, 1e-12)))
        frames_out.append(dct2(energies, n_coeffs))
    return frames_out


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
