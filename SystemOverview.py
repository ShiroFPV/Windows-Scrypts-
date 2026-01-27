import ctypes, ctypes.wintypes as wt
import time, math, random, shutil, sys, msvcrt, os


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
iphlpapi = ctypes.WinDLL("iphlpapi", use_last_error=True)
psapi    = ctypes.WinDLL("psapi", use_last_error=True)
pdh      = ctypes.WinDLL("pdh", use_last_error=True)


STD_OUTPUT_HANDLE = -11
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010

ERROR_INSUFFICIENT_BUFFER = 122


def enable_vt():
    h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    mode = ctypes.c_uint()
    if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
        kernel32.SetConsoleMode(h, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)


def enter_alt():
    sys.stdout.write("\x1b[?1049h\x1b[H")
    sys.stdout.flush()


def exit_alt():
    sys.stdout.write("\x1b[?1049l")
    sys.stdout.flush()


def home_only():
    sys.stdout.write("\x1b[H")
    sys.stdout.flush()


def hide_cursor():
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


def clamp(x, a, b):
    return a if x < a else b if x > b else x


def ema_asym(prev, raw, dt, tau_up=0.25, tau_down=0.80):
    # fast attack, slower release (but not "2 seconds behind reality")
    tau = tau_up if raw > prev else tau_down
    if tau <= 1e-6:
        return raw
    a = 1.0 - math.exp(-dt / tau)
    return prev + a * (raw - prev)


def bar(pct, width):
    pct = clamp(pct, 0.0, 1.0)
    n = int(round(pct * width))
    return "█" * n + " " * (width - n)


def human_bps(bps):
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    x = float(max(0.0, bps))
    i = 0
    while x >= 1024.0 and i < len(units) - 1:
        x /= 1024.0
        i += 1
    return f"{x:.1f} {units[i]}" if i else f"{int(x)} {units[i]}"


def human_bytes(n):
    units = ["B", "KB", "MB", "GB"]
    x = float(max(0, n))
    i = 0
    while x >= 1024.0 and i < len(units) - 1:
        x /= 1024.0
        i += 1
    return f"{x:.1f} {units[i]}" if i else f"{int(x)} {units[i]}"


def fit(s, width):
    if width <= 0:
        return ""
    if len(s) <= width:
        return s
    if width <= 3:
        return s[:width]
    return s[:width - 3] + "..."


# ---- RAM total ----
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
kernel32.GlobalMemoryStatusEx.restype = ctypes.c_int


def read_mem():
    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return 0, 0, 0.0
    total = int(st.ullTotalPhys)
    avail = int(st.ullAvailPhys)
    used = max(0, total - avail)
    return total, used, (used / total) if total else 0.0


# ---- SYS "reserved-ish" (GetPerformanceInfo) ----
class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_uint32),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", ctypes.c_uint32),
        ("ProcessCount", ctypes.c_uint32),
        ("ThreadCount", ctypes.c_uint32),
    ]


psapi.GetPerformanceInfo.argtypes = [ctypes.POINTER(PERFORMANCE_INFORMATION), ctypes.c_uint32]
psapi.GetPerformanceInfo.restype = ctypes.c_int


def read_system_reserved_pct():
    pi = PERFORMANCE_INFORMATION()
    pi.cb = ctypes.sizeof(PERFORMANCE_INFORMATION)
    if not psapi.GetPerformanceInfo(ctypes.byref(pi), pi.cb):
        return 0.0
    page = int(pi.PageSize)
    phys_total = int(pi.PhysicalTotal) * page
    sys_bytes = (int(pi.SystemCache) + int(pi.KernelTotal)) * page
    return clamp((sys_bytes / phys_total) if phys_total else 0.0, 0.0, 1.0)


# ---- NET ----
MAX_INTERFACE_NAME_LEN = 256
MAXLEN_PHYSADDR = 8
MAXLEN_IFDESCR = 256


