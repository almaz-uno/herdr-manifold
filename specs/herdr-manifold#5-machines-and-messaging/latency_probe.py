"""Keystroke-to-patch latency over endpoint generation 1.

usage: python3 -I latency_probe.py <client-socket> <pane-id> [count]
Sends one TextCommit("x") at a time and times the first PaneSurfacePatch after it.
"""
import json, socket, statistics, sys, time
src = open(__file__.replace("latency_probe.py", "endpoint_probe.py")).read().replace("\nmain()\n", "\n")
exec(src)
path, pane = sys.argv[1], sys.argv[2]
count = int(sys.argv[3]) if len(sys.argv) > 3 else 200
hello = {"generation": 1, "cell_width_px": 9, "cell_height_px": 18, "surface_size": {"cols": 100, "rows": 30},
         "pixel_mouse": False, "direct_graphics": False, "endpoint_keybindings": False, "mouse_capture": False,
         "surface_active": True, "snapshot_codecs": ["shell.snapshot.v1"], "surface_codecs": ["shell.surface.v1"],
         "input_codecs": ["shell.input.semantic.v1"], "blob_codecs": ["shell.blob.v1"]}
t0 = time.perf_counter()
s = socket.socket(socket.AF_UNIX); s.connect(path)
s.sendall(frame(endpoint_control("endpoint.hello.v1", json.dumps(hello))))
s.settimeout(1.0)
first = None
try:
    while True:
        m = recv_message(s)
        if first is None:
            first = time.perf_counter() - t0
except socket.timeout:
    pass
print(f"first message after connect: {first*1000:.0f} ms")
samples = []
for k in range(count):
    msg = varint(13) + string(pane) + varint(1) + varint(1) + string("x")
    t = time.perf_counter(); s.sendall(frame(msg))
    s.settimeout(2.0)
    while True:
        m = recv_message(s)
        tag, _ = read_varint(m, 0)
        if tag == 19:
            samples.append((time.perf_counter() - t) * 1000); break
    s.settimeout(0.03)
    try:
        while True: recv_message(s)
    except socket.timeout:
        pass
samples.sort()
p95 = samples[int(0.95 * len(samples)) - 1]
print(f"n={len(samples)} median={statistics.median(samples):.1f} ms p95={p95:.1f} ms min={samples[0]:.1f} max={samples[-1]:.1f}")
s.close()
