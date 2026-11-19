#!/usr/bin/env python3
"""Line-art animated SVG of inter-VLAN routing (router-on-a-stick).

Self-contained SVG: SMIL drives motion so every element shares one clock;
CSS only handles palette (light/dark) and the reduced-motion static view.
"""
import math
import sys

DUR = 14.0  # seconds per loop

# ---------- geometry ----------------------------------------------------------
PC_A = (130, 262)
SW = (480, 292)
RT = (480, 104)
PC_B = (830, 262)

# Cable centre lines (hand-drawn: gentle curves, never ruler straight).
ACCESS_A = [(186, 262), (262, 236), (360, 300), (418, 292)]
TRUNK = [(480, 262), (468, 214), (494, 176), (480, 136)]
ACCESS_B = [(542, 292), (606, 300), (704, 236), (774, 262)]


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


# Motion path: A-cable, hop into switch, trunk up, trunk down, hop out, B-cable.
segments = [
    ("bez", ACCESS_A),
    ("line", [ACCESS_A[-1], (SW[0], SW[1] - 30)]),
    ("line", [(SW[0], SW[1] - 30), TRUNK[0]]),
    ("bez", TRUNK),
    ("bez", rev(TRUNK)),
    ("line", [TRUNK[0], (SW[0] + 10, SW[1] - 30)]),
    ("line", [(SW[0] + 10, SW[1] - 30), ACCESS_B[0]]),
    ("bez", ACCESS_B),
]
d_parts, lengths = [], []
for kind, pts in segments:
    if kind == "bez":
        (x1, y1), (x2, y2), (x3, y3) = pts[1:]
        d_parts.append(f"C{x1} {y1} {x2} {y2} {x3} {y3}")
        lengths.append(blen(pts))
    else:
        d_parts.append(f"L{pts[1][0]} {pts[1][1]}")
        lengths.append(math.dist(*pts))
motion_d = f"M{ACCESS_A[0][0]} {ACCESS_A[0][1]} " + " ".join(d_parts)
total = sum(lengths)
cum = [0.0]
for L in lengths:
    cum.append(cum[-1] + L)
frac = [x / total for x in cum]
at_switch_in = frac[2]   # after A-cable + hop (switch top)
at_router = frac[4]      # end of trunk up
at_switch_out = frac[5]  # end of trunk down
at_end = 1.0

# Timeline (seconds): travel, dwell, travel ...
T = {
    "appear": 0.4,
    "a_go": 0.8, "a_sw": 3.0,      # PC-A -> switch
    "sw_dwell": 4.2,               # MAC learning + tag
    "up_end": 5.6,                 # trunk up
    "rt_dwell": 7.6,               # routing decision
    "down_end": 9.0,               # trunk down
    "b_end": 11.2,                 # switch -> PC-B
    "hold": 12.8,
}
kt = lambda s: f"{s / DUR:.4f}"
motion_times = [0, T["a_go"], T["a_sw"], T["sw_dwell"], T["up_end"], T["rt_dwell"],
                T["down_end"], T["b_end"], DUR]
motion_points = [0, 0, at_switch_in, at_switch_in, at_router, at_router,
                 at_switch_out, at_end, at_end]


def win(start, end, fade=0.25, after=None):
    """opacity keyframes: hidden -> visible [start,end] -> `after` (or hidden)."""
    a = after if after is not None else 0
    pts = [(0, 0), (max(start - fade, 0.001), 0), (start, 1), (end, 1),
           (min(end + fade, DUR - 0.002), a), (DUR, a if after else 0)]
    # ensure strictly non-decreasing times
    times = ";".join(kt(t) for t, _ in pts)
    vals = ";".join(str(v) for _, v in pts)
    return (f'<animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{times}" values="{vals}"/>')


