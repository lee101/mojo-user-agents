from __future__ import annotations

import importlib
import os
import sys

import numpy as np
import pytest

import user_agents as ours
from user_agents import _lib, parsers


def load_upstream():
    repo_python = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "python")
    )
    held = {
        name: module
        for name, module in sys.modules.items()
        if name == "user_agents" or name.startswith("user_agents.")
    }
    for name in held:
        del sys.modules[name]
    old_path = sys.path[:]
    sys.path = [
        path
        for path in sys.path
        if os.path.abspath(path or os.getcwd()) != repo_python
    ]
    try:
        upstream = importlib.import_module("user_agents")
    finally:
        for name in list(sys.modules):
            if name == "user_agents" or name.startswith("user_agents."):
                del sys.modules[name]
        sys.modules.update(held)
        sys.path = old_path
    return upstream


upstream = load_upstream()

VECTORS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.67",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "Chrome/121.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 Chrome/120.0.0.0 YaBrowser/23.11.2.806 "
    "Yowser/2.5 Safari/537.36",
    "Electron/30.0.0 Chrome/124.0.0.0 Safari/537.36",
    "HeadlessChrome/124.0.6367.91",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
    "AppleWebKit/605.1.15 Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPod touch; CPU iPhone OS 15_0 like Mac OS X) "
    "Version/15.0 Mobile Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) "
    "AppleWebKit/605.1.15 CriOS/121.0.6167.73 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) "
    "AppleWebKit/605.1.15 FxiOS/122.0 Mobile/15E148 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "EdgiOS/120.0 Mobile/15E148 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro Build/UQ1A.240205.004; wv) "
    "AppleWebKit/537.36 Version/4.0 Chrome/121.0.6167.101 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UP1A) "
    "AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-X700 Build/TP1A.220624.014) "
    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 "
    "SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; U; Android 12; en-US; Redmi Note 9) "
    "AppleWebKit/537.36 UCBrowser/15.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Android 13; Mobile; rv:120.0) "
    "Gecko/120.0 Firefox/120.0",
    "Mozilla/5.0 (Android 13; Tablet; rv:120.0) "
    "Gecko/120.0 Firefox/120.0",
    "Opera Mini/36.2.2254/191.249",
    "Opera Mobi/12.10 (Android)",
    "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Mobile Safari/537.36 "
    "[FBAN/FB4A;FBAV/400.0.0.37.76;]",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; Yahoo! Slurp; "
    "http://help.yahoo.com/help/us/ysearch/slurp)",
    "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)",
    "Twitterbot/1.0",
    "facebookexternalhit/1.1 "
    "(+http://www.facebook.com/externalhit_uatext.php)",
    "curl/8.7.1",
    "PostmanRuntime/7.39.0",
    "python-requests/2.32.3",
    "Thunderbird/115.10.1",
    "Mozilla/5.0 (X11; CrOS x86_64 15917.63.0) "
    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Windows NT 6.3)",
    "Mozilla/5.0 (Windows NT 6.0)",
    "Mozilla/5.0 (Windows NT 5.1)",
    "Mozilla/5.0 (Windows NT 5.0)",
    "",
]

ADDITIONAL_COVERAGE_VECTORS = [
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "Chrome/120.0 Mobile Safari/537.36 EdgA/120.0",
    "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)",
    "Mozilla/5.0 (Windows NT 6.2)",
    "Mozilla/5.0 (Linux; Android 12; FooPhone Build/SKQ1; wv) "
    "AppleWebKit/537.36 Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36",
]


def signature(agent):
    return (
        tuple(agent.browser),
        tuple(agent.os),
        tuple(agent.device),
        agent.get_browser(),
        agent.get_os(),
        agent.get_device(),
        str(agent),
        agent.is_mobile,
        agent.is_tablet,
        agent.is_pc,
        agent.is_touch_capable,
        agent.is_bot,
        agent.is_email_client,
    )


@pytest.mark.parametrize("user_agent", VECTORS)
def test_parse_matches_upstream(user_agent):
    assert signature(ours.parse(user_agent)) == signature(upstream.parse(user_agent))


def test_parse_many_matches_repeated_upstream_parse():
    values = VECTORS + [VECTORS[0], VECTORS[9], "curl/8.7.1"]
    actual = ours.parse_many(values)
    expected = [upstream.parse(value) for value in values]
    assert [signature(value) for value in actual] == [
        signature(value) for value in expected
    ]
    assert [value.ua_string for value in actual] == values


