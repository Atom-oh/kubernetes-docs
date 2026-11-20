#!/usr/bin/env python3
"""Line-art animated SVG of the edge-to-origin path with a private origin.

Copies the approved prototype (gen_basics_06_part5_anim0.py): same palette
tokens, pen filter, stroke classes, font stack, caption layout, packet-tag
style and ko/en COPY structure. Reuses the motion()/packet()/anim() helpers
and the keyTimes self-check from gen_networking_expert_07_..._anim0.py.
SMIL drives motion on one shared clock; CSS only handles palette
(light/dark) and the reduced-motion static view.

Story (house reference design): a viewer's cacheable GET misses at the edge
POP and the regional edge cache. CloudFront reaches the origin through a VPC
origin: a service-managed ENI in a private subnet connects to an internal ALB
whose security group admits only CloudFront-VPCOrigins-Service-SG (or the
CloudFront origin-facing managed prefix list); the ALB forwards to its target
group. Then an internet client aims straight at the ALB and fails: an internal
ALB has private addresses only, so nothing on the internet routes to it.
No internet-facing load balancer and no public-CIDR ingress appear anywhere.

Addresses are RFC 1918 examples (10.0.11.0/24 and 10.0.12.0/24 private subnets).
"""
import math
import sys

DUR = 14.0  # seconds per loop

# ---------- geometry ----------------------------------------------------------
VIEWER = (90, 160)
ATTACK = (90, 318)
POP = (270, 160)
REC = (440, 160)
ENI = (620, 160)
ALB = (760, 160)
TG = (888, 160)
VPC_BOX = (556, 76, 388, 270)   # x, y, w, h: VPC boundary (dashed)
SUB_BOX = (574, 104, 352, 150)  # private subnets

# Cable centre lines (hand-drawn: gentle curves, never ruler straight).
V_POP = [(146, 156), (184, 138), (210, 178), (240, 160)]
POP_REC = [(300, 160), (340, 140), (372, 180), (402, 160)]
REC_ENI = [(478, 160), (520, 140), (568, 180), (602, 160)]
ENI_ALB = [(638, 160), (672, 142), (700, 178), (726, 160)]
ALB_TG = [(794, 160), (820, 146), (846, 174), (870, 160)]
ATTACK_PATH = [(138, 282), (270, 258), (420, 306), (552, 290)]  # ends at the VPC edge

SG_RING = (ALB[0], ALB[1], 40, 34)  # cx, cy, rx, ry: ALB security group


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


# Packet 1 (viewer request): dwell at the centre of each box on the way in.
P1_D, P1_F = motion([
    ("bez", V_POP), ("line", [V_POP[-1], POP]), ("line", [POP, POP_REC[0]]),        # 1, 2, 3
    ("bez", POP_REC), ("line", [POP_REC[-1], REC]), ("line", [REC, REC_ENI[0]]),    # 4, 5, 6
    ("bez", REC_ENI), ("line", [REC_ENI[-1], ENI]), ("line", [ENI, ENI_ALB[0]]),    # 7, 8, 9
    ("bez", ENI_ALB), ("line", [ENI_ALB[-1], ALB]), ("line", [ALB, ALB_TG[0]]),     # 10, 11, 12
    ("bez", ALB_TG), ("line", [ALB_TG[-1], TG]),                                    # 13, 14
])
# Packet 2 (internet client straight at the ALB): stops at the VPC boundary.
P2_D, P2_F = motion([("bez", ATTACK_PATH)])

