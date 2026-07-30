"""mojo-user-agents against user-agents on identical unique strings."""

from __future__ import annotations

import gc
import importlib
import math
import os
import platform
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_PYTHON = os.path.join(ROOT, "python")


def import_implementations():
    sys.path = [
        path
        for path in sys.path
        if os.path.abspath(path or os.getcwd()) != os.path.abspath(REPO_PYTHON)
    ]
    upstream = importlib.import_module("user_agents")
    for name in list(sys.modules):
        if name == "user_agents" or name.startswith("user_agents."):
            del sys.modules[name]
    sys.path.insert(0, REPO_PYTHON)
    ours = importlib.import_module("user_agents")
    return ours, upstream


ours, upstream = import_implementations()


def best_time(function, repeats=3):
    function()
    best = math.inf
    result = None
    for _ in range(repeats):
        gc.collect()
        start = time.perf_counter()
        result = function()
        best = min(best, time.perf_counter() - start)
    return best, result


def cpu_name():
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as source:
            for line in source:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown CPU"


BASES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
    "AppleWebKit/605.1.15 Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UQ1A; wv) "
    "AppleWebKit/537.36 Version/4.0 Chrome/121.0.6167.101 Mobile Safari/537.36",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
]


def signature(agent):
    return (
        tuple(agent.browser),
        tuple(agent.os),
        tuple(agent.device),
        agent.is_mobile,
        agent.is_tablet,
        agent.is_pc,
        agent.is_bot,
    )


def reference(values):
    return [upstream.parse(value) for value in values]


def print_row(name, mojo_time, reference_time):
    ratio = reference_time / mojo_time
    result = "faster" if ratio >= 1 else "slower"
    print(
        f"| {name} | {mojo_time * 1e3:.2f} ms | "
        f"{reference_time * 1e3:.2f} ms | {ratio:.2f}x | {result} |"
    )


def main():
    values = [
        f"{BASES[index % len(BASES)]} sample-id/{index}"
        for index in range(2_000)
    ]
    print(f"Machine: {cpu_name()}; {os.cpu_count()} logical CPUs")
    print(
        f"Software: Python {platform.python_version()}, "
        f"user-agents {'.'.join(map(str, upstream.VERSION))}; best of 3 warm runs"
    )
    print()
    print("| case | mojo-user-agents | user-agents | ratio | result |")
    print("|---|---:|---:|---:|---|")

    mojo_time, mojo_result = best_time(lambda: ours.parse_many(values))
    reference_time, reference_result = best_time(lambda: reference(values))
    if [signature(value) for value in mojo_result] != [
        signature(value) for value in reference_result
    ]:
        raise AssertionError("benchmark parser outputs differ")
    print_row("parse 2,000 unique mixed UAs", mojo_time, reference_time)

    repeated = [BASES[0]] * 2_000
    mojo_time, mojo_result = best_time(lambda: ours.parse_many(repeated))
    reference_time, reference_result = best_time(lambda: reference(repeated))
    if [signature(value) for value in mojo_result] != [
        signature(value) for value in reference_result
    ]:
        raise AssertionError("repeated benchmark parser outputs differ")
    print_row("parse_many 2,000 repeated UAs", mojo_time, reference_time)

    def parse_repeated(implementation):
        result = None
        for _ in range(2_000):
            result = implementation.parse(BASES[0])
        return result

    mojo_time, mojo_result = best_time(lambda: parse_repeated(ours))
    reference_time, reference_result = best_time(lambda: parse_repeated(upstream))
    if signature(mojo_result) != signature(reference_result):
        raise AssertionError("single parser outputs differ")
    print_row("parse one cached UA 2,000 times", mojo_time, reference_time)


if __name__ == "__main__":
    main()
