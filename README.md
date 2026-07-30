# mojo-user-agents

`mojo-user-agents` is a standalone port of the common parsing path from
[user-agents](https://pypi.org/project/user-agents/) to Mojo. It exposes the
same `user_agents.parse(user_agent_string)` entry point, namedtuple-shaped
browser/OS/device results, `UserAgent` properties, and display helpers for the
covered subset. It does not import `user-agents` or `ua-parser` at runtime.

This is a focused parser, not a copy of the entire uap-core regex database.
Its native classifier targets the browser, operating-system, device, bot, and
HTTP-client families that dominate ordinary web traffic. Unknown input is
reported with upstream's `Other` values rather than guessed.

## Coverage

The implemented browser and client families are:

- Chrome, Chrome Mobile, Chrome Mobile WebView, Chrome Mobile iOS, and
  HeadlessChrome
- Edge and Edge Mobile, including Chromium Android and iOS tokens
- Firefox, Firefox Mobile, and Firefox iOS
- Safari and Mobile Safari
- Opera, Opera Mini, Opera Mobile, Samsung Internet, UC Browser, Yandex
  Browser, Electron, and Facebook's in-app browser
- IE 11 and older `MSIE` tokens
- Googlebot, bingbot, Yahoo! Slurp, DuckDuckBot, Twitterbot, and FacebookBot
- curl, PostmanRuntime, Python Requests, and Thunderbird

Operating-system coverage includes Windows 2000 through Windows 10, macOS,
iOS, Android, Chrome OS, Ubuntu, and generic Linux.
Device coverage includes iPhone, iPad, iPod, Mac, spiders, generic
smartphones/tablets/feature phones, Google Pixel, Samsung `SM-` models, Xiaomi
Redmi models, and generic Android model extraction. Browser and OS versions
contain up to the same three components retained by `user-agents` 2.2.0.

The upstream-compatible API includes:

- `parse(user_agent_string)`
- `Browser`, `OperatingSystem`, `Device`, and `UserAgent` in
  `user_agents.parsers`
- `parse_version`, `parse_browser`, `parse_operating_system`, and
  `parse_device`
- `get_browser`, `get_os`, `get_device`, `is_mobile`, `is_tablet`, `is_pc`,
  `is_touch_capable`, `is_bot`, and `is_email_client`
- `parse_many(iterable)`, a port-specific batch extension that amortizes FFI
  and object-construction overhead

The parity suite compares complete namedtuple values, formatted strings, and
all convenience predicates against the real `user-agents` 2.2.0 package over
desktop, mobile, tablet, crawler, HTTP-client, and unknown published-style
user-agent vectors.

Not covered are the long tail of the full uap-core database: full-record
Windows Phone parity (the OS token is recognized, but device details may
differ), legacy feature phones, game consoles, smart TVs, unusual embedded
webviews, most email clients, the many less common crawlers and native
applications, and custom regex rule files. Uncovered inputs produce partial
results or `Other`; they are not guaranteed to match upstream. This package
is therefore not a general replacement for every rule in `ua-parser`.

## Install

From the repository checkout:

```bash
pixi install
pixi run build
pixi run test
```

The build produces `dist/libmojo-user-agents.so`. Pixi sets
`PYTHONPATH=python`, so the package runs directly from the checkout.
`user-agents` 2.2.0 is installed only as the development parity reference.

## Usage

```python
from user_agents import parse, parse_many

ua = parse(
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
    "AppleWebKit/605.1.15 Version/17.4 Mobile/15E148 Safari/604.1"
)

assert ua.browser.family == "Mobile Safari"
assert ua.browser.version == (17, 4)
assert ua.os.family == "iOS"
assert ua.device.family == "iPhone"
assert ua.is_mobile and ua.is_touch_capable

agents = parse_many(["curl/8.7.1", "Twitterbot/1.0"])
assert agents[0].browser.family == "curl"
assert agents[1].is_bot
```

## Benchmarks

Measured with `pixi run bench` on an Intel Xeon E5-2697 v4 at 2.30 GHz,
72 logical CPUs, Python 3.13.14, and `user-agents` 2.2.0. The workload has
2,000 unique mixed desktop, mobile, and bot strings so the upstream regex
cache cannot turn that comparison into a repeated dictionary lookup. Two
cache-friendly workloads also measure repeated batch and single-value parsing.
Times are the best of three warm runs. Ratio is upstream time divided by
mojo-user-agents time. The benchmark validates all browser, OS, and device
results and classification predicates before printing.

| case | mojo-user-agents | user-agents | ratio | result |
|---|---:|---:|---:|---|
| parse 2,000 unique mixed UAs | 29.62 ms | 2600.51 ms | 87.80x | faster |
| parse_many 2,000 repeated UAs | 1.46 ms | 17.53 ms | 12.03x | faster |
| parse one cached UA 2,000 times | 3.25 ms | 15.96 ms | 4.91x | faster |

The speedup comes from replacing an ordered scan through hundreds of regular
expressions with a bounded set of literal token scans for the explicitly
covered families. Repeated strings reuse a bounded cache of immutable parsed
components, and duplicate strings in one batch are classified only once. It
should not be interpreted as equivalent coverage of the full uap-core ruleset.

No GPU, SIMD, or threaded path is included.

## How it works

`parse_many` UTF-8 encodes its input into one contiguous `uint8` buffer and
builds an `int64` offset array. Python allocates a fixed 12-`int64` result
record per string, then passes the three buffer addresses and record count
through `ctypes`. The call includes the byte and element capacities. A single
exported Mojo function validates non-null and aligned pointers, capacities,
and monotonic in-range offsets before reconstructing the buffers as
`UnsafePointer[..., AnyOrigin[mut=True]]` and classifying the complete batch.

Each result record carries numeric browser, OS, and device family codes,
three browser version components, three OS version components, and a
zero-copy byte range for an Android model. Mojo never allocates memory across
the ABI. Python maps the compact records to upstream-compatible namedtuples
and `UserAgent` objects. A bounded 512-entry cache retains only those immutable
components; every call still returns a distinct `UserAgent`. Batch callers
also deduplicate identical strings before packing NumPy views and crossing
FFI. Python retains the packed bytes, offsets, and result arrays for the whole
native call, and rejects buffers with the wrong dtype, stride, or alignment.

The classifier applies specific tokens before generic engine tokens: for
example, `SamsungBrowser/`, `Edg/`, and `OPR/` win before `Chrome/`, while
mobile Safari requires both an Apple mobile device token and `Version/`.
Device and convenience-property decisions then follow `user-agents` 2.2.0's
observable behavior.

MIT.
