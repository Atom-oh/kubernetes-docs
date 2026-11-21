#!/usr/bin/env python3
"""Line-art animated SVG: IRSA in detail (webhook, projected token, STS, OIDC trust).

Same house style and helpers as gen_security_17_eks_workload_identity_migration_anim0.py
(copied from gen_basics_06_part5_anim0.py and gen 09): palette tokens plus one
--green token for returned credentials, pen filter, stroke classes, font
stack, caption layout, packet tags, ko/en COPY, anim()/win()/move() on one
shared SMIL clock with the keyTimes self-check. CSS only handles palette
(light/dark) and the reduced-motion static view.

Story:
a. A Pod is created with a ServiceAccount annotated eks.amazonaws.com/role-arn.
   The EKS mutating webhook (amazon-eks-pod-identity-webhook) injects env AWS_ROLE_ARN,
   AWS_WEB_IDENTITY_TOKEN_FILE and a projected ServiceAccount token volume at
   /var/run/secrets/eks.amazonaws.com/serviceaccount/token.
b. kubelet issues and refreshes that token: audience sts.amazonaws.com, issuer
   = the cluster OIDC issuer, sub = system:serviceaccount:<namespace>:<sa>.
c. The SDK sends the token (a tag carrying aud / sub) to regional AWS STS
   AssumeRoleWithWebIdentity.
d. STS validates the token signature against the cluster OIDC issuer keys
   through the IAM OIDC provider registered in the account, then checks the
   role trust policy conditions aud and sub.
e. Temporary credentials (green key) return to the SDK.
"""
import math
import sys

DUR = 16.0  # seconds per loop
W, H = 960, 500

# ---------- geometry ----------------------------------------------------------
CARD_H = 46
SA = (134, 100, 210)                 # centre x, centre y, width
HOOK = (134, 190, 210)
POD = (330, 190)                     # Pod glyph centre (80 x 60)
POD_W, POD_H = 80, 60
KUBELET = (330, 306, 150)
STS = (690, 190, 200)
PROVIDER = (690, 100, 200)
ISSUER = (872, 100, 112)
ROLE = (755, 290, 350, 74)           # centre x, centre y, width, height
INJ_NOTE = (258, 62, 294, 88)        # x, y, w, h
TOK_NOTE = (30, 246, 220, 104)
CLUSTER_BOX = (24, 58, 536, 300)
AWS_BOX = (572, 58, 366, 300)

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



def left(card):
    return card[0] - card[2] // 2


def right(card):
    return card[0] + card[2] // 2


def top(card):
    return card[1] - CARD_H // 2


def bottom(card):
    return card[1] + CARD_H // 2


def vwig(x, y0, y1, amp=8):
    dy = y1 - y0
    return [(x, y0), (x - amp, round(y0 + dy * 0.33)), (x + amp, round(y0 + dy * 0.66)), (x, y1)]


