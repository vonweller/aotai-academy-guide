# -*- coding: utf-8 -*-
"""零依赖 MQTT broker（内网演示用，QoS0/1，保留消息支持）

现场没有 mosquitto 时用它顶：
  python 03_网页3D/bridge/broker.py --port 1883

注意：这是**教学/演示用**的最简 broker，只监听 0.0.0.0:1883，无认证。
不要暴露到公网。
"""
import argparse
import socket
import struct
import threading
import time


def log(*a):
    print("[broker]", *a)


class Msg(object):
    __slots__ = ("topic", "payload", "qos", "retain")

    def __init__(self, topic, payload, qos=0, retain=False):
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain


class Client(object):
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.client_id = ""
        self.subs = []           # [(filter, qos)]
        self.alive = True

    def matches(self, topic):
        for f, _ in self.subs:
            if _topic_match(f, topic):
                return True
        return False


def _topic_match(filt, topic):
    ft = filt.split("/")
    tt = topic.split("/")
    for i, p in enumerate(ft):
        if p == "#":
            return True
        if i >= len(tt):
            return False
        if p == "+":
            continue
        if p != tt[i]:
            return False
    return len(ft) == len(tt)


class Broker(object):
    def __init__(self, host="0.0.0.0", port=1883):
        self.host = host
        self.port = port
        self.clients = []
        self.lock = threading.Lock()
        self.retained = {}
        self.srv = None

    # ---------- 编解码 ----------
    @staticmethod
    def _read_exact(sock, n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("eof")
            buf += chunk
        return buf

    @staticmethod
    def _read_remaining(sock):
        mult, value = 1, 0
        for _ in range(4):
            b = Broker._read_exact(sock, 1)[0]
            value += (b & 0x7F) * mult
            mult *= 128
            if not (b & 0x80):
                break
        return value

    @staticmethod
    def _enc_remaining(n):
        out = b""
        while True:
            d = n % 128
            n //= 128
            if n > 0:
                d |= 0x80
            out += bytes([d])
            if n == 0:
                return out

    @staticmethod
    def _enc_str(s):
        b = s.encode("utf-8") if isinstance(s, str) else s
        return struct.pack("!H", len(b)) + b

    # ---------- 连接处理 ----------
    def serve(self):
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind((self.host, self.port))
        self.srv.listen(32)
        log("listening on %s:%d" % (self.host, self.port))
        while True:
            try:
                s, addr = self.srv.accept()
            except Exception:
                break
            t = threading.Thread(target=self._client_thread, args=(s, addr))
            t.daemon = True
            t.start()

    def _client_thread(self, sock, addr):
        c = Client(sock, addr)
        log("connect", addr)
        try:
            while c.alive:
                hdr = self._read_exact(sock, 1)[0]
                ptype = (hdr & 0xF0) >> 4
                flags = hdr & 0x0F
                rl = self._read_remaining(sock)
                body = self._read_exact(sock, rl) if rl else b""
                if ptype == 1:            # CONNECT
                    self._handle_connect(c, body)
                elif ptype == 3:          # PUBLISH
                    self._handle_publish(c, flags, body)
                elif ptype == 8:          # SUBSCRIBE
                    self._handle_subscribe(c, body)
                elif ptype == 10:         # UNSUBSCRIBE
                    self._handle_unsubscribe(c, body)
                elif ptype == 12:         # PINGREQ
                    sock.sendall(b"\xd0\x00")
                elif ptype == 14:         # DISCONNECT
                    c.alive = False
        except Exception as e:
            log("client gone", addr, e)
        finally:
            with self.lock:
                if c in self.clients:
                    self.clients.remove(c)
            try:
                sock.close()
            except Exception:
                pass

    def _handle_connect(self, c, body):
        try:
            i = 0
            plen = struct.unpack("!H", body[i:i + 2])[0]; i += 2
            i += plen                                    # protocol name
            i += 1                                       # level
            cflags = body[i]; i += 1
            i += 2                                       # keepalive
            idlen = struct.unpack("!H", body[i:i + 2])[0]; i += 2
            c.client_id = body[i:i + idlen].decode("utf-8", "ignore"); i += idlen
        except Exception:
            c.client_id = "client-%d" % id(c)
        with self.lock:
            self.clients.append(c)
        c.sock.sendall(b"\x20\x02\x00\x00")   # CONNACK ok
        log("connected", c.client_id)

    def _handle_subscribe(self, c, body):
        pid = struct.unpack("!H", body[0:2])[0]
        i = 2
        granted = b""
        while i < len(body):
            tlen = struct.unpack("!H", body[i:i + 2])[0]; i += 2
            topic = body[i:i + tlen].decode("utf-8", "ignore"); i += tlen
            qos = body[i] if i < len(body) else 0
            i += 1
            c.subs.append((topic, qos))
            granted += bytes([min(qos, 1)])
            log("sub", c.client_id, "->", topic)
            # 补发保留消息
            for rt, msg in list(self.retained.items()):
                if _topic_match(topic, rt):
                    self._send_publish(c, msg, force_qos=0)
        pkt = b"\x90" + self._enc_remaining(2 + len(granted)) + struct.pack("!H", pid) + granted
        c.sock.sendall(pkt)

    def _handle_unsubscribe(self, c, body):
        try:
            pid = struct.unpack("!H", body[0:2])[0]
            i = 2
            tlen = struct.unpack("!H", body[i:i + 2])[0]; i += 2
            topic = body[i:i + tlen].decode("utf-8", "ignore")
            c.subs = [(f, q) for (f, q) in c.subs if f != topic]
            c.sock.sendall(b"\xb0\x02" + struct.pack("!H", pid))
        except Exception:
            pass

    def _handle_publish(self, c, flags, body):
        qos = (flags >> 1) & 0x03
        retain = bool(flags & 0x01)
        i = 0
        tlen = struct.unpack("!H", body[i:i + 2])[0]; i += 2
        topic = body[i:i + tlen].decode("utf-8", "ignore"); i += tlen
        pid = None
        if qos > 0:
            pid = struct.unpack("!H", body[i:i + 2])[0]; i += 2
        payload = body[i:]
        msg = Msg(topic, payload, qos, retain)
        if retain:
            self.retained[topic] = msg
        self._route(msg)
        if qos == 1 and pid is not None:
            c.sock.sendall(b"\x40\x02" + struct.pack("!H", pid))

    def _route(self, msg):
        with self.lock:
            targets = [cl for cl in list(self.clients) if cl.matches(msg.topic)]
        for cl in targets:
            try:
                self._send_publish(cl, msg)
            except Exception:
                cl.alive = False

    def _send_publish(self, cl, msg, force_qos=None):
        qos = 0 if force_qos is None else force_qos
        flags = (qos << 1) | (1 if msg.retain else 0)
        body = self._enc_str(msg.topic) + (struct.pack("!H", 0) if qos else b"") + msg.payload
        pkt = bytes([0x30 | flags]) + self._enc_remaining(len(body)) + body
        cl.sock.sendall(pkt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=1883)
    a = ap.parse_args()
    Broker(a.host, a.port).serve()


if __name__ == "__main__":
    main()
