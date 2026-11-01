"""Decode GSND CONTROL (RFCOMM DLCI 0x08) as a [Group][Code][Len:2BE][Value] stream per direction, with protobuf-looking values expanded.
Input: the output of btsnoop_rfcomm.py for dlci 8."""
import re, sys
def varint(b, i):
    v = s = 0
    while True:
        x = b[i]; i += 1; v |= (x & 0x7f) << s; s += 7
        if not x & 0x80: return v, i
def proto(b, depth=0):
    i = 0; out = []
    while i < len(b):
        tag, i = varint(b, i); f, wt = tag >> 3, tag & 7
        if f == 0: raise ValueError
        if wt == 0: v, i = varint(b, i); out.append(f"{f}:{v}")
        elif wt == 2:
            n, i = varint(b, i); v = b[i:i+n]; i += n
            if i > len(b): raise ValueError
            if v and all(32 <= c < 127 for c in v): out.append(f'{f}:"{v.decode()}"')
            else:
                try: out.append(f"{f}:{{{proto(v, depth+1)}}}" if depth < 5 and v else f"{f}:<{v.hex()}>")
                except Exception: out.append(f"{f}:<{v.hex()}>")
        elif wt == 5: out.append(f"{f}:x32({b[i:i+4].hex()})"); i += 4
        elif wt == 1: out.append(f"{f}:x64({b[i:i+8].hex()})"); i += 8
        else: raise ValueError
    if i != len(b): raise ValueError
    return " ".join(out)
buf = {"phone->buds": bytearray(), "buds->phone": bytearray()}
for line in open(sys.argv[1]):
    m = re.match(r"(\S+) (\S+) dlci=0x08 (UIH\S*) len=(\d+) ?(.*)", line.strip())
    if not m or m[4] == "0": continue
    ts, who = m[1], m[2]
    b = buf[who]; b += bytes.fromhex(m[5])
    while len(b) >= 4:
        n = (b[2] << 8) | b[3]
        if len(b) < 4 + n: break
        g, c, v = b[0], b[1], bytes(b[4:4+n]); del b[:4+n]
        try: desc = proto(v) if v else ""
        except Exception: desc = f"<{v.hex()}>"
        print(f"{ts} {who:11} {g:02x} {c:02x} len={n:<3} {desc}")