class MIB_IFROW(ctypes.Structure):
    _fields_ = [
        ("wszName", ctypes.c_wchar * MAX_INTERFACE_NAME_LEN),
        ("dwIndex", ctypes.c_uint32), ("dwType", ctypes.c_uint32),
        ("dwMtu", ctypes.c_uint32), ("dwSpeed", ctypes.c_uint32),
        ("dwPhysAddrLen", ctypes.c_uint32), ("bPhysAddr", ctypes.c_ubyte * MAXLEN_PHYSADDR),
        ("dwAdminStatus", ctypes.c_uint32), ("dwOperStatus", ctypes.c_uint32),
        ("dwLastChange", ctypes.c_uint32),
        ("dwInOctets", ctypes.c_uint32), ("dwInUcastPkts", ctypes.c_uint32),
        ("dwInNUcastPkts", ctypes.c_uint32), ("dwInDiscards", ctypes.c_uint32),
        ("dwInErrors", ctypes.c_uint32), ("dwInUnknownProtos", ctypes.c_uint32),
        ("dwOutOctets", ctypes.c_uint32), ("dwOutUcastPkts", ctypes.c_uint32),
        ("dwOutNUcastPkts", ctypes.c_uint32), ("dwOutDiscards", ctypes.c_uint32),
        ("dwOutErrors", ctypes.c_uint32), ("dwOutQLen", ctypes.c_uint32),
        ("dwDescrLen", ctypes.c_uint32), ("bDescr", ctypes.c_ubyte * MAXLEN_IFDESCR),
    ]


iphlpapi.GetIfTable.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.c_int]
iphlpapi.GetIfTable.restype = ctypes.c_ulong


def read_net_octets():
    size = ctypes.c_ulong(0)
    rc = iphlpapi.GetIfTable(None, ctypes.byref(size), 0)
    if rc != ERROR_INSUFFICIENT_BUFFER or size.value == 0:
        return 0, 0

    buf = ctypes.create_string_buffer(size.value)
    if iphlpapi.GetIfTable(buf, ctypes.byref(size), 0) != 0:
        return 0, 0

    num = ctypes.c_uint32.from_buffer_copy(buf, 0).value
    off = 4
    a = ctypes.alignment(MIB_IFROW)
    off = (off + (a - 1)) & ~(a - 1)
    row_sz = ctypes.sizeof(MIB_IFROW)

    rx = tx = 0
    for i in range(num):
        o = off + i * row_sz
        if o + row_sz > len(buf):
            break
        row = MIB_IFROW.from_buffer_copy(buf, o)
        if row.dwSpeed == 0:
            continue
        rx += int(row.dwInOctets)
        tx += int(row.dwOutOctets)
    return rx, tx


# ---- PDH ----
PDH_HQUERY = ctypes.c_void_p
PDH_HCOUNTER = ctypes.c_void_p
PDH_FMT_DOUBLE = 0x00000200
PDH_MORE_DATA = 0x800007D2

pdh.PdhOpenQueryW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(PDH_HQUERY)]
pdh.PdhOpenQueryW.restype = ctypes.c_ulong
pdh.PdhAddEnglishCounterW.argtypes = [PDH_HQUERY, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(PDH_HCOUNTER)]
pdh.PdhAddEnglishCounterW.restype = ctypes.c_ulong
pdh.PdhCollectQueryData.argtypes = [PDH_HQUERY]
pdh.PdhCollectQueryData.restype = ctypes.c_ulong
pdh.PdhCloseQuery.argtypes = [PDH_HQUERY]
pdh.PdhCloseQuery.restype = ctypes.c_ulong


class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    class _V(ctypes.Union):
        _fields_ = [
            ("longValue", ctypes.c_long),
            ("doubleValue", ctypes.c_double),
            ("largeValue", ctypes.c_longlong),
            ("AnsiStringValue", ctypes.c_char_p),
            ("WideStringValue", ctypes.c_wchar_p),
        ]
    _anonymous_ = ("V",)
    _fields_ = [("CStatus", ctypes.c_ulong), ("V", _V)]


pdh.PdhGetFormattedCounterValue.argtypes = [
    PDH_HCOUNTER, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(PDH_FMT_COUNTERVALUE)
]
pdh.PdhGetFormattedCounterValue.restype = ctypes.c_ulong


class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
    _fields_ = [("szName", ctypes.c_wchar_p), ("FmtValue", PDH_FMT_COUNTERVALUE)]


