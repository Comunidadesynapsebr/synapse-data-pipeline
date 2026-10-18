from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
from bs4 import BeautifulSoup

from .config import Config


class RateLimiter:
    def __init__(self, rate: float):
        self.delay = 1.0 / max(rate, 0.01)
        self.lock = asyncio.Lock()
        self.last = 0.0

    async def wait(self) -> None:
        async with self.lock:
            now = time.monotonic()
            pause = self.delay - (now - self.last)
            if pause > 0:
                await asyncio.sleep(pause)
            self.last = time.monotonic()


async def _robots_allowed(session: aiohttp.ClientSession, url: str, ua: str, cache: dict[str, RobotFileParser]) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in cache:
        rp = RobotFileParser()
        rp.set_url(origin + "/robots.txt")
        try:
            async with session.get(rp.url, timeout=10) as response:
                if response.status == 200:
                    rp.parse((await response.text()).splitlines())
                else:
                    rp.parse([])
        except (aiohttp.ClientError, asyncio.TimeoutError):
            rp.parse([])
        cache[origin] = rp
    return cache[origin].can_fetch(ua, url)


def _record(url: str, html: str, meta: dict) -> dict:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return {
        "id": hashlib.sha256(url.encode()).hexdigest()[:24],
        "text": text,
        "source_url": url,
        "source_title": meta.get("title", ""),
        "license": meta.get("license", "unknown"),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


async def collect(manifest: str | Path, out: str | Path, cfg: Config) -> int:
    c = cfg.collection
    ua = c.get("user_agent", "SynapseDataPipeline/0.1")
    timeout = aiohttp.ClientTimeout(total=int(c.get("timeout_seconds", 30)))
    headers = {"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9"}
    allowed = set(c.get("allowed_domains", []))
    blocked = set(c.get("blocked_domains", []))
    max_bytes = int(c.get("max_bytes_per_document", 50_000_000))
    limiter = RateLimiter(float(c.get("requests_per_second", 2)))
    sem = asyncio.Semaphore(int(c.get("concurrency", 8)))
    robots: dict[str, RobotFileParser] = {}
    rows: list[dict] = []

    with Path(manifest).open(encoding="utf-8") as fh:
        entries = [json.loads(line) for line in fh if line.strip()]

    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        async def one(entry: dict) -> dict | None:
            url = entry["url"]
            parsed = urlparse(url)
            if parsed.scheme not in set(c.get("allowed_schemes", ["https"])):
                return None
            if parsed.hostname in blocked or (allowed and parsed.hostname not in allowed):
                return None
            async with sem:
                await limiter.wait()
                if c.get("respect_robots_txt", True) and not await _robots_allowed(session, url, ua, robots):
                    return None
                try:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        body = await response.content.read(max_bytes + 1)
                        if len(body) > max_bytes:
                            return None
                        return _record(url, body.decode(response.charset or "utf-8", errors="replace"), entry)
                except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeError):
                    return None

        results = await asyncio.gather(*(one(e) for e in entries))
        rows = [r for r in results if r and r.get("text")]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with Path(out).open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)
