"""Fast classification of common user-agent strings in packed UTF-8 buffers."""

comptime BPtr = UnsafePointer[UInt8, AnyOrigin[mut=True]]
comptime IPtr = UnsafePointer[Int64, AnyOrigin[mut=True]]
comptime RECORD_SIZE = 12


def find_marker(src: BPtr, start: Int, end: Int, marker: StringSlice) -> Int:
    var needle = marker.as_bytes()
    var size = len(needle)
    if size == 0:
        return start
    var i = start
    while i + size <= end:
        if src[i] == needle[0]:
            var equal = True
            for j in range(1, size):
                if src[i + j] != needle[j]:
                    equal = False
                    break
            if equal:
                return i + size
        i += 1
    return -1


def has(src: BPtr, start: Int, end: Int, marker: StringSlice) -> Bool:
    return find_marker(src, start, end, marker) >= 0


def parse_version(src: BPtr, position: Int, end: Int, result: IPtr, slot: Int):
    if position < 0:
        return
    var cursor = position
    for component in range(3):
        if cursor >= end or src[cursor] < UInt8(48) or src[cursor] > UInt8(57):
            break
        var value = 0
        while cursor < end and src[cursor] >= UInt8(48) and src[cursor] <= UInt8(57):
            var digit = Int(src[cursor] - UInt8(48))
            if value > (9223372036854775807 - digit) // 10:
                # Python turns this sentinel into an explicit OverflowError.
                result[slot + component] = -4
                return
            value = value * 10 + digit
            cursor += 1
        result[slot + component] = Int64(value)
        if cursor >= end or (src[cursor] != UInt8(46) and src[cursor] != UInt8(95)):
            break
        cursor += 1


def trim_left(src: BPtr, start: Int, end: Int) -> Int:
    var i = start
    while i < end and src[i] == UInt8(32):
        i += 1
    return i


def trim_right(src: BPtr, start: Int, end: Int) -> Int:
    var i = end
    while i > start and src[i - 1] == UInt8(32):
        i -= 1
    return i


def android_model(src: BPtr, start: Int, end: Int, android_after: Int, result: IPtr):
    if android_after < 0:
        return
    var close = android_after
    while close < end and src[close] != UInt8(41):
        close += 1
    var version_end = android_after
    while (
        version_end < close
        and (
            (src[version_end] >= UInt8(48) and src[version_end] <= UInt8(57))
            or src[version_end] == UInt8(46)
            or src[version_end] == UInt8(95)
        )
    ):
        version_end += 1
    if version_end >= close or src[version_end] != UInt8(59):
        return
    var build_after = find_marker(src, android_after, close, " Build/")
    var model_end = build_after - 7 if build_after >= 0 else close
    var model_start = version_end + 1
    for i in range(version_end + 1, model_end):
        if src[i] == UInt8(59):
            model_start = i + 1
    model_start = trim_left(src, model_start, model_end)
    model_end = trim_right(src, model_start, model_end)
    if model_end <= model_start:
        return
    if (
        (model_end - model_start == 1 and src[model_start] == UInt8(85))
        or (model_end - model_start == 2 and src[model_start] == UInt8(119)
            and src[model_start + 1] == UInt8(118))
        or has(src, model_start, model_end, "Mobile")
        or has(src, model_start, model_end, "Tablet")
        or has(src, model_start, model_end, "rv:")
    ):
        return
    result[9] = Int64(model_start - start)
    result[10] = Int64(model_end - model_start)


