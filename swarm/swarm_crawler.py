"""虫群爬虫 — 10 Worker (L4) + 1 King (L12)。

Worker: 执行实际爬取, 4维向量索引, 服从虫王调度
King:   不直接爬取, 12维向量空间, 虫洞检测与穿越, 调度全局

零API依赖 · 纯 httpx + asyncio
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import queue
import re
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse, urljoin

import httpx

from .swarm_vector import URLEntry, VectorL4, VectorL12, VectorIndex, _cosine
from .swarm_wormhole import WormholeEngine

logger = logging.getLogger("swarm")


# ═══════════════════════════════════════════════════════
#  共享状态
# ═══════════════════════════════════════════════════════

@dataclass
class SwarmState:
    """虫群共享状态 — 线程安全。"""
    work_queue: queue.Queue = field(default_factory=queue.Queue)
    visited: set[str] = field(default_factory=set)
    found_urls: set[str] = field(default_factory=set)
    url_entries: dict[str, URLEntry] = field(default_factory=dict)
    secrets: dict[str, list[dict]] = field(default_factory=dict)
    domain_freq: dict[str, int] = field(default_factory=dict)
    link_graph: dict[str, set[str]] = field(default_factory=dict)
    total_pages: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    # 向量索引
    index_l4: VectorIndex = field(default_factory=lambda: VectorIndex(dim=4))
    index_l12: VectorIndex = field(default_factory=lambda: VectorIndex(dim=12))

    # 虫洞引擎
    wormhole: WormholeEngine = field(default_factory=WormholeEngine)

    def add_visited(self, url: str) -> bool:
        """原子性标记已访问, 返回是否为新URL"""
        with self.lock:
            if url in self.visited:
                return False
            self.visited.add(url)
            return True

    def record_page(self):
        with self.lock:
            self.total_pages += 1

    def add_link(self, src: str, tgt: str):
        with self.lock:
            self.link_graph.setdefault(src, set()).add(tgt)
        self.wormhole.ingest_edge(src, tgt)

    def bump_domain(self, domain: str):
        with self.lock:
            self.domain_freq[domain] = self.domain_freq.get(domain, 0) + 1


# ═══════════════════════════════════════════════════════
#  敏感信息正则 (内置, 可扩展)
# ═══════════════════════════════════════════════════════

_DEFAULT_RULES: dict[str, str] = {
    "Swagger": r"\b[\w/]+?((swagger-ui\.html)|(\"swagger\":)|(Swagger UI))\b",
    "JWT": r"['\"]ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._/-]{10,}['\"]",
    "Internal_IP": r"[^0-9]((127\.0\.0\.1)|(10\.\d{1,3}\.\d{1,3}\.\d{1,3})|(172\.((1[6-9])|(2\d)|(3[01]))\.\d{1,3}\.\d{1,3})|(192\.168\.\d{1,3}\.\d{1,3}))",
    "Cloud_Key": r"\b((accesskeyid)|(accesskeysecret)|\b(LTAI[a-z0-9]{12,20}))\b",
    "Shiro": r"(=deleteMe|rememberMe=)",
    "Email": r"['\"][\w]+(?:\.[\w]+)*@(?:[\w](?:[\w-]*[\w])?\.)+[\w](?:[\w-]*[\w])?['\"]",
    "Phone_CN": r"['\"]1[3-9]\d{9}['\"]",
    "ID_Card": r"\b\d{6}(18|19|20)\d{2}(0[1-9]|1[012])([012]\d|30|31)\d{3}[\dXx]\b",
    "API_Key_32": r"[\"'][0-9a-zA-Z]{32}['\"]",
    "JS_Map": r"\b[\w/]+?\.js\.map\b",
    "Git_Leak": r"\.(git|svn|htaccess|env|DS_Store)\b",
    "Config_Leak": r"(wp-config|web\.config|phpinfo|\.well-known)",
}

_URL_FIND = [
    re.compile(r"""[\"'`]\s{0,6}(https?://[-a-zA-Z0-9()@:%_+.~#?&/={}]{2,250}?)\s{0,6}[\"'`]"""),
    re.compile(r"""=\s{0,6}(https?://[-a-zA-Z0-9()@:%_+.~#?&/={}]{2,250})"""),
    re.compile(r"""[\"'`]\s{0,6}([#,.]{0,2}/[-a-zA-Z0-9()@:%_+.~#?&/={}]{2,250}?)\s{0,6}[\"'`]"""),
    re.compile(r"""href\s{0,6}=\s{0,6}[\"'`]?\s{0,6}([-a-zA-Z0-9()@:%_+.~#?&/={}]{2,250})"""),
]

_DANGEROUS_PATHS = {"logout", "delete", "remove", "update", "destroy", "admin/drop"}


