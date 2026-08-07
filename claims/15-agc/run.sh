#!/bin/bash
# Claim #15 — "1960s computers were too weak to navigate to the Moon."
# Reproduces the full pipeline: clone -> build -> assemble -> verify -> run -> figure.
# Tested on macOS (clang). Requires: git, cc/clang, make, python3.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="$HERE/data"
RESULTS="$HERE/results"
VAGC="$DATA/virtualagc"
mkdir -p "$DATA" "$RESULTS"

# ---- 1. Obtain the Virtual AGC project (emulator + transcribed flight source) ----
if [ ! -d "$VAGC" ]; then
    git clone --depth 1 https://github.com/virtualagc/virtualagc "$VAGC"
fi

# ---- 2. Build the CLI tools only (no wxWidgets GUI needed) ----
make -C "$VAGC/yaYUL" cc=cc NVER=\\\"local\\\"        # the assembler
make -C "$VAGC/yaAGC" cc=cc NVER=\\\"local\\\"        # the AGC CPU emulator
cc -O2 -DNVER='"\"local\""' -o "$VAGC/Tools/oct2bin" "$VAGC/Tools/oct2bin.c" "$VAGC/Tools/utils.c"  # octal-listing -> binary converter

# ---- 3. Assemble the real Apollo 11 LM flight software (Luminary 099) ----
( cd "$VAGC/Luminary099" && "$VAGC/yaYUL/yaYUL" MAIN.agc ) > "$DATA/yaYUL-full.log" 2>&1
grep -E 'Fatal errors|Unresolved symbols' "$DATA/yaYUL-full.log"
# trimmed listing for results/ (full 7 MB log stays in gitignored data/)
{ sed -n 1,6p "$DATA/yaYUL-full.log"; echo
  echo '[... ~66,500 lines of assembly listing + symbol table trimmed; full log: data/yaYUL-full.log ...]'; echo
  grep -B1 -A3 'Unresolved symbols' "$DATA/yaYUL-full.log" | tail -5
  echo; echo 'Bank checksum ("bugger") words computed by yaYUL, one per fixed bank (36 banks):'
  grep 'Bugger' "$DATA/yaYUL-full.log"
} > "$RESULTS/yaYUL-assembly-trimmed.log"

# ---- 4. Verify bit-identical vs the independent transcription of the flown rope ----
mkdir -p "$DATA/refbin"
( cd "$DATA/refbin" && "$VAGC/Tools/oct2bin" < "$VAGC/Luminary099/AP11ROPE.binsource" )
{ echo "=== Checksum verification: assembled-from-source vs independent rope transcription ==="
  echo "Date: $(date)"; echo
  echo "MAIN.agc.bin = yaYUL output from Luminary099/MAIN.agc (Apollo 11 LM source listing)"
  echo "oct2bin.bin  = Tools/oct2bin output from AP11ROPE.binsource (independent OCR+proofed"
  echo "               transcription of the physical rope's octal listing; parity-checked)"; echo
  cmp "$VAGC/Luminary099/MAIN.agc.bin" "$DATA/refbin/oct2bin.bin" \
      && echo "cmp: files are BYTE-IDENTICAL (73728 bytes = 36864 fixed-memory words)"
  echo; shasum -a 256 "$VAGC/Luminary099/MAIN.agc.bin" "$DATA/refbin/oct2bin.bin"
  echo; echo "yaYUL summary:"; grep -E 'Unresolved symbols|Fatal errors' "$DATA/yaYUL-full.log"
  echo; echo "Bank checksum (bugger) words emitted by yaYUL (one per fixed bank, 36 banks):"
  grep 'Bugger' "$DATA/yaYUL-full.log"
} > "$RESULTS/checksum-verification.txt"
head -12 "$RESULTS/checksum-verification.txt"

# ---- 5. Run it: boot the flight software on the emulated AGC, instrumented ----
mkdir -p "$DATA/run"
cp "$VAGC/Luminary099/MAIN.agc.bin" "$DATA/run/Luminary099.bin"
python3 "$HERE/scripts/monitor_run.py" "$RESULTS" "$DATA/run" "$VAGC/yaAGC/yaAGC" 60

# ---- 6. Figure (needs matplotlib; prefers the repo venv, skips gracefully) ----
for PY in "$HERE/../../.venv/bin/python" python3; do
    if "$PY" -c 'import matplotlib' 2>/dev/null; then
        "$PY" "$HERE/scripts/make_figure.py"; break
    fi
done || echo "matplotlib not available - skipping figure"

echo "Done. Evidence in $RESULTS/"