pdh.PdhGetFormattedCounterArrayW.argtypes = [
    PDH_HCOUNTER, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
    ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p
]
pdh.PdhGetFormattedCounterArrayW.restype = ctypes.c_ulong


class CpuReader:
    def __init__(self):
        self.q = PDH_HQUERY()
        self.c = PDH_HCOUNTER()
        self.ok = False
        if pdh.PdhOpenQueryW(None, None, ctypes.byref(self.q)) != 0:
            return
        path = r"\Processor(_Total)\% Processor Time"
        if pdh.PdhAddEnglishCounterW(self.q, path, None, ctypes.byref(self.c)) != 0:
            pdh.PdhCloseQuery(self.q)
            return
        pdh.PdhCollectQueryData(self.q)  # prime
        self.ok = True

    def read_pct(self):
        if not self.ok:
            return 0.0
        if pdh.PdhCollectQueryData(self.q) != 0:
            return 0.0
        typ = ctypes.c_ulong(0)
        val = PDH_FMT_COUNTERVALUE()
        if pdh.PdhGetFormattedCounterValue(self.c, PDH_FMT_DOUBLE, ctypes.byref(typ), ctypes.byref(val)) != 0:
            return 0.0
        return clamp(float(val.doubleValue) / 100.0, 0.0, 1.0)

    def close(self):
        if self.ok:
            pdh.PdhCloseQuery(self.q)
            self.ok = False


class GpuReader:
    def __init__(self):
        self.q = PDH_HQUERY()
        self.c = PDH_HCOUNTER()
        self.ok = False
        if pdh.PdhOpenQueryW(None, None, ctypes.byref(self.q)) != 0:
            return
        path = r"\GPU Engine(*)\Utilization Percentage"
        if pdh.PdhAddEnglishCounterW(self.q, path, None, ctypes.byref(self.c)) != 0:
            pdh.PdhCloseQuery(self.q)
            return
        pdh.PdhCollectQueryData(self.q)
        self.ok = True

    def read_pct(self):
        if not self.ok:
            return 0.0
        if pdh.PdhCollectQueryData(self.q) != 0:
            return 0.0

        buf_sz = ctypes.c_ulong(0)
        cnt = ctypes.c_ulong(0)
        rc = pdh.PdhGetFormattedCounterArrayW(self.c, PDH_FMT_DOUBLE, ctypes.byref(buf_sz), ctypes.byref(cnt), None)
        if rc != PDH_MORE_DATA or buf_sz.value == 0 or cnt.value == 0:
            return 0.0

        buf = ctypes.create_string_buffer(buf_sz.value)
        if pdh.PdhGetFormattedCounterArrayW(self.c, PDH_FMT_DOUBLE, ctypes.byref(buf_sz), ctypes.byref(cnt), buf) != 0:
            return 0.0

        items = (PDH_FMT_COUNTERVALUE_ITEM_W * cnt.value).from_buffer(buf)

        sum_3d = 0.0
        max_any = 0.0
        for it in items:
            v = float(it.FmtValue.doubleValue)
            if v > max_any:
                max_any = v
            name = it.szName or ""
            if "engtype_3D" in name:
                sum_3d += v

        pick = sum_3d if sum_3d > 0.1 else max_any
        return clamp(pick / 100.0, 0.0, 1.0)

    def close(self):
        if self.ok:
            pdh.PdhCloseQuery(self.q)
            self.ok = False


# ---- RAM hog (group by exe, take max) ----
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype  = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype  = wt.BOOL

psapi.EnumProcesses.argtypes = [ctypes.POINTER(wt.DWORD), wt.DWORD, ctypes.POINTER(wt.DWORD)]
psapi.EnumProcesses.restype  = wt.BOOL

psapi.GetProcessImageFileNameW.argtypes = [wt.HANDLE, wt.LPWSTR, wt.DWORD]
psapi.GetProcessImageFileNameW.restype  = wt.DWORD

psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD]
psapi.GetProcessMemoryInfo.restype  = wt.BOOL


class PROCESS_MEMORY_COUNTERS_EX2(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
        ("PrivateWorkingSetSize", ctypes.c_size_t),
        ("SharedCommitUsage", ctypes.c_ulonglong),
    ]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def enum_pids():
    size = 4096
    while True:
        arr = (wt.DWORD * size)()
        needed = wt.DWORD(0)
        if not psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(needed)):
            return []
        count = needed.value // ctypes.sizeof(wt.DWORD)
        if count < size:
            return arr[:count]
        size *= 2
        if size > 1_000_000:
            return []


