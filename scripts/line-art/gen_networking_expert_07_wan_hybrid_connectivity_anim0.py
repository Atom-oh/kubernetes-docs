#!/usr/bin/env python3
"""Line-art animated SVG of hybrid failover: Direct Connect primary, VPN backup.

Copies the approved prototype (gen_basics_06_part5_anim0.py): same palette
tokens, pen filter, stroke classes, font stack, caption layout, packet-tag
style and ko/en COPY structure. Reuses the keyTimes self-check from
gen_basics_06_part5_anim1.py. SMIL drives motion on one shared clock; CSS
only handles palette (light/dark) and the reduced-motion static view.

Story: packet 1 goes on-prem router -> DX location -> Transit Gateway -> VPC.
The DX gateway is drawn as a control-plane label only (it reflects BGP routes
and sits outside the data path). Then the DX link is cut, BFD drops the BGP
session, and packet 2 takes the IPsec VPN over the internet to the same TGW.

Addresses: on-prem 10.10.0.0/16 and VPC 10.20.0.0/16 (RFC 1918); the VPN
outside addresses 203.0.113.10 and 198.51.100.10 (RFC 5737); AS 65010 is a
private ASN (64512-65534).
"""
import math
import sys

DUR = 14.0  # seconds per loop

# ---------- geometry ----------------------------------------------------------
ROUTER = (110, 150)
DXL = (410, 150)
TGW = (610, 150)
VPC = (850, 150)
CLOUD = (380, 292)

# Cable centre lines (hand-drawn: gentle curves, never ruler straight).
DX_A = [(164, 150), (230, 128), (310, 172), (382, 150)]      # router -> DX location
DX_B = [(438, 150), (480, 130), (520, 168), (558, 150)]      # DX location -> TGW
LAST = [(662, 150), (705, 132), (752, 168), (828, 150)]      # TGW -> VPC instance
VPN_A = [(150, 172), (200, 182), (205, 260), (330, 292)]     # router -> internet
VPN_B = [(430, 292), (520, 292), (602, 252), (610, 176)]     # internet -> TGW

NOTE = (640, 236, 280, 62)  # x, y, w, h: routing-table note (right, below VPC)


