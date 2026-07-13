"""
client/tier_detector.py — Hardware Capability Classification
=============================================================
Implements the Asymmetric Capability Model (Section 3.4).

Classification rule (Section 3.4):
    Tier 1: RAM < 4 GB  → Plaintext Fallback (Template Engine only)
    Tier 2: RAM >= 4 GB → SLM-Capable (Template + on-device Small Language Model)

Detection method:
    Uses psutil.virtual_memory() for cross-platform RAM detection.
    Falls back to conservative Tier 1 if psutil is not installed.

Additional factors reported (for audit/demo purposes):
    - Total RAM
    - Available RAM
    - CPU core count
    - Platform (OS)
    - Python version
"""

from __future__ import annotations
import platform
import sys
import os

TIER_1_RAM_THRESHOLD_GB = 4.0   # Section 3.4 boundary
TIER_1 = 1
TIER_2 = 2


def _get_ram_gb() -> float:
    """Return total physical RAM in GB. Returns 0.0 on failure."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass
    # Fallback: read /proc/meminfo on Linux
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except (FileNotFoundError, PermissionError):
        pass
    # Windows fallback via ctypes
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullTotalPhys / (1024 ** 3)
    except Exception:
        pass
    return 0.0   # Unknown — default to conservative Tier 1


def detect_tier(ram_gb: float | None = None) -> int:
    """
    Detect device tier based on RAM.

    Args:
        ram_gb: Override RAM value in GB (for testing). If None, auto-detect.

    Returns:
        TIER_1 (1) or TIER_2 (2).
    """
    if ram_gb is None:
        ram_gb = _get_ram_gb()
    return TIER_2 if ram_gb >= TIER_1_RAM_THRESHOLD_GB else TIER_1


def get_system_info() -> dict:
    """
    Return a full system info dict for audit logs and the demo UI.

    Returns:
        dict with keys:
            tier           — 1 or 2
            ram_gb         — detected RAM in GB (rounded to 1 dp)
            ram_threshold  — 4.0 (GB)
            tier_label     — human-readable tier label
            os             — operating system name
            cpu_cores      — logical CPU count
            python_version — Python version string
            slm_eligible   — bool: True if Tier 2
            psutil_avail   — bool: True if psutil was importable
    """
    try:
        import psutil
        ram_gb    = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        avail_gb  = round(psutil.virtual_memory().available / (1024 ** 3), 1)
        cpu_cores = psutil.cpu_count(logical=True)
        psutil_ok = True
    except ImportError:
        ram_gb    = round(_get_ram_gb(), 1)
        avail_gb  = None
        cpu_cores = os.cpu_count() or 1
        psutil_ok = False

    tier = detect_tier(ram_gb)
    return {
        "tier":           tier,
        "ram_gb":         ram_gb,
        "ram_available_gb": avail_gb,
        "ram_threshold_gb": TIER_1_RAM_THRESHOLD_GB,
        "tier_label":     f"Tier {tier} — {'SLM-Capable Smartphone' if tier == TIER_2 else 'Basic Device (Template Only)'}",
        "os":             platform.system() + " " + platform.release(),
        "cpu_cores":      cpu_cores,
        "python_version": sys.version.split()[0],
        "slm_eligible":   tier == TIER_2,
        "psutil_avail":   psutil_ok,
    }