def _compile_rules(extra: dict[str, str] | None = None) -> list[tuple[str, re.Pattern]]:
    rules = dict(_DEFAULT_RULES)
    if extra:
        rules.update(extra)
    return [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in rules.items()]


def _extract_secrets(text: str, rules: list[tuple[str, re.Pattern]]) -> list[dict]:
    results = []
    for name, pattern in rules:
        for m in pattern.finditer(text):
            data = m.group(1) if m.lastindex else m.group(0)
            results.append({"type": name, "data": data})
    return results


def _extract_links(base_url: str, text: str) -> set[str]:
    links: set[str] = set()
    for pat in _URL_FIND:
        for m in pat.finditer(text):
            raw = m.group(1)
            if raw.startswith(("http://", "https://")):
                links.add(raw)
            elif raw.startswith("/"):
                links.add(urljoin(base_url, raw))
    return links


def _is_dangerous(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(d in path for d in _DANGEROUS_PATHS)


# ═══════════════════════════════════════════════════════
#  Worker Crawler (向量4级)
# ═══════════════════════════════════════════════════════

class WorkerCrawler:
    """一只工蚁 — 执行实际爬取+提取, L4向量索引。

    每个Worker有自己的 worker_id (0-9), asyncio loop, httpx client.
    从共享 work_queue 取任务, 结果写回 SwarmState.
    """

    def __init__(
        self,
        worker_id: int,
        state: SwarmState,
        *,
        headers: dict | None = None,
        proxy: str | None = None,
        timeout: float = 10.0,
        follow_redirects: bool = True,
        max_page: int = 0,
    ):
        self.id = worker_id
        self.state = state
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
        }
        self.proxy = proxy
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_page = max_page
        self._rules = _compile_rules()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pages_done = 0

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name=f"Worker-{self.id}", daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._work())
        except Exception:
            logger.error("Worker-%d crashed: %s", self.id, traceback.format_exc())
        finally:
            loop.close()

    async def _work(self):
        async with httpx.AsyncClient(
            verify=False,
            proxy=self.proxy,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        ) as client:
            idle_count = 0
            while not self._stop.is_set():
                # 检查全局页数限制
                if self.max_page > 0 and self.state.total_pages >= self.max_page:
                    break

                try:
                    entry: URLEntry = self.state.work_queue.get_nowait()
                except queue.Empty:
                    idle_count += 1
                    if idle_count > 30:  # 3秒无任务
                        break
                    await asyncio.sleep(0.1)
                    continue

                idle_count = 0
                await self._process(client, entry)

    async def _process(self, client: httpx.AsyncClient, entry: URLEntry):
        if _is_dangerous(entry.url):
            return

        self.state.record_page()
        self._pages_done += 1

        try:
            resp = await client.get(
                entry.url,
                headers=self.headers,
                follow_redirects=self.follow_redirects,
                timeout=self.timeout,
            )
            entry.status = resp.status_code
        except Exception as e:
            logger.debug("Worker-%d fetch error %s: %s", self.id, entry.url, e)
            return

        text = resp.text
        entry.content_len = len(text)
        entry.content_hash = hashlib.md5(text[:2000].encode(errors="ignore")).hexdigest()

        # 提取敏感信息
        secrets = _extract_secrets(text, self._rules)
        if secrets:
            entry.secret_count = len(secrets)
            self.state.secrets[entry.url] = secrets

        # 提取链接
        links = _extract_links(entry.url, text)
        entry.link_count = len(links)

        for link in links:
            parsed = urlparse(link)
            self.state.add_link(entry.url, link)
            self.state.bump_domain(parsed.netloc)

            child = URLEntry(
                url=link, domain=parsed.netloc,
                depth=entry.depth + 1, parent=entry.url,
            )
            self.state.url_entries[link] = child
            self.state.found_urls.add(link)

        # L4 向量索引
        vec4 = VectorL4.embed(entry, self.state.domain_freq)
        self.state.index_l4.add(entry, vec4)

        # 虫洞探测 — Worker只做probe
        portal_targets = self.state.wormhole.probe(entry.url, vec4, k=3)
        for portal in portal_targets:
            target_url = portal["target"]
            if self.state.add_visited(target_url):
                portal_entry = URLEntry(
                    url=target_url, depth=entry.depth + 1,
                    parent=f"wormhole:{entry.url}",
                )
                self.state.url_entries[target_url] = portal_entry
                self.state.work_queue.put(portal_entry)
                logger.info("Worker-%d wormhole jump → %s (proximity=%.3f)",
                            self.id, target_url, portal["proximity"])

        # 子链接入队 (过滤后)
        for link in links:
            if self.state.add_visited(link):
                child = self.state.url_entries.get(link)
                if child:
                    self.state.work_queue.put(child)

    @property
    def stats(self) -> dict:
        return {"worker_id": self.id, "pages_done": self._pages_done, "alive": not self._stop.is_set()}


