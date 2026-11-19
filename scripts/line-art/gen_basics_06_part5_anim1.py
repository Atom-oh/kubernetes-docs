#!/usr/bin/env python3
"""Line-art animated SVG of PAT (NAPT): two inside hosts share one public IP.

Copies the approved prototype (gen_basics_06_part5_anim0.py): same palette
tokens, pen filter, stroke classes, font stack, caption layout, packet-tag
style and ko/en COPY structure. SMIL drives motion on one shared clock; CSS
only handles palette (light/dark) and the reduced-motion static view.

Addresses: inside hosts use RFC 1918 (10.0.1.0/24); the NAT public address
(203.0.113.10) and the server (198.51.100.20) use separate RFC 5737
documentation blocks.
"""
import math
import sys

DUR = 14.0  # seconds per loop

# ---------- geometry ----------------------------------------------------------
HOST_A = (110, 105)
HOST_B = (110, 250)
NAT = (450, 152)
SRV = (840, 150)

# Cable centre lines (hand-drawn: gentle curves, never ruler straight).
CABLE_A = [(166, 105), (252, 86), (318, 162), (398, 146)]
CABLE_B = [(166, 250), (262, 270), (318, 176), (398, 160)]
WAN = [(502, 152), (584, 128), (700, 178), (800, 150)]

NAT_L_A = CABLE_A[-1]     # where packet A meets the NAT puck
NAT_L_B = CABLE_B[-1]     # where packet B / the reply meets the NAT puck
NAT_R = WAN[0]            # NAT puck, WAN side

# Translation-table box (below the WAN cable, clear of every packet tag).
TB = (452, 214, 330, 100)  # x, y, w, h


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


def rev(p):
    return list(reversed(p))


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


# Packet 1: Host-A -> NAT (dwell) -> across the puck -> WAN -> server.
P1_D, P1_F = motion([("bez", CABLE_A), ("line", [NAT_L_A, NAT_R]), ("bez", WAN)])
# Packet 2: Host-B -> NAT (dwell) -> across the puck -> WAN -> server.
P2_D, P2_F = motion([("bez", CABLE_B), ("line", [NAT_L_B, NAT_R]), ("bez", WAN)])
# Reply: server -> WAN -> NAT (dwell) -> across the puck -> Host-B.
P3_D, P3_F = motion([("bez", rev(WAN)), ("line", [NAT_R, NAT_L_B]), ("bez", rev(CABLE_B))])

# Timeline (seconds): travel, dwell, travel ...
T = {
    "a_on": 0.3, "a_go": 0.6, "a_nat": 2.2, "a_dwell": 3.4, "a_srv": 5.0,
    "b_on": 5.0, "b_go": 5.3, "b_nat": 6.6, "b_dwell": 7.8, "b_srv": 9.0,
    "r_on": 9.0, "r_go": 9.2, "r_nat": 10.2, "r_dwell": 11.2, "r_end": 12.6,
    "hold": 13.2,
}
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


