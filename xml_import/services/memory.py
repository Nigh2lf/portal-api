"""Memória do processo atual, para o log da importação (só funciona de verdade no Linux)."""

from __future__ import annotations

import os
import sys


def rss_mb() -> float | None:
    """Memória residente agora, em MB; ``None`` fora do Linux."""
    try:
        with open("/proc/self/statm", encoding="ascii") as fh:
            pages = int(fh.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE") / 1048576
    except (OSError, ValueError, IndexError, AttributeError):
        return None


def peak_rss_mb() -> float | None:
    """Pico de memória residente desde que o processo subiu, em MB; ``None`` no Windows."""
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux informa em KB; macOS em bytes.
    return peak / 1048576 if sys.platform == "darwin" else peak / 1024


def describe() -> str:
    """``"rss=123 MB, pico=456 MB"`` ou ``"rss=?"`` quando a plataforma não informa."""
    now, peak = rss_mb(), peak_rss_mb()
    parts = [f"rss={now:.0f} MB" if now is not None else "rss=?"]
    if peak is not None:
        parts.append(f"pico={peak:.0f} MB")
    return ", ".join(parts)
