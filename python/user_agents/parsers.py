"""Upstream-compatible objects built from the Mojo classifier."""

from __future__ import annotations

from collections import OrderedDict, namedtuple
from collections.abc import Iterable

from ._lib import classify

MOBILE_DEVICE_FAMILIES = (
    "iPhone",
    "iPod",
    "Generic Smartphone",
    "Generic Feature Phone",
    "PlayStation Vita",
    "iOS-Device",
)
PC_OS_FAMILIES = ("Windows 95", "Windows 98", "Solaris")
MOBILE_OS_FAMILIES = (
    "Windows Phone",
    "Windows Phone OS",
    "Symbian OS",
    "Bada",
    "Windows CE",
    "Windows Mobile",
    "Maemo",
)
MOBILE_BROWSER_FAMILIES = (
    "IE Mobile",
    "Opera Mobile",
    "Opera Mini",
    "Chrome Mobile",
    "Chrome Mobile WebView",
    "Chrome Mobile iOS",
)
TABLET_DEVICE_FAMILIES = (
    "iPad",
    "BlackBerry Playbook",
    "Blackberry Playbook",
    "Kindle",
    "Kindle Fire",
    "Kindle Fire HD",
    "Galaxy Tab",
    "Xoom",
    "Dell Streak",
)
TOUCH_CAPABLE_OS_FAMILIES = (
    "iOS",
    "Android",
    "Windows Phone",
    "Windows CE",
    "Windows Mobile",
    "Firefox OS",
    "MeeGo",
)
TOUCH_CAPABLE_DEVICE_FAMILIES = (
    "BlackBerry Playbook",
    "Blackberry Playbook",
    "Kindle Fire",
)
EMAIL_PROGRAM_FAMILIES = {
    "Outlook",
    "Windows Live Mail",
    "AirMail",
    "Apple Mail",
    "Thunderbird",
    "Lightning",
    "ThunderBrowse",
    "The Bat!",
    "Lotus Notes",
    "IBM Notes",
    "Barca",
    "MailBar",
    "kmail2",
    "YahooMobileMail",
}

BROWSER_FAMILIES = (
    "Other",
    "Chrome",
    "Edge",
    "Firefox",
    "Safari",
    "Mobile Safari",
    "Chrome Mobile",
    "Chrome Mobile WebView",
    "Chrome Mobile iOS",
    "Firefox iOS",
    "Opera",
    "Samsung Internet",
    "IE",
    "Googlebot",
    "bingbot",
    "Yahoo! Slurp",
    "DuckDuckBot",
    "Twitterbot",
    "FacebookBot",
    "Yandex Browser",
    "Opera Mini",
    "Opera Mobile",
    "UC Browser",
    "Electron",
    "Facebook",
    "Edge Mobile",
    "Firefox Mobile",
    "curl",
    "PostmanRuntime",
    "Python Requests",
    "Thunderbird",
    "HeadlessChrome",
)
OS_FAMILIES = (
    "Other",
    "Windows",
    "iOS",
    "Android",
    "Mac OS X",
    "Linux",
    "Chrome OS",
    "Windows Phone",
    "Ubuntu",
)

Browser = namedtuple("Browser", ["family", "version", "version_string"])
OperatingSystem = namedtuple(
    "OperatingSystem", ["family", "version", "version_string"]
)
Device = namedtuple("Device", ["family", "brand", "model"])
COMPONENT_CACHE_SIZE = 512
_component_cache = OrderedDict()


def verify_attribute(attribute):
    if isinstance(attribute, str) and attribute.isdigit():
        return int(attribute)
    return attribute


def parse_version(major=None, minor=None, patch=None, patch_minor=None):
    values = tuple(
        verify_attribute(value)
        for value in (major, minor, patch, patch_minor)
        if value is not None
    )
    return values


def parse_browser(family, major=None, minor=None, patch=None, patch_minor=None):
    version = parse_version(major, minor, patch)
    return Browser(family, version, ".".join(map(str, version)))


def parse_operating_system(
    family, major=None, minor=None, patch=None, patch_minor=None
):
    version = parse_version(major, minor, patch)
    return OperatingSystem(family, version, ".".join(map(str, version)))


def parse_device(family, brand, model):
    return Device(family, brand, model)


def _version(row, start):
    values = []
    for raw in row[start : start + 3]:
        value = int(raw)
        if value == -1:
            break
        if value == -4:
            raise OverflowError("version component exceeds signed int64 range")
        if value == -2:
            values.append("Vista")
        elif value == -3:
            values.append("XP")
        else:
            values.append(value)
    return tuple(values)


def _device(row, raw):
    code = int(row[8])
    fixed = {
        0: Device("Other", None, None),
        1: Device("iPhone", "Apple", "iPhone"),
        2: Device("iPad", "Apple", "iPad"),
        3: Device("iPod", "Apple", "iPod"),
        4: Device("Spider", "Spider", "Desktop"),
        5: Device("Mac", "Apple", "Mac"),
        10: Device("Generic Tablet", "Generic", "Tablet"),
        11: Device("Generic Smartphone", "Generic", "Smartphone"),
        12: Device("Generic Feature Phone", "Generic", "Feature Phone"),
    }
    if code in fixed:
        return fixed[code]
    start = int(row[9])
    end = start + int(row[10])
    model = raw[start:end].decode("utf-8")
    if code == 6:
        return Device(model, "Google", model)
    if code == 7:
        return Device(f"Samsung {model}", "Samsung", model)
    if code == 8:
        return Device(f"XiaoMi {model}", "XiaoMi", model)
    return Device(model, "Generic_Android", model)


