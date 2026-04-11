"""虫群协调器 — 完整生命周期管理。

seed → spawn king + 10 workers → crawl → wormhole detect → aggregate → report

独立运行, 不依赖任何引擎API.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from typing import Any

from .swarm_crawler import KingCrawler, WorkerCrawler, SwarmState
from .swarm_vector import URLEntry, VectorIndex
from .swarm_wormhole import WormholeEngine

logger = logging.getLogger("swarm")


class SwarmCoordinator:
    """协调10 Workers + 1 King的完整生命周期。

    用法::

        coord = SwarmCoordinator(seed_urls=["https://target.com"])
        result = coord.run()
        print(result)
    """

    def __init__(
        self,
        seed_urls: list[str],
        *,
        num_workers: int = 10,
        max_pages: int = 5000,
        max_depth: int = 5,
        headers: dict | None = None,
        proxy: str | None = None,
        timeout: float = 10.0,
        wormhole_interval: float = 30.0,
        extra_rules: dict[str, str] | None = None,
    ):
        self.seed_urls = seed_urls
        self.num_workers = num_workers
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.headers = headers
        self.proxy = proxy
        self.timeout = timeout
        self.wormhole_interval = wormhole_interval
        self.extra_rules = extra_rules

        self.state = SwarmState()
        self.workers: list[WorkerCrawler] = []
        self.king: KingCrawler | None = None
        self._start_time = 0.0

    def run(self) -> dict[str, Any]:
        """同步运行虫群, 返回最终报告。"""
        self._start_time = time.time()
        self._spawn()
        self._launch()
        self._wait()
        return self._report()

    def _spawn(self):
        """创建10 Workers + 1 King。"""
        for wid in range(self.num_workers):
            w = WorkerCrawler(
                worker_id=wid,
                state=self.state,
                headers=self.headers,
                proxy=self.proxy,
                timeout=self.timeout,
                max_page=self.max_pages,
            )
            self.workers.append(w)

        self.king = KingCrawler(
            state=self.state,
            workers=self.workers,
            wormhole_interval=self.wormhole_interval,
        )

    def _launch(self):
        """King种子注入 → 启动所有Worker → 启动King。"""
        logger.info("Swarm: seeding %d URLs", len(self.seed_urls))
        self.king.seed(self.seed_urls, max_depth=self.max_depth)

        for w in self.workers:
            w.start()
            logger.info("Swarm: Worker-%d started", w.id)

        self.king.start()
        logger.info("Swarm: King started — %d workers active", len(self.workers))

    def _wait(self):
        """等待所有Worker完成。"""
        for w in self.workers:
            if w._thread:
                w._thread.join()
        self.king.stop()
        if self.king._thread:
            self.king._thread.join()
        logger.info("Swarm: all threads finished")

    def _report(self) -> dict[str, Any]:
        """聚合最终报告。"""
        elapsed = time.time() - self._start_time

        # 敏感信息汇总
        all_secrets: list[dict] = []
        for url, items in self.state.secrets.items():
            for item in items:
                all_secrets.append({
                    "url": url,
                    "type": item["type"],
                    "data": item["data"],
                })

        # 按类型统计
        type_counts: dict[str, int] = {}
        for s in all_secrets:
            type_counts[s["type"]] = type_counts.get(s["type"], 0) + 1

        # 域统计
        top_domains = sorted(
            self.state.domain_freq.items(), key=lambda x: x[1], reverse=True,
        )[:20]

        return {
            "summary": {
                "elapsed_seconds": round(elapsed, 2),
                "total_pages": self.state.total_pages,
                "unique_urls": len(self.state.found_urls),
                "secrets_found": len(all_secrets),
                "wormholes_detected": self.king.stats["wormholes_found"],
                "wormhole_jumps": self.king.stats["jumps_injected"],
                "l4_indexed": self.state.index_l4.size(),
                "l12_indexed": self.state.index_l12.size(),
                "num_workers": self.num_workers,
            },
            "secrets": all_secrets,
            "secret_type_counts": type_counts,
            "top_domains": top_domains,
            "worker_stats": [w.stats for w in self.workers],
            "king_stats": self.king.stats,
            "wormhole_stats": self.state.wormhole.stats(),
        }


def run_swarm(
    targets: list[str],
    *,
    workers: int = 10,
    max_pages: int = 5000,
    proxy: str | None = None,
    output: str | None = None,
    verbose: bool = False,
) -> dict:
    """便捷入口。"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    coord = SwarmCoordinator(
        seed_urls=targets,
        num_workers=workers,
        max_pages=max_pages,
        proxy=proxy,
    )
    result = coord.run()

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info("Report saved to %s", output)

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SwarmCrawler — 10 Workers + 1 King")
    parser.add_argument("targets", nargs="+", help="Seed URLs")
    parser.add_argument("-w", "--workers", type=int, default=10)
    parser.add_argument("-m", "--max-pages", type=int, default=5000)
    parser.add_argument("-p", "--proxy", default=None)
    parser.add_argument("-o", "--output", default=None) 
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    result = run_swarm(
        args.targets,
        workers=args.workers,
        max_pages=args.max_pages,
        proxy=args.proxy,
        output=args.output,
        verbose=args.verbose,
    )

    print(f"\n=== Swarm Report ===")
    s = result["summary"]
    print(f"  Pages:      {s['total_pages']}")
    print(f"  URLs:       {s['unique_urls']}")
    print(f"  Secrets:    {s['secrets_found']}")
    print(f"  Wormholes:  {s['wormholes_detected']}")
    print(f"  Jumps:      {s['wormhole_jumps']}")
    print(f"  L4 indexed: {s['l4_indexed']}")
    print(f"  L12 indexed:{s['l12_indexed']}")
    print(f"  Time:       {s['elapsed_seconds']}s")
