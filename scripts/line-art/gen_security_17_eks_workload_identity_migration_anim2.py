#!/usr/bin/env python3
"""Line-art animated SVG: EKS Pod Identity in detail (association, Agent, EKS Auth).

Same house style and helpers as gen_security_17_eks_workload_identity_migration_anim0.py
(copied from gen_basics_06_part5_anim0.py and gen 09): palette tokens plus one
--green token for returned credentials, pen filter, stroke classes, font
stack, caption layout, packet tags, ko/en COPY, anim()/win()/move() on one
shared SMIL clock with the keyTimes self-check. CSS only handles palette
(light/dark) and the reduced-motion static view.

Story:
a. A Pod Identity association in the EKS API maps cluster + namespace +
   ServiceAccount to an IAM role (no annotation, no OIDC provider).
b. On Pod creation EKS injects AWS_CONTAINER_CREDENTIALS_FULL_URI
   (http://169.254.170.23/v1/credentials), AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
   and a projected token at
   /var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token
   (audience pods.eks.amazonaws.com).
c. The SDK calls the Pod Identity Agent (hostNetwork DaemonSet, link-local
   169.254.170.23) on the same node.
d. The Agent calls EKS Auth AssumeRoleForPodIdentity with the node role's
   eks-auth:AssumeRoleForPodIdentity permission (AmazonEKSWorkerNodePolicy).
e. EKS Auth validates the token, finds the association, assumes the role
   (trust principal pods.eks.amazonaws.com, sts:AssumeRole + sts:TagSession)
   and attaches session tags (eks-cluster-arn, kubernetes-namespace,
   kubernetes-service-account).
f. Credentials return via the Agent to the SDK.
The node role only lets the Agent call EKS Auth; the app permission lives on
the Pod Identity role.
"""
import math
import sys

DUR = 18.0  # seconds per loop
W, H = 960, 500

# ---------- geometry ----------------------------------------------------------
CARD_H = 46
POD = (110, 200)                     # Pod glyph centre (80 x 60)
POD_W, POD_H = 80, 60
AGENT = (340, 200, 190, 62)          # centre x, centre y, width, height
NODE_ROLE = (340, 306, 250, 62)
ASSOC = (725, 100, 400, 62)
AUTH = (622, 200, 200, 46)
PID_ROLE = (842, 200, 166, 46)
TRUST = (522, 256, 406, 88)          # x, y, w, h: trust policy + session tags note
INJ_NOTE = (30, 62, 458, 96)
NODE_BOX = (24, 58, 470, 300)
AWS_BOX = (512, 58, 426, 300)

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
    return card[1] - card[3] // 2


def bottom(card):
    return card[1] + card[3] // 2


def vwig(x, y0, y1, amp=8):
    dy = y1 - y0
    return [(x, y0), (x - amp, round(y0 + dy * 0.33)), (x + amp, round(y0 + dy * 0.66)), (x, y1)]


POD_R = POD[0] + POD_W // 2
Y = POD[1]
POD_AGENT = wig(POD_R, left(AGENT), Y, 8)
AGENT_AUTH = wig(right(AGENT), left(AUTH), Y, -8)
ROLE_AGENT = vwig(NODE_ROLE[0], top(NODE_ROLE), bottom(AGENT))
AUTH_ASSOC = vwig(AUTH[0], top(AUTH), bottom(ASSOC))
AUTH_ROLE = wig(right(AUTH), left(PID_ROLE), Y, 5)
ROLE_TRUST = vwig(PID_ROLE[0], bottom(PID_ROLE), TRUST[1])

# Request: Pod -> Agent (dwell at its left edge, hidden while crossing) -> EKS Auth.
REQ_D, REQ_F = motion([("bez", POD_AGENT), ("line", [(left(AGENT), Y), (right(AGENT), Y)]),
                       ("bez", AGENT_AUTH)])
RET_D, RET_F = motion(reverse([("bez", POD_AGENT), ("line", [(left(AGENT), Y), (right(AGENT), Y)]),
                               ("bez", AGENT_AUTH)]))

