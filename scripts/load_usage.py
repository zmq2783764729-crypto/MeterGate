# 用途：测量本机新事件上报、幂等重放和分页查询的响应分位数。
import argparse
import json
import math
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="测量本机计量接口")
    parser.add_argument("mode", choices=["new", "replay", "list"])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--tenant", type=UUID)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    if urlsplit(args.url).hostname not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("仅支持本地服务")
    if not 1 <= args.requests <= 10000 or not 1 <= args.concurrency <= 100:
        parser.error("请求数须在 1 到 10000 之间，并发数须在 1 到 100 之间")
    token = os.getenv("MG_LOAD_BEARER") if args.mode == "list" else os.getenv("MG_LOAD_API_KEY")
    if not token or (args.mode == "list" and args.tenant is None):
        parser.error("请设置对应的凭据环境变量，分页模式还需要企业编号")
    headers = {"Authorization": f"Bearer {token}"} if args.mode == "list" else {"X-API-Key": token}
    sample = {
        "event_id": str(uuid4()),
        "metric": "data_query",
        "quantity": 1,
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    with httpx.Client(
        base_url=args.url, headers=headers, timeout=15, follow_redirects=False, trust_env=False
    ) as client:
        if (
            args.mode == "replay"
            and client.post("/v1/usage/events", json=sample).status_code != 200
        ):
            raise SystemExit("未能创建待重放事件")

        def run_request(_: int) -> tuple[str, float]:
            start = perf_counter()
            try:
                if args.mode == "list":
                    response = client.get(
                        f"/v1/tenants/{args.tenant}/usage/events", params={"limit": 20}
                    )
                else:
                    payload = {**sample, "event_id": str(uuid4())} if args.mode == "new" else sample
                    response = client.post("/v1/usage/events", json=payload)
                result = str(response.status_code)
            except httpx.HTTPError:
                result = "transport_error"
            return result, (perf_counter() - start) * 1000

        started = perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(pool.map(run_request, range(args.requests)))
        elapsed = perf_counter() - started
    durations = sorted(duration for _, duration in results)
    totals = Counter(code for code, _ in results)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "concurrency": args.concurrency,
                "requests": len(results),
                "status_counts": totals,
                "success_rate": totals["200"] / len(results),
                "p50_ms": round(durations[math.ceil(len(durations) * 0.50) - 1], 2),
                "p95_ms": round(durations[math.ceil(len(durations) * 0.95) - 1], 2),
                "requests_per_second": round(len(results) / elapsed, 2),
            }
        )
    )


if __name__ == "__main__":
    main()
