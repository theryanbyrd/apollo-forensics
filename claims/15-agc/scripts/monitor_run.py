#!/usr/bin/env python3
"""
Launch yaAGC running the freshly assembled Apollo 11 LM software (Luminary099.bin),
let it boot and execute for RUN_SECONDS of wall time, and capture evidence that
authentic 1969 flight code is executing in real time on the emulated AGC:

  1. Cycle counting: yaAGC writes a core-dump file every --dump-time seconds.
     The dump contains the engine's 64-bit CycleCounter (one count per Memory
     Cycle Time, 11.72 us) as an octal value on line 2561 (after 512 i/o channel
     lines + 8*0400 erasable-memory lines; see yaAGC/agc_engine_init.c,
     MakeCoreDump()).  Sampling it over wall time gives measured MCT/sec, to be
     compared with the authentic rate AGC_PER_SECOND = (1024000+6)/12 = 85333
     (yaAGC/agc_engine.h line 207).

  2. DSKY channel traffic: we connect to yaAGC's socket (the same interface the
     yaDSKY panel uses) and log every i/o-channel packet the flight software
     emits, with wall-clock timestamps.  Packet format per FormIoPacket() in
     yaAGC/agc_utilities.c.

  3. Host cost: `ps -o %cpu,rss` sampled every second on the yaAGC process.

Writes results JSON + logs into the results/ directory given as argv[1].
Usage: python3 monitor_run.py <results_dir> <run_dir> <yaAGC_binary> [run_seconds]
"""
import json
import os
import re
import select
import socket
import statistics
import subprocess
import sys
import time

RESULTS = sys.argv[1]
RUNDIR = sys.argv[2]
YAAGC = sys.argv[3]
RUN_SECONDS = int(sys.argv[4]) if len(sys.argv) > 4 else 60
PORT = 19697
AGC_PER_SECOND = (1024000 + 6) // 12  # 85333, from yaAGC/agc_engine.h
CYCLE_LINE_INDEX = 512 + 8 * 0o400   # 2560 lines precede CycleCounter

os.chdir(RUNDIR)
if os.path.exists("core"):
    os.remove("core")  # fresh boot, no resume

proc = subprocess.Popen(
    [YAAGC, "--exec=Luminary099.bin", "--nodebug", "--no-resume",
     "--dump-time=5", f"--port={PORT}"],
    stdout=open(os.path.join(RESULTS, "yaAGC-stdout.log"), "w"),
    stderr=subprocess.STDOUT,
)
print(f"yaAGC pid={proc.pid}")
time.sleep(2.0)  # let it boot and open the socket

sock = socket.create_connection(("127.0.0.1", PORT), timeout=5)
sock.setblocking(False)

chan_log = open(os.path.join(RESULTS, "dsky-channel-log.txt"), "w")
chan_log.write("# t_wall(s)  channel(octal)  value(octal)   [decoded yaAGC i/o packets]\n")

def read_cycle_counter():
    """Parse CycleCounter (octal) from yaAGC's periodic core-dump file."""
    try:
        with open("core") as f:
            lines = f.read().splitlines()
        if len(lines) <= CYCLE_LINE_INDEX:
            return None
        return int(lines[CYCLE_LINE_INDEX], 8)
    except (FileNotFoundError, ValueError):
        return None

t0 = time.monotonic()
buf = b""
packet_count = 0
chan_hist = {}
cpu_samples = []
rss_samples = []
cycle_samples = []  # (wall_time, cycle_count)
logged_lines = 0
next_ps = 0.0

while (now := time.monotonic() - t0) < RUN_SECONDS:
    # --- socket: drain and decode channel packets ---
    r, _, _ = select.select([sock], [], [], 0.2)
    if r:
        try:
            data = sock.recv(65536)
            if data:
                buf += data
        except BlockingIOError:
            pass
    # Packets are 4 bytes with 2-bit signatures 00,01,10,11 (agc_utilities.c)
    while len(buf) >= 4:
        if (buf[0] & 0xC0) == 0x00 and (buf[1] & 0xC0) == 0x40 \
           and (buf[2] & 0xC0) == 0x80 and (buf[3] & 0xC0) == 0xC0:
            channel = (buf[0] << 3) | ((buf[1] >> 3) & 7)
            value = ((buf[1] & 7) << 12) | ((buf[2] & 0x3F) << 6) | (buf[3] & 0x3F)
            packet_count += 1
            chan_hist[channel] = chan_hist.get(channel, 0) + 1
            if logged_lines < 4000:
                chan_log.write(f"{now:8.3f}  {channel:03o}  {value:05o}\n")
                logged_lines += 1
            buf = buf[4:]
        else:
            buf = buf[1:]  # resync
    # --- ps sampling (1/sec) ---
    if now >= next_ps:
        ps = subprocess.run(
            ["ps", "-o", "%cpu=,rss=", "-p", str(proc.pid)],
            capture_output=True, text=True)
        m = re.findall(r"[\d.]+", ps.stdout)
        if len(m) >= 2:
            cpu_samples.append(float(m[0]))
            rss_samples.append(int(m[1]))
        cc = read_cycle_counter()
        if cc is not None and (not cycle_samples or cc != cycle_samples[-1][1]):
            cycle_samples.append((round(now, 3), cc))
        next_ps = now + 1.0
    if proc.poll() is not None:
        print("yaAGC exited early!", file=sys.stderr)
        break

wall = time.monotonic() - t0
# precise cumulative CPU cost before terminating (ps cputime = total CPU-seconds)
cputime_s = None
out = subprocess.run(["ps", "-o", "cputime=", "-p", str(proc.pid)],
                     capture_output=True, text=True).stdout.strip()
m = re.match(r"(?:(\d+):)?(\d+):(\d+)\.(\d+)", out)
if m:
    h = int(m.group(1) or 0)
    cputime_s = h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + float("0." + m.group(4))
sock.close()
proc.terminate()
proc.wait(timeout=10)
chan_log.close()

# --- crunch numbers ---
result = {
    "run_wall_seconds": round(wall, 3),
    "agc_authentic_cycles_per_sec": AGC_PER_SECOND,
    "channel_packets_received": packet_count,
    "channels_seen_octal": {f"{ch:03o}": n for ch, n in sorted(chan_hist.items())},
    "cputime_total_seconds": cputime_s,
    "cputime_percent_of_one_core": round(100 * cputime_s / wall, 2) if cputime_s else None,
    "cpu_percent_samples": cpu_samples,
    "cpu_percent_mean": round(statistics.mean(cpu_samples), 3) if cpu_samples else None,
    "cpu_percent_max": max(cpu_samples) if cpu_samples else None,
    "rss_kb_max": max(rss_samples) if rss_samples else None,
    "cycle_samples": cycle_samples,
}
if len(cycle_samples) >= 2:
    (ta, ca), (tb, cb) = cycle_samples[0], cycle_samples[-1]
    result["cycles_first_sample"] = ca
    result["cycles_last_sample"] = cb
    result["measured_cycles_per_sec"] = round((cb - ca) / (tb - ta), 1)
    result["speed_vs_real_agc"] = round(result["measured_cycles_per_sec"] / AGC_PER_SECOND, 4)

with open(os.path.join(RESULTS, "runtime-measurements.json"), "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps({k: v for k, v in result.items()
                  if k not in ("cpu_percent_samples", "cycle_samples")}, indent=2))
