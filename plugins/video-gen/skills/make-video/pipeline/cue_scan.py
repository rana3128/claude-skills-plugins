#!/usr/bin/env python3
"""Scan build.log cue timings for sync problems (text only, no frames).

usage: .venv/bin/python cue_scan.py <part dir> [<part dir> ...]
Flags elements revealed in the last 1.5 s of a scene (their cue word never matched, or matched
the final words) and 4+ elements revealed at the same instant. Legit flags: the cue really is
the scene's last spoken word, or a deliberate group (three gateways -> one Redis).
"""
import re
import sys
from pathlib import Path

for d in sys.argv[1:]:
    log = (Path(d) / "build.log").read_text()
    lens = {m.group(2).strip(): float(m.group(1)) for m in re.finditer(r"^\s+\d+\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+[\d.]+\s+\d+\s+(.*)$", log, re.M)}
    for m in re.finditer(r"cues for '(.*?)':\n((?:\s+[\d.]+s .*\n)+)", log):
        head, body = m.group(1), m.group(2)
        L = lens.get(head)
        times = [(float(t), x.strip()) for t, x in re.findall(r"([\d.]+)s  (.*)", body)]
        late = [x for t, x in times if L and t > L - 1.5]
        same = {}
        for t, x in times: same.setdefault(t, []).append(x)
        crowd = [v for v in same.values() if len(v) >= 4]
        if late or crowd:
            print(Path(d).name, "|", head, "| late:", [x[:30] for x in late], "| clusters:", [len(c) for c in crowd])