# ═══════════════════════════════════════════════════════
#  King Crawler (虫王, 向量12级)
# ═══════════════════════════════════════════════════════

class KingCrawler:
    """虫王 — 不直接爬取, 负责:
    1. 将种子URL分配给Workers
    2. 定期对L4索引升维到L12
    3. 执行虫洞检测 (φ-traversal)
    4. 通过虫洞穿越发现远端高价值目标
    5. 向Workers注入虫洞跳转任务
    6. 聚类分析, 调度Worker到不同域/区域

    向量12级: 完整12维嵌入, 虫洞张力感知
    """

    def __init__(
        self,
        state: SwarmState,
        workers: list[WorkerCrawler],
        *,
        wormhole_interval: float = 30.0,
        upgrade_interval: float = 15.0,
    ):
        self.state = state
        self.workers = workers
        self._wormhole_interval = wormhole_interval
        self._upgrade_interval = upgrade_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._cycles = 0
        self._wormholes_found = 0
        self._jumps_injected = 0
        self._seed_time = time.time()

    def start(self):
        self._stop.clear()
        self._seed_time = time.time()
        self._thread = threading.Thread(
            target=self._king_loop, name="King", daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def seed(self, urls: list[str], max_depth: int = 2):
        """种子注入 — 虫王分配初始任务给Workers。"""
        for url in urls:
            parsed = urlparse(url)
            entry = URLEntry(url=url, domain=parsed.netloc, depth=0)
            self.state.url_entries[url] = entry
            self.state.found_urls.add(url)
            self.state.add_visited(url)
            self.state.bump_domain(parsed.netloc)
            self.state.work_queue.put(entry)

    def _king_loop(self):
        last_wormhole = 0.0
        last_upgrade = 0.0

        while not self._stop.is_set():
            now = time.time()
            self._cycles += 1

            # ── 周期性: L4 → L12 升维 ──
            if now - last_upgrade >= self._upgrade_interval:
                self._upgrade_vectors()
                last_upgrade = now

            # ── 周期性: 虫洞检测 ──
            if now - last_wormhole >= self._wormhole_interval:
                self._detect_wormholes()
                last_wormhole = now

            # ── 检查Workers存活 ──
            alive = sum(1 for w in self.workers if not w._stop.is_set())
            if alive == 0 and self.state.work_queue.empty():
                break

            time.sleep(2.0)

    def _upgrade_vectors(self):
        """L4 → L12 升维 — 虫王独有能力。"""
        domain_vecs: dict[str, list[list[float]]] = {}
        upgraded = 0

        for url, entry in list(self.state.url_entries.items()):
            if entry._vec4 and not entry._vec12:
                vec12 = VectorL12.embed(
                    entry,
                    domain_freq=self.state.domain_freq,
                    link_graph=self.state.link_graph,
                    domain_vecs=domain_vecs,
                    seed_time=self._seed_time,
                )
                self.state.index_l12.add(entry, vec12)
                self.state.wormhole.ingest_vector(url, vec12)
                upgraded += 1

                # 收集域向量用于漂移计算
                domain_vecs.setdefault(entry.domain, []).append(entry._vec4)

        if upgraded > 0:
            logger.info("King: upgraded %d vectors L4→L12", upgraded)

    def _detect_wormholes(self):
        """虫洞检测 + 穿越注入。"""
        if self.state.index_l12.size() < 10:
            return

        result = self.state.wormhole.detect(top_n=10)
        if result["status"] != "detected":
            return

        wormholes = result["wormholes"]
        self._wormholes_found = result.get("total_candidates", 0)

        # 通过虫洞注入跳转任务
        for wh in wormholes:
            for endpoint in (wh["target"], wh["source"]):
                if self.state.add_visited(endpoint):
                    entry = URLEntry(
                        url=endpoint,
                        depth=1,  # 虫洞跳转不增加过多深度
                        parent="wormhole:king",
                    )
                    self.state.url_entries[endpoint] = entry
                    self.state.work_queue.put(entry)
                    self._jumps_injected += 1
                    logger.info("King: wormhole inject → %s (Ψ=%.3f)",
                                endpoint, wh["strength"])

        # 聚类分析 — 如果L12索引够大, 分配Workers到不同区域
        if self.state.index_l12.size() > 50:
            clusters = self.state.index_l12.cluster(k=min(len(self.workers), 5))
            # 每个cluster中未已访问的URL优先入队
            for cluster in clusters:
                for entry in cluster:
                    if entry.url not in self.state.visited:
                        self.state.work_queue.put(entry)

    @property
    def stats(self) -> dict:
        return {
            "king_cycles": self._cycles,
            "wormholes_found": self._wormholes_found,
            "jumps_injected": self._jumps_injected,
            "l12_indexed": self.state.index_l12.size(),
            "wormhole_engine": self.state.wormhole.stats(),
        }