def test_documented_family_coverage_is_explicit_and_matches_upstream():
    values = VECTORS + ADDITIONAL_COVERAGE_VECTORS
    actual = [ours.parse(value) for value in values]
    expected = [upstream.parse(value) for value in values]
    assert [signature(value) for value in actual] == [
        signature(value) for value in expected
    ]
    assert {value.browser.family for value in actual} == set(parsers.BROWSER_FAMILIES)
    assert {
        "Windows", "Mac OS X", "iOS", "Android", "Chrome OS", "Ubuntu", "Linux"
    } <= {value.os.family for value in actual}
    assert {
        "iPhone",
        "iPad",
        "iPod",
        "Mac",
        "Spider",
        "Generic Smartphone",
        "Generic Tablet",
        "Generic Feature Phone",
        "Pixel 8",
        "Samsung SM-S918B",
        "XiaoMi Redmi Note 9",
        "FooPhone",
    } <= {value.device.family for value in actual}


def test_parse_many_accepts_a_generator_and_empty_input():
    assert ours.parse_many([]) == []
    values = ours.parse_many(value for value in ("curl/8.7.1", "β-client"))
    assert values[0].browser.family == "curl"
    assert values[1].browser.family == "Other"
    assert values[1].ua_string == "β-client"


def test_repeated_inputs_are_classified_once_and_return_distinct_agents(monkeypatch):
    value = VECTORS[0]
    calls = []
    classify = parsers.classify

    def recording_classify(strings):
        calls.append(list(strings))
        return classify(strings)

    parsers._component_cache.clear()
    monkeypatch.setattr(parsers, "classify", recording_classify)
    try:
        agents = ours.parse_many([value, value, value])
        cached = ours.parse(value)
    finally:
        parsers._component_cache.clear()

    assert calls == [[value]]
    assert agents[0] is not agents[1]
    assert [signature(agent) for agent in agents] == [
        signature(upstream.parse(value))
    ] * 3
    assert signature(cached) == signature(upstream.parse(value))


def test_component_cache_is_bounded():
    values = [f"curl/8.7.{index}" for index in range(parsers.COMPONENT_CACHE_SIZE)]
    parsers._component_cache.clear()
    try:
        ours.parse_many(values)
        ours.parse("curl/9.0.0")
        assert len(parsers._component_cache) == parsers.COMPONENT_CACHE_SIZE
        assert values[0] not in parsers._component_cache
    finally:
        parsers._component_cache.clear()


def test_public_namedtuple_helpers_match_upstream():
    from user_agents import parsers as current

    upstream_parsers = upstream.parsers
    assert current.parse_version("1", "02", "beta", None) == (
        upstream_parsers.parse_version("1", "02", "beta", None)
    )
    assert tuple(current.parse_browser("Browser", "1", "2", "3")) == tuple(
        upstream_parsers.parse_browser("Browser", "1", "2", "3")
    )
    assert tuple(current.parse_operating_system("OS", "1", "2")) == tuple(
        upstream_parsers.parse_operating_system("OS", "1", "2")
    )
    assert tuple(current.parse_device("Phone", "Brand", "Model")) == tuple(
        upstream_parsers.parse_device("Phone", "Brand", "Model")
    )


def test_user_agent_constructor_and_attributes_match_upstream():
    value = VECTORS[15]
    actual = parsers.UserAgent(value)
    expected = upstream.parsers.UserAgent(value)
    assert actual.ua_string == expected.ua_string
    assert signature(actual) == signature(expected)


def test_non_string_input_is_rejected():
    with pytest.raises(TypeError, match="string"):
        ours.parse(None)


def test_ffi_rejects_invalid_pointers_capacities_and_offsets():
    function = _lib.lib().mua_parse_many
    data = np.array([ord("x")], dtype=np.uint8)
    offsets = np.array([0, 1], dtype=np.int64)
    results = np.empty(_lib.RECORD_SIZE, dtype=np.int64)
    data_address = _lib._address(data, np.dtype(np.uint8))
    offsets_address = _lib._address(offsets, np.dtype(np.int64))
    results_address = _lib._address(results, np.dtype(np.int64))

    assert function(0, 1, offsets_address, 2, 1, results_address, 12) == -2
    assert function(data_address, 1, offsets_address, 1, 1, results_address, 12) == -4
    assert function(data_address, 1, offsets_address, 2, 1, results_address, 11) == -4

    offsets[1] = 2
    assert function(data_address, 1, offsets_address, 2, 1, results_address, 12) == -5
    offsets[:] = (1, 1)
    assert function(data_address, 1, offsets_address, 2, 1, results_address, 12) == -5


def test_python_ffi_guard_rejects_wrong_dtype_and_stride():
    values = np.arange(8, dtype=np.int64)
    with pytest.raises(TypeError, match="expected uint8"):
        _lib._address(values, np.dtype(np.uint8))
    with pytest.raises(ValueError, match="C-contiguous"):
        _lib._address(values[::2], np.dtype(np.int64))


def test_oversized_version_component_is_not_silently_narrowed():
    with pytest.raises(OverflowError, match="int64"):
        ours.parse("curl/9999999999999999999")
