"""btsnoop_hci.log -> RFCOMM frames per DLCI (with direction and time). Usage: btsnoop_rfcomm.py <log> [dlci,...]"""
import struct, sys, datetime
path = sys.argv[1]
want = {int(x, 0) for x in sys.argv[2].split(",")} if len(sys.argv) > 2 else None
data = open(path, "rb").read()
assert data[:8] == b"btsnoop\0", "not btsnoop"
off = 16
EPOCH = 0x00dcddb30f2f8000  # btsnoop timestamp offset (us from year 0 to 1970)
reasm = {}      # (handle, dir) -> bytearray
rfcomm_cids = set()  # (handle, cid) known RFCOMM channels
pending = {}    # (handle, scid-from-req) -> psm
def ts(t):
    return datetime.datetime.fromtimestamp((t - EPOCH) / 1e6).strftime("%H:%M:%S.%f")[:-3]
def fcs_skip(frame):
    return frame
def on_l2cap(handle, d, pdu, t):
    if len(pdu) < 4: return
    ln, cid = struct.unpack_from("<HH", pdu)
    body = pdu[4:4+ln]
    if cid == 1:  # signalling
        i = 0
        while i + 4 <= len(body):
            code, ident, l = body[i], body[i+1], struct.unpack_from("<H", body, i+2)[0]
            p = body[i+4:i+4+l]
            if code == 0x02 and len(p) >= 4:  # conn req: psm, scid
                psm, scid = struct.unpack_from("<HH", p)
                pending[(handle, ident)] = (psm, scid, d)
            elif code == 0x03 and len(p) >= 8:  # conn rsp: dcid, scid, result
                dcid, scid, res = struct.unpack_from("<HHH", p)
                req = pending.get((handle, ident))
                if req and req[0] == 3 and res == 0:
                    rfcomm_cids.add((handle, dcid)); rfcomm_cids.add((handle, scid))
            i += 4 + l
        return
    if (handle, cid) not in rfcomm_cids or len(body) < 4: return
    addr, ctrl = body[0], body[1]
    dlci = addr >> 2
    if body[2] & 1: length, hl = body[2] >> 1, 3
    else: length, hl = (body[2] >> 1) | (body[3] << 7), 4
    ftype = ctrl & 0xEF
    names = {0x2F: "SABM", 0x63: "UA", 0x0F: "DM", 0x43: "DISC", 0xEF: "UIH"}
    name = names.get(ftype, hex(ctrl))
    payload = body[hl:hl+length]
    if ftype == 0xEF and ctrl & 0x10 and dlci != 0:  # credit byte
        payload = body[hl+1:hl+1+length]
        name = "UIH+credit"
    if want is not None and dlci not in want: return
    who = "phone->buds" if d == 0 else "buds->phone"
    if dlci == 0 and ftype == 0xEF:
        name = "MUX"
    print(f"{ts(t)} {who} dlci=0x{dlci:02x} {name} len={len(payload)} {payload.hex(' ')}")
while off + 24 <= len(data):
    olen, ilen, flags, drops, t = struct.unpack_from(">IIIIq", data, off); off += 24
    pkt = data[off:off+ilen]; off += ilen
    d = flags & 1  # 0 = sent (host->controller = phone->buds), 1 = received
    if not pkt or pkt[0] != 0x02 or len(pkt) < 5: continue  # H4 ACL only
    hdr, ln = struct.unpack_from("<HH", pkt, 1)
    handle, pb = hdr & 0x0fff, (hdr >> 12) & 3
    frag = pkt[5:5+ln]
    key = (handle, d)
    if pb in (0, 2):
        reasm[key] = bytearray(frag)
    else:
        reasm.setdefault(key, bytearray()).extend(frag)
    buf = reasm[key]
    if len(buf) >= 4 and len(buf) >= 4 + struct.unpack_from("<H", buf)[0]:
        on_l2cap(handle, d, bytes(buf), t); reasm[key] = bytearray()
