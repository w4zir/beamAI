"""
Simple benchmark script similar to Apache Bench (ab) for Windows.
Usage: python scripts/benchmark.py <url> [--requests=1000] [--concurrency=10]
"""
import asyncio
import httpx
import time
import sys
import argparse
from typing import List, Tuple
from statistics import mean, median, stdev


async def make_request(client: httpx.AsyncClient, url: str) -> Tuple[float, int, bool]:
    """Make a single HTTP request and return timing info."""
    start = time.time()
    try:
        response = await client.get(url, timeout=30.0)
        elapsed = time.time() - start
        return (elapsed, response.status_code, True)
    except Exception as e:
        elapsed = time.time() - start
        print(f"Request failed: {e}", file=sys.stderr)
        return (elapsed, 0, False)


async def run_benchmark(url: str, num_requests: int, concurrency: int):
    """Run benchmark with specified parameters."""
    print(f"Benchmarking {url}")
    print(f"Requests: {num_requests}, Concurrency: {concurrency}\n")
    
    async with httpx.AsyncClient() as client:
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request():
            async with semaphore:
                return await make_request(client, url)
        
        # Run all requests
        start_time = time.time()
        tasks = [bounded_request() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
    
    # Process results
    times = [r[0] for r in results]
    status_codes = [r[1] for r in results]
    successes = [r[2] for r in results]
    
    successful = sum(successes)
    failed = num_requests - successful
    
    # Calculate statistics
    if successful > 0:
        successful_times = [t for t, s in zip(times, successes) if s]
        avg_time = mean(successful_times)
        median_time = median(successful_times)
        min_time = min(successful_times)
        max_time = max(successful_times)
        if len(successful_times) > 1:
            stddev_time = stdev(successful_times)
        else:
            stddev_time = 0.0
    else:
        avg_time = median_time = min_time = max_time = stddev_time = 0.0
    
    # Print results (similar to ab output)
    print("=" * 60)
    print("Benchmark Results")
    print("=" * 60)
    print(f"Total requests:      {num_requests}")
    print(f"Successful requests: {successful}")
    print(f"Failed requests:     {failed}")
    print(f"Total time:          {total_time:.3f} seconds")
    print(f"Requests per second: {num_requests / total_time:.2f} [#/sec]")
    print(f"Time per request:    {total_time / num_requests * 1000:.2f} [ms] (mean)")
    if successful > 0:
        print(f"Time per request:    {avg_time * 1000:.2f} [ms] (mean, across all concurrent requests)")
        print(f"Time per request:    {median_time * 1000:.2f} [ms] (median)")
        print(f"Min request time:    {min_time * 1000:.2f} [ms]")
        print(f"Max request time:    {max_time * 1000:.2f} [ms]")
        print(f"Std deviation:       {stddev_time * 1000:.2f} [ms]")
    
    # Status code breakdown
    status_counts = {}
    for code in status_codes:
        status_counts[code] = status_counts.get(code, 0) + 1
    
    print("\nStatus code breakdown:")
    for code in sorted(status_counts.keys()):
        print(f"  {code}: {status_counts[code]}")


def main():
    parser = argparse.ArgumentParser(description="Benchmark HTTP endpoint")
    parser.add_argument("url", help="URL to benchmark")
    parser.add_argument("-n", "--requests", type=int, default=1000, help="Number of requests (default: 1000)")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Concurrency level (default: 10)")
    
    args = parser.parse_args()
    
    asyncio.run(run_benchmark(args.url, args.requests, args.concurrency))


if __name__ == "__main__":
    main()

