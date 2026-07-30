"""ctypes binding for the packed user-agent parser."""

from __future__ import annotations

import ctypes
import os
import subprocess
from collections.abc import Sequence

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(ROOT, "dist", "libmojo-user-agents.so")
I = ctypes.c_int64
RECORD_SIZE = 12
_STATUS_ERRORS = {
    -1: "negative length or record count",
    -2: "null pointer",
    -3: "misaligned int64 buffer",
    -4: "buffer capacity is too small",
    -5: "invalid offsets",
}
_library: ctypes.CDLL | None = None


class BuildError(RuntimeError):
    pass


def build(force: bool = False) -> str:
    source = os.path.join(ROOT, "src", "user_agents.mojo")
    if (
        not force
        and os.path.exists(LIB)
        and os.path.getmtime(LIB) >= os.path.getmtime(source)
    ):
        return LIB
    command = [
        "pixi",
        "run",
        "--manifest-path",
        os.path.join(ROOT, "pixi.toml"),
        "build",
    ]
    process = subprocess.run(
        command, capture_output=True, text=True, timeout=1800, cwd=ROOT
    )
    if process.returncode or not os.path.exists(LIB):
        raise BuildError((process.stderr or process.stdout).strip()[:4000])
    return LIB


def lib() -> ctypes.CDLL:
    global _library
    if _library is None:
        _library = ctypes.CDLL(build())
        function = _library.mua_parse_many
        function.argtypes = [I, I, I, I, I, I, I]
        function.restype = I
    return _library


def _address(array: np.ndarray, dtype: np.dtype) -> int:
    if array.dtype != dtype:
        raise TypeError(f"expected {dtype} buffer, got {array.dtype}")
    if not array.flags.c_contiguous:
        raise ValueError("FFI buffers must be C-contiguous")
    if not array.flags.aligned:
        raise ValueError("FFI buffers must be naturally aligned")
    address = int(array.ctypes.data)
    if not address:
        raise ValueError("cannot pass a null buffer to Mojo")
    return address


def classify(strings: Sequence[str]) -> tuple[bytes, np.ndarray, np.ndarray]:
    encoded = []
    offsets = np.empty(len(strings) + 1, dtype=np.int64)
    offsets[0] = 0
    total_bytes = 0
    for index, value in enumerate(strings):
        if not isinstance(value, str):
            raise TypeError("user agent must be a string")
        raw = value.encode("utf-8")
        encoded.append(raw)
        total_bytes += len(raw)
        if total_bytes > np.iinfo(np.int64).max:
            raise OverflowError("packed user-agent data exceeds signed int64 range")
        offsets[index + 1] = total_bytes
    joined = b"".join(encoded)
    data = np.frombuffer(joined, dtype=np.uint8) if joined else np.zeros(1, dtype=np.uint8)
    results = np.empty((len(strings), RECORD_SIZE), dtype=np.int64)
    if strings:
        parsed = lib().mua_parse_many(
            _address(data, np.dtype(np.uint8)),
            data.size,
            _address(offsets, np.dtype(np.int64)),
            offsets.size,
            len(strings),
            _address(results, np.dtype(np.int64)),
            results.size,
        )
        if parsed != len(strings):
            detail = _STATUS_ERRORS.get(parsed, f"unexpected status {parsed}")
            raise RuntimeError(f"Mojo parser failed: {detail}")
    return joined, offsets, results