# ---------- copy --------------------------------------------------------------
COPY = {
    "ko": {
        "title": "VLAN 간 라우팅: 프레임 하나가 스위치와 라우터를 지나는 길",
        "desc": ("VLAN 10의 PC-A가 VLAN 20의 PC-B로 IP 패킷을 보낸다. PC-A는 목적지가 다른 서브넷이므로 "
                 "게이트웨이 MAC으로 프레임을 만든다. 스위치는 출발 MAC을 포트에 학습하고 트렁크로 내보내며 "
                 "802.1Q 태그 VLAN 10을 붙인다. 라우터는 라우팅 테이블로 10.0.20.0/24 하위 인터페이스를 고르고 "
                 "TTL을 64에서 63으로 줄인 뒤 L2 헤더를 새로 쓴다. 프레임은 VLAN 20 태그로 트렁크를 내려오고, "
                 "스위치는 태그를 떼어 VLAN 20 액세스 포트의 PC-B에 전달한다."),
        "pcA": ["PC-A", "VLAN 10 · 10.0.10.5"],
        "pcB": ["PC-B", "VLAN 20 · 10.0.20.7"],
        "sw": "L2 액세스 스위치",
        "rt": "라우터 (하위 인터페이스 .10 / .20)",
        "trunk": "802.1Q 트렁크",
        "acc10": "액세스 포트 · VLAN 10",
        "acc20": "액세스 포트 · VLAN 20",
        "mac": ["MAC 테이블", "PC-A MAC → 포트 1 · VLAN 10"],
        "rib": ["라우팅 테이블", "10.0.20.0/24 → .20 인터페이스"],
        "steps": [
            "① PC-A: 목적지가 다른 서브넷 → 게이트웨이 10.0.10.1의 MAC으로 프레임을 만든다",
            "② 스위치: 출발 MAC을 포트 1에 학습하고, 트렁크로 내보내며 802.1Q 태그 VLAN 10을 붙인다",
            "③ 라우터: 경로를 찾아 .20 인터페이스 선택 · TTL 64→63 · L2 헤더를 새로 쓴다 (IP 주소는 그대로)",
            "④ 트렁크: 같은 케이블을 이번엔 VLAN 20 태그로 내려온다",
            "⑤ 스위치: 태그를 떼고 VLAN 20 액세스 포트로 전달 → PC-B 수신",
        ],
        "hint": "패킷 위 꼬리표: 지금 바뀐 헤더 값",
    },
    "en": {
        "title": "Inter-VLAN routing: one frame's path through a switch and a router",
        "desc": ("PC-A in VLAN 10 sends an IP packet to PC-B in VLAN 20. Because the destination is on another subnet, "
                 "PC-A addresses the frame to the gateway MAC. The switch learns the source MAC on its port and sends the "
                 "frame up the trunk with an 802.1Q VLAN 10 tag. The router looks up 10.0.20.0/24, picks the .20 "
                 "subinterface, decrements TTL from 64 to 63 and rewrites the L2 header. The frame comes back down the "
                 "trunk tagged VLAN 20, and the switch strips the tag and delivers it on PC-B's VLAN 20 access port."),
        "pcA": ["PC-A", "VLAN 10 · 10.0.10.5"],
        "pcB": ["PC-B", "VLAN 20 · 10.0.20.7"],
        "sw": "L2 access switch",
        "rt": "Router (subinterfaces .10 / .20)",
        "trunk": "802.1Q trunk",
        "acc10": "access port · VLAN 10",
        "acc20": "access port · VLAN 20",
        "mac": ["MAC table", "PC-A MAC → port 1 · VLAN 10"],
        "rib": ["Routing table", "10.0.20.0/24 → .20 subinterface"],
        "steps": [
            "① PC-A: destination is on another subnet → frame addressed to gateway 10.0.10.1's MAC",
            "② Switch: learns the source MAC on port 1, sends it up the trunk with 802.1Q tag VLAN 10",
            "③ Router: route lookup picks the .20 subinterface · TTL 64→63 · new L2 header (IP addresses unchanged)",
            "④ Trunk: back down the same cable, now tagged VLAN 20",
            "⑤ Switch: strips the tag, forwards out the VLAN 20 access port → PC-B receives it",
        ],
        "hint": "Tag on the packet: the header field that just changed",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(lang):
    k = COPY[lang]
    W, H = 960, 500
    steps_t = [(T["a_go"], T["a_sw"]), (T["a_sw"], T["sw_dwell"] + 0.6),
               (T["sw_dwell"] + 0.6, T["rt_dwell"]), (T["rt_dwell"], T["down_end"]),
               (T["down_end"], T["b_end"] + 0.4)]
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
    for path, cls in ((ACCESS_A, "cable"), (ACCESS_B, "cable")):
        for dy in (-2.5, 2.5):
            g.append(f'<path class="{cls}" d="{c([(x, y + dy) for x, y in path])}"/>')
    for dx in (-3, 3):
        g.append(f'<path class="trunk" d="{c([(x + dx, y) for x, y in TRUNK])}"/>')
    # laptops
    for (x, y) in (PC_A, PC_B):
        g.append(f'<path class="ink" d="M{x-44} {y-40} q2 -3 6 -3 l76 1 q5 0 5 5 l-1 50 l-88 1 z"/>')
        g.append(f'<path class="thin" d="M{x-36} {y-31} l70 1 l-1 34 l-69 0 z"/>')
        g.append(f'<path class="ink" d="M{x-54} {y+13} l108 0 q4 0 2 4 l-6 7 l-100 0 l-6 -7 q-2 -4 2 -4"/>')
    # switch
    sx, sy = SW
    g.append(f'<path class="ink" d="M{sx-62} {sy-26} q0 -4 5 -4 l114 1 q6 0 6 5 l0 44 q0 5 -6 5 l-114 -1 q-5 0 -5 -5 z"/>')
    for i in range(8):
        px = sx - 48 + i * 13
        g.append(f'<path class="thin" d="M{px} {sy+4} l8 0 l0 7 l-8 0 z"/>')
    g.append(f'<circle class="fillink" cx="{sx+40}" cy="{sy-12}" r="2.2"/><circle class="fillink" cx="{sx+48}" cy="{sy-12}" r="2.2"/>')
    # router (puck with arrows)
    rx, ry = RT
    g.append(f'<path class="ink" d="M{rx-52} {ry-14} q0 -16 52 -16 q52 0 52 16 l0 22 q0 16 -52 16 q-52 0 -52 -16 z"/>')
    g.append(f'<path class="thin" d="M{rx-52} {ry-14} q0 16 52 16 q52 0 52 -16"/>')
    for (x1, y1, x2, y2) in ((rx-22, ry-20, rx-6, ry-12), (rx+22, ry-8, rx+6, ry-16),
                             (rx-6, ry-20, rx-22, ry-12), (rx+6, ry-8, rx+22, ry-16)):
        g.append(f'<path class="thin" d="M{x1} {y1} L{x2} {y2}"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    for (x, y), (n, sub) in ((PC_A, k["pcA"]), (PC_B, k["pcB"])):
        o.append(f'<text class="t" x="{x}" y="{y+48}" text-anchor="middle" font-weight="600">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+66}" text-anchor="middle">{esc(sub)}</text>')
    o.append(f'<text class="t" x="{sx}" y="{sy+50}" text-anchor="middle" font-weight="600">{esc(k["sw"])}</text>')
    o.append(f'<text class="t" x="{rx+66}" y="{ry+4}" font-weight="600">{esc(k["rt"])}</text>')
    o.append(f'<text class="s bl" x="{TRUNK[1][0]-14}" y="{TRUNK[1][1]+6}" text-anchor="end">{esc(k["trunk"])}</text>')
    o.append(f'<text class="s" x="{ACCESS_A[1][0]+14}" y="{ACCESS_A[1][1]-6}">{esc(k["acc10"])}</text>')
    o.append(f'<text class="s" x="{ACCESS_B[2][0]-20}" y="{ACCESS_B[2][1]-8}" text-anchor="end">{esc(k["acc20"])}</text>')

    def note(x, y, lines, start, end, cls):
        r = [f'<g opacity="0">{win(start, end, after=0.0)}']
        w = 250
        r.append(f'<path class="thin" filter="url(#pen)" d="M{x} {y} l{w} 0 l0 42 l-{w} 0 z"/>')
        r.append(f'<text class="s {cls}" x="{x+10}" y="{y+17}" font-weight="700">{esc(lines[0])}</text>')
        r.append(f'<text class="t" x="{x+10}" y="{y+35}" font-size="13.5">{esc(lines[1])}</text></g>')
        return "".join(r)

    # --- motion layer ---
    m = ['<g class="motion">']
    m.append(note(sx + 76, sy - 150, k["mac"], T["a_sw"], T["sw_dwell"] + 1.2, "acc"))
    m.append(note(rx - 330, ry + 46, k["rib"], T["up_end"], T["rt_dwell"] + 0.4, "acc"))
    # packet (envelope) with header tags
    kp = ";".join(f"{p:.4f}" for p in motion_points)
    ktm = ";".join(kt(t) for t in motion_times)
    m.append('<g>')
    m.append(win(T["appear"], T["hold"]))
    m.append(f'<animateMotion dur="{DUR}s" repeatCount="indefinite" calcMode="linear" '
             f'keyPoints="{kp}" keyTimes="{ktm}" path="{motion_d}"/>')
    m.append('<path class="pk" d="M-17 -11 l34 0 l0 22 l-34 0 z"/><path class="pkl" d="M-17 -11 l17 12 l17 -12"/>')
    tags = [
        ("dst MAC=GW · TTL 64", T["appear"], T["a_sw"], "acc"),
        ("VLAN 10 · TTL 64", T["a_sw"] + 0.3, T["up_end"] + 0.3, "bl"),
        ("TTL 63 · dst MAC=PC-B", T["up_end"] + 0.8, T["rt_dwell"], "acc"),
        ("VLAN 20 · TTL 63", T["rt_dwell"], T["down_end"], "bl"),
        ("untagged · TTL 63", T["down_end"] + 0.2, T["hold"], "acc"),
    ]
    for text, s0, s1, cls in tags:
        m.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                 f'<text class="tag {cls}" x="22" y="-14">{esc(text)}</text></g>')
    m.append('</g>')
    # captions
    cy0 = 384
    for i, (txt, (s0, s1)) in enumerate(zip(k["steps"], steps_t)):
        y = cy0 + i * 22
        m.append(f'<g opacity="0">'
                 f'<animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" '
                 f'keyTimes="0;{kt(max(s0-0.2,0.001))};{kt(s0)};{kt(s1)};{kt(s1+0.3)};{kt(T["hold"])};{kt(T["hold"]+0.4)};1" '
                 f'values="0;0;1;1;0.42;0.42;0;0"/>'
                 f'<text class="cap" x="40" y="{y}">{esc(txt)}</text></g>')
    m.append(f'<text class="s" x="{W-32}" y="{H-14}" text-anchor="end">{esc(k["hint"])}</text>')
    m.append('</g>')
    o.extend(m)

    # --- static (reduced motion) layer ---
    st = ['<g class="static">']
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    for (x, y, label) in ((ACCESS_A[1][0] + 30, 262, "①"), (sx - 26, sy - 46, "②"),
                          (rx - 70, ry + 4, "③"), (sx + 24, sy - 70, "④"), (ACCESS_B[2][0] + 6, 276, "⑤")):
        st.append(f'<text class="tag acc" x="{x}" y="{y}" font-size="16">{label}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-basics-06-network-fundamentals-part5-anim-0.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets", f"{lang}-basics-06-network-fundamentals-part5-anim-0.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build(lang))
    print("ok", round(total, 1), [round(x, 3) for x in frac])
