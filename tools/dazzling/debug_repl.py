#!/usr/bin/env python3
"""Persistent, stdlib-only client for Dazzling Platinum's lockstep protocol."""
import argparse
import glob
import json
import os
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import zlib

PREFIX = "/tmp/dz-dbg-"
FIXED_RTC = "2026-01-01T12:00:00"
SKIP = {"save.bin", "save-backups", "build.ninja", "compile_commands.json", "sim_config.ini"}


def paths(name):
    if not name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name):
        raise ValueError("session name may contain only letters, digits, '_' and '-'")
    base = PREFIX + name
    return base + ".sock", base + ".pid", base + ".log", base + ".work"


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def cleanup_files(name, include_work=False):
    sock, pid, log, work = paths(name)
    for path in (sock, pid):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    if include_work:
        shutil.rmtree(work, ignore_errors=True)


def prepare_work(game, name, save=None):
    game = os.path.abspath(game)
    if not os.path.isfile(game):
        raise FileNotFoundError(game)
    _, _, _, work = paths(name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    game_dir = os.path.dirname(game)
    for entry in os.listdir(game_dir):
        if entry in SKIP or entry.startswith(("meson-", "save.bin")) or entry.endswith((".p", ".log")):
            continue
        os.symlink(os.path.join(game_dir, entry), os.path.join(work, entry))
    with open(os.path.join(work, "sim_config.ini"), "w", encoding="utf-8") as f:
        f.write("[General]\nInternalResolutionScale=2\n")
    save_dst = os.path.join(work, "save.bin")
    if save:
        shutil.copyfile(os.path.abspath(save), save_dst)
    return game, work, save_dst


class Game:
    def __init__(self, game, name, save=None, fast_boot=False):
        game, self.work, save_path = prepare_work(game, name, save)
        env = dict(os.environ)
        env.setdefault("LP_NUM_THREADS", "2")
        if sys.platform.startswith("linux"):
            env.setdefault("SIM_G2_GPU", "0")
            env.setdefault("SIM_RENDERER", "gl")
        env.update({"SIM_HEADLESS": "1", "SIM_CONTROL": "stdio", "SIM_FIXED_RTC": FIXED_RTC,
                    "SIM_SEED": "12345", "SIM_SAVE_PATH": save_path, "SDL_MAC_BACKGROUND_APP": "1"})
        if fast_boot:
            env["SIM_BOOT_DIRECT_SAVE"] = "1"
        stderr_path = paths(name)[2]
        self.stderr = open(stderr_path, "ab", buffering=0)
        self.proc = subprocess.Popen([game], cwd=self.work, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, env=env, text=True, bufsize=1)

    def command(self, command, timeout=120):
        if self.proc.poll() is not None:
            raise RuntimeError("game exited with status %s (see %s)" % (self.proc.returncode, self.stderr.name))
        self.proc.stdin.write(json.dumps(command, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("game command timed out")
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("game closed its control stream (see %s)" % self.stderr.name)
        return json.loads(line)

    def close(self):
        if self.proc.poll() is None:
            try:
                self.command({"cmd": "quit"}, 3)
            except Exception:
                pass
        try:
            self.proc.wait(3)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.stderr.close()


def bmp_to_png(src, dst):
    data = open(src, "rb").read()
    if data[:2] != b"BM" or len(data) < 54:
        raise ValueError("game screenshot is not BMP")
    offset = struct.unpack_from("<I", data, 10)[0]
    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    # SDL commonly writes 32-bit BI_BITFIELDS (compression=3) with the
    # standard little-endian B,G,R,A masks; the first three bytes remain BGR.
    if width <= 0 or height == 0 or bpp not in (24, 32) or compression not in (0, 3):
        raise ValueError("unsupported BMP layout")
    top_down = height < 0
    height = abs(height)
    pixel_bytes = bpp // 8
    stride = (width * pixel_bytes + 3) & ~3
    raw = bytearray()
    for y in range(height):
        sy = y if top_down else height - 1 - y
        row = data[offset + sy * stride:offset + sy * stride + width * pixel_bytes]
        raw.append(0)
        for x in range(width):
            b, g, r = row[x * pixel_bytes:x * pixel_bytes + 3]
            raw.extend((r, g, b))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(dst, "wb") as f:
        f.write(png)


def take_shot(game, destination):
    destination = os.path.abspath(destination)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    fd, bmp = tempfile.mkstemp(prefix="dz-shot-", suffix=".bmp", dir=game.work)
    os.close(fd)
    try:
        reply = game.command({"cmd": "screenshot", "path": bmp})
        if reply.get("ok") is False:
            raise RuntimeError(reply.get("error", "screenshot failed"))
        bmp_to_png(bmp, destination)
    finally:
        try:
            os.unlink(bmp)
        except FileNotFoundError:
            pass
    return {"ok": True, "path": destination, "bytes": os.path.getsize(destination)}


def socket_request(name, request, timeout=130):
    sock_path = paths(name)[0]
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(sock_path)
        client.sendall(json.dumps(request).encode() + b"\n")
        buf = bytearray()
        while not buf.endswith(b"\n"):
            part = client.recv(65536)
            if not part:
                break
            buf += part
    if not buf:
        raise RuntimeError("debug daemon returned no reply")
    return json.loads(buf)


def daemon(args):
    sock_path, pid_path, _, _ = paths(args.name)
    cleanup_files(args.name)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    game = None
    try:
        server.bind(sock_path)
        os.chmod(sock_path, 0o600)
        server.listen(8)
        with open(pid_path, "w", encoding="ascii") as f:
            f.write(str(os.getpid()) + "\n")
        game = Game(args.game, args.name, args.save, args.fast_boot)
        # Proves that the first control point has been reached before start returns.
        ready = game.command({"cmd": "state"})
        running = True
        while running:
            conn, _ = server.accept()
            with conn:
                try:
                    line = b""
                    while not line.endswith(b"\n"):
                        block = conn.recv(65536)
                        if not block:
                            break
                        line += block
                    request = json.loads(line)
                    action = request.get("action")
                    if action == "ping":
                        reply = {"ok": True, "pid": os.getpid(), "game_pid": game.proc.pid, "ready": ready}
                    elif action == "command":
                        reply = game.command(request["command"])
                    elif action == "shot":
                        reply = take_shot(game, request["path"])
                    elif action == "stop":
                        game.close()
                        game = None
                        reply = {"ok": True, "stopped": args.name}
                        running = False
                    else:
                        reply = {"ok": False, "error": "unknown daemon action"}
                except Exception as exc:
                    reply = {"ok": False, "error": str(exc)}
                conn.sendall(json.dumps(reply, separators=(",", ":")).encode() + b"\n")
    finally:
        if game is not None:
            game.close()
        server.close()
        cleanup_files(args.name)


def cmd_start(args):
    sock_path, pid_path, log_path, _ = paths(args.name)
    if os.path.exists(pid_path):
        try:
            pid = int(open(pid_path).read())
        except (OSError, ValueError):
            pid = -1
        if alive(pid):
            raise RuntimeError("session already exists: " + args.name)
    cleanup_files(args.name, include_work=True)
    script = os.path.abspath(__file__)
    argv = [sys.executable, script, "_daemon", args.name, "--game", os.path.abspath(args.game)]
    if args.save:
        argv += ["--save", os.path.abspath(args.save)]
    if args.fast_boot:
        argv.append("--fast-boot")
    log = open(log_path, "ab", buffering=0)
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                            start_new_session=True, close_fds=True)
    log.close()
    deadline = time.time() + args.timeout
    last_error = None
    while time.time() < deadline and proc.poll() is None:
        if os.path.exists(sock_path):
            try:
                reply = socket_request(args.name, {"action": "ping"}, 2)
                print(json.dumps({"ok": True, "name": args.name, **reply}, indent=2, sort_keys=True))
                return
            except Exception as exc:
                last_error = exc
        time.sleep(.05)
    raise RuntimeError("session failed to become ready%s; see %s" % (": " + str(last_error) if last_error else "", log_path))


def cmd_send(args):
    command = json.loads(args.command)
    print(json.dumps(socket_request(args.name, {"action": "command", "command": command}), indent=2, sort_keys=True))


def cmd_shot(args):
    reply = socket_request(args.name, {"action": "shot", "path": os.path.abspath(args.path)})
    if not reply.get("ok"):
        raise RuntimeError(reply.get("error"))
    print(json.dumps(reply, indent=2, sort_keys=True))


def cmd_stop(args):
    reply = socket_request(args.name, {"action": "stop"}, 10)
    deadline = time.time() + 5
    pid_path = paths(args.name)[1]
    while os.path.exists(pid_path) and time.time() < deadline:
        time.sleep(.05)
    print(json.dumps(reply, indent=2, sort_keys=True))


def cmd_list(_args):
    sessions = []
    for pid_path in glob.glob(PREFIX + "*.pid"):
        name = pid_path[len(PREFIX):-4]
        try:
            pid = int(open(pid_path).read())
        except (OSError, ValueError):
            continue
        if alive(pid):
            try:
                info = socket_request(name, {"action": "ping"}, .5)
            except Exception:
                info = {"ok": False}
            sessions.append({"name": name, "pid": pid, **info})
    print(json.dumps(sessions, indent=2, sort_keys=True))


def cmd_run(args):
    name = "oneshot-%d" % os.getpid()
    game = Game(args.game, name, args.save, args.fast_boot)
    replies = []
    try:
        game.command({"cmd": "state"})
        for value in args.cmd:
            replies.append(game.command(json.loads(value)))
        if args.shot:
            replies.append(take_shot(game, args.shot))
    finally:
        game.close()
        cleanup_files(name, include_work=True)
    for reply in replies:
        print(json.dumps(reply, indent=2, sort_keys=True))


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="subcommand", required=True)
    run = sub.add_parser("run", help="boot, execute commands, optionally shoot, then exit")
    run.add_argument("--game", default="build_linux/main"); run.add_argument("--save")
    run.add_argument("--cmd", action="append", default=[]); run.add_argument("--shot"); run.add_argument("--fast-boot", action="store_true")
    run.set_defaults(func=cmd_run)
    start = sub.add_parser("start", help="start a persistent session")
    start.add_argument("name"); start.add_argument("--game", default="build_linux/main"); start.add_argument("--save")
    start.add_argument("--fast-boot", action="store_true"); start.add_argument("--timeout", type=float, default=30)
    start.set_defaults(func=cmd_start)
    send = sub.add_parser("send", help="send one JSON game command")
    send.add_argument("name"); send.add_argument("command"); send.set_defaults(func=cmd_send)
    shot = sub.add_parser("shot", help="write a PNG screenshot")
    shot.add_argument("name"); shot.add_argument("path"); shot.set_defaults(func=cmd_shot)
    stop = sub.add_parser("stop", help="cleanly stop a session")
    stop.add_argument("name"); stop.set_defaults(func=cmd_stop)
    listing = sub.add_parser("list", help="list live sessions"); listing.set_defaults(func=cmd_list)
    hidden = sub.add_parser("_daemon")
    hidden.add_argument("name"); hidden.add_argument("--game", required=True); hidden.add_argument("--save")
    hidden.add_argument("--fast-boot", action="store_true"); hidden.set_defaults(func=daemon)
    return ap


def main():
    args = parser().parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        print("debug_repl: error: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
