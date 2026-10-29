"""Herdr endpoint generation 1 probe: handshake, then log what the server sends.

usage: python3 -I endpoint_probe.py <client-socket> <out-dir> [seconds]
"""
import json
import os
import socket
import struct
import sys
import time

CLIENT_TAGS = {"EndpointControl": 20}
SERVER_TAGS = {0: "Welcome", 12: "ClientShellSnapshot", 13: "PaneSurface",
               14: "SemanticNotification", 15: "ClientShellError",
               17: "ClientShellKeyboardReportAll", 18: "ClientShellEndpointResponseChunk",
               19: "PaneSurfacePatch", 20: "EndpointControl", 8: "MouseCapture",
               6: "WindowTitle", 3: "ServerShutdown", 4: "Notify"}


def varint(n):
    # bincode 2, config::standard(): varint integers, little endian
    if n < 251:
        return bytes([n])
    if n < 1 << 16:
        return b"\xfb" + struct.pack("<H", n)
    if n < 1 << 32:
        return b"\xfc" + struct.pack("<I", n)
    return b"\xfd" + struct.pack("<Q", n)


def read_varint(buf, i):
    b = buf[i]
    if b < 251:
        return b, i + 1
    size = {251: 2, 252: 4, 253: 8}[b]
    fmt = {2: "<H", 4: "<I", 8: "<Q"}[size]
    return struct.unpack_from(fmt, buf, i + 1)[0], i + 1 + size


def string(s):
    raw = s.encode()
    return varint(len(raw)) + raw


def read_string(buf, i):
    n, i = read_varint(buf, i)
    return buf[i:i + n].decode(), i + n


def frame(payload):
    return struct.pack("<I", len(payload)) + payload


def recv_exact(sock, n):
    out = b""
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise EOFError
        out += chunk
    return out


def recv_message(sock):
    (n,) = struct.unpack("<I", recv_exact(sock, 4))
    return recv_exact(sock, n)


def endpoint_control(kind, data):
    return varint(CLIENT_TAGS["EndpointControl"]) + string(kind) + string(data)


def main():
    path, out, seconds = sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 3
    os.makedirs(out, exist_ok=True)
    hello = {
        "generation": 1, "cell_width_px": 9, "cell_height_px": 18,
        "surface_size": {"cols": 100, "rows": 30},
        "pixel_mouse": False, "direct_graphics": False,
        "endpoint_keybindings": False, "mouse_capture": False, "surface_active": True,
        "surface_reuse": False, "surface_delta": False, "surface_scroll": False,
        "snapshot_codecs": ["shell.snapshot.v1"], "surface_codecs": ["shell.surface.v1"],
        "input_codecs": ["shell.input.semantic.v1"], "blob_codecs": ["shell.blob.v1"],
    }
    sock = socket.socket(socket.AF_UNIX)
    sock.connect(path)
    sock.sendall(frame(endpoint_control("endpoint.hello.v1", json.dumps(hello))))
    sock.settimeout(seconds)
    start, count = time.time(), 0
    while time.time() - start < seconds:
        try:
            msg = recv_message(sock)
        except (socket.timeout, EOFError) as error:
            print("stop:", type(error).__name__)
            break
        tag, i = read_varint(msg, 0)
        name = SERVER_TAGS.get(tag, f"tag{tag}")
        count += 1
        line = f"{time.time() - start:6.3f}s #{count} {name} {len(msg)} B"
        if name == "EndpointControl":
            kind, i = read_string(msg, i)
            data, i = read_string(msg, i)
            line += f" kind={kind} data={len(data)} B"
            with open(os.path.join(out, f"{count:03d}-{kind}.json"), "w") as f:
                f.write(data)
        else:
            with open(os.path.join(out, f"{count:03d}-{name}.bin"), "wb") as f:
                f.write(msg)
        print(line)
    sock.close()


main()