def move(d, fr, go, arrive, dwell, end):
    """Travel cable 1, dwell at the NAT edge, then cross the puck and travel on."""
    times = [0, go, arrive, dwell, end, DUR]
    nat_edge = fr[1]
    points = [0, 0, nat_edge, nat_edge, 1, 1]
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
        "title": "PAT: 두 내부 호스트가 공인 IP 하나를 나눠 쓰는 법",
        "desc": ("사설망 10.0.1.0/24의 Host-A(10.0.1.10)와 Host-B(10.0.1.20)가 둘 다 출발지 포트 50000으로 "
                 "서버 198.51.100.20:443에 연결한다. NAT 장비는 Host-A의 첫 패킷을 보고 변환 테이블에 "
                 "10.0.1.10:50000 → 203.0.113.10:30001 행을 만들고 출발지를 공인 주소로 바꾼다. Host-B의 패킷에는 "
                 "같은 공인 IP의 다른 포트 30002를 배정해 10.0.1.20:50000 → 203.0.113.10:30002 행을 만든다. "
                 "서버의 응답은 목적지 203.0.113.10:30002로 돌아오고, NAT는 공인 포트로 테이블을 찾아 2행과 일치시킨 뒤 "
                 "목적지를 10.0.1.20:50000으로 되돌려 Host-B에 전달한다."),
        "hostA": ["Host-A", "10.0.1.10"],
        "hostB": ["Host-B", "10.0.1.20"],
        "lan": "사설망 10.0.1.0/24 (RFC 1918)",
        "nat": ["NAT 장비 (PAT)", "공인 IP 203.0.113.10"],
        "srv": ["서버", "198.51.100.20:443"],
        "table": "변환 테이블",
        "cols": "내부 ip:port → 공인 ip:port",
        "rows": ["10.0.1.10:50000 → 203.0.113.10:30001",
                 "10.0.1.20:50000 → 203.0.113.10:30002"],
        "steps": [
            "① Host-A → 서버 198.51.100.20:443 · 출발지 10.0.1.10:50000",
            "② NAT: 테이블에 1행을 만들고 출발지를 203.0.113.10:30001로 바꾼다",
            "③ Host-B도 출발지 포트 50000 → NAT가 공인 포트 30002를 배정해 둘을 구분한다",
            "④ 응답의 목적지 203.0.113.10:30002 → 공인 포트로 테이블을 찾아 2행과 일치",
            "⑤ NAT가 목적지를 10.0.1.20:50000으로 되돌려 Host-B에 전달한다",
        ],
        "hint": "패킷 위 꼬리표: 지금 바뀐 헤더 값",
    },
    "en": {
        "title": "PAT: two inside hosts sharing one public IP",
        "desc": ("Host-A (10.0.1.10) and Host-B (10.0.1.20) on private network 10.0.1.0/24 both connect from source "
                 "port 50000 to server 198.51.100.20:443. On Host-A's first packet the NAT device adds the translation "
                 "row 10.0.1.10:50000 → 203.0.113.10:30001 and rewrites the source to the public address. For Host-B's "
                 "packet it assigns a different port on the same public IP, adding 10.0.1.20:50000 → "
                 "203.0.113.10:30002. The server's reply returns to destination 203.0.113.10:30002; the NAT looks up "
                 "the table by public port, matches row 2, rewrites the destination back to 10.0.1.20:50000 and "
                 "delivers it to Host-B."),
        "hostA": ["Host-A", "10.0.1.10"],
        "hostB": ["Host-B", "10.0.1.20"],
        "lan": "private 10.0.1.0/24 (RFC 1918)",
        "nat": ["NAT device (PAT)", "public IP 203.0.113.10"],
        "srv": ["Server", "198.51.100.20:443"],
        "table": "Translation table",
        "cols": "inside ip:port → public ip:port",
        "rows": ["10.0.1.10:50000 → 203.0.113.10:30001",
                 "10.0.1.20:50000 → 203.0.113.10:30002"],
        "steps": [
            "① Host-A → server 198.51.100.20:443 · source 10.0.1.10:50000",
            "② NAT: adds row 1 and rewrites the source to 203.0.113.10:30001",
            "③ Host-B also uses source port 50000 → NAT assigns public port 30002 to keep them apart",
            "④ Reply to 203.0.113.10:30002 → lookup by public port matches row 2",
            "⑤ NAT rewrites the destination back to 10.0.1.20:50000 → Host-B receives it",
        ],
        "hint": "Tag on the packet: the header field that just changed",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    W, H = 960, 500
    steps_t = [(T["a_go"], T["a_nat"]), (T["a_nat"], T["a_srv"]),
               (T["b_go"], T["b_srv"]), (T["r_go"], T["r_dwell"]),
               (T["r_dwell"], T["r_end"] + 0.2)]
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
  .row{fill:var(--ink);font-size:13.5px} .hl{fill:var(--blue);fill-opacity:.16}
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
    for path in (CABLE_A, CABLE_B):
        for dy in (-2.5, 2.5):
            g.append(f'<path class="cable" d="{c([(x, y + dy) for x, y in path])}"/>')
    for dy in (-3, 3):
        g.append(f'<path class="trunk" d="{c([(x, y + dy) for x, y in WAN])}"/>')
    # private-network boundary (dashed hand-drawn loop around both hosts)
    g.append('<path class="thin" stroke-dasharray="2 7" d="M44 62 q-6 -8 10 -10 l200 2 q12 0 12 12 '
             'l-4 262 q0 12 -12 12 l-198 -2 q-12 0 -12 -12 z"/>')
    # laptops
    for (x, y) in (HOST_A, HOST_B):
        g.append(f'<path class="ink" d="M{x-44} {y-40} q2 -3 6 -3 l76 1 q5 0 5 5 l-1 50 l-88 1 z"/>')
        g.append(f'<path class="thin" d="M{x-36} {y-31} l70 1 l-1 34 l-69 0 z"/>')
        g.append(f'<path class="ink" d="M{x-54} {y+13} l108 0 q4 0 2 4 l-6 7 l-100 0 l-6 -7 q-2 -4 2 -4"/>')
    # NAT device (router puck with arrows)
    rx, ry = NAT
    g.append(f'<path class="ink" d="M{rx-52} {ry-14} q0 -16 52 -16 q52 0 52 16 l0 22 q0 16 -52 16 q-52 0 -52 -16 z"/>')
    g.append(f'<path class="thin" d="M{rx-52} {ry-14} q0 16 52 16 q52 0 52 -16"/>')
    for (x1, y1, x2, y2) in ((rx-22, ry-20, rx-6, ry-12), (rx+22, ry-8, rx+6, ry-16),
                             (rx-6, ry-20, rx-22, ry-12), (rx+6, ry-8, rx+22, ry-16)):
        g.append(f'<path class="thin" d="M{x1} {y1} L{x2} {y2}"/>')
    # server tower (top kept below the packet tag at the cable end)
    sx, sy = SRV
    g.append(f'<path class="ink" d="M{sx-38} {sy-30} q0 -4 4 -4 l68 1 q5 0 5 5 l-1 76 q0 4 -4 4 l-68 -1 q-4 0 -4 -4 z"/>')
    for i in range(3):
        yy = sy - 18 + i * 20
        g.append(f'<path class="thin" d="M{sx-26} {yy} l50 1 M{sx-26} {yy+8} l34 0"/>')
    g.append(f'<circle class="fillink" cx="{sx+18}" cy="{sy+34}" r="2.2"/>')
    # translation table frame
    tx, ty, tw, th = TB
    g.append(f'<path class="thin" d="M{tx} {ty} l{tw} 1 l-1 {th} l-{tw-1} -1 z"/>')
    g.append(f'<path class="thin" d="M{tx+6} {ty+40} l{tw-12} 0"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    for (x, y), (n, sub) in ((HOST_A, k["hostA"]), (HOST_B, k["hostB"])):
        o.append(f'<text class="t" x="{x}" y="{y+48}" text-anchor="middle" font-weight="600">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+66}" text-anchor="middle">{esc(sub)}</text>')
    o.append(f'<text class="s" x="52" y="358">{esc(k["lan"])}</text>')
    o.append(f'<text class="t" x="{rx}" y="{ry-80}" text-anchor="middle" font-weight="600">{esc(k["nat"][0])}</text>')
    o.append(f'<text class="s bl" x="{rx}" y="{ry-62}" text-anchor="middle">{esc(k["nat"][1])}</text>')
    o.append(f'<text class="t" x="{sx}" y="{sy+74}" text-anchor="middle" font-weight="600">{esc(k["srv"][0])}</text>')
    o.append(f'<text class="s" x="{sx}" y="{sy+92}" text-anchor="middle">{esc(k["srv"][1])}</text>')
    o.append(f'<text class="s acc" x="{tx+10}" y="{ty+17}" font-weight="700">{esc(k["table"])}</text>')
    o.append(f'<text class="s" x="{tx+10}" y="{ty+33}">{esc(k["cols"])}</text>')
    row_y = [ty + 62, ty + 86]

    # --- motion layer ---
    m = ['<g class="motion">']
    # table rows: row 1 appears at NAT dwell of packet A, row 2 at packet B;
    # row 2 flashes again when the reply is matched.
    for i, (start, flash) in enumerate(((T["a_nat"], None), (T["b_nat"], T["r_nat"]))):
        y = row_y[i]
        m.append(f'<g opacity="0">{win(start, T["hold"])}')
        m.append(f'<rect class="hl" x="{tx+5}" y="{y-16}" width="{tw-10}" height="22" rx="4" opacity="0">'
                 + anim("opacity", [0, start, start + 0.15, T[("a" if i == 0 else "b") + "_dwell"], T[("a" if i == 0 else "b") + "_dwell"] + 0.4, DUR],
                        [0, 0, 1, 1, 0, 0]) + '</rect>')
        if flash is not None:
            m.append(f'<rect class="hl" x="{tx+5}" y="{y-16}" width="{tw-10}" height="22" rx="4" opacity="0">'
                     + anim("opacity", [0, flash, flash + 0.15, T["r_dwell"], T["r_dwell"] + 0.4, DUR],
                            [0, 0, 1, 1, 0, 0]) + '</rect>')
        m.append(f'<text class="row" x="{tx+12}" y="{y}">{esc(k["rows"][i])}</text></g>')

    def packet(d, fr, on, go, arrive, dwell, end, off, tags):
        r = ['<g>', win(on, off, fade=0.2), move(d, fr, go, arrive, dwell, end)]
        r.append('<path class="pk" d="M-17 -11 l34 0 l0 22 l-34 0 z"/><path class="pkl" d="M-17 -11 l17 12 l17 -12"/>')
        for text, s0, s1, cls in tags:
            r.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                     f'<text class="tag halo {cls}" x="0" y="-38" text-anchor="middle">{esc(text)}</text></g>')
        r.append('</g>')
        return "".join(r)

    m.append(packet(P1_D, P1_F, T["a_on"], T["a_go"], T["a_nat"], T["a_dwell"], T["a_srv"], T["a_srv"] + 0.1, [
        ("src 10.0.1.10:50000", T["a_on"], T["a_nat"] + 0.3, "acc"),
        ("src 203.0.113.10:30001", T["a_nat"] + 0.6, T["a_srv"] - 0.1, "bl"),
    ]))
    m.append(packet(P2_D, P2_F, T["b_on"] + 0.2, T["b_go"], T["b_nat"], T["b_dwell"], T["b_srv"], T["b_srv"] + 0.1, [
        ("src 10.0.1.20:50000", T["b_on"] + 0.2, T["b_nat"] + 0.3, "acc"),
        ("src 203.0.113.10:30002", T["b_nat"] + 0.6, T["b_srv"] - 0.1, "bl"),
    ]))
    m.append(packet(P3_D, P3_F, T["r_on"] + 0.2, T["r_go"], T["r_nat"], T["r_dwell"], T["r_end"], T["hold"], [
        ("dst 203.0.113.10:30002", T["r_on"] + 0.2, T["r_nat"] + 0.3, "acc"),
        ("dst 10.0.1.20:50000", T["r_nat"] + 0.6, T["hold"], "bl"),
    ]))
    # captions
    cy0 = 384
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
    st = ['<g class="static">']
    for i, txt in enumerate(k["rows"]):
        st.append(f'<text class="row" x="{tx+12}" y="{row_y[i]}">{esc(txt)}</text>')
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    for (x, y, label) in ((214, 80, "①"), (rx - 74, ry - 22, "②"), (186, 236, "③"),
                          (640, 196, "④"), (300, 222, "⑤")):
        st.append(f'<text class="tag acc" x="{x}" y="{y}" font-size="16">{label}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    return "\n".join(o)


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-basics-06-network-fundamentals-part5-anim-1.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets", f"{lang}-basics-06-network-fundamentals-part5-anim-1.svg")
        svg = build(lang)
        assert "\u2014" not in svg, "em dash in output"
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [round(x, 3) for x in P1_F], [round(x, 3) for x in P3_F])