def _components_from_record(raw, row):
    browser_version = _version(row, 1)
    os_version = _version(row, 5)
    browser = Browser(
        BROWSER_FAMILIES[int(row[0])],
        browser_version,
        ".".join(map(str, browser_version)),
    )
    operating_system = OperatingSystem(
        OS_FAMILIES[int(row[4])],
        os_version,
        ".".join(map(str, os_version)),
    )
    return browser, operating_system, _device(row, raw)


class UserAgent:
    def __init__(self, user_agent_string, browser=None, os=None, device=None):
        if browser is None:
            parsed = parse_many([user_agent_string])[0]
            browser, os, device = parsed.browser, parsed.os, parsed.device
        self.ua_string = user_agent_string
        self.os = os
        self.browser = browser
        self.device = device

    def __str__(self):
        return f"{self.get_device()} / {self.get_os()} / {self.get_browser()}"

    def __unicode__(self):
        return str(self)

    def _is_android_tablet(self):
        return (
            "Mobile Safari" not in self.ua_string
            and self.browser.family != "Firefox Mobile"
        )

    def _is_blackberry_touch_capable_device(self):
        return (
            "Blackberry 99" in self.device.family
            or "Blackberry 95" in self.device.family
        )

    def get_device(self):
        return "PC" if self.is_pc else self.device.family

    def get_os(self):
        return f"{self.os.family} {self.os.version_string}".strip()

    def get_browser(self):
        return f"{self.browser.family} {self.browser.version_string}".strip()

    @property
    def is_tablet(self):
        if self.device.family in TABLET_DEVICE_FAMILIES:
            return True
        if self.os.family == "Android" and self._is_android_tablet():
            return True
        if self.os.family == "Windows" and self.os.version_string.startswith("RT"):
            return True
        return self.os.family == "Firefox OS" and "Mobile" not in self.browser.family

    @property
    def is_mobile(self):
        if self.device.family in MOBILE_DEVICE_FAMILIES:
            return True
        if self.browser.family in MOBILE_BROWSER_FAMILIES:
            return True
        if self.os.family in ("Android", "Firefox OS") and not self.is_tablet:
            return True
        if (
            self.os.family == "BlackBerry OS"
            and self.device.family != "Blackberry Playbook"
        ):
            return True
        if self.os.family in MOBILE_OS_FAMILIES:
            return True
        if "J2ME" in self.ua_string or "MIDP" in self.ua_string:
            return True
        if "iPhone;" in self.ua_string or "Googlebot-Mobile" in self.ua_string:
            return True
        if self.device.family == "Spider" and "Mobile" in self.browser.family:
            return True
        return "NokiaBrowser" in self.ua_string and "Mobile" in self.ua_string

    @property
    def is_touch_capable(self):
        if self.os.family in TOUCH_CAPABLE_OS_FAMILIES:
            return True
        if self.device.family in TOUCH_CAPABLE_DEVICE_FAMILIES:
            return True
        if self.os.family == "Windows":
            if self.os.version_string.startswith(("RT", "CE")):
                return True
            if self.os.version_string.startswith("8") and "Touch" in self.ua_string:
                return True
        return (
            "BlackBerry" in self.os.family
            and self._is_blackberry_touch_capable_device()
        )

    @property
    def is_pc(self):
        if (
            "Windows NT" in self.ua_string
            or self.os.family in PC_OS_FAMILIES
            or (self.os.family == "Windows" and self.os.version_string == "ME")
        ):
            return True
        if self.os.family == "Mac OS X" and "Silk" not in self.ua_string:
            return True
        if "Maemo" in self.ua_string:
            return False
        if "Chrome OS" in self.os.family:
            return True
        return "Linux" in self.ua_string and "X11" in self.ua_string

    @property
    def is_bot(self):
        return self.device.family == "Spider"

    @property
    def is_email_client(self):
        return self.browser.family in EMAIL_PROGRAM_FAMILIES


def parse_many(user_agent_strings: Iterable[str]):
    strings = list(user_agent_strings)
    components_by_value = {}
    missing = []
    for value in strings:
        if not isinstance(value, str):
            raise TypeError("user agent must be a string")
        if value in components_by_value:
            continue
        components = _component_cache.get(value)
        if components is None:
            missing.append(value)
            components_by_value[value] = None
        else:
            _component_cache.move_to_end(value)
            components_by_value[value] = components

    if missing:
        joined, offsets, records = classify(missing)
        cache_new = len(missing) <= COMPONENT_CACHE_SIZE
        for index, value in enumerate(missing):
            start = int(offsets[index])
            end = int(offsets[index + 1])
            components = _components_from_record(
                joined[start:end], records[index]
            )
            components_by_value[value] = components
            if cache_new:
                _component_cache[value] = components
                _component_cache.move_to_end(value)
                if len(_component_cache) > COMPONENT_CACHE_SIZE:
                    _component_cache.popitem(last=False)

    return [
        UserAgent(value, *components_by_value[value])
        for value in strings
    ]


def parse(user_agent_string):
    return parse_many([user_agent_string])[0]