def parse_one(src: BPtr, start: Int, end: Int, result: IPtr):
    for i in range(RECORD_SIZE):
        result[i] = -1
    result[0] = 0
    result[4] = 0
    result[8] = 0
    result[9] = 0
    result[10] = 0
    result[11] = 1

    var android_after = find_marker(src, start, end, "Android ")
    var is_android = android_after >= 0 or has(src, start, end, "(Android)")
    var is_ios = (
        has(src, start, end, "iPhone")
        or has(src, start, end, "iPad")
        or has(src, start, end, "iPod")
    )

    # OS codes are decoded by the Python object layer.
    var position = find_marker(src, start, end, "Windows Phone ")
    if position >= 0:
        result[4] = 7
        parse_version(src, position, end, result, 5)
    else:
        position = find_marker(src, start, end, "iPhone OS ")
        if position < 0:
            position = find_marker(src, start, end, "CPU OS ")
        if position >= 0:
            result[4] = 2
            parse_version(src, position, end, result, 5)
        elif android_after >= 0:
            result[4] = 3
            parse_version(src, android_after, end, result, 5)
        elif is_android:
            result[4] = 3
        else:
            position = find_marker(src, start, end, "CrOS ")
            if position >= 0:
                result[4] = 6
                while position < end and src[position] != UInt8(32):
                    position += 1
                parse_version(src, position + 1, end, result, 5)
            elif has(src, start, end, "Windows NT 10.0") or has(src, start, end, "Windows NT 6.4"):
                result[4] = 1
                result[5] = 10
            elif has(src, start, end, "Windows NT 6.3"):
                result[4] = 1
                result[5] = 8
                result[6] = 1
            elif has(src, start, end, "Windows NT 6.2"):
                result[4] = 1
                result[5] = 8
            elif has(src, start, end, "Windows NT 6.1"):
                result[4] = 1
                result[5] = 7
            elif has(src, start, end, "Windows NT 6.0"):
                result[4] = 1
                result[5] = -2
            elif has(src, start, end, "Windows NT 5.2") or has(src, start, end, "Windows NT 5.1"):
                result[4] = 1
                result[5] = -3
            elif has(src, start, end, "Windows NT 5.0"):
                result[4] = 1
                result[5] = 2000
            elif has(src, start, end, "Mac OS X "):
                result[4] = 4
                position = find_marker(src, start, end, "Mac OS X ")
                parse_version(src, position, end, result, 5)
            elif has(src, start, end, "Ubuntu"):
                result[4] = 8
            elif has(src, start, end, "Linux"):
                result[4] = 5

    # More specific browser tokens must precede the Chromium/Gecko fallbacks.
    position = find_marker(src, start, end, "facebookexternalhit/")
    if position >= 0:
        result[0] = 18
        parse_version(src, position, end, result, 1)
    else:
        position = find_marker(src, start, end, "Googlebot/")
        if position >= 0:
            result[0] = 13
            parse_version(src, position, end, result, 1)
        else:
            position = find_marker(src, start, end, "bingbot/")
            if position >= 0:
                result[0] = 14
                parse_version(src, position, end, result, 1)
            else:
                position = find_marker(src, start, end, "DuckDuckBot/")
                if position >= 0:
                    result[0] = 16
                    parse_version(src, position, end, result, 1)
                else:
                    position = find_marker(src, start, end, "Twitterbot/")
                    if position >= 0:
                        result[0] = 17
                        parse_version(src, position, end, result, 1)
                    elif has(src, start, end, "Yahoo! Slurp"):
                        result[0] = 15
                    else:
                        position = find_marker(src, start, end, "FBAV/")
                        if position >= 0:
                            result[0] = 24
                            parse_version(src, position, end, result, 1)
                        else:
                            position = find_marker(src, start, end, "Electron/")
                            if position >= 0:
                                result[0] = 23
                                parse_version(src, position, end, result, 1)
                            else:
                                position = find_marker(src, start, end, "EdgiOS/")
                                if position >= 0:
                                    result[0] = 25
                                    parse_version(src, position, end, result, 1)
                                else:
                                    position = find_marker(src, start, end, "EdgA/")
                                    if position >= 0:
                                        result[0] = 25
                                        parse_version(src, position, end, result, 1)
                                    else:
                                        position = find_marker(src, start, end, "Edg/")
                                        if position < 0:
                                            position = find_marker(src, start, end, "Edge/")
                                        if position >= 0:
                                            result[0] = 25 if result[4] == 7 else 2
                                            parse_version(src, position, end, result, 1)
                                        else:
                                            position = find_marker(src, start, end, "OPR/")
                                            if position >= 0:
                                                result[0] = 10
                                                parse_version(src, position, end, result, 1)
                                            else:
                                                position = find_marker(src, start, end, "Opera Mini/")
                                                if position >= 0:
                                                    result[0] = 20
                                                    parse_version(src, position, end, result, 1)
                                                elif has(src, start, end, "Opera Mobi"):
                                                    result[0] = 21
                                                else:
                                                    position = find_marker(src, start, end, "SamsungBrowser/")
                                                    if position >= 0:
                                                        result[0] = 11
                                                        parse_version(src, position, end, result, 1)
                                                    else:
                                                        position = find_marker(src, start, end, "UCBrowser/")
                                                        if position >= 0:
                                                            result[0] = 22
                                                            parse_version(src, position, end, result, 1)
                                                        else:
                                                            position = find_marker(src, start, end, "YaBrowser/")
                                                            if position >= 0:
                                                                result[0] = 19
                                                                parse_version(src, position, end, result, 1)
                                                            else:
                                                                position = find_marker(src, start, end, "CriOS/")
                                                                if position >= 0:
                                                                    result[0] = 8
                                                                    parse_version(src, position, end, result, 1)
                                                                else:
                                                                    position = find_marker(src, start, end, "FxiOS/")
                                                                    if position >= 0:
                                                                        result[0] = 9
                                                                        parse_version(src, position, end, result, 1)
                                                                    else:
                                                                        position = find_marker(src, start, end, "HeadlessChrome/")
                                                                        if position >= 0:
                                                                            result[0] = 31
                                                                            parse_version(src, position, end, result, 1)
                                                                        else:
                                                                            position = find_marker(src, start, end, "Firefox/")
                                                                            if position >= 0:
                                                                                result[0] = 26 if is_android else 3
                                                                                parse_version(src, position, end, result, 1)
                                                                            else:
                                                                                position = find_marker(src, start, end, "Chrome/")
                                                                                if position >= 0:
                                                                                    result[0] = Int64(7 if is_android and has(src, start, end, "; wv)") else (6 if is_android and has(src, start, end, "Mobile") else 1))
                                                                                    parse_version(src, position, end, result, 1)
                                                                                else:
                                                                                    position = find_marker(src, start, end, "Version/")
                                                                                    if position >= 0 and has(src, start, end, "Safari/"):
                                                                                        result[0] = 5 if is_ios else 4
                                                                                        parse_version(src, position, end, result, 1)
                                                                                    else:
                                                                                        position = find_marker(src, start, end, "MSIE ")
                                                                                        if position < 0 and has(src, start, end, "Trident/"):
                                                                                            position = find_marker(src, start, end, "rv:")
                                                                                        if position >= 0:
                                                                                            result[0] = 12
                                                                                            parse_version(src, position, end, result, 1)
                                                                                        else:
                                                                                            position = find_marker(src, start, end, "curl/")
                                                                                            if position >= 0:
                                                                                                result[0] = 27
                                                                                                parse_version(src, position, end, result, 1)
                                                                                            else:
                                                                                                position = find_marker(src, start, end, "PostmanRuntime/")
                                                                                                if position >= 0:
                                                                                                    result[0] = 28
                                                                                                    parse_version(src, position, end, result, 1)
                                                                                                else:
                                                                                                    position = find_marker(src, start, end, "python-requests/")
                                                                                                    if position >= 0:
                                                                                                        result[0] = 29
                                                                                                        parse_version(src, position, end, result, 1)
                                                                                                        result[3] = -1
                                                                                                    else:
                                                                                                        position = find_marker(src, start, end, "Thunderbird/")
                                                                                                        if position >= 0:
                                                                                                            result[0] = 30
                                                                                                            parse_version(src, position, end, result, 1)

    var browser = Int(result[0])
    if browser >= 13 and browser <= 18:
        result[8] = 4
    elif has(src, start, end, "iPad"):
        result[8] = 2
    elif has(src, start, end, "iPod"):
        result[8] = 3
    elif has(src, start, end, "iPhone"):
        result[8] = 1
    elif has(src, start, end, "Macintosh"):
        result[8] = 5
    elif is_android:
        if has(src, start, end, "Tablet;") or has(src, start, end, "; Tablet;"):
            result[8] = 10
        else:
            android_model(src, start, end, android_after, result)
            if result[10] > 0:
                var model_start = start + Int(result[9])
                var model_end = model_start + Int(result[10])
                if has(src, model_start, model_end, "Pixel"):
                    result[8] = 6
                elif has(src, model_start, model_end, "SM-"):
                    result[8] = 7
                elif has(src, model_start, model_end, "Redmi"):
                    result[8] = 8
                else:
                    result[8] = 9
            else:
                result[8] = 11
    elif browser == 20:
        result[8] = 12
    elif browser == 21 or browser == 24:
        result[8] = 11