def read_top_ram_group(total_phys):
    if total_phys <= 0:
        return "", 0, 0.0, 0

    totals = {}  # name -> [bytes, count]

    for pid in enum_pids():
        if pid == 0:
            continue

        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, int(pid))
        if not h:
            continue

        try:
            mem = 0
            pmc2 = PROCESS_MEMORY_COUNTERS_EX2()
            pmc2.cb = ctypes.sizeof(pmc2)
            if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc2), pmc2.cb):
                mem = int(pmc2.PrivateWorkingSetSize) or int(pmc2.WorkingSetSize)
            else:
                pmc = PROCESS_MEMORY_COUNTERS()
                pmc.cb = ctypes.sizeof(pmc)
                if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                    mem = int(pmc.WorkingSetSize)
                else:
                    continue

            buf = ctypes.create_unicode_buffer(1024)
            n = psapi.GetProcessImageFileNameW(h, buf, 1024)
            name = os.path.basename(buf.value) if n else f"PID {pid}"
            if not name:
                name = f"PID {pid}"

            cur = totals.get(name)
            if cur is None:
                totals[name] = [mem, 1]
            else:
                cur[0] += mem
                cur[1] += 1
        finally:
            kernel32.CloseHandle(h)

    if not totals:
        return "", 0, 0.0, 0

    best_name, (best_bytes, best_cnt) = max(totals.items(), key=lambda kv: kv[1][0])
    return best_name, best_bytes, (best_bytes / total_phys) if total_phys else 0.0, best_cnt


# ---- Creature / moods ----
def color_for(m):
    return {
        "SLEEPY":  "\x1b[36m",
        "OK":      "\x1b[32m",
        "HYPER":   "\x1b[35m",
        "SHADERS": "\x1b[35;1m",
        "TNT":     "\x1b[31m",
        "CHROME":  "\x1b[33m",
        "PANIC":   "\x1b[33;1m",
        "RAGE":    "\x1b[31;1m",
        "WIN":     "\x1b[34m",
    }.get(m, "\x1b[0m")


def pick_face(mood, t, blink):
    top = " /\\_/\\ "
    if blink:
        mid = "(= -.-=)"
    else:
        mid_pool = {
            "OK":      ["(=^.^=)", "(=^o^=)"],
            "SLEEPY":  ["(= -.-=)", "(= -_- =)"],
            "HYPER":   ["(=^o^=)", "(=^O^=)"],
            "SHADERS": ["(=^*^=)", "(=^.^=)"],
            "TNT":     ["(=^#^=)", "(=O.O=)"],
            "CHROME":  ["(=o_o=)", "(=-_- =)"],
            "PANIC":   ["(=O.O=)", "(=0.0=)"],
            "RAGE":    ["(=>.<=)", "(=x_x=)"],
            "WIN":     ["(=o_o=)", "(=._.=)"],
        }.get(mood, ["(=^.^=)"])
        mid = mid_pool[int(t * 5) % len(mid_pool)]
    bot = ""
    return top, mid, bot


def sys_sentence(sys_pct):
    if sys_pct >= 0.28:
        return "Windows landlord tax."
    if sys_pct >= 0.18:
        return "Windows is hoarding cache."
    return "Windows behaving."


class Particles:
    def __init__(self):
        self.p = []

    def reset(self, w, h, n=90):
        self.p = []
        for _ in range(n):
            self.p.append([random.uniform(1, max(2, w - 2)),
                           random.uniform(1, max(2, h - 2)),
                           random.choice([-1, 1]) * random.random() * 0.8,
                           random.choice([-1, 1]) * random.random() * 0.4,
                           random.choice(["·", ".", "*", "+", "°"])])

    def step(self, w, h, energy):
        k = 0.25 + 1.75 * energy
        for q in self.p:
            q[0] += q[2] * k
            q[1] += q[3] * k
            if q[0] < 1: q[0], q[2] = 1, -q[2]
            if q[0] > w - 2: q[0], q[2] = w - 2, -q[2]
            if q[1] < 1: q[1], q[3] = 1, -q[3]
            if q[1] > h - 2: q[1], q[3] = h - 2, -q[3]


