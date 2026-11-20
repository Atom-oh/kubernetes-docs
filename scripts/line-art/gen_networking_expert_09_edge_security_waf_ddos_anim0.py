#!/usr/bin/env python3
"""Line-art animated SVG of edge security: Shield absorbs, WAF filters, origin stays private.

Copies the approved prototype (gen_basics_06_part5_anim0.py): same palette
tokens, pen filter, stroke classes, font stack, caption layout, packet-tag
style and ko/en COPY structure. Reuses the motion()/packet()/anim() helpers,
the keyTimes self-check and the VPC origin / internal ALB / security-group
ring drawing from gen_networking_expert_08_cdn_edge_delivery_anim1.py so the
two chapters look continuous. SMIL drives motion on one shared clock; CSS only
handles palette (light/dark) and the reduced-motion static view.

Story (house reference design, attack-side view):
1. A botnet sends an L3/L4 flood (UDP reflection, SYN flood) at the CloudFront
   edge. Shield mitigations at the edge pass only traffic that is valid for web
   applications, so the flood is absorbed there and does not reach the origin.
2. A bot sends a well-formed HTTPS flood on /login. It passes the L3/L4 layer,
   and a rate-based rule in the WAF web ACL blocks it (Block -> 403).
3. A legitimate GET passes Shield, no WAF rule terminates it, so the web ACL
   default action (Allow) applies. CloudFront reaches the origin through a VPC
   origin ENI in a private subnet; the internal ALB (created from an Ingress
   with scheme internal) admits only CloudFront-VPCOrigins-Service-SG; the ALB
   forwards to a Pod IP target, whose NetworkPolicy admits only the ALB subnet.
No internet-facing load balancer and no public-CIDR ingress appear anywhere.

Addresses are RFC 1918 examples (10.0.11.0/24 ENI, 10.0.12.0/24 ALB,
10.0.13.0/24 Pods). The rule name "rate-login" is an example name.
"""
import math
import sys

DUR = 14.0  # seconds per loop

# ---------- geometry ----------------------------------------------------------
CLIENT = (80, 140)
BOTS = [(54, 252), (100, 270), (58, 298)]
SHIELD = (228, 140)          # legitimate lane crosses the shield here
SHIELD_C = (228, 184)        # shield label centre
WAF = (370, 140)
ENI = (548, 140)
ALB = (690, 140)
POD = (858, 140)
EDGE_BOX = (166, 66, 290, 278)  # x, y, w, h: CloudFront edge (dashed)
VPC_BOX = (470, 76, 474, 268)   # VPC boundary (dashed)
SUB_BOX = (486, 100, 446, 186)  # private subnets
WAF_BOX = (340, 98, 60, 84)     # web ACL box

# Cable centre lines (hand-drawn: gentle curves, never ruler straight).
C_SH = [(136, 138), (156, 122), (174, 156), (192, 140)]
SH_WAF = [(264, 140), (292, 124), (314, 156), (340, 140)]
WAF_ENI = [(400, 140), (444, 124), (492, 158), (530, 140)]
ENI_ALB = [(566, 140), (602, 124), (628, 158), (656, 140)]
ALB_POD = [(724, 140), (766, 124), (796, 158), (826, 140)]
L7_A = [(118, 266), (150, 270), (190, 262), (228, 258)]   # bot -> through shield
L7_B = [(228, 258), (276, 254), (330, 232), (360, 184)]   # shield -> WAF bottom
VOL = [(76, 298), (130, 304), (170, 290), (204, 276)]     # bot -> shield edge

SG_RING = (ALB[0], ALB[1], 40, 34)  # cx, cy, rx, ry: ALB security group
NP_RING = (POD[0], POD[1], 36, 32)  # Pod NetworkPolicy


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


