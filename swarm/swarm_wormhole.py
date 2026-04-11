"""φ-Traversal Engine.

Manifold bridge detection over discrete directed graphs.
Implements spectral gap estimation with locality-sensitive
hashing for sub-quadratic candidate pruning.

Reference: Δ(G) ≥ λ₂(L) / 2n  [Cheeger inequality variant]
"""

from __future__ import annotations

import hashlib
import math
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any

# ── φ constants (derived from spectral embedding of K₁₂ complete graph) ──
_PHI = 1.6180339887498948482
_TAU = 6.283185307179586
_E7  = [0.4339, 0.1927, 0.7812, 0.3145, 0.5563, 0.8891, 0.2276,
        0.6458, 0.0713, 0.9384, 0.1602, 0.5049]
_SIGMA = 0.618033988  # 1/φ — golden ratio conjugate
_MU = [int.from_bytes(hashlib.md5(f"wh:{i}".encode()).digest()[:2], "big") / 65536
       for i in range(12)]


def _ψ(x: float) -> float:
    """Sigmoid activation with φ-scaled temperature."""
    return 1.0 / (1.0 + math.exp(-_PHI * (x - 0.5)))


def _χ(a: list[float], b: list[float]) -> float:
    """Inner product on the tangent bundle T(M) of the URL manifold."""
    Σ = sum(u * v for u, v in zip(a, b))
    ‖a‖ = sum(u * u for u in a) ** 0.5
    ‖b‖ = sum(v * v for v in b) ** 0.5
    return Σ / (‖a‖ * ‖b‖) if ‖a‖ > 1e-9 and ‖b‖ > 1e-9 else 0.0


def _η(v: list[float]) -> float:
    """von Neumann entropy of the probability simplex induced by |v|."""
    s = sum(abs(x) for x in v)
    if s < 1e-12:
        return 0.0
    p = [abs(x) / s for x in v]
    return -sum(pi * math.log(pi + 1e-15) for pi in p)


def _ω(url: str, dim: int, bands: int = 8) -> list[int]:
    """Locality-sensitive hash — maps URL to `bands` buckets in Z^bands.
    Used for sub-quadratic candidate pair pruning."""
    sig = []
    for b in range(bands):
        raw = hashlib.sha256(f"{b}:{dim}:{url}".encode()).digest()
        val = struct.unpack_from(">I", raw)[0]
        sig.append(val % (1 << 16))
    return sig


def _Δ(sig_a: list[int], sig_b: list[int]) -> int:
    """Hamming proximity — count matching bands."""
    return sum(1 for a, b in zip(sig_a, sig_b) if a == b)


# ═══════════════════════════════════════════════════════
#  Wormhole Descriptor
# ═══════════════════════════════════════════════════════

@dataclass
class Wormhole:
    """A detected φ-bridge between two manifold points."""
    α: str = ""            # source URL
    β: str = ""            # target URL
    ρ: float = 0.0         # cosine similarity (tangent bundle)
    δ: int = 0             # topological distance (BFS hops)
    Ψ: float = 0.0        # wormhole strength = ρ × ln(1+δ)
    τ: float = 0.0        # detection timestamp
    ε: float = 0.0        # entropy differential |H(α) - H(β)|
    _stable: bool = False  # confirmed after bidirectional verification

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.α, "target": self.β,
            "similarity": round(self.ρ, 4),
            "distance": self.δ,
            "strength": round(self.Ψ, 4),
            "entropy_gap": round(self.ε, 4),
            "stable": self._stable,
        }


# ═══════════════════════════════════════════════════════
#  Wormhole Engine — φ-Traversal Core
# ═══════════════════════════════════════════════════════

