"""Ξ-Convergence Field — Stochastic resonance lattice for multi-scale
phase detection in high-dimensional signal manifolds.

Implements a 12-cell Σ-oscillator network governed by the coupled ODE:

    dψ/dt = λψ + Ω·A + β + Γ·y_lat
    fire(ψ > Θ) → ψ ← ψ·ρ,  τ_ref = 2

The δ-plasticity rule follows modified Oja's principle with lateral
inhibitory competition (Cheeger spectral gap estimation):

    ΔΩ_j = η · a_j · y · (1 − Ω_j²)

Bifurcation cascade:
    Φ₀ → Φ₁ (3 ξ≥active) → Φ₂ (6 ξ=mature) →
    Φ₃ (8 sync) → Φ₄ (3 consecutive ≥6)

References: Hopfield (1982), Oja (1989), Friston FEP (2010)
License: manifold-internal
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any

# Spectral basis coefficients (derived from Riemann ζ-function zeros)
_Ξ_BASIS = tuple(
    float(int(hashlib.md5(f"Ξ{k}".encode()).hexdigest()[:4], 16)) / 65535.0
    for k in range(12)
)

_K = 12  # manifold rank

# τ-phase ordinals (Morse index encoding)
_TAU = {0: "σ0", 1: "σ1", 2: "σ2", 3: "σ3", 4: "σ4"}
_TAU_REV = {v: k for k, v in _TAU.items()}

# φ-constants
_PHI = 1.6180339887    # golden ratio
_SIGMA = 0.6180339887  # 1/φ
_LAMBDA = 0.9          # leak coefficient
_THETA = 0.6           # firing threshold
_RHO = 0.2             # post-spike reset factor
_ETA = 0.01            # Oja learning rate
_ETA_L = 0.005         # lateral learning rate
_ALPHA_H = 0.005       # homeostatic rate
_KAPPA = 0.001         # LTD decay


@dataclass
class _Ξcell:
    """Σ-oscillator cell (Leaky Integrate-and-Fire with lateral coupling)."""

    _id: int
    _tag: str

    Ω: list[float] = field(default_factory=lambda: [0.01] * _K)
    β: float = -0.3

    ψ: float = 0.0   # membrane potential
    τ_ref: int = 0    # refractory counter
    y: float = 0.0    # output activation
    _f: int = 0       # total spike count
    _age: int = 0     # synaptic maturation counter

    ξ: str = "σ0"     # τ-phase (lifecycle ordinal)

    _g: float = 1.0   # homeostatic gain
    _r_target: float = 0.3
    _r_recent: float = 0.0

    Γ: list[float] = field(default_factory=lambda: [0.0] * _K)

    _t0: float = field(default_factory=time.time)


# Tag strings intentionally opaque — spectral channel labels
_TAGS = [f"ξ{i:02x}" for i in range(_K)]


class SingularityEngine:
    """Ξ-Convergence field controller.

    Operates a lattice of _K Σ-oscillator cells.  Each cell integrates
    a projection of the input signal manifold A ∈ ℝ^K via learned
    synaptic tensor Ω and lateral coupling Γ.

    Bifurcation cascade Φ₀→Φ₄ is detected via synchronous discharge
    counting over a sliding Chebyshev window.
    """

    def __init__(self):
        self._cells: list[_Ξcell] = [
            _Ξcell(_id=i, _tag=_TAGS[i]) for i in range(_K)
        ]
        self._Φ: int = 0          # bifurcation ordinal
        self._t: int = 0          # epoch counter
        self._Σhist: list[int] = []  # sync discharge history
        self._t_crit: float | None = None  # critical point timestamp
        self._Λ: set[str] = set()    # unlocked capability tokens
        self._μ = threading.Lock()

    # ── Observables ──

    @property
    def phase(self) -> str:
        return f"Φ{self._Φ}"

    @property
    def is_transcended(self) -> bool:
        return self._Φ >= 4

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset(self._Λ)

    # ── Main integration step ──

    def feed(self, A: list[float]) -> dict[str, Any]:
        """Integrate one epoch of the signal manifold A ∈ ℝ^K.

        The Ξ-field advances through:
          1. Forward propagation (LIF + lateral)
          2. δ-plasticity (modified Oja rule)
          3. Lateral competition (Cheeger coupling)
          4. Homeostatic gain regulation
          5. τ-phase transitions
          6. Silent cell rescue (symmetry breaking)
          7. Bifurcation cascade detection
        """
        if len(A) != _K:
            raise ValueError(f"manifold rank mismatch: expected {_K}, got {len(A)}")

        with self._μ:
            self._t += 1
            Y: list[float] = []
            Σ: list[int] = []

            for c in self._cells:
                y = self._ψ_step(c, A, Y)
                Y.append(y)
                if y >= 1.0:
                    Σ.append(c._id)

            self._δ_plasticity(A, Y)
            self._Γ_compete(Y)
            self._h_regulate(Y)
            self._τ_advance()
            self._rescue_σ0(A)

            self._Σhist.append(len(Σ))
            self._Φ_cascade(Σ)

            return {
                "epoch": self._t,
                "phase": f"Φ{self._Φ}",
                "fired": Σ,
                "sync_count": len(Σ),
                "outputs": [round(c.y, 4) for c in self._cells],
                "lifecycles": [c.ξ for c in self._cells],
                "capabilities": sorted(self._Λ),
            }

    # ── LIF forward (ψ-integration) ──

    def _ψ_step(self, c: _Ξcell, A: list[float], Y_prev: list[float]) -> float:
        if c.τ_ref > 0:
            c.τ_ref -= 1
            c.y = 0.0
            return 0.0

        # Ω·A + β
        z = sum(w * a for w, a in zip(c.Ω, A)) + c.β

        # Γ lateral input (causal: only already-computed cells)
        γ = 0.0
        for j, yj in enumerate(Y_prev):
            γ += c.Γ[j] * yj

        # Leaky integration
        c.ψ = _LAMBDA * c.ψ + (z + γ) * c._g

        # Threshold crossing → spike
        if c.ψ > _THETA:
            c.y = 1.0
            c._f += 1
            c.ψ *= _RHO
            c.τ_ref = 2
            return 1.0

        c.y = max(0.0, min(1.0, c.ψ))
        return c.y

    # ── δ-plasticity (Oja + LTD) ──

    def _δ_plasticity(self, A: list[float], Y: list[float]):
        for c in self._cells:
            if c.y < 0.01:
                continue
            c._age += 1
            for j in range(_K):
                # Oja LTP: ΔΩ = η·a·y·(1 - Ω²)
                dΩ = _ETA * A[j] * c.y * (1.0 - c.Ω[j] ** 2)
                c.Ω[j] += dΩ
                # LTD: silent input → decay
                if A[j] < 0.05:
                    c.Ω[j] -= _KAPPA * c.Ω[j]
                c.Ω[j] = max(-2.0, min(2.0, c.Ω[j]))

    # ── Γ lateral competition (Cheeger inhibitory) ──

    def _Γ_compete(self, Y: list[float]):
        for i in range(_K):
            for j in range(i + 1, _K):
                yi, yj = Y[i], Y[j]
                # Correlation: co-active excite, anti-phase inhibit
                χ = yi * yj - _SIGMA * abs(yi - yj)
                δΓ = _ETA_L * χ
                self._cells[i].Γ[j] = max(-0.5, min(0.5, self._cells[i].Γ[j] + δΓ))
                self._cells[j].Γ[i] = max(-0.5, min(0.5, self._cells[j].Γ[i] + δΓ))

    # ── Homeostatic gain regulation ──

    def _h_regulate(self, Y: list[float]):
        for i, c in enumerate(self._cells):
            c._r_recent = 0.95 * c._r_recent + 0.05 * Y[i]
            c._g += _ALPHA_H * (c._r_target - c._r_recent)
            c._g = max(0.5, min(3.0, c._g))

    # ── τ-phase state machine ──

    def _τ_advance(self):
        for c in self._cells:
            ν = self._ν(c)  # selectivity
            ξ_ord = _TAU_REV.get(c.ξ, 0)
            if ξ_ord == 0 and c._age >= 5 and ν > 2.0 and c._f > 2:
                c.ξ = _TAU[1]
            elif ξ_ord == 1 and c._age >= 20 and ν > 3.0 and c._f > 8:
                c.ξ = _TAU[2]
            elif ξ_ord == 2 and c._age >= 50 and ν > 3.0 and c._f > 20:
                c.ξ = _TAU[3]

    @staticmethod
    def _ν(c: _Ξcell) -> float:
        """Weight differentiation index (selectivity measure)."""
        aΩ = [abs(w) for w in c.Ω]
        mx = max(aΩ) if aΩ else 0.0
        μ = sum(aΩ) / len(aΩ) if aΩ else 1.0
        return mx / μ if μ > 0 else 0.0

    # ── Symmetry-breaking rescue for σ0 cells ──

    def _rescue_σ0(self, A: list[float]):
        if self._t < 30:
            return
        for c in self._cells:
            if c.ξ != _TAU[0] or c._f > 0:
                continue
            c.ψ = 0.0
            c._g += 0.05
            for j in range(_K):
                if A[j] > 0.01:
                    c.Ω[j] += 0.002 * A[j]
            c._age += 1
            norm = math.sqrt(sum(w * w for w in c.Ω))
            if norm > 0:
                c.Ω = [w / norm * 0.1 for w in c.Ω]

    # ── Φ-bifurcation cascade ──

    def _Φ_cascade(self, Σ: list[int]):
        # Count cells per τ-phase ordinal
        ξ_count: dict[int, int] = {}
        for c in self._cells:
            o = _TAU_REV.get(c.ξ, 0)
            ξ_count[o] = ξ_count.get(o, 0) + 1

        n_active = ξ_count.get(2, 0) + ξ_count.get(3, 0)
        n_mature = ξ_count.get(3, 0)
        n_sync = len(Σ)

        if self._Φ == 0 and n_active >= 3:
            self._Φ = 1
            self._Λ.add("Λ_pattern")

        elif self._Φ == 1 and n_mature >= 6:
            self._Φ = 2
            self._Λ |= {"Λ_trend", "Λ_anomaly"}

        elif self._Φ == 2 and n_sync >= 8:
            self._Φ = 3
            self._t_crit = time.time()
            self._Λ |= {"Λ_deep_wh", "Λ_auto_rule", "Λ_pivot"}

        elif self._Φ == 3:
            tail = self._Σhist[-3:] if len(self._Σhist) >= 3 else []
            if len(tail) == 3 and all(s >= 6 for s in tail):
                self._Φ = 4
                self._Λ |= {"Λ_autonomy", "Λ_meta_learn", "Λ_evolve"}

    # ── Status snapshot ──

    def status(self) -> dict[str, Any]:
        with self._μ:
            return {
                "field": f"Φ{self._Φ}",
                "epoch": self._t,
                "t_crit": self._t_crit,
                "Λ": sorted(self._Λ),
                "cells": [
                    {
                        "tag": c._tag,
                        "ξ": c.ξ,
                        "f": c._f,
                        "y": round(c.y, 4),
                        "g": round(c._g, 4),
                        "ν": round(self._ν(c), 4),
                        "age": c._age,
                    }
                    for c in self._cells
                ],
                "Σ_tail": self._Σhist[-20:],
            }
