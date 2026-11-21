#!/usr/bin/env python3
"""Line-art animated SVG: where a Pod's AWS credentials come from (three lanes).

Copies the approved prototype (gen_basics_06_part5_anim0.py) and its later
sibling gen_networking_expert_09_edge_security_waf_ddos_anim0.py: same palette
tokens, pen filter, stroke classes, font stack, caption layout, packet-tag
style, ko/en COPY structure, anim()/win()/move() helpers and keyTimes
self-check. SMIL drives motion on one shared clock; CSS only handles palette
(light/dark) and the reduced-motion static view.

The house palette has only two accents (vermilion, blue). This chapter needs a
third colour for returned credentials, so one --green token is added in the
same light/dark rules. Colour semantics: request = blue envelope, returned
credentials = green key, denied = vermilion (as gen 09 shows "blocked").

Story (three lanes, one after another):
1. Node instance profile: the Pod's AWS SDK asks EC2 IMDSv2 (169.254.169.254)
   and gets node role credentials.
2. IRSA: the SDK calls AWS STS AssumeRoleWithWebIdentity and gets IRSA role
   credentials.
3. EKS Pod Identity: the SDK calls the Pod Identity Agent (169.254.170.23) on
   the same node, which calls EKS Auth AssumeRoleForPodIdentity, and gets Pod
   Identity role credentials.
4. Each Pod signs its S3 request with the credentials it got.
"""
import math
import sys

DUR = 18.0  # seconds per loop
W, H = 960, 500

# ---------- geometry ----------------------------------------------------------
LY = [126, 216, 306]                 # lane centre lines
POD_X = 80                           # Pod glyph centre
START_X = 104                        # Pod's right edge: requests leave here
HOP1 = (300, 166)                    # (centre x, width): IMDS / Agent (on the node)
HOP2 = (590, 220)                    # STS / EKS Auth (AWS)
ROLE = (840, 160)                    # IAM role card
CARD_H = 46
NODE_BOX = (30, 62, 380, 292)        # x, y, w, h: worker node (dashed)
AWS_BOX = (440, 62, 500, 292)        # AWS services (dashed)


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


def wig(x0, x1, y, amp=10):
    """Hand-drawn cable between two x positions on one lane."""
    dx = x1 - x0
    return [(x0, y), (round(x0 + dx * 0.33), y - amp), (round(x0 + dx * 0.66), y + amp), (x1, y)]


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


def reverse(segments):
    return [(kind, list(reversed(pts))) for kind, pts in reversed(segments)]


def edges(card):
    cx, w = card
    return cx - w // 2, cx + w // 2


def lane_segments(y, cards):
    """Cables from the Pod through each card (entering at its left edge) to the role card."""
    segs, x = [], START_X
    for i, card in enumerate(cards):
        left, right = edges(card)
        segs.append(("bez", wig(x, left, y, 10 if i % 2 == 0 else -10)))
        if card is not cards[-1]:
            segs.append(("line", [(left, y), (right, y)]))
        x = right
    return segs


LANE_CARDS = [[HOP1, ROLE], [HOP2, ROLE], [HOP1, HOP2, ROLE]]
SEGS = [lane_segments(y, cards) for y, cards in zip(LY, LANE_CARDS)]
REQ = [motion(s) for s in SEGS]
RET = [motion(reverse(s)) for s in SEGS]