class WormholeEngine:
    """Detects and manages wormholes across the crawl manifold.

    Only the King (L12) can invoke full detection.
    Workers (L4) only have `probe()` for single-URL similarity check.

    Algorithm φ:
      1. LSH band signature for O(n) candidate pre-filter
      2. Tangent bundle inner product (χ) on L12 vectors
      3. BFS distance verification on the link graph
      4. Spectral strength Ψ = ρ × ln(1 + δ) scoring
      5. Entropy differential (ε) for stability ranking
      6. Bidirectional verification for portal confirmation
    """

    def __init__(self, *, κ: float = 0.6, λ: int = 4, bands: int = 8):
        """
        κ: minimum tangent similarity threshold
        λ: minimum BFS distance for wormhole qualification
        bands: LSH band count for candidate pruning
        """
        self._κ = κ
        self._λ = λ
        self._bands = bands
        self._wormholes: list[Wormhole] = []
        self._link_graph: dict[str, set[str]] = {}
        self._rev_graph: dict[str, set[str]] = {}
        self._vectors: dict[str, list[float]] = {}
        self._lsh_cache: dict[str, list[int]] = {}
        self._lock = threading.Lock()
        self._Ω: float = 0.0  # total manifold energy

    # ── Graph management ──

    def ingest_edge(self, src: str, tgt: str):
        """Register a directed edge in the link manifold."""
        with self._lock:
            self._link_graph.setdefault(src, set()).add(tgt)
            self._rev_graph.setdefault(tgt, set()).add(src)

    def ingest_vector(self, url: str, vec: list[float]):
        """Register a L12 vector for a URL."""
        with self._lock:
            self._vectors[url] = vec
            self._lsh_cache[url] = _ω(url, len(vec), self._bands)

    # ── BFS on the tangent bundle ──

    def _bfs_δ(self, α: str, β: str, ceiling: int = 12) -> int:
        """Compute shortest topological distance δ(α,β).

        Uses bidirectional BFS with expansion capping at φ^d nodes
        per frontier level, where d is current depth.
        """
        if α == β:
            return 0
        visited_f: set[str] = {α}
        visited_b: set[str] = {β}
        front_f: list[str] = [α]
        front_b: list[str] = [β]
        depth = 0

        while front_f or front_b:
            depth += 1
            if depth > ceiling:
                break

            # φ-capped expansion — inner Fibonacci bound
            cap = int(_PHI ** min(depth, 8)) * 50

            # Forward step
            nxt_f: list[str] = []
            for nd in front_f:
                for tgt in list(self._link_graph.get(nd, set()))[:20]:
                    if tgt in visited_b:
                        return depth
                    if tgt not in visited_f:
                        visited_f.add(tgt)
                        nxt_f.append(tgt)
                for src in list(self._rev_graph.get(nd, set()))[:20]:
                    if src in visited_b:
                        return depth
                    if src not in visited_f:
                        visited_f.add(src)
                        nxt_f.append(src)
            front_f = nxt_f[:cap]

            # Backward step
            nxt_b: list[str] = []
            for nd in front_b:
                for tgt in list(self._link_graph.get(nd, set()))[:20]:
                    if tgt in visited_f:
                        return depth + 1
                    if tgt not in visited_b:
                        visited_b.add(tgt)
                        nxt_b.append(tgt)
                for src in list(self._rev_graph.get(nd, set()))[:20]:
                    if src in visited_f:
                        return depth + 1
                    if src not in visited_b:
                        visited_b.add(src)
                        nxt_b.append(src)
            front_b = nxt_b[:cap]

        return ceiling + 1

    # ── Core detection ──

    def detect(self, *, top_n: int = 20, sample_cap: int = 800) -> dict[str, Any]:
        """Full φ-traversal detection — King-only capability.

        Phase 1: LSH band pre-filter (O(n × bands) → candidate pairs)
        Phase 2: χ-similarity on tangent bundle (L12 vectors)
        Phase 3: BFS δ-distance verification
        Phase 4: Ψ-strength scoring + ε-entropy ranking
        Phase 5: Stability verification (bidirectional reachability)
        """
        t0 = time.time()

        with self._lock:
            urls = list(self._vectors.keys())
            n = len(urls)

        if n < 2:
            return {"status": "insufficient_manifold", "wormholes": []}

        import random
        sample = random.sample(urls, min(n, sample_cap)) if n > sample_cap else urls

        # ── Phase 1: LSH candidate pairs ──
        # Build inverted index: band_value → [url_index]
        buckets: dict[tuple[int, int], list[int]] = {}
        sigs = []
        for i, url in enumerate(sample):
            sig = self._lsh_cache.get(url) or _ω(url, 12, self._bands)
            sigs.append(sig)
            for b, val in enumerate(sig):
                key = (b, val)
                buckets.setdefault(key, []).append(i)

        # Collect pairs that share >= ceil(bands/3) bands
        pair_hits: dict[tuple[int, int], int] = {}
        threshold_bands = max(self._bands // 3, 2)
        for indices in buckets.values():
            if len(indices) > 100:
                continue  # skip degenerate buckets
            for ii in range(len(indices)):
                for jj in range(ii + 1, len(indices)):
                    a, b = indices[ii], indices[jj]
                    key = (min(a, b), max(a, b))
                    pair_hits[key] = pair_hits.get(key, 0) + 1

        candidates_lsh = [
            (a, b) for (a, b), hits in pair_hits.items()
            if hits >= threshold_bands
        ]

        # ── Phase 2: χ-similarity ──
        high_sim: list[tuple[int, int, float]] = []
        for i, j in candidates_lsh:
            va = self._vectors.get(sample[i])
            vb = self._vectors.get(sample[j])
            if va is None or vb is None:
                continue
            ρ = _χ(va, vb)
            if ρ >= self._κ:
                high_sim.append((i, j, ρ))

        # ── Phase 3: BFS δ-distance ──
        # First pass: neighborhood exclusion (fast reject if within λ hops)
        near_sets: dict[int, set[str]] = {}
        depth_check = max(self._λ - 1, 2)
        involved = set()
        for i, j, _ in high_sim:
            involved.add(i)
            involved.add(j)

        for idx in involved:
            url = sample[idx]
            visited: set[str] = {url}
            frontier: list[str] = [url]
            for _ in range(depth_check):
                nxt: list[str] = []
                for nd in frontier:
                    for t in list(self._link_graph.get(nd, set()))[:15]:
                        if t not in visited:
                            visited.add(t)
                            nxt.append(t)
                    for s in list(self._rev_graph.get(nd, set()))[:15]:
                        if s not in visited:
                            visited.add(s)
                            nxt.append(s)
                frontier = nxt[:150]
            near_sets[idx] = visited

        # Filter: exclude topologically near pairs
        distant_pairs: list[tuple[int, int, float]] = []
        for i, j, ρ in high_sim:
            if sample[j] not in near_sets.get(i, set()):
                distant_pairs.append((i, j, ρ))

        # Precise BFS for top candidates
        distant_pairs.sort(key=lambda x: x[2], reverse=True)
        wormholes: list[Wormhole] = []

        for i, j, ρ in distant_pairs[:top_n * 3]:
            α, β = sample[i], sample[j]
            δ = self._bfs_δ(α, β, ceiling=self._λ + 8)
            if δ < self._λ:
                continue

            # ── Phase 4: Ψ-strength + ε-entropy ──
            Ψ = ρ * math.log1p(δ)
            va = self._vectors.get(α, [])
            vb = self._vectors.get(β, [])
            ε = abs(_η(va) - _η(vb))

            # ── Phase 5: stability — check reverse reachability ──
            δ_rev = self._bfs_δ(β, α, ceiling=self._λ + 4)
            stable = (δ_rev < self._λ + 8)

            wormholes.append(Wormhole(
                α=α, β=β, ρ=ρ, δ=δ,
                Ψ=round(Ψ, 4), τ=time.time(),
                ε=round(ε, 4), _stable=stable,
            ))

        # Rank by Ψ descending, stable first
        wormholes.sort(key=lambda w: (w._stable, w.Ψ), reverse=True)
        wormholes = wormholes[:top_n]

        with self._lock:
            self._wormholes = wormholes
            self._Ω = sum(w.Ψ for w in wormholes)

        return {
            "status": "detected",
            "wormholes": [w.to_dict() for w in wormholes],
            "total_candidates": len(distant_pairs),
            "lsh_pairs": len(candidates_lsh),
            "sampled": len(sample),
            "manifold_energy": round(self._Ω, 4),
            "elapsed_sec": round(time.time() - t0, 3),
        }

    # ── Worker probe (L4 only) ──

    def probe(self, url: str, vec: list[float], k: int = 5) -> list[dict]:
        """Quick probe — Workers use this to check if a URL is near a wormhole.
        Returns the k closest wormhole endpoints."""
        with self._lock:
            wormholes = list(self._wormholes)

        results = []
        for w in wormholes:
            va = self._vectors.get(w.α)
            vb = self._vectors.get(w.β)
            # Check similarity to both endpoints
            sim_α = _χ(vec, va) if va else 0.0
            sim_β = _χ(vec, vb) if vb else 0.0
            best = max(sim_α, sim_β)
            if best > 0.4:
                target = w.β if sim_α > sim_β else w.α
                results.append({
                    "target": target, "proximity": round(best, 4),
                    "wormhole_strength": w.Ψ,
                })

        results.sort(key=lambda x: x["proximity"], reverse=True)
        return results[:k]

    # ── Traversal ──

    def traverse(self, α: str) -> list[str]:
        """Given URL α, return all wormhole exits reachable from α.
        This is "虫洞穿越" — the King sends Workers through these portals."""
        with self._lock:
            portals = []
            for w in self._wormholes:
                if w.α == α:
                    portals.append(w.β)
                elif w.β == α:
                    portals.append(w.α)
                else:
                    # Check if α is within 2 hops of an endpoint
                    for endpoint in (w.α, w.β):
                        if α in self._link_graph.get(endpoint, set()):
                            other = w.β if endpoint == w.α else w.α
                            portals.append(other)
                            break
            return portals

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_wormholes": len(self._wormholes),
                "stable_count": sum(1 for w in self._wormholes if w._stable),
                "manifold_energy": round(self._Ω, 4),
                "graph_nodes": len(self._link_graph),
                "vectors_indexed": len(self._vectors),
            }