# Legitimate request: dwell at the centre of each box on the way in.
G_D, G_F = motion([
    ("bez", C_SH), ("line", [C_SH[-1], SHIELD]), ("line", [SHIELD, SH_WAF[0]]),        # 1, 2, 3
    ("bez", SH_WAF), ("line", [SH_WAF[-1], WAF]), ("line", [WAF, WAF_ENI[0]]),         # 4, 5, 6
    ("bez", WAF_ENI), ("line", [WAF_ENI[-1], ENI]), ("line", [ENI, ENI_ALB[0]]),       # 7, 8, 9
    ("bez", ENI_ALB), ("line", [ENI_ALB[-1], ALB]), ("line", [ALB, ALB_POD[0]]),       # 10, 11, 12
    ("bez", ALB_POD), ("line", [ALB_POD[-1], POD]),                                    # 13, 14
])
# L7 flood request: through the shield, stops at the WAF.
L_D, L_F = motion([("bez", L7_A), ("bez", L7_B)])
# Volumetric flood: stops at the shield edge.
V_D, V_F = motion([("bez", VOL)])

# Timeline (seconds): travel, dwell, travel ...
T = {
    "v_on": 0.3, "v_go": 0.5, "v_travel": 1.1, "v_gap": 0.4,
    "l_on": 2.6, "l_go": 2.9, "l_sh": 3.9, "l_sh_go": 4.4, "l_waf": 5.3, "l_off": 6.3,
    "g_on": 6.5, "g_go": 6.7, "g_sh": 7.3, "g_sh_go": 7.7, "g_waf": 8.2, "g_waf_go": 8.9,
    "g_eni": 9.5, "g_eni_go": 9.9, "g_alb": 10.4, "g_alb_go": 10.9, "g_pod": 11.7, "g_off": 12.3,
    "hold": 12.8,
}
V_ARRIVE = [T["v_go"] + i * T["v_gap"] + T["v_travel"] for i in range(3)]
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
        "title": "엣지 보안: Shield가 흡수하고 WAF가 거르며 오리진은 비공개",
        "desc": ("봇넷이 CloudFront 엣지로 L3/L4 플러드(UDP 반사, SYN 플러드)를 보낸다. 엣지의 Shield 완화는 웹 "
                 "애플리케이션에 유효한 트래픽만 통과시키므로 플러드는 엣지에서 흡수되고 오리진에 닿지 않는다. 이어서 봇이 "
                 "/login에 정상 형식의 HTTPS 요청을 대량으로 보낸다. 이 요청은 L3/L4 계층을 통과하지만 WAF 웹 ACL의 속도 "
                 "기반 규칙(예: rate-login)에 걸려 Block되고 403을 받는다. 마지막으로 정상 사용자의 GET은 Shield를 지나고, "
                 "어떤 WAF 규칙도 평가를 끝내지 않으므로 웹 ACL 기본 작업(Allow)이 적용된다. CloudFront는 VPC 오리진을 거쳐 "
                 "오리진에 연결한다. 프라이빗 서브넷의 서비스 관리형 ENI(예: 10.0.11.25)가 internal ALB(10.0.12.40)에 "
                 "연결하고, ALB 보안 그룹은 CloudFront-VPCOrigins-Service-SG에서 온 트래픽만 허용한다. Ingress(scheme: "
                 "internal)로 만든 ALB가 Pod IP(10.0.13.31) 대상으로 전달하고, Pod의 NetworkPolicy는 ALB 서브넷에서 온 "
                 "트래픽만 허용하며 응답은 200이다. 이 그림에는 인터넷용 로드 밸런서도, 공개 CIDR을 허용하는 인바운드 "
                 "규칙도 없다."),
        "client": ["클라이언트", "HTTPS"],
        "botnet": "봇넷",
        "edge": "CloudFront 엣지 · DNS + Anycast",
        "shield": ["Shield", "Standard"],
        "waf": ["WAF 웹 ACL", "전역 · us-east-1"],
        "eni": ["VPC 오리진 ENI", "10.0.11.25"],
        "alb": ["internal ALB", "Ingress · scheme: internal"],
        "pod": ["Pod", "10.0.13.31"],
        "vpc": "VPC: 프라이빗 서브넷만 사용",
        "sg": "ALB SG 인바운드: CloudFront-VPCOrigins-Service-SG만",
        "np": "NetworkPolicy 인그레스: ipBlock 10.0.12.0/24(ALB 서브넷)만",
        "vol": ["UDP 반사 · SYN 플러드", "엣지에서 흡수됨"],
        "l7": ["GET /login · 5분에 2,400건", "정상 TCP/TLS: Shield 통과", "규칙 rate-login: Block\n→ 403 Forbidden"],
        "g": ["HTTPS · GET /menu.json", "정상 TCP/TLS ✓", "종료 규칙 없음 → 기본 작업 Allow",
              "src 10.0.11.25 (ENI)\ndst 10.0.12.40", "SG: src = VPC 오리진 SG ✓",
              "src 10.0.12.40 (ALB)\ndst 10.0.13.31", "NetworkPolicy ✓ · 200 OK"],
        "steps": [
            "① 봇넷의 L3/L4 플러드(UDP 반사, SYN 플러드): Shield가 엣지에서 흡수하고 오리진에는 닿지 않는다",
            "② /login L7 HTTP 플러드: 정상 형식이라 L3/L4를 지나지만 WAF 속도 기반 규칙이 403으로 Block한다",
            "③ 정상 GET: 평가를 끝내는 WAF 규칙이 없으므로 웹 ACL 기본 작업(Allow)으로 전달된다",
            "④ VPC 오리진 ENI → internal ALB: ALB SG는 VPC 오리진 SG(또는 origin-facing prefix list)만 허용",
            "⑤ ALB(Ingress, scheme: internal) → Pod IP: NetworkPolicy는 ALB 서브넷만 허용하고 200을 돌려준다",
        ],
        "hint": "패킷 위 꼬리표: 지금 바뀐 필드나 판정",
    },
    "en": {
        "title": "Edge security: Shield absorbs, WAF filters, the origin stays private",
        "desc": ("A botnet sends an L3/L4 flood (UDP reflection, SYN flood) at the CloudFront edge. Shield mitigations at "
                 "the edge pass only traffic that is valid for web applications, so the flood is absorbed there and does "
                 "not reach the origin. Next, a bot floods /login with well-formed HTTPS requests. They pass the L3/L4 "
                 "layer, but a rate-based rule in the WAF web ACL (example name rate-login) matches, and the request is "
                 "blocked with 403. Finally, a legitimate GET passes Shield; no WAF rule terminates its evaluation, so the "
                 "web ACL default action (Allow) applies. CloudFront reaches the origin through a VPC origin: a "
                 "service-managed ENI in a private subnet (for example 10.0.11.25) connects to an internal ALB "
                 "(10.0.12.40) whose security group admits only CloudFront-VPCOrigins-Service-SG. The ALB, created from "
                 "an Ingress with scheme internal, forwards to a Pod IP target (10.0.13.31); the Pod's NetworkPolicy "
                 "admits only the ALB subnet, and the response is 200. There is no internet-facing load balancer and no "
                 "inbound rule that admits a public CIDR."),
        "client": ["Client", "HTTPS"],
        "botnet": "Botnet",
        "edge": "CloudFront edge · DNS + anycast",
        "shield": ["Shield", "Standard"],
        "waf": ["WAF web ACL", "global · us-east-1"],
        "eni": ["VPC origin ENI", "10.0.11.25"],
        "alb": ["Internal ALB", "Ingress · scheme: internal"],
        "pod": ["Pod", "10.0.13.31"],
        "vpc": "VPC: private subnets only",
        "sg": "ALB SG inbound: CloudFront-VPCOrigins-Service-SG only",
        "np": "NetworkPolicy ingress: ipBlock 10.0.12.0/24 (ALB subnet) only",
        "vol": ["UDP reflection · SYN flood", "absorbed at the edge"],
        "l7": ["GET /login · 2,400 in 5 min", "valid TCP/TLS: passes Shield", "rule rate-login: Block\n→ 403 Forbidden"],
        "g": ["HTTPS · GET /menu.json", "valid TCP/TLS ✓", "no terminating rule → default Allow",
              "src 10.0.11.25 (ENI)\ndst 10.0.12.40", "SG: src = VPC origin SG ✓",
              "src 10.0.12.40 (ALB)\ndst 10.0.13.31", "NetworkPolicy ✓ · 200 OK"],
        "steps": [
            "① Botnet L3/L4 flood (UDP reflection, SYN flood): Shield absorbs it at the edge; it never reaches the origin",
            "② L7 HTTP flood on /login: well-formed, so it passes L3/L4, but a WAF rate-based rule blocks it with 403",
            "③ Legitimate GET: no WAF rule terminates it, so the web ACL default action (Allow) forwards it",
            "④ VPC origin ENI → internal ALB: the ALB SG admits only the VPC origin SG (or the origin-facing prefix list)",
            "⑤ ALB (Ingress, scheme: internal) → Pod IP: NetworkPolicy admits only the ALB subnet, and the Pod returns 200",
        ],
        "hint": "Tag on the packet: the field or verdict that just changed",
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def laptop(g, x, y):
    """Laptop symbol, as in the prototype."""
    g.append(f'<path class="ink" d="M{x-44} {y-40} q2 -3 6 -3 l76 1 q5 0 5 5 l-1 50 l-88 1 z"/>')
    g.append(f'<path class="thin" d="M{x-36} {y-31} l70 1 l-1 34 l-69 0 z"/>')
    g.append(f'<path class="ink" d="M{x-54} {y+13} l108 0 q4 0 2 4 l-6 7 l-100 0 l-6 -7 q-2 -4 2 -4"/>')


def bot(g, x, y):
    """Small compromised host: a monitor on a stand."""
    g.append(f'<path class="ink" d="M{x-14} {y-10} l28 1 l-1 18 l-27 -1 z"/>')
    g.append(f'<path class="thin" d="M{x-3} {y+9} l0 5 M{x-9} {y+15} l18 0"/>')
    g.append(f'<circle class="fillink" cx="{x+8}" cy="{y-4}" r="1.6"/>')


def shield_path():
    x, y = SHIELD[0], 114
    return (f"M{x-36} {y} q36 -10 72 0 l-1 96 q-4 54 -35 92 q-31 -38 -35 -92 z")


def burst():
    """Absorption mark where the volumetric flood ends at the shield edge."""
    x, y = VOL[-1]
    r = []
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        r.append(f"M{x + 5 * math.cos(a):.1f} {y + 5 * math.sin(a):.1f} "
                 f"L{x + 11 * math.cos(a):.1f} {y + 11 * math.sin(a):.1f}")
    return f'<path class="pkl" stroke-width="2" d="{" ".join(r)}"/>'


def block_mark():
    """Block at the WAF: vermilion X where the L7 path ends."""
    x, y = L7_B[-1]
    return (f'<path class="pkl" stroke-width="3" d="M{x-9} {y-9} L{x+9} {y+9} M{x+9} {y-9} L{x-9} {y+9}"/>')


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    W, H = 960, 500
    steps_t = [(T["v_on"], V_ARRIVE[-1] + 0.1), (T["l_on"], T["l_off"]),
               (T["g_on"], T["g_waf_go"] + 0.3), (T["g_eni"] - 0.2, T["g_alb_go"]),
               (T["g_alb_go"], T["g_off"])]
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
    ex, ey, ew, eh = EDGE_BOX
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="M{ex} {ey+6} q0 -6 6 -6 l{ew-12} 1 q6 0 6 6 l-1 {eh-12} q0 6 -6 6 l-{ew-12} -1 q-6 0 -6 -6 z"/>')
    vx, vy, vw, vh = VPC_BOX
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="M{vx} {vy+6} q0 -6 6 -6 l{vw-12} 1 q6 0 6 6 l-1 {vh-12} q0 6 -6 6 l-{vw-12} -1 q-6 0 -6 -6 z"/>')
    sx, sy, sw, sh = SUB_BOX
    g.append(f'<path class="thin" stroke-dasharray="1 5" d="M{sx} {sy} l{sw} 1 l-1 {sh} l-{sw-1} -1 z"/>')
    for path in (C_SH, SH_WAF, WAF_ENI, ENI_ALB, ALB_POD):
        for dy in (-2.5, 2.5):
            g.append(f'<path class="cable" d="{c([(x, y + dy) for x, y in path])}"/>')
    # attack paths: dashed single pen lines
    for path in (L7_A, L7_B, VOL):
        g.append(f'<path class="cable" stroke-dasharray="6 7" d="{c(path)}"/>')
    laptop(g, *CLIENT)
    for b in BOTS:
        bot(g, *b)
    # Shield: a shield outline with inner strokes above and below the label
    g.append(f'<path class="ink" d="{shield_path()}"/>')
    x = SHIELD[0]
    g.append(f'<path class="thin" d="M{x-26} 122 q26 -7 52 0 M{x+26} 212 q-3 40 -26 70 q-23 -30 -26 -70"/>')
    # WAF web ACL: a box listing rules in priority order
    wx, wy, ww, wh = WAF_BOX
    g.append(f'<path class="ink" d="M{wx} {wy+4} q0 -4 4 -4 l{ww-8} 1 q4 0 4 4 l-1 {wh-8} q0 4 -4 4 l-{ww-8} -1 q-4 0 -4 -4 z"/>')
    for i, yy in enumerate((wy + 16, wy + 30, wy + 56, wy + 70)):
        g.append(f'<path class="thin" d="M{wx+10} {yy} l{ww-20} 1"/>')
    # VPC origin ENI: a small card with a port (as in 08)
    x, y = ENI
    g.append(f'<path class="ink" d="M{x-18} {y-14} l36 1 l-1 28 l-35 -1 z"/>')
    g.append(f'<path class="thin" d="M{x-8} {y-4} l16 0 l0 8 l-16 0 z"/>')
    # internal ALB inside its security-group ring (as in 08)
    x, y = ALB
    g.append(f'<path class="ink" d="M{x-22} {y-16} q0 -4 4 -4 l26 0 q4 0 4 4 l0 32 q0 4 -4 4 l-26 0 q-4 0 -4 -4 z"/>')
    g.append(f'<path class="thin" d="M{x-12} {y} l16 -9 M{x-12} {y} l16 0 M{x-12} {y} l16 9"/>')
    cx, cy, rx, ry = SG_RING
    g.append(f'<ellipse class="trunk" stroke-dasharray="4 5" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>')
    # Pod: a box holding one container, inside a NetworkPolicy ring
    x, y = POD
    g.append(f'<path class="ink" d="M{x-17} {y-15} l34 1 l-1 29 l-33 -1 z"/>')
    g.append(f'<path class="thin" d="M{x-8} {y-6} l16 0 l0 12 l-16 0 z"/>')
    nx, ny, nrx, nry = NP_RING
    g.append(f'<ellipse class="trunk" stroke-dasharray="2 4" cx="{nx}" cy="{ny}" rx="{nrx}" ry="{nry}"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    x, y = CLIENT
    o.append(f'<text class="t" x="{x}" y="{y+48}" text-anchor="middle" font-weight="600">{esc(k["client"][0])}</text>')
    o.append(f'<text class="s" x="{x}" y="{y+66}" text-anchor="middle">{esc(k["client"][1])}</text>')
    o.append(f'<text class="t" x="34" y="334" font-weight="600">{esc(k["botnet"])}</text>')
    o.append(f'<text class="s" x="{ex+14}" y="{ey+20}" font-weight="700">{esc(k["edge"])}</text>')
    sx0, sy0 = SHIELD_C
    o.append(f'<text class="t" x="{sx0}" y="{sy0}" text-anchor="middle" font-weight="600" font-size="14">{esc(k["shield"][0])}</text>')
    o.append(f'<text class="s" x="{sx0}" y="{sy0+16}" text-anchor="middle">{esc(k["shield"][1])}</text>')
    o.append(f'<text class="t" x="{WAF[0]}" y="268" text-anchor="middle" font-weight="600" font-size="14">{esc(k["waf"][0])}</text>')
    o.append(f'<text class="s" x="{WAF[0]}" y="285" text-anchor="middle">{esc(k["waf"][1])}</text>')
    for (x, y), (n, sub), dy in ((ENI, k["eni"], 40), (ALB, k["alb"], 54), (POD, k["pod"], 54)):
        o.append(f'<text class="t" x="{x}" y="{y+dy}" text-anchor="middle" font-weight="600" font-size="14">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+dy+17}" text-anchor="middle">{esc(sub)}</text>')
    o.append(f'<text class="s" x="{vx+14}" y="{vy+vh-14}" font-weight="700">{esc(k["vpc"])}</text>')
    o.append(f'<text class="s bl" x="{sx+sw-8}" y="{sy+sh-30}" text-anchor="end">{esc(k["sg"])}</text>')
    o.append(f'<text class="s bl" x="{sx+sw-8}" y="{sy+sh-12}" text-anchor="end">{esc(k["np"])}</text>')

    vx0, vy0 = VOL[-1]

    def vol_note(i):
        return (f'<text class="tag halo acc" x="{vx0+22}" y="334">{esc(k["vol"][i])}</text>')

    # --- motion layer ---
    m = ['<g class="motion">']
    # highlights: WAF box (block, then allow), SG ring, NetworkPolicy ring
    m.append(f'<g opacity="0">{win(T["l_waf"], T["l_off"], fade=0.2)}'
             f'<path class="pkl" stroke-width="3" d="M{wx} {wy+4} q0 -4 4 -4 l{ww-8} 1 q4 0 4 4 l-1 {wh-8} q0 4 -4 4 l-{ww-8} -1 q-4 0 -4 -4 z"/></g>')
    m.append(f'<g opacity="0">{win(T["g_waf"], T["g_waf_go"], fade=0.2)}'
             f'<path class="trunk" stroke-width="3" d="M{wx} {wy+4} q0 -4 4 -4 l{ww-8} 1 q4 0 4 4 l-1 {wh-8} q0 4 -4 4 l-{ww-8} -1 q-4 0 -4 -4 z"/></g>')
    m.append(f'<g opacity="0">{win(T["g_alb"], T["g_alb_go"], fade=0.2)}'
             f'<ellipse class="trunk" stroke-width="3" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/></g>')
    m.append(f'<g opacity="0">{win(T["g_pod"], T["g_off"], fade=0.2)}'
             f'<ellipse class="trunk" stroke-width="3" cx="{nx}" cy="{ny}" rx="{nrx}" ry="{nry}"/></g>')
    # persistent outcome marks: absorption at the shield, block at the WAF
    m.append(f'<g opacity="0">{win(V_ARRIVE[0], T["hold"], fade=0.15)}{burst()}</g>')
    m.append(f'<g opacity="0">{win(T["l_waf"], T["hold"], fade=0.15)}{block_mark()}</g>')
    # volumetric note changes in place: vector name while travelling, outcome after
    m.append(f'<g opacity="0">{win(T["v_on"], V_ARRIVE[0] - 0.1, fade=0.2)}{vol_note(0)}</g>')
    m.append(f'<g opacity="0">{win(V_ARRIVE[0] + 0.1, T["l_on"] + 0.6, fade=0.2)}{vol_note(1)}</g>')

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

    # 1. volumetric flood: three packets, staggered, each absorbed at the shield edge
    for i, arrive in enumerate(V_ARRIVE):
        go = T["v_go"] + i * T["v_gap"]
        m.append(packet(V_D, [(0, 0), (go, 0), (arrive, 1), (DUR, 1)],
                        T["v_on"] + i * T["v_gap"], arrive + 0.05, []))
    # 2. L7 flood request: passes the shield, blocked by the WAF rate-based rule
    lf = L_F
    m.append(packet(L_D, [(0, 0), (T["l_go"], 0), (T["l_sh"], lf[1]), (T["l_sh_go"], lf[1]),
                          (T["l_waf"], 1), (DUR, 1)],
                    T["l_on"], T["l_off"], [
        (k["l7"][0], T["l_on"], T["l_sh"] - 0.1, "acc", -6, -22, "start"),
        (k["l7"][1], T["l_sh"] + 0.1, T["l_waf"] - 0.1, "bl", -6, -22, "start"),
        (k["l7"][2], T["l_waf"] + 0.1, T["l_off"], "acc", 14, 24, "start"),
    ]))
    # 3. legitimate request: Shield, WAF default Allow, VPC origin, ALB, Pod
    f = G_F
    gt = k["g"]
    m.append(packet(G_D, [
        (0, 0), (T["g_go"], 0), (T["g_sh"], f[2]), (T["g_sh_go"], f[2]),
        (T["g_waf"], f[5]), (T["g_waf_go"], f[5]), (T["g_eni"], f[8]), (T["g_eni_go"], f[8]),
        (T["g_alb"], f[11]), (T["g_alb_go"], f[11]), (T["g_pod"], 1), (DUR, 1)],
        T["g_on"], T["g_off"], [
        (gt[0], T["g_on"], T["g_sh"] - 0.1, "acc", 0, -24, "middle"),
        (gt[1], T["g_sh"] + 0.1, T["g_waf"] - 0.1, "bl", 0, -24, "middle"),
        (gt[2], T["g_waf"] + 0.1, T["g_eni"] - 0.1, "bl", 0, -24, "middle"),
        (gt[3], T["g_eni"] + 0.1, T["g_alb"] - 0.1, "acc", 0, -50, "middle"),
        (gt[4], T["g_alb"] + 0.1, T["g_alb_go"] - 0.1, "bl", 0, -46, "middle"),
        (gt[5], T["g_alb_go"] + 0.1, T["g_pod"] - 0.1, "acc", 0, -50, "middle"),
        (gt[6], T["g_pod"] + 0.1, T["g_off"], "bl", -20, -46, "end"),
    ]))
    # captions
    cy0 = 378
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
    st = ['<g class="static">', burst(), block_mark(), vol_note(1)]
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    for (x, y, label) in ((140, 326, "①"), (300, 206, "②"), (CLIENT[0] - 8, 92, "③"),
                          (ENI[0] - 8, 116, "④"), (POD[0] - 8, 98, "⑤")):
        st.append(f'<text class="tag acc" x="{x}" y="{y}" font-size="16">{label}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    return "\n".join(o)


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-networking-expert-09-edge-security-waf-ddos-anim-0.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-networking-expert-09-edge-security-waf-ddos-anim-0.svg")
        svg = build(lang)
        assert "\u2014" not in svg, "em dash in output"
        assert "0.0.0.0" not in svg and "::/0" not in svg, "public CIDR must not appear"
        assert "scheme: internet-facing" not in svg, "no internet-facing load balancer"
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [round(x, 3) for x in G_F], [round(x, 3) for x in L_F])