POD_R = POD[0] + POD_W // 2
POD_B = POD[1] + POD_H // 2
SA_HOOK = vwig(SA[0], bottom(SA), top(HOOK))
HOOK_POD = wig(right(HOOK), POD[0] - POD_W // 2, POD[1], 6)
KUBE_POD = vwig(KUBELET[0], top(KUBELET), POD_B)
POD_STS = wig(POD_R, left(STS), POD[1])
STS_PROV = vwig(STS[0], top(STS), bottom(PROVIDER))
PROV_ISS = [(right(PROVIDER), 100), (right(PROVIDER) + 9, 94), (left(ISSUER) - 9, 106), (left(ISSUER), 100)]
STS_ROLE = vwig(STS[0], bottom(STS), ROLE[1] - ROLE[3] // 2)

INJ_D, _ = motion([("bez", HOOK_POD)])
KUBE_D, _ = motion([("bez", KUBE_POD)])
REQ_D, _ = motion([("bez", POD_STS)])
RET_D, _ = motion([("bez", list(reversed(POD_STS)))])

# Timeline (seconds)
T = {
    "sa": 0.4, "hook": 1.0, "inj_go": 1.6, "inj_in": 2.2, "note": 2.2, "a_end": 2.8,
    "kube": 3.0, "tok_go": 3.4, "tok_in": 4.3, "b_end": 4.6,
    "req_on": 4.8, "req_go": 5.0, "req_in": 6.4, "c_end": 6.6,
    "sts": 6.6, "prov": 7.0, "iss": 7.4, "sig": 8.0, "role": 8.6, "aud": 9.0, "sub": 9.4, "d_end": 10.2,
    "ret_on": 10.3, "ret_go": 10.5, "ret_in": 12.0, "e_end": 12.4,
    "hold": 14.6,
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
        "title": "IRSA: projected 토큰을 STS에서 IRSA 역할 자격 증명으로 바꾸기",
        "desc": ("ServiceAccount에 eks.amazonaws.com/role-arn 주석이 있는 상태에서 Pod가 생성된다. EKS Pod Identity "
                 "webhook(mutating admission)이 env AWS_ROLE_ARN과 AWS_WEB_IDENTITY_TOKEN_FILE, 그리고 "
                 "/var/run/secrets/eks.amazonaws.com/serviceaccount/token 경로의 projected ServiceAccount 토큰 볼륨을 "
                 "주입한다. kubelet은 이 토큰을 발급하고 갱신하며, 토큰의 audience는 sts.amazonaws.com, issuer는 클러스터 "
                 "OIDC issuer, sub는 system:serviceaccount:<namespace>:<serviceaccount>이다. SDK는 aud와 sub를 담은 토큰을 "
                 "리전 AWS STS의 AssumeRoleWithWebIdentity로 보낸다. STS는 계정에 등록된 IAM OIDC provider를 통해 클러스터 "
                 "OIDC issuer의 키로 토큰 서명을 검증하고, 역할 신뢰 정책의 aud와 sub 조건을 확인한다. 마지막으로 IRSA 역할의 "
                 "임시 자격 증명이 SDK로 돌아온다."),
        "cluster": "EKS 클러스터",
        "aws": "AWS",
        "sa": ["ServiceAccount", "eks.amazonaws.com/role-arn"],
        "hook": ["EKS mutating 웹훅", "IRSA 변수 주입"],
        "kubelet": ["kubelet", "토큰 발급 · 갱신"],
        "pod": "Pod · AWS SDK",
        "sts": ["AWS STS (리전)", "AssumeRoleWithWebIdentity"],
        "prov": ["IAM OIDC provider", "계정에 등록"],
        "iss": ["OIDC issuer", "클러스터 키"],
        "role": "IRSA 역할 · 신뢰 정책 조건",
        "role_rows": ["aud = sts.amazonaws.com", "sub = system:serviceaccount:<ns>:<sa>"],
        "inj": ["webhook이 주입", "env AWS_ROLE_ARN", "env AWS_WEB_IDENTITY_TOKEN_FILE",
                "projected 토큰 볼륨", "/var/run/secrets/eks.amazonaws.com/", "serviceaccount/token"],
        "tok": ["projected 토큰 클레임", "aud  sts.amazonaws.com", "iss  클러스터 OIDC issuer",
                "sub  system:serviceaccount:", "       <ns>:<sa>"],
        "token": "aud · sub",
        "req_tag": "토큰 → STS",
        "sig": "서명 검증 ✓",
        "ret": "IRSA 역할 임시 자격 증명",
        "steps": [
            "① Pod 생성: webhook이 role-arn 주석을 보고 env 두 개와 projected 토큰 볼륨을 주입한다",
            "② kubelet이 토큰을 발급·갱신한다: aud sts.amazonaws.com · iss 클러스터 OIDC issuer · sub ServiceAccount",
            "③ SDK가 토큰을 리전 AWS STS의 AssumeRoleWithWebIdentity로 보낸다",
            "④ STS: IAM OIDC provider로 issuer 키를 찾아 서명을 검증하고, 신뢰 정책의 aud · sub를 확인한다",
            "⑤ IRSA 역할의 임시 자격 증명이 SDK로 돌아온다",
        ],
        "hint": "파란 꼬리표: 토큰(aud · sub) · 초록 열쇠: 돌아온 자격 증명",
    },
    "en": {
        "title": "IRSA: trading the projected token for IRSA role credentials at STS",
        "desc": ("A Pod is created with a ServiceAccount annotated eks.amazonaws.com/role-arn. The EKS Pod Identity "
                 "webhook (mutating admission) injects the env vars AWS_ROLE_ARN and AWS_WEB_IDENTITY_TOKEN_FILE and a "
                 "projected ServiceAccount token volume at /var/run/secrets/eks.amazonaws.com/serviceaccount/token. "
                 "kubelet issues and refreshes the token; its audience is sts.amazonaws.com, its issuer is the cluster "
                 "OIDC issuer, and its sub is system:serviceaccount:<namespace>:<serviceaccount>. The SDK sends the "
                 "token, carrying aud and sub, to regional AWS STS AssumeRoleWithWebIdentity. STS validates the token "
                 "signature against the cluster OIDC issuer keys through the IAM OIDC provider registered in the "
                 "account, then checks the aud and sub conditions in the role trust policy. Temporary credentials for "
                 "the IRSA role return to the SDK."),
        "cluster": "EKS cluster",
        "aws": "AWS",
        "sa": ["ServiceAccount", "eks.amazonaws.com/role-arn"],
        "hook": ["EKS mutating webhook", "injects IRSA env"],
        "kubelet": ["kubelet", "issues · refreshes"],
        "pod": "Pod · AWS SDK",
        "sts": ["AWS STS (regional)", "AssumeRoleWithWebIdentity"],
        "prov": ["IAM OIDC provider", "registered in the account"],
        "iss": ["OIDC issuer", "cluster keys"],
        "role": "IRSA role · trust policy conditions",
        "role_rows": ["aud = sts.amazonaws.com", "sub = system:serviceaccount:<ns>:<sa>"],
        "inj": ["webhook injects", "env AWS_ROLE_ARN", "env AWS_WEB_IDENTITY_TOKEN_FILE",
                "projected token volume", "/var/run/secrets/eks.amazonaws.com/", "serviceaccount/token"],
        "tok": ["projected token claims", "aud  sts.amazonaws.com", "iss  cluster OIDC issuer",
                "sub  system:serviceaccount:", "       <ns>:<sa>"],
        "token": "aud · sub",
        "req_tag": "token → STS",
        "sig": "signature ✓",
        "ret": "IRSA role credentials",
        "steps": [
            "① Pod created: the webhook reads the role-arn annotation, injects two env vars and a projected token volume",
            "② kubelet issues and refreshes the token: aud sts.amazonaws.com · iss cluster OIDC issuer · sub ServiceAccount",
            "③ The SDK sends the token to regional AWS STS AssumeRoleWithWebIdentity",
            "④ STS checks the signature with the issuer keys via the IAM OIDC provider, then the trust policy aud · sub",
            "⑤ Temporary IRSA role credentials return to the SDK",
        ],
        "hint": "Blue tag: the token (aud · sub) · green key: returned credentials",
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


TOKEN = ('<path class="rq" d="M-40 -10 l68 0 l10 10 l-10 10 l-68 0 z"/>'
         '<circle class="rql" cx="-33" cy="0" r="3"/>'
         '<text class="tag bl" x="-2" y="4" text-anchor="middle" style="font-size:11px">aud · sub</text>')


SMALL_ENVELOPE = ('<path class="rq" d="M-12 -8 l24 0 l0 16 l-24 0 z"/>'
                  '<path class="rql" d="M-12 -8 l12 9 l12 -9"/>')


def band(g, pts, vertical=False):
    """Two pen lines per cable, as in the prototype."""
    for o in (-2.5, 2.5):
        if vertical:
            g.append(f'<path class="cable" d="{c([(x + o, y) for x, y in pts])}"/>')
        else:
            g.append(f'<path class="cable" d="{c([(x, y + o) for x, y in pts])}"/>')


def note_box(x, y, w, h, lines, size=12.5):
    """Thin pen box: bold blue header line, then rows."""
    r = [f'<path class="thin" filter="url(#pen)" d="M{x} {y} l{w} 0 l0 {h} l-{w} 0 z"/>']
    r.append(f'<text class="s bl" x="{x+10}" y="{y+17}" font-weight="700">{esc(lines[0])}</text>')
    for i, line in enumerate(lines[1:]):
        fits(line, size, w - 16)
        r.append(f'<text class="row" x="{x+10}" y="{y+34+i*14}" style="font-size:{size - 0.5}px">{esc(line)}</text>')
    return "".join(r)


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    steps_t = [(T["sa"], T["a_end"]), (T["kube"], T["b_end"]), (T["req_on"], T["c_end"]),
               (T["sts"], T["d_end"]), (T["ret_on"], T["e_end"])]
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="t d" font-family="Pretendard, \'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Noto Sans CJK KR\', \'Malgun Gothic\', \'Segoe UI\', sans-serif">')
    o.append(f'<title id="t">{esc(k["title"])}</title><desc id="d">{esc(k["desc"])}</desc>')
    o.append(STYLE)
    o.append(PEN)
    o.append(f'<rect class="paper" width="{W}" height="{H}"/>')
    o.append(f'<text class="h" x="32" y="40">{esc(k["title"])}</text>')

    cards = [(SA, k["sa"]), (HOOK, k["hook"]), (KUBELET, k["kubelet"]), (STS, k["sts"]),
             (PROVIDER, k["prov"]), (ISSUER, k["iss"])]
    for (cx, cy, w), lines in cards:
        fits(lines[0], 13.5, w - 12, bold=True)
        fits(lines[1], 12.5, w - 12)
    rx, ry, rw, rh = ROLE
    fits(k["role"], 13.5, rw - 60, bold=True)

    # --- drawing (pen-wobbled) ---
    g = ['<g filter="url(#pen)">']
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*CLUSTER_BOX)}"/>')
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*AWS_BOX)}"/>')
    for pts, vertical in ((SA_HOOK, True), (HOOK_POD, False), (KUBE_POD, True), (POD_STS, False),
                          (STS_PROV, True), (PROV_ISS, False), (STS_ROLE, True)):
        band(g, pts, vertical)
    for (cx, cy, w), _ in cards:
        g.append(f'<path class="ink" d="{box_d(cx, cy, w, CARD_H)}"/>')
    g.append(f'<path class="ink" d="{box_d(rx, ry, rw, rh)}"/>')
    bx, by = rx - rw // 2 + 4, ry - rh // 2 - 6
    g.append(f'<path class="thin" d="M{bx} {by} l14 0 l0 11 l-14 0 z M{bx+4} {by+4} l6 0 M{bx+4} {by+7} l4 0"/>')
    px, py = POD
    g.append(f'<path class="ink" d="M{px-POD_W//2} {py-POD_H//2} l{POD_W} 1 l-1 {POD_H-1} l-{POD_W-1} -1 z"/>')
    g.append(f'<path class="thin" d="M{px-18} {py-14} l36 0 l0 28 l-36 0 z"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    cx0, cy0b, cw, ch = CLUSTER_BOX
    ax, ay, aw, ah = AWS_BOX
    o.append(f'<text class="s" x="{cx0+cw-12}" y="{cy0b+ch-10}" text-anchor="end" font-weight="700">{esc(k["cluster"])}</text>')
    o.append(f'<text class="s" x="{ax+aw-12}" y="{ay+ah-10}" text-anchor="end" font-weight="700">{esc(k["aws"])}</text>')
    for (cx, cy, w), lines in cards:
        card_text(o, cx, cy, lines)
    o.append(f'<text class="t" x="{px+10}" y="{POD_B+22}" font-weight="600" style="font-size:13.5px">{esc(k["pod"])}</text>')
    o.append(f'<text class="t" x="{rx - rw//2 + 26}" y="{ry - 13}" font-weight="600" style="font-size:13.5px">{esc(k["role"])}</text>')
    role_rows_y = [ry + 8, ry + 27]
    for yy, row in zip(role_rows_y, k["role_rows"]):
        fits(row, 13, rw - 60)
        o.append(f'<text class="row" x="{rx - rw//2 + 26}" y="{yy}" style="font-size:13px">{esc(row)}</text>')

    ix, iy, iw, ih = INJ_NOTE
    tx, ty, tw_, th = TOK_NOTE
    inj = note_box(ix, iy, iw, ih, [k["inj"][0], k["inj"][1], k["inj"][2], "vol " + k["inj"][4], k["inj"][5]])
    tok = note_box(tx, ty, tw_, th, k["tok"])
    sig_x, sig_y = ISSUER[0], bottom(ISSUER) + 18
    sig = f'<text class="tag halo gr" x="{sig_x}" y="{sig_y}" text-anchor="middle">{esc(k["sig"])}</text>'

    def check(yy):
        x = rx + rw // 2 - 26
        return f'<path class="okl" d="M{x} {yy-5} l5 5 l9 -11"/>'

    # --- motion layer ---
    m = ['<g class="motion">']

    def hl(d, start, end):
        return (f'<g opacity="0">{win(start, end, fade=0.2)}'
                f'<path class="trunk" style="stroke-width:3px" d="{d}"/></g>')

    pod_d = f"M{px-POD_W//2} {py-POD_H//2} l{POD_W} 1 l-1 {POD_H-1} l-{POD_W-1} -1 z"
    m.append(hl(box_d(SA[0], SA[1], SA[2], CARD_H), T["sa"], T["hook"] + 0.2))
    m.append(hl(box_d(HOOK[0], HOOK[1], HOOK[2], CARD_H), T["hook"], T["inj_in"]))
    m.append(hl(pod_d, T["inj_in"], T["a_end"]))
    m.append(hl(box_d(KUBELET[0], KUBELET[1], KUBELET[2], CARD_H), T["kube"], T["b_end"]))
    m.append(hl(box_d(STS[0], STS[1], STS[2], CARD_H), T["sts"], T["d_end"]))
    m.append(hl(box_d(PROVIDER[0], PROVIDER[1], PROVIDER[2], CARD_H), T["prov"], T["role"]))
    m.append(hl(box_d(ISSUER[0], ISSUER[1], ISSUER[2], CARD_H), T["iss"], T["role"]))
    m.append(hl(box_d(rx, ry, rw, rh), T["role"], T["d_end"]))
    m.append(hl(pod_d, T["ret_in"], T["e_end"] + 0.3))

    # persistent notes and checks (stay until the loop resets)
    m.append(f'<g opacity="0">{win(T["note"], T["hold"], fade=0.3)}{inj}</g>')
    m.append(f'<g opacity="0">{win(T["kube"] + 0.3, T["hold"], fade=0.3)}{tok}</g>')
    m.append(f'<g opacity="0">{win(T["sig"], T["hold"], fade=0.2)}{sig}</g>')
    m.append(f'<g opacity="0">{win(T["aud"], T["hold"], fade=0.2)}{check(role_rows_y[0])}</g>')
    m.append(f'<g opacity="0">{win(T["sub"], T["hold"], fade=0.2)}{check(role_rows_y[1])}</g>')

    def pulse(d, keys, on, off, glyph, tags=()):
        r = ['<g>', win(on, off, fade=0.15), move(d, keys), glyph]
        for text, s0, s1, cls, ty_ in tags:
            r.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                     f'<text class="tag halo {cls}" x="0" y="{ty_}" text-anchor="middle">{esc(text)}</text></g>')
        r.append('</g>')
        return "".join(r)

    # a. webhook mutates the Pod spec
    m.append(pulse(INJ_D, [(0, 0), (T["inj_go"], 0), (T["inj_in"], 1), (DUR, 1)],
                   T["inj_go"] - 0.1, T["inj_in"], SMALL_ENVELOPE))
    # b. kubelet writes the token into the Pod
    m.append(pulse(KUBE_D, [(0, 0), (T["tok_go"], 0), (T["tok_in"], 1), (DUR, 1)],
                   T["tok_go"] - 0.1, T["tok_in"], TOKEN))
    # c. SDK sends the token to STS
    m.append(pulse(REQ_D, [(0, 0), (T["req_go"], 0), (T["req_in"], 1), (DUR, 1)],
                   T["req_on"], T["req_in"] + 0.1, TOKEN,
                   [(k["req_tag"], T["req_go"] + 0.2, T["req_in"] - 0.1, "bl", -18)]))
    # e. temporary credentials come back
    m.append(pulse(RET_D, [(0, 0), (T["ret_go"], 0), (T["ret_in"], 1), (DUR, 1)],
                   T["ret_on"], T["hold"], KEY,
                   [(k["ret"], T["ret_on"], T["e_end"] + 0.6, "gr", -18)]))

    # captions
    cy0 = 378
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
    st = ['<g class="static">', inj, tok, sig, check(role_rows_y[0]), check(role_rows_y[1])]
    st.append(f'<g transform="translate({(POD_R + left(STS)) // 2} {POD[1]})">{TOKEN}</g>')
    st.append(f'<g transform="translate({POD_R} {POD[1] + 0})">{KEY}</g>')
    for (x, y, label) in ((right(HOOK) + 10, HOOK[1] - 16, "①"), (KUBELET[0] - KUBELET[2] // 2 - 4, KUBELET[1] - 30, "②"),
                          ((POD_R + left(STS)) // 2 - 8, POD[1] - 22, "③"), (STS[0] + STS[2] // 2 + 6, STS[1] - 26, "④"),
                          (POD_R + 30, POD[1] + 24, "⑤")):
        st.append(f'<text class="tag halo bl" x="{x}" y="{y}" style="font-size:16px">{label}</text>')
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
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-security-17-eks-workload-identity-migration-anim-1.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-security-17-eks-workload-identity-migration-anim-1.svg")
        svg = build(lang)
        check_output(svg)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok")