# Timeline (seconds): each lane = request out, dwell at each hop, credentials back.
# A pulse is hidden for the "thr" 0.2 s while it crosses a card, so it never
# covers the card text; it dwells visibly at the card edge instead.
T = {
    "l1_on": 0.4, "l1_go": 0.6, "l1_hop": 1.3, "l1_hop_go": 1.8, "l1_thr": 2.0, "l1_role": 3.0,
    "l1_back": 3.3, "l1_rhop": 4.3, "l1_rhop_go": 4.6, "l1_rthr": 4.8, "l1_home": 5.2,
    "l2_on": 5.4, "l2_go": 5.6, "l2_hop": 6.6, "l2_hop_go": 7.1, "l2_thr": 7.3, "l2_role": 7.6,
    "l2_back": 7.9, "l2_rhop": 8.2, "l2_rhop_go": 8.6, "l2_rthr": 8.8, "l2_home": 9.6,
    "l3_on": 9.8, "l3_go": 10.0, "l3_hop": 10.4, "l3_hop_go": 10.8, "l3_thr": 11.0,
    "l3_hop2": 11.3, "l3_hop2_go": 11.7, "l3_thr2": 11.9, "l3_role": 12.2,
    "l3_back": 12.5, "l3_rhop2": 12.8, "l3_rhop2_go": 13.1, "l3_rthr2": 13.3,
    "l3_rhop": 13.6, "l3_rhop_go": 13.9, "l3_rthr": 14.1, "l3_home": 14.5,
    "sign": 14.8, "sign_end": 16.0,
    "hold": 16.4,
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


def vis(windows, fade=0.12):
    """opacity keyframes for several visible windows [(start, end), ...]."""
    pts = [(0, 0)]
    for s0, s1 in windows:
        pts += [(max(s0 - fade, pts[-1][0]), 0), (s0, 1), (s1, 1), (min(s1 + fade, DUR - 0.002), 0)]
    pts.append((DUR, 0))
    return anim("opacity", [t for t, _ in pts], [v for _, v in pts])


def check_anims():
    for ts, vs in ANIMS:
        t = [float(x) for x in ts.split(";")]
        v = vs.split(";")
        assert t[0] == 0 and t[-1] == 1, ts
        assert all(b >= a for a, b in zip(t, t[1:])), ts
        assert len(t) == len(v), (ts, vs)


def tw(s, size, bold=False):
    """Rough rendered width: CJK and symbols ~1em, capitals/digits ~0.62em, others ~0.53em."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x2460 or 0x2190 <= o <= 0x21FF:
            w += 1.0
        elif ch.isupper() or ch.isdigit():
            w += 0.62
        elif ch == " ":
            w += 0.3
        else:
            w += 0.53
    return w * size * (1.06 if bold else 1.0)


def fits(s, size, room, bold=False):
    assert tw(s, size, bold) <= room, (s, round(tw(s, size, bold)), room)


# ---------- copy --------------------------------------------------------------
COPY = {
    "ko": {
        "title": "Pod의 AWS 자격 증명은 어디서 오는가: 세 갈래 경로",
        "desc": ("같은 앱 Pod 세 개가 AWS SDK로 자격 증명을 요청한다. 첫째, 노드 인스턴스 프로파일 경로에서는 SDK가 "
                 "EC2 IMDSv2(169.254.169.254)에 요청하고 노드 역할 자격 증명을 받는다. 둘째, IRSA 경로에서는 SDK가 "
                 "AWS STS AssumeRoleWithWebIdentity를 호출해 IRSA 역할의 임시 자격 증명을 받는다. 셋째, EKS Pod "
                 "Identity 경로에서는 SDK가 같은 노드의 Pod Identity Agent(169.254.170.23)를 부르고, Agent가 EKS Auth "
                 "AssumeRoleForPodIdentity를 호출해 Pod Identity 역할의 임시 자격 증명을 받는다. 요청은 파란 봉투, "
                 "돌아오는 자격 증명은 초록 열쇠로 표시한다. 마지막으로 각 Pod는 받은 자격 증명으로 S3 요청에 서명한다."),
        "node": "워커 노드 (EC2)",
        "aws": "AWS",
        "lanes": ["① 노드 인스턴스 프로파일", "② IRSA", "③ EKS Pod Identity"],
        "pod": "Pod",
        "imds": ["EC2 IMDSv2", "169.254.169.254"],
        "agent": ["Pod Identity Agent", "169.254.170.23"],
        "sts": ["AWS STS", "AssumeRoleWithWebIdentity"],
        "auth": ["EKS Auth", "AssumeRoleForPodIdentity"],
        "roles": [["노드 역할", "IAM 역할"], ["IRSA 역할", "IAM 역할"], ["Pod Identity 역할", "IAM 역할"]],
        "req": ["자격 증명 요청", "웹 ID 토큰", "Pod 토큰"],
        "req2": "Agent → EKS Auth",
        "ret": ["노드 역할 자격 증명", "IRSA 역할 임시 자격 증명", "Pod Identity 역할 임시 자격 증명"],
        "signed": "S3 요청에 서명",
        "steps": [
            "① 노드 인스턴스 프로파일: SDK가 IMDSv2(169.254.169.254)에서 노드 역할 자격 증명을 받는다",
            "② IRSA: SDK가 AWS STS AssumeRoleWithWebIdentity를 호출해 IRSA 역할 자격 증명을 받는다",
            "③ Pod Identity: SDK → 같은 노드의 Agent(169.254.170.23) → EKS Auth AssumeRoleForPodIdentity",
            "④ 세 Pod는 각자 받은 자격 증명으로 S3 요청에 서명한다",
        ],
        "hint": "파란 봉투: 요청 · 초록 열쇠: 돌아온 자격 증명",
    },
    "en": {
        "title": "Where a Pod's AWS credentials come from: three paths",
        "desc": ("Three Pods of the same app ask for credentials through the AWS SDK. On the node instance profile path, "
                 "the SDK asks EC2 IMDSv2 (169.254.169.254) and gets the node role's credentials. On the IRSA path, the "
                 "SDK calls AWS STS AssumeRoleWithWebIdentity and gets temporary credentials for the IRSA role. On the "
                 "EKS Pod Identity path, the SDK calls the Pod Identity Agent (169.254.170.23) on the same node, and the "
                 "Agent calls EKS Auth AssumeRoleForPodIdentity to get temporary credentials for the Pod Identity role. "
                 "Requests are drawn as blue envelopes and returned credentials as green keys. Finally, each Pod signs "
                 "its S3 request with the credentials it got."),
        "node": "Worker node (EC2)",
        "aws": "AWS",
        "lanes": ["① Node instance profile", "② IRSA", "③ EKS Pod Identity"],
        "pod": "Pod",
        "imds": ["EC2 IMDSv2", "169.254.169.254"],
        "agent": ["Pod Identity Agent", "169.254.170.23"],
        "sts": ["AWS STS", "AssumeRoleWithWebIdentity"],
        "auth": ["EKS Auth", "AssumeRoleForPodIdentity"],
        "roles": [["Node role", "IAM role"], ["IRSA role", "IAM role"], ["Pod Identity role", "IAM role"]],
        "req": ["credentials request", "web identity token", "Pod token"],
        "req2": "Agent → EKS Auth",
        "ret": ["node role credentials", "IRSA role credentials", "Pod Identity role credentials"],
        "signed": "signs S3 request",
        "steps": [
            "① Node instance profile: the SDK gets node role credentials from IMDSv2 (169.254.169.254)",
            "② IRSA: the SDK calls AWS STS AssumeRoleWithWebIdentity and gets IRSA role credentials",
            "③ Pod Identity: SDK → Agent on the same node (169.254.170.23) → EKS Auth AssumeRoleForPodIdentity",
            "④ Each Pod signs its S3 request with the credentials it got",
        ],
        "hint": "Blue envelope: request · green key: returned credentials",
    },
}

STYLE = """<style>
  svg{--paper:#f7f1e3;--ink:#2b2724;--soft:#8a8177;--accent:#d9480f;--blue:#1864ab;--green:#2b8a3e;--wash:#efe5cf}
  @media (prefers-color-scheme:dark){svg{--paper:#1e2240;--ink:#ece6d6;--soft:#9aa0bd;--accent:#ff8b5e;--blue:#8cc8ff;--green:#8ce99a;--wash:#272c52}}
  .paper{fill:var(--paper)} .wash{fill:var(--wash)}
  .ink{fill:none;stroke:var(--ink);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
  .thin{fill:none;stroke:var(--ink);stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
  .cable{fill:none;stroke:var(--ink);stroke-width:1.5;stroke-linecap:round}
  .trunk{fill:none;stroke:var(--blue);stroke-width:1.5;stroke-linecap:round}
  .fillink{fill:var(--ink)} .t{fill:var(--ink);font-size:15px} .s{fill:var(--soft);font-size:12.5px}
  .h{fill:var(--ink);font-size:17px;font-weight:600} .acc{fill:var(--accent)} .bl{fill:var(--blue)} .gr{fill:var(--green)}
  .pk{fill:var(--paper);stroke:var(--accent);stroke-width:2;stroke-linejoin:round}
  .pkl{fill:none;stroke:var(--accent);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
  .rq{fill:var(--paper);stroke:var(--blue);stroke-width:2;stroke-linejoin:round}
  .rql{fill:none;stroke:var(--blue);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
  .ky{fill:var(--paper);stroke:var(--green);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
  .okl{fill:none;stroke:var(--green);stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
  .tag{font-size:12px;font-weight:700} .cap{font-size:15px;fill:var(--ink)}
  .row{fill:var(--ink);font-size:13.5px}
  .halo{paint-order:stroke;stroke:var(--paper);stroke-width:4px;stroke-linejoin:round}
  .static{display:none}
  @media (prefers-reduced-motion:reduce){.motion{display:none}.static{display:inline}}
</style>"""

PEN = """<defs><filter id="pen" filterUnits="userSpaceOnUse" x="0" y="0" width="960" height="500">
  <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="7"/>
  <feDisplacementMap in="SourceGraphic" scale="1.6"/></filter></defs>"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box_d(cx, cy, w, h):
    """Hand-drawn rounded box path centred on (cx, cy)."""
    x, y = cx - w / 2, cy - h / 2
    return (f"M{x:g} {y+4:g} q0 -4 4 -4 l{w-8:g} 1 q4 0 4 4 l-1 {h-8:g} "
            f"q0 4 -4 4 l-{w-8:g} -1 q-4 0 -4 -4 z")


def dashed_d(x, y, w, h):
    return f"M{x} {y+6} q0 -6 6 -6 l{w-12} 1 q6 0 6 6 l-1 {h-12} q0 6 -6 6 l-{w-12} -1 q-6 0 -6 -6 z"


def pod(g, x, y):
    """Pod: a box holding one container (as in gen 09), drawn a little larger."""
    g.append(f'<path class="ink" d="M{x-22} {y-17} l44 1 l-1 33 l-43 -1 z"/>')
    g.append(f'<path class="thin" d="M{x-11} {y-8} l22 0 l0 16 l-22 0 z"/>')


ENVELOPE = ('<path class="rq" d="M-17 -11 l34 0 l0 22 l-34 0 z"/>'
            '<path class="rql" d="M-17 -11 l17 12 l17 -12"/>')
# Key: bow on the right so it trails a key moving left; origin at the tip.
KEY = ('<circle class="ky" cx="16" cy="0" r="6.5"/>'
       '<path class="ky" d="M9.5 0 L-4 0 M0 0 l0 5 M-4 0 l0 6"/>')


def card_text(o, cx, cy, lines, bold_size=13.5):
    o.append(f'<text class="t" x="{cx}" y="{cy-3}" text-anchor="middle" font-weight="600" '
             f'style="font-size:{bold_size}px">{esc(lines[0])}</text>')
    o.append(f'<text class="s" x="{cx}" y="{cy+14}" text-anchor="middle">{esc(lines[1])}</text>')


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    steps_t = [(T["l1_on"], T["l1_home"]), (T["l2_on"], T["l2_home"]),
               (T["l3_on"], T["l3_home"]), (T["sign"], T["sign_end"])]
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="t d" font-family="Pretendard, \'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Noto Sans CJK KR\', \'Malgun Gothic\', \'Segoe UI\', sans-serif">')
    o.append(f'<title id="t">{esc(k["title"])}</title><desc id="d">{esc(k["desc"])}</desc>')
    o.append(STYLE)
    o.append(PEN)
    o.append(f'<rect class="paper" width="{W}" height="{H}"/>')
    o.append(f'<text class="h" x="32" y="40">{esc(k["title"])}</text>')

    # card list: (centre x, lane y, width, text lines)
    cards = [
        (HOP1[0], LY[0], HOP1[1], k["imds"]),
        (HOP2[0], LY[1], HOP2[1], k["sts"]),
        (HOP1[0], LY[2], HOP1[1], k["agent"]),
        (HOP2[0], LY[2], HOP2[1], k["auth"]),
    ] + [(ROLE[0], y, ROLE[1], k["roles"][i]) for i, y in enumerate(LY)]
    for cx, cy, w, lines in cards:
        fits(lines[0], 13.5, w - 14, bold=True)
        fits(lines[1], 12.5, w - 14)
    fits(k["signed"], 12, edges(HOP1)[0] - START_X - 6, bold=True)

    # --- drawing (pen-wobbled) ---
    g = ['<g filter="url(#pen)">']
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*NODE_BOX)}"/>')
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*AWS_BOX)}"/>')
    for segs in SEGS:
        for kind, pts in segs:
            if kind != "bez":
                continue
            for dy in (-2.5, 2.5):
                g.append(f'<path class="cable" d="{c([(x, y + dy) for x, y in pts])}"/>')
    for y in LY:
        pod(g, POD_X, y)
    for cx, cy, w, _ in cards:
        g.append(f'<path class="ink" d="{box_d(cx, cy, w, CARD_H)}"/>')
    # role cards: a small ID badge in the top-left corner
    for y in LY:
        bx, by = ROLE[0] - ROLE[1] // 2 + 4, y - CARD_H // 2 - 6
        g.append(f'<path class="thin" d="M{bx} {by} l14 0 l0 11 l-14 0 z M{bx+4} {by+4} l6 0 M{bx+4} {by+7} l4 0"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    nx, ny, nw, nh = NODE_BOX
    ax, ay, aw, ah = AWS_BOX
    o.append(f'<text class="s" x="{nx+nw-12}" y="{ny+20}" text-anchor="end" font-weight="700">{esc(k["node"])}</text>')
    o.append(f'<text class="s" x="{ax+aw-12}" y="{ay+20}" text-anchor="end" font-weight="700">{esc(k["aws"])}</text>')
    for i, y in enumerate(LY):
        o.append(f'<text class="t" x="{nx+14}" y="{y-36}" font-weight="600" style="font-size:14px">{esc(k["lanes"][i])}</text>')
        o.append(f'<text class="s" x="{POD_X}" y="{y+32}" text-anchor="middle">{esc(k["pod"])}</text>')
    for cx, cy, w, lines in cards:
        card_text(o, cx, cy, lines)

    # --- motion layer ---
    m = ['<g class="motion">']

    def hl(cx, cy, w, start, end):
        return (f'<g opacity="0">{win(start, end, fade=0.2)}'
                f'<path class="trunk" style="stroke-width:3px" d="{box_d(cx, cy, w, CARD_H)}"/></g>')

    # card highlights while a pulse dwells there
    m.append(hl(HOP1[0], LY[0], HOP1[1], T["l1_hop"], T["l1_hop_go"]))
    m.append(hl(ROLE[0], LY[0], ROLE[1], T["l1_role"], T["l1_back"]))
    m.append(hl(HOP2[0], LY[1], HOP2[1], T["l2_hop"], T["l2_hop_go"]))
    m.append(hl(ROLE[0], LY[1], ROLE[1], T["l2_role"], T["l2_back"]))
    m.append(hl(HOP1[0], LY[2], HOP1[1], T["l3_hop"], T["l3_hop_go"]))
    m.append(hl(HOP2[0], LY[2], HOP2[1], T["l3_hop2"], T["l3_hop2_go"]))
    m.append(hl(ROLE[0], LY[2], ROLE[1], T["l3_role"], T["l3_back"]))

    def pulse(d, keys, windows, glyph, tags):
        r = ['<g>', vis(windows), move(d, keys), glyph]
        for text, s0, s1, cls in tags:
            r.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                     f'<text class="tag halo {cls}" x="0" y="36" text-anchor="middle">{esc(text)}</text></g>')
        r.append('</g>')
        return "".join(r)

    # lane 1: IMDS -> node role
    d, f = REQ[0]
    m.append(pulse(d, [(0, 0), (T["l1_go"], 0), (T["l1_hop"], f[1]), (T["l1_hop_go"], f[1]),
                       (T["l1_thr"], f[2]), (T["l1_role"], 1), (DUR, 1)],
                   [(T["l1_on"], T["l1_hop_go"]), (T["l1_thr"], T["l1_role"] + 0.1)], ENVELOPE,
                   [(k["req"][0], T["l1_go"] + 0.3, T["l1_role"], "bl")]))
    d, f = RET[0]
    m.append(pulse(d, [(0, 0), (T["l1_back"], 0), (T["l1_rhop"], f[1]), (T["l1_rhop_go"], f[1]),
                       (T["l1_rthr"], f[2]), (T["l1_home"], 1), (DUR, 1)],
                   [(T["l1_back"] - 0.1, T["l1_rhop_go"]), (T["l1_rthr"], T["hold"])], KEY,
                   [(k["ret"][0], T["l1_back"], T["l1_rhop_go"], "gr")]))
    # lane 2: STS -> IRSA role
    d, f = REQ[1]
    m.append(pulse(d, [(0, 0), (T["l2_go"], 0), (T["l2_hop"], f[1]), (T["l2_hop_go"], f[1]),
                       (T["l2_thr"], f[2]), (T["l2_role"], 1), (DUR, 1)],
                   [(T["l2_on"], T["l2_hop_go"]), (T["l2_thr"], T["l2_role"] + 0.1)], ENVELOPE,
                   [(k["req"][1], T["l2_go"] + 0.3, T["l2_role"], "bl")]))
    d, f = RET[1]
    m.append(pulse(d, [(0, 0), (T["l2_back"], 0), (T["l2_rhop"], f[1]), (T["l2_rhop_go"], f[1]),
                       (T["l2_rthr"], f[2]), (T["l2_home"], 1), (DUR, 1)],
                   [(T["l2_back"] - 0.1, T["l2_rhop_go"]), (T["l2_rthr"], T["hold"])], KEY,
                   [(k["ret"][1], T["l2_rthr"], T["l2_home"] - 0.3, "gr")]))
    # lane 3: Agent -> EKS Auth -> Pod Identity role
    d, f = REQ[2]
    m.append(pulse(d, [(0, 0), (T["l3_go"], 0), (T["l3_hop"], f[1]), (T["l3_hop_go"], f[1]),
                       (T["l3_thr"], f[2]), (T["l3_hop2"], f[3]), (T["l3_hop2_go"], f[3]),
                       (T["l3_thr2"], f[4]), (T["l3_role"], 1), (DUR, 1)],
                   [(T["l3_on"], T["l3_hop_go"]), (T["l3_thr"], T["l3_hop2_go"]),
                    (T["l3_thr2"], T["l3_role"] + 0.1)], ENVELOPE,
                   [(k["req"][2], T["l3_go"] + 0.15, T["l3_hop_go"] - 0.1, "bl"),
                    (k["req2"], T["l3_thr"], T["l3_role"], "bl")]))
    d, f = RET[2]
    m.append(pulse(d, [(0, 0), (T["l3_back"], 0), (T["l3_rhop2"], f[1]), (T["l3_rhop2_go"], f[1]),
                       (T["l3_rthr2"], f[2]), (T["l3_rhop"], f[3]), (T["l3_rhop_go"], f[3]),
                       (T["l3_rthr"], f[4]), (T["l3_home"], 1), (DUR, 1)],
                   [(T["l3_back"] - 0.1, T["l3_rhop2_go"]), (T["l3_rthr2"], T["l3_rhop_go"]),
                    (T["l3_rthr"], T["hold"])], KEY,
                   [(k["ret"][2], T["l3_back"], T["l3_rhop_go"], "gr")]))

    # step 4: each Pod signs its S3 request with the key it holds
    for y in LY:
        m.append(f'<g opacity="0">{win(T["sign"], T["sign_end"] + 0.3, fade=0.2)}'
                 f'<ellipse class="okl" cx="{START_X + 9}" cy="{y}" rx="21" ry="13"/>'
                 f'<text class="tag halo gr" x="{START_X + 2}" y="{y + 31}">{esc(k["signed"])}</text></g>')

    # captions
    cy0 = 384
    for i, (txt, (s0, s1)) in enumerate(zip(k["steps"], steps_t)):
        y = cy0 + i * 22
        fits(txt, 15, W - 80)
        assert s1 + 0.3 < T["hold"], txt
        m.append(f'<g opacity="0">'
                 + anim("opacity", [0, max(s0 - 0.2, 0.001), s0, s1, s1 + 0.3, T["hold"], T["hold"] + 0.4, DUR],
                        [0, 0, 1, 1, 0.42, 0.42, 0, 0])
                 + f'<text class="cap" x="40" y="{y}">{esc(txt)}</text></g>')
    m.append(f'<text class="s" x="{W-32}" y="{H-14}" text-anchor="end">{esc(k["hint"])}</text>')
    m.append('</g>')
    o.extend(m)

    # --- static (reduced motion) layer: end state ---
    st = ['<g class="static">']
    for i, y in enumerate(LY):
        st.append(f'<g transform="translate({START_X} {y})">{KEY}</g>')
        st.append(f'<text class="tag halo gr" x="{START_X + 2}" y="{y + 31}">{esc(k["signed"])}</text>')
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    st.append(f'<text class="s" x="{W-32}" y="{H-14}" text-anchor="end">{esc(k["hint"])}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    return "\n".join(o)


def check_output(svg):
    assert "—" not in svg, "em dash in output"
    for bad in ("<script", "href", "@import", "<foreignObject", "<image"):
        assert bad not in svg, bad
    assert svg.count("url(") == svg.count("url(#pen)"), "only the pen filter may be referenced"


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-security-17-eks-workload-identity-migration-anim-0.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-security-17-eks-workload-identity-migration-anim-0.svg")
        svg = build(lang)
        check_output(svg)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [[round(x, 3) for x in f] for _, f in REQ])