@export("mua_parse_many")
def mua_parse_many(
    data_addr: Int,
    data_len: Int,
    offsets_addr: Int,
    offsets_len: Int,
    count: Int,
    results_addr: Int,
    results_len: Int,
) abi("C") -> Int:
    if count < 0 or data_len < 0 or offsets_len < 0 or results_len < 0:
        return -1
    if count == 0:
        return 0
    if data_addr == 0 or offsets_addr == 0 or results_addr == 0:
        return -2
    if offsets_addr % 8 != 0 or results_addr % 8 != 0:
        return -3
    # Written this way rather than count + 1 / count * RECORD_SIZE so hostile
    # ABI callers cannot overflow the capacity checks themselves.
    if offsets_len <= count or count > results_len // RECORD_SIZE:
        return -4

    var data = BPtr(unsafe_from_address=data_addr)
    var offsets = IPtr(unsafe_from_address=offsets_addr)
    var results = IPtr(unsafe_from_address=results_addr)
    if offsets[0] != 0:
        return -5
    for index in range(count):
        var start = Int(offsets[index])
        var end = Int(offsets[index + 1])
        if start < 0 or end < start or end > data_len:
            return -5
        parse_one(
            data,
            start,
            end,
            results + index * RECORD_SIZE,
        )
    return count
