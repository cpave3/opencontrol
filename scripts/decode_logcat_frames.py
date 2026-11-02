"""Decode OpenControl debug-mode hex lines (`DLCI 0x02: 7e ...`) from a logcat capture: HDLC -> pw_rpc -> settings payload.
Serial numbers (GetHardwareInfo field 7) are redacted from the output."""
import re, sys, zlib
names = {}
def h(s):
    r = len(s); c = 65599
    for ch in s.encode(): r = (r + c * ch) & 0xffffffff; c = (c * 65599) & 0xffffffff
    return r
for n in ['maestro_pw.Maestro','GetSoftwareInfo','GetHardwareInfo','SubscribeRuntimeInfo','WriteSetting','ReadSetting','SubscribeToSettingsChanges','a10a20.kpi.Kpi','KpiStream']:
    names[h(n)] = n
def varint(b, i):
    v = s = 0
    while True:
        x = b[i]; i += 1; v |= (x & 0x7f) << s; s += 7
        if not x & 0x80: return v, i
def fields(b):
    i = 0; out = []
    while i < len(b):
        tag, i = varint(b, i); f, wt = tag >> 3, tag & 7
        if wt == 0: v, i = varint(b, i)
        elif wt == 1: v = bytes(b[i:i+8]); i += 8
        elif wt == 5: v = bytes(b[i:i+4]); i += 4
        elif wt == 2: n, i = varint(b, i); v = bytes(b[i:i+n]); i += n
        else: raise ValueError(wt)
        if i > len(b) or f == 0: raise ValueError("truncated")
        out.append((f, wt, v))
    return out
def show(b, depth=0):
    try: fs = fields(b)
    except Exception: return b.hex()
    parts = []
    for f, wt, v in fs:
        if wt == 2:
            inner = show(v, depth + 1) if v and depth < 4 else v.hex()
            parts.append(f"{f}:{{{inner}}}" if inner and not inner.startswith("'") else f"{f}:{inner}")
        elif wt == 5: parts.append(f"{f}:f32({__import__('struct').unpack('<f', v)[0]:.2f})")
        elif wt == 1: parts.append(f"{f}:x64")
        else: parts.append(f"{f}:{v}")
    return " ".join(parts)
TYPES = {0:'REQ',1:'RESP',2:'CLI_STREAM',4:'CLI_ERR',5:'SRV_ERR',7:'SRV_STREAM'}
buf = bytearray()
for line in open(sys.argv[1]):
    m = re.search(r'(\d\d:\d\d:\d\d\.\d+).*DLCI 0x02: ([0-9a-f ]+)', line)
    if not m: continue
    ts = m[1]; buf += bytes.fromhex(m[2])
    while True:
        try: s = buf.index(0x7e)
        except ValueError: buf.clear(); break
        try: e = buf.index(0x7e, s + 1)
        except ValueError: del buf[:s]; break
        raw = bytes(buf[s+1:e]); del buf[:e]
        if not raw: continue
        un = bytearray(); esc = False
        for x in raw:
            if esc: un.append(x ^ 0x20); esc = False
            elif x == 0x7d: esc = True
            else: un.append(x)
        data, crc = bytes(un[:-4]), int.from_bytes(un[-4:], 'little')
        ok = zlib.crc32(data) == crc
        i = 0
        while not data[i] & 1: i += 1
        pkt = data[i+2:]
        p = {f: (int.from_bytes(v, 'little') if wt == 5 else v) for f, wt, v in fields(pkt)}
        payload = p.get(5, b"")
        meth = names.get(p.get(4), hex(p.get(4, 0)))
        if meth == 'GetHardwareInfo' and payload:
            desc = " ".join(f"{f}:{v}" if wt == 0 else f"{f}:<{len(v)}B{' redacted' if f == 7 else ''}>" for f, wt, v in fields(payload))
        else:
            desc = show(payload) if payload else ""
        print(f"{ts} crc={'ok' if ok else 'BAD'} {TYPES.get(p.get(1), p.get(1))} ch={p.get(2)} {meth} call={p.get(7, '-')} status={p.get(6, 0)} | {desc}")