def bar_line(name, pct, inner_w):
    left = f"{name} {int(pct*100):3d}% |"
    right = "|"
    bw = max(1, inner_w - len(left) - len(right))
    return left + bar(pct, bw) + right


def main():
    enable_vt()
    enter_alt()
    hide_cursor()

    cpu_reader = CpuReader()
    gpu_reader = GpuReader()
    stars = Particles()

    # slower updates + anti-0-glitch
    STATS_DT = 0.25      # stats refresh rate
    PROC_DT  = 1.25      # scan processes slower

    CPU_GLITCH_FLOOR = 0.02   # treat <2% as "maybe glitch"
    CPU_GLITCH_HOLD_S = 0.40  # hide brief dips
    CPU_TAU_UP = 0.25         # bar reacts quickly up
    CPU_TAU_DOWN = 0.80       # bar falls slower (no 18->0->18)

    prev_net = read_net_octets()
    last_stats = 0.0
    last_proc = 0.0

    cpu_raw = 0.0       # PDH raw
    cpu_num = 0.0       # displayed number (raw + glitch-hold)
    cpu_bar = 0.0       # displayed bar (smoothed)
    last_nonzero = 0.0

    mem_pct = 0.0
    sys_pct = 0.0
    gpu_pct = 0.0
    rx_bps = tx_bps = 0.0
    total_phys = 0

    top_ram_name = ""
    top_ram_bytes = 0
    top_ram_pct = 0.0
    top_ram_cnt = 0

    prev_wh = None

    try:
        while True:
            now = time.time()
            w, h = shutil.get_terminal_size((110, 34))

            if prev_wh != (w, h):
                sys.stdout.write("\x1b[2J\x1b[H")
                sys.stdout.flush()
                prev_wh = (w, h)
                stars.p = []

            if not stars.p:
                stars.reset(w, h, n=min(180, max(70, (w * h) // 90)))

            if now - last_stats >= STATS_DT:
                dt = max(1e-3, now - last_stats)

                cpu_raw = cpu_reader.read_pct()

                if cpu_raw > CPU_GLITCH_FLOOR:
                    last_nonzero = now

                # "don't show 0" if it bounces: only hold for a short time window
                if cpu_raw < CPU_GLITCH_FLOOR and (now - last_nonzero) < CPU_GLITCH_HOLD_S:
                    cpu_num = cpu_num  # keep last number
                else:
                    cpu_num = cpu_raw

                cpu_bar = ema_asym(cpu_bar, cpu_num, dt, tau_up=CPU_TAU_UP, tau_down=CPU_TAU_DOWN)

                total_phys, _, mem_pct = read_mem()
                sys_pct = read_system_reserved_pct()
                gpu_pct = gpu_reader.read_pct()

                cur_net = read_net_octets()
                drx = (cur_net[0] - prev_net[0]) & 0xFFFFFFFF
                dtx = (cur_net[1] - prev_net[1]) & 0xFFFFFFFF
                rx_bps = drx / dt
                tx_bps = dtx / dt
                prev_net = cur_net

                last_stats = now

            if now - last_proc >= PROC_DT:
                top_ram_name, top_ram_bytes, top_ram_pct, top_ram_cnt = read_top_ram_group(total_phys)
                last_proc = now

            beat = 0.5 + 0.5 * math.sin(now * 2.2)
            blink = (int(now * 10) % 37) == 0

            cpu = cpu_num
            net = rx_bps + tx_bps

            if mem_pct > 0.93:
                mood = "PANIC"
            elif top_ram_pct > 0.10:
                mood = "CHROME"
            elif cpu > 0.92:
                mood = "RAGE"
            elif cpu > 0.75:
                mood = "TNT"
            elif gpu_pct > 0.80:
                mood = "SHADERS"
            elif sys_pct > 0.26:
                mood = "WIN"
            elif net > 2_000_000:
                mood = "HYPER"
            elif cpu < 0.08 and mem_pct < 0.55:
                mood = "SLEEPY"
            else:
                mood = "OK"

            col = color_for(mood)
            net_energy = clamp(net / 4_000_000.0, 0.0, 1.0)
            energy = clamp(0.12 + 0.75 * cpu_bar + 0.55 * net_energy + 0.25 * gpu_pct, 0.0, 1.0)

            stars.step(w, h, energy)

            canvas = [[" "] * w for _ in range(h)]
            for x, y, _, _, ch in stars.p:
                xi, yi = int(x), int(y)
                if 0 <= yi < h and 0 <= xi < w:
                    canvas[yi][xi] = ch

            box_w = min(86, max(56, w - 4))
            box_h = 16
            x0 = (w - box_w) // 2
            y0 = (h - box_h) // 2
            inner_w = box_w - 4

            def put(y, x, s):
                if 0 <= y < h:
                    for i, c in enumerate(s):
                        xx = x + i
                        if 0 <= xx < w:
                            canvas[y][xx] = c

            put(y0, x0, "╭" + "─" * (box_w - 2) + "╮")
            for i in range(1, box_h - 1):
                put(y0 + i, x0, "│" + " " * (box_w - 2) + "│")
            put(y0 + box_h - 1, x0, "╰" + "─" * (box_w - 2) + "╯")

            heart = "♥" if beat > 0.5 else "♡"
            put(y0 + 1, x0 + 2, fit(f"Heart: {heart}   Mood: {mood}", inner_w))

            cx = x0 + box_w // 2
            cy = y0 + 2
            face0, face1, face2 = pick_face(mood, now, blink)
            put(cy + 0, cx - 3, face0)
            put(cy + 1, cx - 3, face1)

            put(y0 + 6, x0 + 2, fit(bar_line("CPU", cpu_bar, inner_w), inner_w))
            put(y0 + 7, x0 + 2, fit(bar_line("RAM", mem_pct, inner_w), inner_w))

            if top_ram_name:
                hog = f"RAM hog: {top_ram_name} ({top_ram_cnt}) {int(top_ram_pct*100):2d}% {human_bytes(top_ram_bytes)}"
            else:
                hog = "RAM hog: <unknown>"
            put(y0 + 8, x0 + 2, fit(hog, inner_w))

            sys_text = f"SYS {int(sys_pct*100):3d}%  {sys_sentence(sys_pct)}"
            put(y0 + 9, x0 + 2, fit(sys_text, inner_w))

            put(y0 + 10, x0 + 2, fit(bar_line("GPU", gpu_pct, inner_w), inner_w))
            put(y0 + 11, x0 + 2, fit(f"NET {human_bps(rx_bps)} ↓   {human_bps(tx_bps)} ↑", inner_w))

            roast_default = {
                "SLEEPY":  "Cat idle. If it dies, it dies.",
                "OK":      "Stable. Boring. Good.",
                "HYPER":   "Zoomies. Packets doing parkour.",
                "SHADERS": "GPU glam. FPS debt incoming.",
                "TNT":     "CPU >75%. Heat mode engaged.",
                "PANIC":   "RAM is gone. This is not fine.",
                "RAGE":    "CPU boss fight. Something is cooking hard.",
                "WIN":     "Windows reserved more. For what? Vibes.",
            }
            if mood == "CHROME":
                eater = top_ram_name or "Something"
                roast = f"{eater} is eating RAM. Close it, champ."
            else:
                roast = roast_default[mood]

            put(y0 + 13, x0 + 2, fit(roast, inner_w))
            put(y0 + box_h - 2, x0 + 2, fit("Keys: q=quit   r=reset stars", inner_w))

            home_only()
            frame = col + "\n".join(("".join(row)).ljust(w)[:w] for row in canvas) + "\x1b[0m"
            sys.stdout.write(frame)
            sys.stdout.flush()

            if msvcrt.kbhit():
                k = msvcrt.getwch()
                if k in ("q", "Q"):
                    break
                if k in ("r", "R"):
                    stars.reset(w, h, n=min(180, max(70, (w * h) // 90)))

            time.sleep(1 / 60)

    finally:
        try:
            cpu_reader.close()
        except Exception:
            pass
        try:
            gpu_reader.close()
        except Exception:
            pass
        sys.stdout.write("\x1b[0m")
        show_cursor()
        exit_alt()
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