# Timeline (seconds): travel, dwell, travel ...
T = {
    "p1_on": 0.3, "p1_go": 0.8, "p1_pop": 1.7, "p1_pop_go": 2.3, "p1_rec": 3.1, "p1_rec_go": 3.6,
    "p1_eni": 4.5, "p1_eni_go": 5.2, "p1_alb": 6.0, "p1_alb_go": 6.9, "p1_tg": 7.7, "p1_off": 8.2,
    "p2_on": 8.5, "p2_go": 8.8, "p2_wall": 10.3, "p2_off": 10.8,
    "hold": 12.8,
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
        "title": "엣지에서 오리진까지: VPC 오리진과 internal ALB",
        "desc": ("뷰어가 HTTPS로 GET /menu.json을 보낸다. 캐시할 수 있는 GET이지만 엣지 POP과 리전 엣지 캐시에서 모두 "
                 "MISS이므로 CloudFront가 오리진에 요청한다. 오리진 연결은 VPC 오리진을 거친다. CloudFront가 프라이빗 "
                 "서브넷에 만든 서비스 관리형 ENI(예: 10.0.11.25)가 internal ALB(10.0.12.40)에 연결한다. ALB 보안 그룹은 "
                 "CloudFront-VPCOrigins-Service-SG(또는 CloudFront origin-facing 관리형 prefix list)에서 오는 트래픽만 "
                 "허용하고, ALB 리스너가 대상 그룹으로 전달한다. 이어서 인터넷 클라이언트가 ALB에 직접 접속하려 한다. "
                 "internal ALB의 노드는 프라이빗 주소만 가지므로 인터넷에서 그 주소로 가는 경로가 없고 연결은 VPC 경계에서 "
                 "실패한다. 이 그림에는 인터넷용 로드 밸런서도, 공개 CIDR을 허용하는 인바운드 규칙도 없다."),
        "viewer": ["뷰어", "HTTPS"],
        "attack": ["인터넷 클라이언트", "ALB 직접 접속 시도"],
        "pop": ["엣지 POP", "TLS 종료"],
        "rec": ["리전 엣지 캐시", ""],
        "eni": ["VPC 오리진 ENI", "10.0.11.25"],
        "alb": ["internal ALB", "10.0.12.40"],
        "tg": ["대상 그룹", ""],
        "vpc": "VPC: 프라이빗 서브넷만 사용",
        "igw": "인터넷 게이트웨이는 연결만 필요, 이 경로의 라우팅에는 쓰이지 않음",
        "sg": "SG 인바운드: CloudFront-VPCOrigins-Service-SG만",
        "wall": ["× 경로 없음", "internal ALB = 프라이빗 주소만"],
        "steps": [
            "① 뷰어 → 엣지 POP (HTTPS): 캐시할 수 있는 GET이 POP과 리전 엣지 캐시에서 모두 MISS",
            "② CloudFront가 VPC 오리진으로 연결: 프라이빗 서브넷의 서비스 관리형 ENI가 출발지",
            "③ ALB 보안 그룹은 VPC 오리진 SG(또는 origin-facing prefix list)에서 온 트래픽만 허용",
            "④ ALB 리스너 → 대상 그룹: 대상은 ALB 보안 그룹에서 온 트래픽만 받도록 설계",
            "⑤ 인터넷에서 ALB로 직접 접속: internal ALB는 프라이빗 주소만 있어 인터넷 경로가 없다",
        ],
        "hint": "패킷 위 꼬리표: 지금 바뀐 헤더 값",
    },
    "en": {
        "title": "Edge to origin: a VPC origin and an internal ALB",
        "desc": ("A viewer sends GET /menu.json over HTTPS. It is a cacheable GET, but it misses at both the edge POP and "
                 "the regional edge cache, so CloudFront requests it from the origin. The origin connection goes through a "
                 "VPC origin: a service-managed ENI that CloudFront created in a private subnet (for example 10.0.11.25) "
                 "connects to an internal ALB (10.0.12.40). The ALB security group admits only traffic from "
                 "CloudFront-VPCOrigins-Service-SG (or the CloudFront origin-facing managed prefix list), and the ALB "
                 "listener forwards to the target group. Then an internet client tries to reach the ALB directly. The "
                 "nodes of an internal ALB have private addresses only, so nothing on the internet routes to them and the "
                 "attempt fails at the VPC boundary. There is no internet-facing load balancer and no inbound rule that "
                 "admits a public CIDR."),
        "viewer": ["Viewer", "HTTPS"],
        "attack": ["Internet client", "tries the ALB directly"],
        "pop": ["Edge POP", "TLS ends here"],
        "rec": ["Regional edge cache", ""],
        "eni": ["VPC origin ENI", "10.0.11.25"],
        "alb": ["Internal ALB", "10.0.12.40"],
        "tg": ["Target group", ""],
        "vpc": "VPC: private subnets only",
        "igw": "internet gateway attached, not used to route this path",
        "sg": "SG inbound: CloudFront-VPCOrigins-Service-SG only",
        "wall": ["× no route", "internal ALB = private IPs only"],
        "steps": [
            "① Viewer → edge POP over HTTPS: a cacheable GET that misses at the POP and the regional edge cache",
            "② CloudFront connects through the VPC origin: a service-managed ENI in a private subnet is the source",
            "③ The ALB security group admits only the VPC origin SG (or the origin-facing prefix list)",
            "④ ALB listener → target group; targets are designed to accept traffic only from the ALB security group",
            "⑤ An internet client aims at the ALB: an internal ALB has private addresses only, so no internet path exists",
        ],
        "hint": "Tag on the packet: the header field that just changed",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def laptop(g, x, y):
    """Laptop symbol, as in the prototype."""
    g.append(f'<path class="ink" d="M{x-44} {y-40} q2 -3 6 -3 l76 1 q5 0 5 5 l-1 50 l-88 1 z"/>')
    g.append(f'<path class="thin" d="M{x-36} {y-31} l70 1 l-1 34 l-69 0 z"/>')
    g.append(f'<path class="ink" d="M{x-54} {y+13} l108 0 q4 0 2 4 l-6 7 l-100 0 l-6 -7 q-2 -4 2 -4"/>')


def cage(g, x, y, w=30):
    """Cache site: a cage with shelves of disks."""
    g.append(f'<path class="ink" d="M{x-w} {y-36} q0 -4 4 -4 l{2*w-8} 1 q5 0 5 5 l-1 68 q0 4 -4 4 l-{2*w-8} -1 q-4 0 -4 -4 z"/>')
    for i in range(4):
        yy = y - 26 + i * 15
        g.append(f'<path class="thin" d="M{x-14} {yy} l28 1 l0 8 l-28 0 z"/>')
    g.append(f'<circle class="fillink" cx="{x+8}" cy="{y-22}" r="1.8"/>')


def wall_mark():
    """Failure at the VPC boundary: vermilion X where the attack path ends."""
    x, y = ATTACK_PATH[-1]
    return (f'<path class="pkl" stroke-width="3" d="M{x-10} {y-10} L{x+10} {y+10} M{x+10} {y-10} L{x-10} {y+10}"/>')


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    W, H = 960, 500
    steps_t = [(T["p1_on"], T["p1_rec_go"]), (T["p1_rec_go"], T["p1_eni_go"] + 0.3),
               (T["p1_alb"], T["p1_alb_go"]), (T["p1_alb_go"], T["p1_off"]),
               (T["p2_on"], T["p2_off"] + 1.4)]
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
    vx, vy, vw, vh = VPC_BOX
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="M{vx} {vy+6} q0 -6 6 -6 l{vw-12} 1 q6 0 6 6 l-1 {vh-12} q0 6 -6 6 l-{vw-12} -1 q-6 0 -6 -6 z"/>')
    sx, sy, sw, sh = SUB_BOX
    g.append(f'<path class="thin" stroke-dasharray="1 5" d="M{sx} {sy} l{sw} 1 l-1 {sh} l-{sw-1} -1 z"/>')
    for path in (V_POP, POP_REC, REC_ENI, ENI_ALB, ALB_TG):
        for dy in (-2.5, 2.5):
            g.append(f'<path class="cable" d="{c([(x, y + dy) for x, y in path])}"/>')
    # attack path: one dashed pen line that stops at the VPC boundary
    g.append(f'<path class="cable" stroke-dasharray="6 7" d="{c(ATTACK_PATH)}"/>')
    laptop(g, *VIEWER)
    laptop(g, *ATTACK)
    cage(g, *POP)
    cage(g, *REC, w=34)
    # VPC origin ENI: a small card with a port
    x, y = ENI
    g.append(f'<path class="ink" d="M{x-18} {y-14} l36 1 l-1 28 l-35 -1 z"/>')
    g.append(f'<path class="thin" d="M{x-8} {y-4} l16 0 l0 8 l-16 0 z"/>')
    # internal ALB: box fanning out, inside a dashed security-group ring
    x, y = ALB
    g.append(f'<path class="ink" d="M{x-22} {y-16} q0 -4 4 -4 l26 0 q4 0 4 4 l0 32 q0 4 -4 4 l-26 0 q-4 0 -4 -4 z"/>')
    g.append(f'<path class="thin" d="M{x-12} {y} l16 -9 M{x-12} {y} l16 0 M{x-12} {y} l16 9"/>')
    cx, cy, rx, ry = SG_RING
    g.append(f'<ellipse class="trunk" stroke-dasharray="4 5" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>')
    # target group: three instances
    x, y = TG
    for dy in (-30, 0, 30):
        g.append(f'<path class="ink" d="M{x-14} {y+dy-11} l28 1 l-1 21 l-27 -1 z"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    for (x, y), (n, sub) in ((VIEWER, k["viewer"]),):
        o.append(f'<text class="t" x="{x}" y="{y+48}" text-anchor="middle" font-weight="600">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+66}" text-anchor="middle">{esc(sub)}</text>')
    x, y = ATTACK
    o.append(f'<text class="t" x="{x+66}" y="{y+8}" font-weight="600">{esc(k["attack"][0])}</text>')
    o.append(f'<text class="s" x="{x+66}" y="{y+26}">{esc(k["attack"][1])}</text>')
    for (x, y), (n, sub), dy in ((POP, k["pop"], 58), (REC, k["rec"], 58), (ENI, k["eni"], 40),
                                 (ALB, k["alb"], 54), (TG, k["tg"], 64)):
        o.append(f'<text class="t" x="{x}" y="{y+dy}" text-anchor="middle" font-weight="600" font-size="14">{esc(n)}</text>')
        if sub:
            o.append(f'<text class="s" x="{x}" y="{y+dy+17}" text-anchor="middle">{esc(sub)}</text>')
    o.append(f'<text class="s" x="{vx+14}" y="{vy+vh-14}" font-weight="700">{esc(k["vpc"])}</text>')
    o.append(f'<text class="s" x="{vx+vw-8}" y="{vy+vh+16}" text-anchor="end">{esc(k["igw"])}</text>')
    o.append(f'<text class="s bl" x="{sx+sw-8}" y="{sy+sh-10}" text-anchor="end">{esc(k["sg"])}</text>')

    wx, wy = ATTACK_PATH[-1]

    def wall_note():
        return (f'<text class="tag acc" x="{wx-16}" y="{wy-26}" text-anchor="end">{esc(k["wall"][0])}</text>'
                f'<text class="s" x="{wx-16}" y="{wy-10}" text-anchor="end">{esc(k["wall"][1])}</text>')

    # --- motion layer ---
    m = ['<g class="motion">']
    # the security group ring lights up while it admits the request
    m.append(f'<g opacity="0">{win(T["p1_alb"], T["p1_alb_go"], fade=0.2)}'
             f'<ellipse class="trunk" stroke-width="3" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/></g>')
    m.append(f'<g opacity="0">{win(T["p2_wall"], T["hold"], fade=0.15)}{wall_mark()}{wall_note()}</g>')

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

    f = P1_F
    m.append(packet(P1_D, [
        (0, 0), (T["p1_go"], 0), (T["p1_pop"], f[2]), (T["p1_pop_go"], f[2]),
        (T["p1_rec"], f[5]), (T["p1_rec_go"], f[5]), (T["p1_eni"], f[8]), (T["p1_eni_go"], f[8]),
        (T["p1_alb"], f[11]), (T["p1_alb_go"], f[11]), (T["p1_tg"], 1), (DUR, 1)],
        T["p1_on"], T["p1_off"], [
        ("HTTPS · GET /menu.json", T["p1_on"], T["p1_pop"] - 0.1, "acc", 0, -24, "middle"),
        ("TLS ends · MISS", T["p1_pop"] + 0.1, T["p1_rec"] - 0.1, "bl", 0, -54, "middle"),
        ("regional cache: MISS", T["p1_rec"] + 0.1, T["p1_eni"] - 0.1, "bl", 0, -54, "middle"),
        ("src 10.0.11.25 (ENI)\ndst 10.0.12.40", T["p1_eni"] + 0.1, T["p1_alb"] - 0.1, "acc", 0, -50, "middle"),
        ("SG: src = VPC origin SG ✓", T["p1_alb"] + 0.1, T["p1_tg"] - 0.1, "bl", 0, -46, "middle"),
        ("→ target", T["p1_tg"], T["p1_off"], "acc", -20, -46, "end"),
    ]))
    m.append(packet(P2_D, [(0, 0), (T["p2_go"], 0), (T["p2_wall"], 1), (DUR, 1)],
                    T["p2_on"], T["p2_off"], [
        ("dst 10.0.12.40 (private)", T["p2_on"], T["p2_off"], "acc", 0, -20, "middle"),
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
    st = ['<g class="static">', wall_mark(), wall_note()]
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    for (x, y, label) in ((VIEWER[0] - 8, 108, "①"), (ENI[0] - 8, 136, "②"), (ALB[0] - 48, 124, "③"),
                          (TG[0] - 36, 116, "④"), (196, 262, "⑤")):
        st.append(f'<text class="tag acc" x="{x}" y="{y}" font-size="16">{label}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    return "\n".join(o)


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-networking-expert-08-cdn-edge-delivery-anim-1.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-networking-expert-08-cdn-edge-delivery-anim-1.svg")
        svg = build(lang)
        assert "\u2014" not in svg, "em dash in output"
        assert "0.0.0.0" not in svg, "public CIDR must not appear"
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [round(x, 3) for x in P1_F], [round(x, 3) for x in P2_F])