# Timeline (seconds)
T = {
    "assoc": 0.3, "a_end": 2.4,
    "inj": 2.6, "b_end": 4.4,
    "req_on": 4.6, "req_go": 4.8, "req_agent": 5.6, "req_agent_go": 6.0, "req_thr": 6.2,
    "c_end": 6.0,
    "node_role": 6.2, "req_auth": 7.4, "d_end": 7.6,
    "auth": 7.8, "valid": 8.2, "lookup": 8.6, "assume": 9.4, "tags": 9.9, "e_end": 11.0,
    "ret_on": 11.1, "ret_go": 11.3, "ret_agent": 12.2, "ret_agent_go": 12.6, "ret_thr": 12.8,
    "ret_home": 13.6, "f_end": 14.0,
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
        "title": "EKS Pod Identity: Agent와 EKS Auth가 association으로 역할을 넘겨준다",
        "desc": ("EKS API의 Pod Identity association이 클러스터, 네임스페이스, ServiceAccount를 IAM 역할에 매핑한다. "
                 "ServiceAccount 주석도 IAM OIDC provider도 필요 없다. Pod가 생성되면 EKS가 env "
                 "AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials와 "
                 "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE, 그리고 "
                 "/var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token 경로의 projected 토큰"
                 "(audience pods.eks.amazonaws.com)을 주입한다. SDK는 같은 노드에서 hostNetwork DaemonSet으로 도는 Pod "
                 "Identity Agent(링크 로컬 169.254.170.23)를 부른다. Agent는 AmazonEKSWorkerNodePolicy가 주는 노드 역할의 "
                 "eks-auth:AssumeRoleForPodIdentity 권한으로 EKS Auth AssumeRoleForPodIdentity를 호출한다. EKS Auth는 토큰을 "
                 "검증하고 association을 찾아, 신뢰 주체가 pods.eks.amazonaws.com이고 sts:AssumeRole과 sts:TagSession을 허용하는 "
                 "역할을 위임받으며 eks-cluster-arn, kubernetes-namespace, kubernetes-service-account 같은 세션 태그를 붙인다. "
                 "자격 증명은 Agent를 거쳐 SDK로 돌아온다. 노드 역할은 Agent가 EKS Auth를 호출하게만 하고, 앱 권한은 Pod "
                 "Identity 역할에 있다."),
        "node": "워커 노드",
        "aws": "AWS",
        "pod": "Pod · AWS SDK",
        "agent": ["Pod Identity Agent", "169.254.170.23", "hostNetwork DaemonSet"],
        "node_role": ["노드 역할", "eks-auth:AssumeRoleForPodIdentity", "Agent → EKS Auth 호출만"],
        "assoc": ["EKS API · Pod Identity association", "클러스터 + 네임스페이스 + ServiceAccount → IAM 역할",
                  "주석 없음 · OIDC provider 없음"],
        "auth": ["EKS Auth", "AssumeRoleForPodIdentity"],
        "pid_role": ["Pod Identity 역할", "앱 권한 (S3 읽기)"],
        "trust": ["역할 신뢰 정책 · 세션 태그", "신뢰 주체 pods.eks.amazonaws.com",
                  "동작 sts:AssumeRole · sts:TagSession",
                  "태그 eks-cluster-arn · kubernetes-namespace ·", "       kubernetes-service-account"],
        "inj": ["Pod 생성 시 EKS가 주입", "env AWS_CONTAINER_CREDENTIALS_FULL_URI",
                "       = http://169.254.170.23/v1/credentials", "env AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
                "vol /var/run/secrets/pods.eks.amazonaws.com/serviceaccount/",
                "       eks-pod-identity-token · aud pods.eks.amazonaws.com"],
        "req": "Pod 토큰",
        "req2": "노드 역할로 호출",
        "valid": "토큰 ✓",
        "found": "찾음 ✓",
        "ret": "Pod Identity 역할 임시 자격 증명",
        "steps": [
            "① association: EKS API가 클러스터 + 네임스페이스 + ServiceAccount를 IAM 역할에 매핑한다",
            "② Pod 생성: EKS가 env 두 개와 projected 토큰(aud pods.eks.amazonaws.com)을 주입한다",
            "③ SDK가 같은 노드의 Pod Identity Agent(169.254.170.23)를 부른다",
            "④ Agent는 노드 역할의 eks-auth 권한으로 EKS Auth를 호출한다: 노드 역할엔 앱 권한이 없다",
            "⑤ EKS Auth: 토큰 검증 → association 조회 → 역할 위임 + 세션 태그 → Agent를 거쳐 SDK로",
        ],
        "hint": "파란 봉투: 요청 · 초록 열쇠: 돌아온 자격 증명",
    },
    "en": {
        "title": "EKS Pod Identity: the Agent and EKS Auth hand over the role by association",
        "desc": ("A Pod Identity association in the EKS API maps the cluster, namespace and ServiceAccount to an IAM role; "
                 "no ServiceAccount annotation and no IAM OIDC provider are involved. When the Pod is created, EKS "
                 "injects AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials, "
                 "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE and a projected token at "
                 "/var/run/secrets/pods.eks.amazonaws.com/serviceaccount/eks-pod-identity-token with audience "
                 "pods.eks.amazonaws.com. The SDK calls the Pod Identity Agent, a hostNetwork DaemonSet on the same node "
                 "at link-local 169.254.170.23. The Agent calls EKS Auth AssumeRoleForPodIdentity using the node role's "
                 "eks-auth:AssumeRoleForPodIdentity permission from AmazonEKSWorkerNodePolicy. EKS Auth validates the "
                 "token, finds the association, assumes the role, whose trust principal is pods.eks.amazonaws.com with "
                 "sts:AssumeRole and sts:TagSession, and attaches session tags such as eks-cluster-arn, "
                 "kubernetes-namespace and kubernetes-service-account. Credentials return through the Agent to the SDK. "
                 "The node role only lets the Agent call EKS Auth; the app permission lives on the Pod Identity role."),
        "node": "Worker node",
        "aws": "AWS",
        "pod": "Pod · AWS SDK",
        "agent": ["Pod Identity Agent", "169.254.170.23", "hostNetwork DaemonSet"],
        "node_role": ["Node role", "eks-auth:AssumeRoleForPodIdentity", "only lets the Agent call EKS Auth"],
        "assoc": ["EKS API · Pod Identity association", "cluster + namespace + ServiceAccount → IAM role",
                  "no annotation · no OIDC provider"],
        "auth": ["EKS Auth", "AssumeRoleForPodIdentity"],
        "pid_role": ["Pod Identity role", "app permission (S3 read)"],
        "trust": ["Role trust policy · session tags", "principal pods.eks.amazonaws.com",
                  "actions sts:AssumeRole · sts:TagSession",
                  "tags eks-cluster-arn · kubernetes-namespace ·", "        kubernetes-service-account"],
        "inj": ["EKS injects at Pod creation", "env AWS_CONTAINER_CREDENTIALS_FULL_URI",
                "       = http://169.254.170.23/v1/credentials", "env AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
                "vol /var/run/secrets/pods.eks.amazonaws.com/serviceaccount/",
                "       eks-pod-identity-token · aud pods.eks.amazonaws.com"],
        "req": "Pod token",
        "req2": "signed as node role",
        "valid": "token ✓",
        "found": "found ✓",
        "ret": "Pod Identity role credentials",
        "steps": [
            "① Association: the EKS API maps cluster + namespace + ServiceAccount to an IAM role",
            "② Pod created: EKS injects two env vars and a projected token (aud pods.eks.amazonaws.com)",
            "③ The SDK calls the Pod Identity Agent on the same node (169.254.170.23)",
            "④ The Agent calls EKS Auth with the node role's eks-auth permission; the node role has no app permission",
            "⑤ EKS Auth: validate token → find association → assume role + session tags → back via the Agent",
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
        fits(line, size - 0.5, w - 16)
        r.append(f'<text class="row" x="{x+10}" y="{y+34+i*14}" xml:space="preserve" '
                 f'style="font-size:{size - 0.5}px">{esc(line)}</text>')
    return "".join(r)


def card3(o, card, lines):
    """Card text: bold title, then one or two small lines."""
    cx, cy, w, h = card
    fits(lines[0], 13.5, w - 12, bold=True)
    y0 = cy - (h // 2) + 20
    o.append(f'<text class="t" x="{cx}" y="{y0}" text-anchor="middle" font-weight="600" '
             f'style="font-size:13.5px">{esc(lines[0])}</text>')
    for i, line in enumerate(lines[1:]):
        fits(line, 12.5, w - 12)
        o.append(f'<text class="s" x="{cx}" y="{y0 + 17 + i * 15}" text-anchor="middle">{esc(line)}</text>')


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    steps_t = [(T["assoc"], T["a_end"]), (T["inj"], T["b_end"]), (T["req_on"], T["c_end"]),
               (T["node_role"], T["d_end"]), (T["auth"], T["f_end"])]
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="t d" font-family="Pretendard, \'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Noto Sans CJK KR\', \'Malgun Gothic\', \'Segoe UI\', sans-serif">')
    o.append(f'<title id="t">{esc(k["title"])}</title><desc id="d">{esc(k["desc"])}</desc>')
    o.append(STYLE)
    o.append(PEN)
    o.append(f'<rect class="paper" width="{W}" height="{H}"/>')
    o.append(f'<text class="h" x="32" y="40">{esc(k["title"])}</text>')
    fits(k["title"], 17, W - 64, bold=True)

    cards = [(AGENT, k["agent"]), (NODE_ROLE, k["node_role"]), (ASSOC, k["assoc"]),
             (AUTH, k["auth"]), (PID_ROLE, k["pid_role"])]

    # --- drawing (pen-wobbled) ---
    g = ['<g filter="url(#pen)">']
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*NODE_BOX)}"/>')
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*AWS_BOX)}"/>')
    for pts, vertical in ((POD_AGENT, False), (AGENT_AUTH, False), (ROLE_AGENT, True),
                          (AUTH_ASSOC, True), (AUTH_ROLE, False), (ROLE_TRUST, True)):
        band(g, pts, vertical)
    for card, _ in cards:
        g.append(f'<path class="ink" d="{box_d(*card)}"/>')
    for card in (NODE_ROLE, PID_ROLE):  # IAM role badge
        bx, by = left(card) + 4, top(card) - 6
        g.append(f'<path class="thin" d="M{bx} {by} l14 0 l0 11 l-14 0 z M{bx+4} {by+4} l6 0 M{bx+4} {by+7} l4 0"/>')
    px, py = POD
    g.append(f'<path class="ink" d="M{px-POD_W//2} {py-POD_H//2} l{POD_W} 1 l-1 {POD_H-1} l-{POD_W-1} -1 z"/>')
    g.append(f'<path class="thin" d="M{px-18} {py-14} l36 0 l0 28 l-36 0 z"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    nx, ny, nw, nh = NODE_BOX
    ax, ay, aw, ah = AWS_BOX
    o.append(f'<text class="s" x="{nx+14}" y="{ny+nh-10}" font-weight="700">{esc(k["node"])}</text>')
    o.append(f'<text class="s" x="{ax+aw-12}" y="{ay-6}" text-anchor="end" font-weight="700">{esc(k["aws"])}</text>')
    for card, lines in cards:
        card3(o, card, lines)
    o.append(f'<text class="t" x="{px}" y="{py + POD_H // 2 + 20}" text-anchor="middle" font-weight="600" '
             f'style="font-size:13.5px">{esc(k["pod"])}</text>')

    ix, iy, iw, ih = INJ_NOTE
    tx, ty, tw_, th = TRUST
    inj = note_box(ix, iy, iw, ih, k["inj"])
    trust = note_box(tx, ty, tw_, th, k["trust"])
    valid = (f'<text class="tag halo gr" x="{left(AUTH) + 8}" y="{top(AUTH) - 8}">{esc(k["valid"])}</text>')
    found = (f'<text class="tag halo gr" x="{AUTH[0] + 14}" y="{bottom(ASSOC) + 22}">{esc(k["found"])}</text>')

    # --- motion layer ---
    m = ['<g class="motion">']

    def hl(d, start, end, cls="trunk"):
        return (f'<g opacity="0">{win(start, end, fade=0.2)}'
                f'<path class="{cls}" style="stroke-width:3px" d="{d}"/></g>')

    pod_d = f"M{px-POD_W//2} {py-POD_H//2} l{POD_W} 1 l-1 {POD_H-1} l-{POD_W-1} -1 z"
    m.append(hl(box_d(*ASSOC), T["assoc"], T["a_end"]))
    m.append(hl(pod_d, T["inj"], T["b_end"]))
    m.append(hl(box_d(*AGENT), T["req_agent"], T["req_agent_go"] + 0.1))
    m.append(hl(box_d(*NODE_ROLE), T["node_role"], T["d_end"]))
    m.append(hl(box_d(*AUTH), T["auth"], T["e_end"]))
    m.append(hl(box_d(*ASSOC), T["lookup"], T["assume"]))
    m.append(hl(box_d(*PID_ROLE), T["assume"], T["e_end"]))
    m.append(hl(f"M{tx} {ty} l{tw_} 0 l0 {th} l-{tw_} 0 z", T["tags"], T["e_end"]))
    m.append(hl(box_d(*AGENT), T["ret_agent"], T["ret_agent_go"] + 0.1))

    # persistent notes (stay until the loop resets)
    m.append(f'<g opacity="0">{win(T["inj"] + 0.2, T["hold"], fade=0.3)}{inj}</g>')
    m.append(f'<g opacity="0">{win(T["assume"], T["hold"], fade=0.3)}{trust}</g>')
    m.append(f'<g opacity="0">{win(T["valid"], T["hold"], fade=0.2)}{valid}</g>')
    m.append(f'<g opacity="0">{win(T["lookup"] + 0.3, T["hold"], fade=0.2)}{found}</g>')

    def pulse(d, keys, windows, glyph, tags=()):
        r = ['<g>', vis(windows), move(d, keys), glyph]
        for text, s0, s1, cls, ty_ in tags:
            r.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                     f'<text class="tag halo {cls}" x="0" y="{ty_}" text-anchor="middle">{esc(text)}</text></g>')
        r.append('</g>')
        return "".join(r)

    f = REQ_F
    m.append(pulse(REQ_D, [(0, 0), (T["req_go"], 0), (T["req_agent"], f[1]), (T["req_agent_go"], f[1]),
                           (T["req_thr"], f[2]), (T["req_auth"], 1), (DUR, 1)],
                   [(T["req_on"], T["req_agent_go"]), (T["req_thr"], T["req_auth"] + 0.1)], ENVELOPE,
                   [(k["req"], T["req_go"] + 0.2, T["req_agent_go"] - 0.1, "bl", 42),
                    (k["req2"], T["req_thr"], T["req_auth"], "bl", 42)]))
    f = RET_F
    m.append(pulse(RET_D, [(0, 0), (T["ret_go"], 0), (T["ret_agent"], f[1]), (T["ret_agent_go"], f[1]),
                           (T["ret_thr"], f[2]), (T["ret_home"], 1), (DUR, 1)],
                   [(T["ret_on"], T["ret_agent_go"]), (T["ret_thr"], T["hold"])], KEY,
                   [(k["ret"], T["ret_on"], T["ret_agent_go"], "gr", 42)]))

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
    st = ['<g class="static">', inj, trust, valid, found]
    st.append(f'<g transform="translate({(right(AGENT) + left(AUTH)) // 2} {Y})">{ENVELOPE}</g>')
    st.append(f'<g transform="translate({POD_R} {Y})">{KEY}</g>')
    for (x, y, label) in ((right(ASSOC) - 22, top(ASSOC) + 18, "①"), (ix + iw - 24, iy + 18, "②"),
                          ((POD_R + left(AGENT)) // 2 - 6, Y - 18, "③"), (right(NODE_ROLE) - 22, top(NODE_ROLE) + 18, "④"),
                          (right(AUTH) - 22, top(AUTH) - 8, "⑤")):
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
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-security-17-eks-workload-identity-migration-anim-2.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-security-17-eks-workload-identity-migration-anim-2.svg")
        svg = build(lang)
        check_output(svg)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [round(x, 3) for x in REQ_F])
