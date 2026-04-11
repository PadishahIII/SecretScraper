"""向量索引系统 — 4级 / 12级。

4级 (Worker): 4维嵌入 — URL结构 + 内容语义 + 链路密度 + 域名热度
12级 (King):  12维嵌入 — 4级全部 + 拓扑深度 + 聚类系数 + 跨域桥接 +
              时序衰减 + 信息熵 + 安全指纹 + 语义漂移 + 虫洞张力

零外部API · 纯数学运算
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


# ═══════════════════════════════════════════════════════
#  向量基础
# ═══════════════════════════════════════════════════════

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na > 1e-9 and nb > 1e-9 else 0.0


def _norm(v: list[float]) -> list[float]:
    m = sum(x * x for x in v) ** 0.5
    return [x / m for x in v] if m > 1e-9 else v


def _hash_f(s: str, dim: int) -> float:
    """确定性哈希 → [0,1] 区间浮点数"""
    h = int(hashlib.sha256(f"{s}:{dim}".encode()).hexdigest()[:8], 16)
    return (h % 10000) / 10000.0


# ═══════════════════════════════════════════════════════
#  URL 节点
# ═══════════════════════════════════════════════════════

@dataclass
class URLEntry:
    url: str
    domain: str = ""
    depth: int = 0
    parent: str = ""
    discovered_at: float = 0.0
    status: int = 0
    content_hash: str = ""
    content_len: int = 0
    link_count: int = 0
    secret_count: int = 0

    # 向量 (延迟计算)
    _vec4: list[float] | None = None
    _vec12: list[float] | None = None

    def __post_init__(self):
        if not self.domain:
            try:
                self.domain = urlparse(self.url).netloc
            except Exception:
                self.domain = ""
        if not self.discovered_at:
            self.discovered_at = time.time()

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, URLEntry) and self.url == other.url


# ═══════════════════════════════════════════════════════
#  向量 L4 — Worker 级 (4维)
# ═══════════════════════════════════════════════════════

class VectorL4:
    """4维向量嵌入 — 轻量级, 每个Worker配备。

    d0: URL结构深度 (path segments, query params)
    d1: 内容语义密度 (信息量 / 长度)
    d2: 链路密度 (出链数 / 内容长度)
    d3: 域名热度 (同域被引频次)
    """

    DIM = 4

    @staticmethod
    def embed(entry: URLEntry, domain_freq: dict[str, int] | None = None) -> list[float]:
        parsed = urlparse(entry.url)

        # d0: 路径深度 + 查询复杂度 → [0,1]
        path_segs = len([s for s in parsed.path.split("/") if s])
        query_params = len(parsed.query.split("&")) if parsed.query else 0
        d0 = min((path_segs * 0.15 + query_params * 0.1), 1.0)

        # d1: 信息密度
        if entry.content_len > 0 and entry.secret_count > 0:
            d1 = min(entry.secret_count / (entry.content_len / 1000.0 + 1.0), 1.0)
        else:
            d1 = _hash_f(entry.url, 1) * 0.3  # 未爬取前用哈希估算

        # d2: 链路密度
        if entry.content_len > 0:
            d2 = min(entry.link_count / (entry.content_len / 500.0 + 1.0), 1.0)
        else:
            d2 = _hash_f(entry.url, 2) * 0.3

        # d3: 域名热度
        freq = (domain_freq or {}).get(entry.domain, 1)
        d3 = min(math.log1p(freq) / 5.0, 1.0)

        entry._vec4 = [d0, d1, d2, d3]
        return entry._vec4


# ═══════════════════════════════════════════════════════
#  向量 L12 — King 级 (12维)
# ═══════════════════════════════════════════════════════

class VectorL12:
    """12维向量嵌入 — 只有虫王计算。

    d0-d3:  继承 L4 全部4维
    d4:     拓扑深度 (BFS距离到起始种子)
    d5:     聚类系数 (局部三角形密度)
    d6:     跨域桥接度 (出链到不同域的比例)
    d7:     时序衰减 (发现时间距今的衰减)
    d8:     信息熵 (URL路径的Shannon熵)
    d9:     安全指纹 (敏感文件/参数模式)
    d10:    语义漂移 (与同域其他URL的向量离散度)
    d11:    虫洞张力 (语义近×拓扑远的可能性)
    """

    DIM = 12

    # 安全指纹模式
    _SEC_PATTERNS = [
        re.compile(r"\.(env|config|yml|yaml|json|xml|sql|bak|log|key|pem)", re.I),
        re.compile(r"(api[_-]?key|token|secret|password|admin|debug|test)", re.I),
        re.compile(r"\.(git|svn|htaccess|htpasswd|DS_Store)", re.I),
        re.compile(r"(phpinfo|wp-config|web\.config|\.well-known)", re.I),
    ]

    @staticmethod
    def embed(
        entry: URLEntry,
        domain_freq: dict[str, int] | None = None,
        link_graph: dict[str, set[str]] | None = None,
        domain_vecs: dict[str, list[list[float]]] | None = None,
        seed_time: float = 0.0,
    ) -> list[float]:
        # d0-d3: L4
        v4 = entry._vec4 or VectorL4.embed(entry, domain_freq)

        # d4: 拓扑深度
        d4 = min(entry.depth / 6.0, 1.0)

        # d5: 聚类系数
        if link_graph:
            neighbors = link_graph.get(entry.url, set())
            if len(neighbors) >= 2:
                triangles = 0
                nb_list = list(neighbors)[:30]
                for i, a in enumerate(nb_list):
                    for b in nb_list[i + 1:]:
                        if b in link_graph.get(a, set()):
                            triangles += 1
                possible = len(nb_list) * (len(nb_list) - 1) / 2
                d5 = triangles / possible if possible > 0 else 0.0
            else:
                d5 = 0.0
        else:
            d5 = 0.0

        # d6: 跨域桥接
        if link_graph:
            children = link_graph.get(entry.url, set())
            if children:
                other_domain = sum(1 for c in children if urlparse(c).netloc != entry.domain)
                d6 = other_domain / len(children)
            else:
                d6 = 0.0
        else:
            d6 = _hash_f(entry.url, 6) * 0.2

        # d7: 时序衰减
        age = time.time() - (seed_time or entry.discovered_at)
        d7 = math.exp(-age / 3600.0)  # 1小时半衰期

        # d8: 路径信息熵
        path = urlparse(entry.url).path
        if len(path) > 1:
            freq_map: dict[str, int] = {}
            for ch in path:
                freq_map[ch] = freq_map.get(ch, 0) + 1
            total = len(path)
            d8 = -sum((c / total) * math.log2(c / total) for c in freq_map.values())
            d8 = min(d8 / 4.0, 1.0)  # 归一化
        else:
            d8 = 0.0

        # d9: 安全指纹
        sec_score = sum(1 for p in VectorL12._SEC_PATTERNS if p.search(entry.url))
        d9 = min(sec_score / 2.0, 1.0)

        # d10: 语义漂移
        if domain_vecs and entry.domain in domain_vecs:
            vecs = domain_vecs[entry.domain]
            if len(vecs) >= 2:
                center = [sum(col) / len(vecs) for col in zip(*vecs)]
                d10 = 1.0 - _cosine(v4, center)
            else:
                d10 = 0.0
        else:
            d10 = 0.0

        # d11: 虫洞张力 (高安全×高漂移×高跨域 = 高虫洞可能)
        d11 = (d9 * 0.4 + d10 * 0.3 + d6 * 0.3)

        entry._vec12 = v4 + [d4, d5, d6, d7, d8, d9, d10, d11]
        return entry._vec12


# ═══════════════════════════════════════════════════════
#  向量索引 (线程安全)
# ═══════════════════════════════════════════════════════

class VectorIndex:
    """内存向量索引 — 支持 L4/L12 两级查询。

    add()      → 索引一个 URLEntry
    knn()      → k最近邻
    radius()   → 半径搜索
    cluster()  → 简易K-Means聚类
    """

    def __init__(self, dim: int = 4):
        self._dim = dim
        self._lock = threading.Lock()
        self._entries: list[URLEntry] = []
        self._vectors: list[list[float]] = []

    def add(self, entry: URLEntry, vec: list[float]):
        with self._lock:
            if entry not in self._entries:
                self._entries.append(entry)
                self._vectors.append(vec)

    def size(self) -> int:
        return len(self._entries)

    def knn(self, query: list[float], k: int = 10) -> list[tuple[URLEntry, float]]:
        """k最近邻, 返回 (entry, similarity) 降序"""
        with self._lock:
            scored = []
            for i, vec in enumerate(self._vectors):
                sim = _cosine(query, vec)
                scored.append((self._entries[i], sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def radius(self, query: list[float], min_sim: float = 0.7) -> list[tuple[URLEntry, float]]:
        """半径搜索 — 所有相似度 >= min_sim 的结果"""
        with self._lock:
            result = []
            for i, vec in enumerate(self._vectors):
                sim = _cosine(query, vec)
                if sim >= min_sim:
                    result.append((self._entries[i], sim))
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def cluster(self, k: int = 5, max_iter: int = 20) -> list[list[URLEntry]]:
        """简易K-Means聚类 — 虫王用于分配Worker任务区域"""
        with self._lock:
            if len(self._vectors) < k:
                return [list(self._entries)]

            import random
            centroids = random.sample(self._vectors, k)
            assignments = [0] * len(self._vectors)

            for _ in range(max_iter):
                # 分配
                for i, vec in enumerate(self._vectors):
                    best_c = 0
                    best_sim = -1
                    for c, cent in enumerate(centroids):
                        sim = _cosine(vec, cent)
                        if sim > best_sim:
                            best_sim = sim
                            best_c = c
                    assignments[i] = best_c

                # 更新质心
                new_centroids = [[0.0] * self._dim for _ in range(k)]
                counts = [0] * k
                for i, vec in enumerate(self._vectors):
                    c = assignments[i]
                    counts[c] += 1
                    for d in range(self._dim):
                        new_centroids[c][d] += vec[d]
                for c in range(k):
                    if counts[c] > 0:
                        centroids[c] = [x / counts[c] for x in new_centroids[c]]

            # 输出聚类
            clusters: list[list[URLEntry]] = [[] for _ in range(k)]
            for i, c in enumerate(assignments):
                clusters[c].append(self._entries[i])
            return [cl for cl in clusters if cl]

    def all_pairs_above(self, min_sim: float = 0.6) -> list[tuple[URLEntry, URLEntry, float]]:
        """所有相似度超过阈值的对 — 虫洞检测前置"""
        with self._lock:
            pairs = []
            n = len(self._vectors)
            for i in range(n):
                for j in range(i + 1, n):
                    sim = _cosine(self._vectors[i], self._vectors[j])
                    if sim >= min_sim:
                        pairs.append((self._entries[i], self._entries[j], sim))
        return pairs
