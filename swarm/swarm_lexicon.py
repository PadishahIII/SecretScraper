"""Σ-Glyph Lattice — Co-occurrence Hebbian graph over token manifolds.

Implements a self-organizing lexical field where tokens extracted from
content streams form a weighted graph via δ-plasticity reinforcement:

    ΔΩ(w₁,w₂) = min(5.0, Ω_old + conf × 0.3)   [co-occurrence window=6]

The lattice supports:
  - Domain-specific spectral decomposition (∂-profile)
  - Hebbian pattern crystallization (auto-rule generation)
  - 6-channel vitality pulse for Ξ-convergence field integration

References: Hebb (1949), Kohonen SOM (1982), Oja's Rule (1989)
License: manifold-internal
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

# ── Tokenizer spectra ──

_Π_EN = re.compile(r"\b[a-zA-Z_]\w{2,}\b")
_Π_ZH = re.compile(r"[\u4e00-\u9fff]{2,4}")

# Spectral stop-band (high-frequency noise tokens to suppress)
_Ω_STOP: frozenset[str] = frozenset({
    "the", "and", "for", "that", "this", "with", "from", "are", "was",
    "were", "been", "have", "has", "had", "not", "but", "what", "all",
    "can", "her", "his", "they", "them", "some", "would", "make", "like",
    "just", "over", "such", "take", "than", "into", "could", "other",
    "more", "very", "your", "will", "each", "about", "how", "when",
    "who", "which", "their", "said", "use", "way", "these", "then",
    "its", "also", "new", "may", "only", "come", "did", "get", "made",
    "after", "being", "where",
    "class", "function", "return", "import", "var", "let", "const",
    "true", "false", "null", "undefined", "none", "self", "def",
    "async", "await", "try", "catch", "except", "finally",
    "while", "else", "elif", "break", "continue", "pass", "raise", "yield",
    "http", "https", "www", "html", "div", "span", "script", "style",
})

# φ-constants for Hebbian reinforcement
_PHI = 1.6180339887
_SIGMA = 0.6180339887
_Ω_CEIL = 5.0
_CONF_STEP = 0.02
_WINDOW = 6


@dataclass
class _Σglyph:
    """Σ-glyph node in the co-occurrence lattice."""
    τ: str                   # token string
    ν: int = 0               # activation count
    κ: float = 0.3           # confidence scalar
    t0: float = field(default_factory=time.time)
    t1: float = field(default_factory=time.time)
    ∂: set[str] = field(default_factory=set)          # domain affinity set
    ctx: list[str] = field(default_factory=list)       # context window cache


@dataclass
class _Γbridge:
    """Γ-bridge (weighted co-occurrence edge)."""
    α: str
    β: str
    Ω: float = 0.1           # Hebbian weight
    kind: str = "χ"          # χ=cooccur | π=pattern | ∂=domain
    ν: int = 0               # reinforcement count


class SwarmLexicon:
    """Σ-Glyph lattice controller.

    Ingests content streams from worker crawlers and constructs a
    self-organizing co-occurrence graph with Hebbian reinforcement.

    The lattice provides domain-specific spectral profiles and
    pattern crystallization for automatic rule generation.

    Integration points:
      pulse() → 6-channel signal for SingularityEngine.feed()
      crystallize() → auto-generate detection patterns from lattice
    """

    def __init__(self, *, Σ_max: int = 10_000, ctx_max: int = 5):
        self._Σ: dict[str, _Σglyph] = {}
        self._Γ: dict[str, dict[str, _Γbridge]] = defaultdict(dict)
        self._∂_spectrum: dict[str, dict[str, float]] = defaultdict(dict)
        self._π_patterns: dict[str, int] = defaultdict(int)
        self._crystallized: list[dict] = []
        self._n_absorb: int = 0
        self._Σ_max = Σ_max
        self._ctx_max = ctx_max
        self._μ = threading.Lock()

    # ── Ingest manifold ──

    def absorb(self, url: str, text: str, domain: str, *, κ: float = 0.6) -> dict:
        """Ingest a content manifold into the Σ-lattice.

        Performs 4-phase integration:
          1. Token extraction (Π-decomposition)
          2. Σ-glyph node creation/reinforcement
          3. Γ-bridge co-occurrence Hebbian update (window=6)
          4. ∂-domain spectral accumulation
        """
        with self._μ:
            self._n_absorb += 1
            tokens = self._Π_decompose(text)
            if not tokens:
                return {"absorbed": 0}

            n_new = 0
            n_strengthen = 0

            for τ in tokens:
                if τ not in self._Σ:
                    if len(self._Σ) >= self._Σ_max:
                        self._evict_cold()
                    self._Σ[τ] = _Σglyph(τ=τ)
                    n_new += 1

                g = self._Σ[τ]
                g.ν += 1
                g.t1 = time.time()
                g.κ = min(1.0, g.κ + _CONF_STEP)
                g.∂.add(domain)

                idx = text.find(τ)
                if idx >= 0:
                    frag = text[max(0, idx - 30): idx + len(τ) + 30].strip()
                    if len(g.ctx) >= self._ctx_max:
                        g.ctx.pop(0)
                    g.ctx.append(frag)

            # Γ-bridge Hebbian (sliding window)
            for i in range(len(tokens)):
                for j in range(i + 1, min(i + _WINDOW, len(tokens))):
                    if tokens[i] != tokens[j]:
                        n_strengthen += self._Γ_reinforce(tokens[i], tokens[j], κ)

            # ∂-domain accumulation
            for τ in tokens:
                old = self._∂_spectrum[domain].get(τ, 0.0)
                self._∂_spectrum[domain][τ] = min(_Ω_CEIL, old + κ * 0.2)

            # π-pattern extraction
            self._π_learn(url)

            return {
                "absorbed": len(tokens),
                "new": n_new,
                "strengthened": n_strengthen,
                "Σ_size": len(self._Σ),
            }

    # ── Query lattice ──

    def query(self, term: str, top_k: int = 10) -> dict:
        """Project a term onto the Σ-lattice and return its neighborhood."""
        with self._μ:
            if term not in self._Σ:
                return {"found": False, "fuzzy": self._fuzzy_proj(term, top_k)}

            g = self._Σ[term]
            neighbors = sorted(
                self._Γ.get(term, {}).values(),
                key=lambda e: e.Ω, reverse=True,
            )[:top_k]

            return {
                "found": True,
                "τ": term,
                "κ": round(g.κ, 3),
                "ν": g.ν,
                "∂": list(g.∂)[:10],
                "neighbors": [
                    {"τ": e.β, "Ω": round(e.Ω, 3), "kind": e.kind, "ν": e.ν}
                    for e in neighbors
                ],
                "ctx": g.ctx[-3:],
            }

    # ── ∂-domain profile ──

    def domain_profile(self, domain: str) -> dict:
        """Spectral decomposition of a domain's token manifold."""
        with self._μ:
            spec = self._∂_spectrum.get(domain, {})
            if not spec:
                return {"domain": domain, "known": False}

            ranked = sorted(spec.items(), key=lambda x: x[1], reverse=True)[:20]

            specific: list[dict] = []
            for τ, score in ranked:
                others = [
                    dv.get(τ, 0.0)
                    for d, dv in self._∂_spectrum.items() if d != domain
                ]
                μ_other = sum(others) / max(1, len(others))
                if score > μ_other * 2:
                    specific.append({
                        "τ": τ,
                        "Ω": round(score, 3),
                        "specificity": round(score / max(0.01, μ_other), 2),
                    })

            return {
                "domain": domain,
                "known": True,
                "top": [{"τ": w, "Ω": round(s, 3)} for w, s in ranked],
                "specific": specific[:10],
                "Σ_size": len(spec),
            }

    # ── Pattern crystallization ──

    def crystallize(self) -> list[dict]:
        """Extract high-Ω bridges adjacent to security-seed tokens.

        Generates compiled regex patterns from lattice topology.
        Requires Λ_auto_rule from SingularityEngine.
        """
        with self._μ:
            seeds = {
                "key", "token", "secret", "password", "api", "auth",
                "credential", "private", "密码", "密钥", "令牌", "认证",
            }

            candidates: list[dict] = []
            for seed in seeds:
                for target, bridge in self._Γ.get(seed, {}).items():
                    if bridge.Ω >= _PHI * _SIGMA and bridge.ν >= 3:
                        candidates.append({
                            "seed": seed, "τ": target, "Ω": bridge.Ω,
                        })

            seen: set[str] = set()
            rules: list[dict] = []
            for c in sorted(candidates, key=lambda x: x["Ω"], reverse=True)[:10]:
                τ = c["τ"]
                if τ in seen or len(τ) < 3:
                    continue
                seen.add(τ)
                rules.append({
                    "name": f"Λ_{τ}",
                    "pattern": rf"\b{re.escape(τ)}\b\s*[=:]\s*[\"'][^\"']+[\"']",
                    "seed": c["seed"],
                    "κ": min(1.0, c["Ω"] / _Ω_CEIL),
                })

            self._crystallized = rules
            return rules

    # ── 6-channel vitality pulse ──

    def pulse(self) -> dict[str, float]:
        """6-dimensional signal vector for Ξ-convergence field integration.

        Channels: coverage | connectivity | density | Ω_strength | κ_mean | vitality
        """
        with self._μ:
            nΣ = len(self._Σ)
            nΓ = sum(len(e) for e in self._Γ.values())

            p0 = min(1.0, nΣ / 90.0)
            p1 = sum(1 for τ in self._Σ if τ in self._Γ and self._Γ[τ]) / max(1, nΣ)
            p2 = min(1.0, self._n_absorb / 100.0)

            if nΓ > 0:
                Ω_sum = sum(e.Ω for edges in self._Γ.values() for e in edges.values())
                p3 = min(1.0, (Ω_sum / nΓ) / 2.0)
            else:
                p3 = 0.0

            p4 = min(1.0, sum(g.κ for g in self._Σ.values()) / max(1, nΣ)) if nΣ else 0.0
            p5 = min(1.0, self._n_absorb / 100.0)

            return {
                "p0": round(p0, 4), "p1": round(p1, 4), "p2": round(p2, 4),
                "p3": round(p3, 4), "p4": round(p4, 4), "p5": round(p5, 4),
            }

    # ── Lattice statistics ──

    def stats(self) -> dict:
        with self._μ:
            return {
                "Σ_total": len(self._Σ),
                "Γ_total": sum(len(e) for e in self._Γ.values()),
                "∂_domains": len(self._∂_spectrum),
                "n_absorb": self._n_absorb,
                "π_patterns": len(self._π_patterns),
                "crystallized": len(self._crystallized),
                "π_top": sorted(
                    self._π_patterns.items(), key=lambda x: x[1], reverse=True,
                )[:10],
            }

    # ════════════════════════════════════════
    #  Internal operators
    # ════════════════════════════════════════

    def _Π_decompose(self, text: str) -> list[str]:
        """Π-decomposition: extract tokens via dual-spectrum filter."""
        seen: set[str] = set()
        tokens: list[str] = []
        cap = text[:5000]

        for m in _Π_EN.finditer(cap):
            τ = m.group().lower()
            if τ not in _Ω_STOP and τ not in seen and len(τ) <= 30:
                tokens.append(τ)
                seen.add(τ)

        for m in _Π_ZH.finditer(cap):
            τ = m.group()
            if τ not in seen:
                tokens.append(τ)
                seen.add(τ)

        return tokens[:50]

    def _Γ_reinforce(self, τ1: str, τ2: str, κ: float) -> int:
        """Hebbian Γ-bridge reinforcement (bidirectional)."""
        n = 0
        for src, tgt in ((τ1, τ2), (τ2, τ1)):
            bridge = self._Γ[src].get(tgt)
            if bridge:
                bridge.Ω = min(_Ω_CEIL, bridge.Ω + κ * 0.3)
                bridge.ν += 1
                if src == τ1:
                    n = 1
            else:
                self._Γ[src][tgt] = _Γbridge(
                    α=src, β=tgt,
                    Ω=max(0.1, κ * _SIGMA), ν=1,
                )
        return n

    def _fuzzy_proj(self, term: str, top_k: int = 5) -> list[str]:
        """Approximate projection via substring kernel."""
        t = term.lower()
        hits: list[str] = []
        for τ in self._Σ:
            if t in τ.lower() or τ.lower() in t:
                hits.append(τ)
                if len(hits) >= top_k:
                    break
        return hits

    def _π_learn(self, url: str):
        """Extract URL path patterns (dynamic segments → *)."""
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2:
            π_parts = []
            for p in parts:
                if re.match(r"^\d+$", p) or len(p) > 30:
                    π_parts.append("*")
                else:
                    π_parts.append(p)
            self._π_patterns["/" + "/".join(π_parts)] += 1

    def _evict_cold(self):
        """Evict the coldest Σ-glyph (lowest activation count)."""
        if not self._Σ:
            return
        coldest = min(self._Σ.values(), key=lambda g: g.ν)
        τ = coldest.τ
        del self._Σ[τ]
        self._Γ.pop(τ, None)
        for edges in self._Γ.values():
            edges.pop(τ, None)