def bez(p, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    u = 1 - t
    return (u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
            u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3)


def blen(p, n=200):
    pts = [bez(p, i / n) for i in range(n + 1)]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def c(p):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    return f"M{x0} {y0} C{x1} {y1} {x2} {y2} {x3} {y3}"


def motion(segments):
    """Build one combined motion path; return (d, cumulative fractions)."""
    start = segments[0][1][0]
    d_parts, lengths = [], []
    for kind, pts in segments:
        if kind == "bez":
            (x1, y1), (x2, y2), (x3, y3) = pts[1:]
            d_parts.append(f"C{x1} {y1} {x2} {y2} {x3} {y3}")
            lengths.append(blen(pts))
        else:
            d_parts.append(f"L{pts[1][0]} {pts[1][1]}")
            lengths.append(math.dist(*pts))
    total = sum(lengths)
    cum = [0.0]
    for L in lengths:
        cum.append(cum[-1] + L)
    return f"M{start[0]} {start[1]} " + " ".join(d_parts), [x / total for x in cum]


# Packet 1 (primary): DX cable, through the DX location, DX cable, across the TGW puck, to the VPC.
P1_D, P1_F = motion([("bez", DX_A), ("line", [DX_A[-1], DX_B[0]]), ("bez", DX_B),
                     ("line", [DX_B[-1], LAST[0]]), ("bez", LAST)])
# Packet 2 (backup): down to the internet, through the cloud, up to the TGW, across it, to the VPC.
P2_D, P2_F = motion([("bez", VPN_A), ("line", [VPN_A[-1], VPN_B[0]]), ("bez", VPN_B),
                     ("line", [VPN_B[-1], LAST[0]]), ("bez", LAST)])

# Timeline (seconds): travel, dwell, travel ...
T = {
    "p1_on": 0.3, "p1_go": 1.2, "p1_dxl": 2.4, "p1_dxl_go": 3.2, "p1_tgw": 4.4,
    "p1_tgw_go": 5.2, "p1_vpc": 6.0, "p1_off": 6.3,
    "cut": 6.5, "withdraw": 7.4,
    "p2_on": 8.0, "p2_go": 8.9, "p2_tgw": 10.7, "p2_tgw_go": 11.4, "p2_vpc": 12.2,
    "hold": 12.8,
}
ESP_TAG = "+ESP · outer IP header\n203.0.113.10 → 198.51.100.10"
kt = lambda s: f"{s / DUR:.4f}"
ANIMS = []  # every keyTimes/values pair, validated before writing


def anim(attr, times, values, extra=""):
    ts = ";".join(kt(t) for t in times)
    vs = ";".join(str(v) for v in values)
    ANIMS.append((ts, vs))
    return (f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{ts}" values="{vs}"{extra}/>')


def win(start, end, fade=0.25, after=None):
    """opacity keyframes: hidden -> visible [start,end] -> `after` (or hidden)."""
    a = after if after is not None else 0
    pts = [(0, 0), (max(start - fade, 0.001), 0), (start, 1), (end, 1),
           (min(end + fade, DUR - 0.002), a), (DUR, a if after else 0)]
    return anim("opacity", [t for t, _ in pts], [v for _, v in pts])


def move(d, keys):
    """keys: [(seconds, path fraction), ...] starting at 0 s and ending at DUR."""
    times = [t for t, _ in keys]
    points = [p for _, p in keys]
    ts = ";".join(kt(t) for t in times)
    kp = ";".join(f"{p:.4f}" for p in points)
    ANIMS.append((ts, kp))
    return (f'<animateMotion dur="{DUR}s" repeatCount="indefinite" calcMode="linear" '
            f'keyPoints="{kp}" keyTimes="{ts}" path="{d}"/>')


def check_anims():
    for ts, vs in ANIMS:
        t = [float(x) for x in ts.split(";")]
        v = vs.split(";")
        assert t[0] == 0 and t[-1] == 1, ts
        assert all(b >= a for a, b in zip(t, t[1:])), ts
        assert len(t) == len(v), (ts, vs)


# ---------- copy --------------------------------------------------------------
COPY = {
    "ko": {
        "title": "하이브리드 장애 조치: DX가 끊기면 패킷이 VPN으로 우회한다",
        "desc": ("온프레미스 라우터(AS 65010, 10.10.0.0/16)는 VPC 10.20.0.0/16으로 가는 BGP 경로를 두 개 배운다. "
                 "LOCAL_PREF 200인 Direct Connect 경로를 골라 첫 패킷을 DX 연결의 802.1Q VLAN 101(transit VIF)로 보낸다. "
                 "패킷은 DX 로케이션을 지나 목적지가 그대로인 채 Transit Gateway에 도착하고, TGW 라우트 테이블에 따라 "
                 "VPC attachment로 전달된다. "
                 "DX 게이트웨이는 BGP 경로만 반사하며 데이터 경로에 있지 않다. 이어서 DX 링크가 끊긴다. BFD가 "
                 "300 ms 간격으로 3번 응답을 받지 못하면 BGP 세션이 내려가고 DX 경로가 양쪽에서 철회된다. "
                 "다음 패킷은 LOCAL_PREF 100인 VPN 경로를 탄다. IPsec이 ESP와 바깥 IP 헤더 203.0.113.10 → "
                 "198.51.100.10을 붙여 인터넷을 지나고, TGW의 VPN attachment에서 복호화되어 VPC에 도착한다. "
                 "돌아오는 트래픽도 DX 경로가 사라졌으므로 VPN 전파 경로를 쓴다."),
        "router": ["온프레미스 라우터", "AS 65010 · 10.10.0.0/16"],
        "dxl": ["DX 로케이션", "transit VIF · VLAN 101"],
        "tgw": ["Transit Gateway", "라우트 테이블"],
        "vpc": ["VPC 10.20.0.0/16", "인스턴스 10.20.1.10"],
        "dxgw": ["DX 게이트웨이", "BGP 경로 반사, 데이터 경로 밖"],
        "dxcable": "Direct Connect · 주 경로",
        "inet": "인터넷",
        "vpn": "Site-to-Site VPN (IPsec 터널 2개) · 백업",
        "note_head": "온프레미스 BGP: 10.20.0.0/16 최적 경로",
        "note1": ["▶ DX (transit VIF) · LOCAL_PREF 200", "   VPN 터널 · LOCAL_PREF 100"],
        "note2": ["× DX: 철회됨 (BGP 세션 다운)", "▶ VPN 터널 · LOCAL_PREF 100"],
        "note_static": ["DX · LOCAL_PREF 200: 주 경로", "VPN · LOCAL_PREF 100: 백업"],
        "steps": [
            "① 온프레미스 라우터: LOCAL_PREF 200인 DX 경로를 골라 802.1Q VLAN 101(transit VIF)로 보낸다",
            "② DX 로케이션 → TGW → VPC attachment, 목적지는 그대로 (DX 게이트웨이는 경로만 반사)",
            "③ DX 링크 단절: BFD가 300 ms × 3 동안 응답을 못 받아 BGP 세션이 내려가고 경로가 철회된다",
            "④ 다음 패킷은 VPN 경로: IPsec이 ESP와 바깥 IP 203.0.113.10 → 198.51.100.10을 붙인다",
            "⑤ TGW가 VPN attachment에서 복호화된 패킷을 VPC로 전달, 돌아오는 경로도 VPN으로 바뀐다",
        ],
        "hint": "패킷 위 꼬리표: 지금 바뀐 헤더 값",
    },
    "en": {
        "title": "Hybrid failover: a packet reroutes from Direct Connect to the VPN",
        "desc": ("The on-premises router (AS 65010, 10.10.0.0/16) learns two BGP paths to VPC 10.20.0.0/16. It sends "
                 "the first packet over the Direct Connect path, which carries LOCAL_PREF 200, on the DX connection's "
                 "802.1Q VLAN 101 (transit VIF). Past the DX location the packet reaches the Transit Gateway with its "
                 "destination unchanged, and the TGW route table forwards it to the VPC attachment. The DX gateway only reflects BGP routes and is not in the data path. Then the DX link "
                 "is cut. When BFD misses three replies at 300 ms intervals, the BGP session goes down and the DX "
                 "routes are withdrawn on both sides. The next packet takes the VPN path with LOCAL_PREF 100: IPsec "
                 "adds ESP and an outer IP header 203.0.113.10 → 198.51.100.10, crosses the internet, is decrypted on "
                 "the TGW's VPN attachment and reaches the VPC. Return traffic also uses the VPN-propagated route "
                 "because the DX route is gone."),
        "router": ["On-prem router", "AS 65010 · 10.10.0.0/16"],
        "dxl": ["DX location", "transit VIF · VLAN 101"],
        "tgw": ["Transit Gateway", "route tables"],
        "vpc": ["VPC 10.20.0.0/16", "instance 10.20.1.10"],
        "dxgw": ["DX gateway", "reflects BGP routes, off the data path"],
        "dxcable": "Direct Connect · primary",
        "inet": "Internet",
        "vpn": "Site-to-Site VPN (2 IPsec tunnels) · backup",
        "note_head": "On-prem BGP: best path to 10.20.0.0/16",
        "note1": ["▶ DX (transit VIF) · LOCAL_PREF 200", "   VPN tunnel · LOCAL_PREF 100"],
        "note2": ["× DX: withdrawn (BGP session down)", "▶ VPN tunnel · LOCAL_PREF 100"],
        "note_static": ["DX · LOCAL_PREF 200: primary", "VPN · LOCAL_PREF 100: backup"],
        "steps": [
            "① On-prem router: the DX path wins with LOCAL_PREF 200; it sends on 802.1Q VLAN 101 (transit VIF)",
            "② DX location → TGW → VPC attachment, destination unchanged (the DX gateway only reflects routes)",
            "③ DX link cut: BFD misses 3 × 300 ms, the BGP session drops and the DX routes are withdrawn",
            "④ Next packet takes the VPN path: IPsec adds ESP and outer IP 203.0.113.10 → 198.51.100.10",
            "⑤ TGW decrypts on the VPN attachment and forwards to the VPC; return traffic moves to the VPN too",
        ],
        "hint": "Tag on the packet: the header field that just changed",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def puck(g, x, y):
    """Router symbol (puck with four arrows), as in the prototype."""
    g.append(f'<path class="ink" d="M{x-52} {y-14} q0 -16 52 -16 q52 0 52 16 l0 22 q0 16 -52 16 q-52 0 -52 -16 z"/>')
    g.append(f'<path class="thin" d="M{x-52} {y-14} q0 16 52 16 q52 0 52 -16"/>')
    for (x1, y1, x2, y2) in ((x-22, y-20, x-6, y-12), (x+22, y-8, x+6, y-16),
                             (x-6, y-20, x-22, y-12), (x+6, y-8, x+22, y-16)):
        g.append(f'<path class="thin" d="M{x1} {y1} L{x2} {y2}"/>')


def cut_mark(cls_extra=""):
    """Visible break on the DX cable: paper gap plus a vermilion X."""
    mx, my = bez(DX_A, 0.5)
    mx, my = round(mx), round(my)
    return (f'<rect class="paper" x="{mx-8}" y="{my-12}" width="16" height="24"/>'
            f'<path class="pkl{cls_extra}" stroke-width="3" d="M{mx-11} {my-11} L{mx+11} {my+11} M{mx+11} {my-11} L{mx-11} {my+11}"/>')


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    W, H = 960, 500
    steps_t = [(T["p1_on"], T["p1_dxl"]), (T["p1_dxl"], T["p1_off"]),
               (T["cut"], T["p2_on"]), (T["p2_on"], T["p2_tgw"]),
               (T["p2_tgw"], T["p2_vpc"] + 0.1)]
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="t d" font-family="Pretendard, \'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Noto Sans CJK KR\', \'Malgun Gothic\', \'Segoe UI\', sans-serif">')
    o.append(f'<title id="t">{esc(k["title"])}</title><desc id="d">{esc(k["desc"])}</desc>')
    o.append("""<style>
  svg{--paper:#f7f1e3;--ink:#2b2724;--soft:#8a8177;--accent:#d9480f;--blue:#1864ab;--wash:#efe5cf}
  @media (prefers-color-scheme:dark){svg{--paper:#1e2240;--ink:#ece6d6;--soft:#9aa0bd;--accent:#ff8b5e;--blue:#8cc8ff;--wash:#272c52}}
  .paper{fill:var(--paper)} .wash{fill:var(--wash)}
  .ink{fill:none;stroke:var(--ink);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
  .thin{fill:none;stroke:var(--ink);stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
  .cable{fill:none;stroke:var(--ink);stroke-width:1.5;stroke-linecap:round}
  .trunk{fill:none;stroke:var(--blue);stroke-width:1.5;stroke-linecap:round}
  .fillink{fill:var(--ink)} .t{fill:var(--ink);font-size:15px} .s{fill:var(--soft);font-size:12.5px}
  .h{fill:var(--ink);font-size:17px;font-weight:600} .acc{fill:var(--accent)} .bl{fill:var(--blue)}
  .pk{fill:var(--paper);stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
  .pkl{fill:none;stroke:var(--accent);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
  .tag{font-size:12px;font-weight:700} .cap{font-size:15px;fill:var(--ink)}
  .row{fill:var(--ink);font-size:13.5px}
  .halo{paint-order:stroke;stroke:var(--paper);stroke-width:4px;stroke-linejoin:round}
  .static{display:none}
  @media (prefers-reduced-motion:reduce){.motion{display:none}.static{display:inline}}
</style>""")
    o.append("""<defs><filter id="pen" filterUnits="userSpaceOnUse" x="0" y="0" width="960" height="500">
  <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="7"/>
  <feDisplacementMap in="SourceGraphic" scale="1.6"/></filter></defs>""")
    o.append(f'<rect class="paper" width="{W}" height="{H}"/>')
    o.append(f'<text class="h" x="32" y="40">{esc(k["title"])}</text>')

    # --- drawing (pen-wobbled) ---
    g = ['<g filter="url(#pen)">']
    # cables: two pen lines per cable (open-stroke band, line-art signature)
    for path in (DX_A, DX_B, LAST):
        for dy in (-2.5, 2.5):
            g.append(f'<path class="cable" d="{c([(x, y + dy) for x, y in path])}"/>')
    # VPN backup: one dashed pen line over the internet
    for path in (VPN_A, VPN_B):
        g.append(f'<path class="cable" stroke-dasharray="6 7" d="{c(path)}"/>')
    # on-prem router and Transit Gateway (router pucks)
    puck(g, *ROUTER)
    puck(g, *TGW)
    # DX location: a cage with a rack inside
    x, y = DXL
    g.append(f'<path class="ink" d="M{x-28} {y-38} q0 -4 4 -4 l48 1 q5 0 5 5 l-1 72 q0 4 -4 4 l-48 -1 q-4 0 -4 -4 z"/>')
    for i in range(4):
        yy = y - 28 + i * 16
        g.append(f'<path class="thin" d="M{x-18} {yy} l36 1 l0 9 l-36 0 z"/>')
    g.append(f'<circle class="fillink" cx="{x+12}" cy="{y-24}" r="2"/><circle class="fillink" cx="{x+12}" cy="{y-8}" r="2"/>')
    # VPC: dashed boundary with one instance
    x, y = VPC
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="M{x-64} {y-38} q0 -6 6 -6 l118 1 q6 0 6 6 l-1 74 q0 6 -6 6 l-117 -1 q-6 0 -6 -6 z"/>')
    g.append(f'<path class="ink" d="M{x-20} {y-18} l40 1 l-1 36 l-39 0 z"/>')
    g.append(f'<path class="thin" d="M{x-12} {y-8} l24 0 M{x-12} {y} l18 0 M{x-12} {y+8} l22 0"/>')
    # internet cloud
    cx, cy = CLOUD
    g.append(f'<path class="ink" d="M{cx-56} {cy+20} q-20 -2 -16 -20 q4 -16 22 -14 q6 -22 32 -18 '
             f'q18 -16 40 0 q24 -6 30 16 q20 2 16 22 q-4 14 -20 14 z"/>')
    # DX gateway: control-plane box above the DX location -> TGW cable, dotted leader
    bx, by = 412, 52
    g.append(f'<path class="thin" stroke-dasharray="2 5" d="M{bx} {by} l170 1 l-1 36 l-169 -1 z"/>')
    g.append(f'<path class="thin" stroke-dasharray="2 5" d="M{bx+118} {by+38} q3 22 0 46"/>')
    # routing-table note frame
    nx, ny, nw, nh = NOTE
    g.append(f'<path class="thin" d="M{nx} {ny} l{nw} 1 l-1 {nh} l-{nw-1} -1 z"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    for (x, y), (n, sub) in ((ROUTER, k["router"]), (DXL, k["dxl"]), (TGW, k["tgw"]), (VPC, k["vpc"])):
        o.append(f'<text class="t" x="{x}" y="{y+60}" text-anchor="middle" font-weight="600">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+78}" text-anchor="middle">{esc(sub)}</text>')
    o.append(f'<text class="s" x="{bx+85}" y="{by+16}" text-anchor="middle" font-weight="700">{esc(k["dxgw"][0])}</text>')
    o.append(f'<text class="s" x="{bx+85}" y="{by+31}" text-anchor="middle">{esc(k["dxgw"][1])}</text>')
    dxm = bez(DX_A, 0.5)
    o.append(f'<text class="s" x="{round(dxm[0])}" y="128" text-anchor="middle">{esc(k["dxcable"])}</text>')
    o.append(f'<text class="s" x="{CLOUD[0]+4}" y="{CLOUD[1]+6}" text-anchor="middle">{esc(k["inet"])}</text>')
    o.append(f'<text class="s" x="40" y="330">{esc(k["vpn"])}</text>')
    o.append(f'<text class="s acc" x="{nx+10}" y="{ny+17}" font-weight="700">{esc(k["note_head"])}</text>')
    row_y = [ny + 37, ny + 55]

    # --- motion layer ---
    m = ['<g class="motion">']
    # VPN path turns blue (active) once the DX routes are withdrawn
    m.append(f'<g opacity="0">{win(T["withdraw"], T["hold"])}')
    for path in (VPN_A, VPN_B):
        m.append(f'<path class="trunk" stroke-width="2.4" stroke-dasharray="6 7" d="{c(path)}"/>')
    m.append('</g>')
    # the DX link break
    m.append(f'<g opacity="0">{win(T["cut"], T["hold"], fade=0.15)}{cut_mark()}</g>')
    # routing-table rows: before and after the withdrawal
    for rows, s0, s1 in ((k["note1"], T["p1_on"] + 0.3, T["withdraw"] - 0.25),
                         (k["note2"], T["withdraw"] + 0.05, T["hold"])):
        m.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}')
        for i, txt in enumerate(rows):
            m.append(f'<text class="row" x="{nx+10}" y="{row_y[i]}">{esc(txt)}</text>')
        m.append('</g>')

    def packet(d, keys, on, off, tags):
        r = ['<g>', win(on, off, fade=0.2), move(d, keys)]
        r.append('<path class="pk" d="M-17 -11 l34 0 l0 22 l-34 0 z"/><path class="pkl" d="M-17 -11 l17 12 l17 -12"/>')
        for text, s0, s1, cls, tx, ty, anchor in tags:
            lines = "".join(f'<tspan x="{tx}" dy="{0 if i == 0 else 14}">{esc(line)}</tspan>'
                            for i, line in enumerate(text.split("\n")))
            r.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                     f'<text class="tag halo {cls}" x="{tx}" y="{ty}" text-anchor="{anchor}">{lines}</text></g>')
        r.append('</g>')
        return "".join(r)

    f1 = P1_F
    m.append(packet(P1_D, [(0, 0), (T["p1_go"], 0), (T["p1_dxl"], f1[1]), (T["p1_dxl_go"], f1[2]),
                           (T["p1_tgw"], f1[3]), (T["p1_tgw_go"], f1[4]), (T["p1_vpc"], 1), (DUR, 1)],
                    T["p1_on"], T["p1_off"], [
        ("802.1Q VLAN 101 · dst 10.20.1.10", T["p1_on"], T["p1_dxl"] + 0.2, "bl", 0, -38, "middle"),
        ("dst 10.20.1.10 (unchanged)", T["p1_dxl"] + 0.4, T["p1_tgw"] + 0.2, "acc", 0, -48, "middle"),
        ("→ VPC attachment · dst 10.20.1.10", T["p1_tgw"] + 0.4, T["p1_off"], "acc", 0, -38, "middle"),
    ]))
    f2 = P2_F
    m.append(packet(P2_D, [(0, 0), (T["p2_go"], 0), (T["p2_tgw"], f2[3]), (T["p2_tgw_go"], f2[4]),
                           (T["p2_vpc"], 1), (DUR, 1)],
                    T["p2_on"], T["hold"], [
        # shown while the router encapsulates; hidden before the tag would reach the
        # DX location labels and the cloud (caption 4 carries the same values)
        (ESP_TAG, T["p2_on"], T["p2_go"] - 0.15, "bl", 22, 0, "start"),
        ("ESP removed · dst 10.20.1.10", T["p2_tgw"] + 0.2, T["hold"], "acc", 20, -60, "middle"),
    ]))
    # captions
    cy0 = 372
    for i, (txt, (s0, s1)) in enumerate(zip(k["steps"], steps_t)):
        y = cy0 + i * 22
        assert s1 + 0.3 < T["hold"], txt
        m.append(f'<g opacity="0">'
                 + anim("opacity", [0, max(s0 - 0.2, 0.001), s0, s1, s1 + 0.3, T["hold"], T["hold"] + 0.4, DUR],
                        [0, 0, 1, 1, 0.42, 0.42, 0, 0])
                 + f'<text class="cap" x="40" y="{y}">{esc(txt)}</text></g>')
    m.append(f'<text class="s" x="{W-32}" y="{H-14}" text-anchor="end">{esc(k["hint"])}</text>')
    m.append('</g>')
    o.extend(m)

    # --- static (reduced motion) layer ---
    st = ['<g class="static">', cut_mark()]
    for i, txt in enumerate(k["note_static"]):
        st.append(f'<text class="row" x="{nx+10}" y="{row_y[i]}">{esc(txt)}</text>')
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    for (x, y, label) in ((ROUTER[0] - 8, 110, "①"), (DXL[0] + 36, 112, "②"), (282, 184, "③"),
                          (214, 252, "④"), (TGW[0] + 58, 124, "⑤")):
        st.append(f'<text class="tag acc" x="{x}" y="{y}" font-size="16">{label}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    return "\n".join(o)


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-networking-expert-07-wan-hybrid-connectivity-anim-0.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-networking-expert-07-wan-hybrid-connectivity-anim-0.svg")
        svg = build(lang)
        assert "\u2014" not in svg, "em dash in output"
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [round(x, 3) for x in P1_F], [round(x, 3) for x in P2_F])
