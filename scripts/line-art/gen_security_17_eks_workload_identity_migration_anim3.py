#!/usr/bin/env python3
"""Line-art animated SVG: the migration, scene by scene, as the live demo runs it.

Same house style and helpers as gen_security_17_eks_workload_identity_migration_anim0.py
(copied from gen_basics_06_part5_anim0.py and gen 09): palette tokens plus one
--green token for allowed reads, pen filter, stroke classes, font stack,
caption layout, packet tags, ko/en COPY, anim()/win()/move() on one shared
SMIL clock with the keyTimes self-check. Denied is vermilion, drawn as gen 09
draws "blocked". CSS only handles palette (light/dark) and the reduced-motion
static view.
A tracking camera on the same clock follows the request in the motion
layer; the static view stays the unmoved overview (see the camera section).

Three copies of one app (orders-legacy, orders-irsa, orders-podid) on one node
read one S3 object (invoices/2026-11.txt, the object demo.sh creates).
1. up: all three get credentials from IMDS -> node role; the node role carries
   the app's s3:GetObject, so every read is allowed.
2. migrate-irsa: the ServiceAccount is annotated and the Deployment rolled out;
   the new orders-irsa Pod uses STS / the IRSA role.
3. migrate-podid: a Pod Identity association is created and the Deployment
   rolled out; the new orders-podid Pod uses the Agent / EKS Auth / the Pod
   Identity role.
4. revoke: the S3 policy is removed from the node role; orders-legacy's read
   is denied (AccessDenied), the other two keep reading.
"""
import math
import sys

DUR = 22.0  # seconds per loop
W, H = 960, 500

# ---------- geometry ----------------------------------------------------------
CARD_H = 46
RY = [124, 210, 296]                 # rows: legacy, irsa, podid
POD_X = 78
POD_R = 100
SRC = (380, 260)                     # credential source cards: centre x, width
BUCKET = (870, 210)
BUCKET_IN = [(836, 192), (836, 210), (836, 228)]
NODE_BOX = (24, 66, 200, 292)
POLICY = (540, 64, 390, 36)          # x, y, w, h: node role policy note
MARK_T = 0.40                        # where on each read cable the verdict sits
MARK_DY = [-9, -9, 21]               # verdict label offsets: clear of each cable

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



SRC_L = SRC[0] - SRC[1] // 2
SRC_R = SRC[0] + SRC[1] // 2
POD_SRC = [wig(POD_R, SRC_L, y, 8) for y in RY]
SRC_S3 = [[(SRC_R, y), (SRC_R + 120, y), (BUCKET_IN[i][0] - 140, BUCKET_IN[i][1]), BUCKET_IN[i]]
          for i, y in enumerate(RY)]
READ = [motion([("bez", POD_SRC[i]), ("line", [(SRC_L, y), (SRC_R, y)]), ("bez", SRC_S3[i])])
        for i, y in enumerate(RY)]
MARKS = [tuple(round(v) for v in bez(SRC_S3[i], MARK_T)) for i in range(3)]

# Timeline (seconds)
T = {
    "s1": 0.3, "s1_go": 0.8, "s1_in": 2.6, "s1_end": 4.2,
    "s2": 4.6, "s2_roll": 5.0, "s2_swap": 5.9, "s2_go": 6.6, "s2_in": 8.0, "s2_end": 9.0,
    "s3": 9.4, "s3_roll": 9.8, "s3_swap": 10.7, "s3_go": 11.4, "s3_in": 12.8, "s3_end": 13.8,
    "s4": 14.2, "strike": 14.6, "s4_go": 16.0, "s4_in": 17.4, "s4_end": 20.0,
    "hold": 20.4,
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


# ---------- camera ------------------------------------------------------------
# The view follows the request. The motion layer holds its own copy of the
# diagram inside a camera <g> that moves on the shared SMIL clock: translate +
# scale (additive="sum"), calcMode="spline", eased in and out. Paper bands
# outside VIEW mask the zoomed diagram (no clip-path: only url(#pen) is
# allowed, and a nested <svg> would get its own SMIL clock); the title,
# captions, hint and badges are drawn after them and never move. The static
# (reduced-motion) layer keeps an unmoved copy, so no camera exists there.
VIEW = (0, 46, 960, 324)             # camera viewport: x, y, w, h (title above, captions below)
OV = (VIEW[0] + VIEW[2] / 2, VIEW[1] + VIEW[3] / 2, 1.0)  # overview = identity
CAMS = []                            # every camera animation, validated before writing


def shot(x0, y0, x1, y1, zmax=1.8, pad=8):
    """Shot (cx, cy, zoom) framing the box plus pad, kept inside VIEW."""
    vx, vy, vw, vh = VIEW
    z = max(1.0, min(zmax, vw / (x1 - x0 + 2 * pad), vh / (y1 - y0 + 2 * pad)))
    hw, hh = vw / z / 2, vh / z / 2
    cx = min(max((x0 + x1) / 2, vx + hw), vx + vw - hw)
    cy = min(max((y0 + y1) / 2, vy + hh), vy + vh - hh)
    wx0, wy0, wx1, wy1 = cx - hw, cy - hh, cx + hw, cy + hh
    assert wx0 <= x0 and wy0 <= y0 and x1 <= wx1 and y1 <= wy1, ("box not in shot", (x0, y0, x1, y1))
    return (round(cx, 2), round(cy, 2), round(z, 4))


def camera(keys):
    """keys: [(seconds, shot[, "via"]), ...] from 0 to DUR. Equal neighbours hold; a move
    eases in and out, except through a "via" key, which it passes without stopping."""
    vx, vy, vw, vh = VIEW
    mx, my = vx + vw / 2, vy + vh / 2
    stop = [len(k) == 2 for k in keys]
    keys = [k[:2] for k in keys]
    ts = ";".join(kt(t) for t, _ in keys)
    num = lambda v: f"{v:.2f}".replace("-0.00", "0.00")
    tr = ";".join(f"{num(mx - z * cx)} {num(my - z * cy)}" for _, (cx, cy, z) in keys)
    sc = ";".join(f"{z:.4f}" for _, (cx, cy, z) in keys)
    ks = ";".join("0 0 1 1" if a == b else f"{0.42 if s0 else 0} 0 {0.58 if s1 else 1} 1"
                  for (_, a), (_, b), s0, s1 in zip(keys, keys[1:], stop, stop[1:]))
    CAMS.append((ts, tr, sc, ks, keys, stop))
    common = (f'dur="{DUR}s" repeatCount="indefinite" calcMode="spline" '
              f'keyTimes="{ts}" keySplines="{ks}"')
    return (f'<animateTransform attributeName="transform" type="translate" {common} values="{tr}"/>'
            f'<animateTransform attributeName="transform" type="scale" additive="sum" {common} values="{sc}"/>')


def check_camera():
    assert CAMS, "no camera"
    for ts, tr, sc, ks, keys, stop in CAMS:
        t = [float(x) for x in ts.split(";")]
        assert t[0] == 0 and t[-1] == 1 and all(0 <= x <= 1 for x in t), ts
        assert all(b > a for a, b in zip(t, t[1:])), ("camera keyTimes not monotonic", ts)
        trs, scs = tr.split(";"), sc.split(";")
        assert len(trs) == len(scs) == len(t) == len(ks.split(";")) + 1, ts
        assert keys[0][1] == keys[-1][1] == OV, "camera must start and end on the overview"
        assert trs[0] == trs[-1] == "0.00 0.00" and float(scs[0]) == float(scs[-1]) == 1.0, (trs[0], scs[0])
        assert all(1.0 <= z <= 2.0 for _, (_, _, z) in keys), "zoom out of range"
        assert stop[0] and stop[-1], "the loop starts and ends on a stop"
        segs = list(zip(keys, keys[1:]))
        move0 = None
        for i, ((t0, a), (t1, b)) in enumerate(segs):
            if a != b:  # a move runs from one stop to the next, maybe through "via" keys
                move0 = t0 if stop[i] else move0
                if stop[i + 1]:
                    assert 0.8 - 1e-6 <= t1 - move0 <= 1.5 + 1e-6, ("camera move must take 0.8-1.5 s", move0, t1)
            else:
                assert stop[i] and stop[i + 1], ("a hold cannot touch a via key", t0)
                if 0 < i < len(segs) - 1:
                    assert t1 - t0 >= 0.6 - 1e-6, ("camera hold must last at least 0.6 s", t0, t1)
        seam = (segs[0][1][0] - segs[0][0][0]) + (segs[-1][1][0] - segs[-1][0][0])
        assert segs[0][0][1] == segs[0][1][1] == segs[-1][0][1] and seam >= 1.0, "overview beat across the seam"


BANDS = (f'<rect class="paper" width="{W}" height="{VIEW[1]}"/>'
         f'<rect class="paper" y="{VIEW[1] + VIEW[3]}" width="{W}" height="{H - VIEW[1] - VIEW[3]}"/>')


# Camera script: scene 1 plays on the overview (all three rows move at once);
# scenes 2 and 3 push in on the row that rolls out and follow its read to the
# bucket; scene 4 frames the struck node role policy, pulls back for the three
# verdicts, then returns to read AccessDenied beside the struck policy.
# Vertical edges are placed in the gaps between card text lines, and the
# bucket-side shots start right of the card text, so held frames cut no text.
CAM_S2A = shot(0, 125, 518, 300, 2.0, pad=0)     # row 2: rollout at the Pod, card swap
CAM_S2B = shot(480, 125, 960, 287, 2.0, pad=0)   # row 2: read reaches the bucket
CAM_S3A = shot(0, 195, 518, 370, 2.0, pad=0)     # row 3: rollout at the Pod, card swap
CAM_S3B = shot(480, 190, 960, 352, 2.0, pad=0)   # row 3: read reaches the bucket
CAM_S4 = shot(480, 58, 960, 220, 2.0, pad=0)     # struck policy, row 1 denied, row 2 allowed
CAM_KEYS = [
    (0, OV), (4.6, OV),                  # up: all three read through the node role
    (5.6, CAM_S2A), (6.8, CAM_S2A),      # migrate-irsa rollout
    (7.8, CAM_S2B), (9.0, CAM_S2B),      # its read is allowed
    (10.2, CAM_S3A), (11.6, CAM_S3A),    # migrate-podid rollout
    (12.6, CAM_S3B), (13.4, CAM_S3B),    # its read is allowed
    (14.4, CAM_S4), (15.0, CAM_S4),      # revoke strikes the node role policy
    (16.0, OV), (18.0, OV),              # three reads: one denied, two allowed
    (19.0, CAM_S4), (19.8, CAM_S4),      # AccessDenied next to the struck policy
    (20.8, OV), (DUR, OV),               # overview beat
]

# ---------- copy --------------------------------------------------------------
COPY = {
    "ko": {
        "title": "마이그레이션 데모: 노드 역할에서 IRSA와 Pod Identity로",
        "desc": ("한 노드에서 같은 앱의 복사본 세 개(orders-legacy, orders-irsa, orders-podid)가 S3 객체 하나를 읽는다. "
                 "시작(up)에는 세 복사본 모두 IMDS를 거쳐 노드 역할 자격 증명을 쓰고, 노드 역할에 앱의 s3:GetObject가 있어 "
                 "읽기가 모두 허용된다. migrate-irsa에서는 ServiceAccount에 주석을 달고 rollout하므로 orders-irsa의 새 Pod가 "
                 "STS를 거쳐 IRSA 역할을 쓴다. migrate-podid에서는 Pod Identity association을 만들고 rollout하므로 "
                 "orders-podid의 새 Pod가 Pod Identity Agent와 EKS Auth를 거쳐 Pod Identity 역할을 쓴다. revoke에서 노드 역할의 "
                 "S3 정책을 지우면 orders-legacy의 읽기는 AccessDenied로 거부되고, 나머지 두 복사본은 계속 읽는다."),
        "node": "노드 1대",
        "col": "자격 증명 출처",
        "pods": ["orders-legacy", "orders-irsa", "orders-podid"],
        "node_src": ["노드 역할", "IMDSv2 169.254.169.254"],
        "irsa_src": ["IRSA 역할", "STS AssumeRoleWithWebIdentity"],
        "podid_src": ["Pod Identity 역할", "Agent → EKS Auth"],
        "bucket": ["S3 객체", "invoices/2026-11.txt"],
        "policy": "노드 역할 정책: s3:GetObject (앱 권한)",
        "revoked": "revoke로 삭제",
        "strike": 0.88,  # strike-through length vs the rough width estimate (checked in frames)
        "irsa_do": "SA 주석 + rollout",
        "podid_do": "association + rollout",
        "ok": "200 OK",
        "deny": "AccessDenied",
        "scenes": ["① up", "② migrate-irsa", "③ migrate-podid", "④ revoke"],
        "steps": [
            "① up (시작): 세 복사본 모두 IMDS → 노드 역할 · 노드 역할에 s3:GetObject가 있어 읽기 허용",
            "② migrate-irsa: ServiceAccount 주석 + rollout → orders-irsa의 새 Pod는 STS · IRSA 역할",
            "③ migrate-podid: association 생성 + rollout → orders-podid의 새 Pod는 Pod Identity 역할",
            "④ revoke: 노드 역할의 S3 정책 삭제 → orders-legacy는 AccessDenied, 나머지 둘은 계속 읽는다",
        ],
        "hint": "파란 봉투: S3 읽기 요청 · 초록 ✓ 허용 · 주황 × 거부",
    },
    "en": {
        "title": "The migration demo: from the node role to IRSA and Pod Identity",
        "desc": ("Three copies of one app (orders-legacy, orders-irsa, orders-podid) on one node read one S3 object. At "
                 "the start (up), all three get node role credentials through IMDS, and the node role carries the app's "
                 "s3:GetObject, so every read is allowed. In migrate-irsa the ServiceAccount is annotated and the "
                 "Deployment rolled out, so the new orders-irsa Pod uses the IRSA role through STS. In migrate-podid a "
                 "Pod Identity association is created and the Deployment rolled out, so the new orders-podid Pod uses "
                 "the Pod Identity role through the Pod Identity Agent and EKS Auth. In revoke the S3 policy is removed "
                 "from the node role: orders-legacy's read is denied with AccessDenied, and the other two keep reading."),
        "node": "One node",
        "col": "Credential source",
        "pods": ["orders-legacy", "orders-irsa", "orders-podid"],
        "node_src": ["Node role", "IMDSv2 169.254.169.254"],
        "irsa_src": ["IRSA role", "STS AssumeRoleWithWebIdentity"],
        "podid_src": ["Pod Identity role", "Agent → EKS Auth"],
        "bucket": ["S3 object", "invoices/2026-11.txt"],
        "policy": "Node role policy: s3:GetObject (app permission)",
        "revoked": "removed by revoke",
        "strike": 0.95,
        "irsa_do": "SA annotation + rollout",
        "podid_do": "association + rollout",
        "ok": "200 OK",
        "deny": "AccessDenied",
        "scenes": ["① up", "② migrate-irsa", "③ migrate-podid", "④ revoke"],
        "steps": [
            "① up (start): all three use IMDS → node role; the node role has s3:GetObject, so reads are allowed",
            "② migrate-irsa: annotate the ServiceAccount + rollout → the new orders-irsa Pod uses STS · IRSA role",
            "③ migrate-podid: create the association + rollout → the new orders-podid Pod uses the Pod Identity role",
            "④ revoke: remove the S3 policy from the node role → orders-legacy gets AccessDenied, the others keep reading",
        ],
        "hint": "Blue envelope: S3 read · green ✓ allowed · vermilion × denied",
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



def band(g, pts):
    for o in (-2.5, 2.5):
        g.append(f'<path class="cable" d="{c([(x, y + o) for x, y in pts])}"/>')


def bucket(g):
    x, y = BUCKET
    g.append(f'<ellipse class="ink" cx="{x}" cy="{y-26}" rx="34" ry="8"/>')
    g.append(f'<path class="ink" d="M{x-34} {y-26} l6 54 q28 10 56 0 l6 -54"/>')
    g.append(f'<path class="thin" d="M{x-31} {y-2} q31 9 62 0"/>')


def ok_mark(x, y, label, dy):
    return (f'<path class="okl" d="M{x-7} {y} l5 6 l10 -13"/>'
            f'<text class="tag halo gr" x="{x+12}" y="{y+dy}">{esc(label)}</text>')


def deny_mark(x, y, label, dy):
    """Denied: vermilion X, as gen 09 draws a block."""
    return (f'<path class="pkl" style="stroke-width:3px" d="M{x-8} {y-8} L{x+8} {y+8} M{x+8} {y-8} L{x-8} {y+8}"/>'
            f'<text class="tag halo acc" x="{x+14}" y="{y+dy}">{esc(label)}</text>')


def src_text(lines, y):
    return (f'<text class="t" x="{SRC[0]}" y="{y-3}" text-anchor="middle" font-weight="600" '
            f'style="font-size:13.5px">{esc(lines[0])}</text>'
            f'<text class="s" x="{SRC[0]}" y="{y+14}" text-anchor="middle">{esc(lines[1])}</text>')


def build(lang):
    ANIMS.clear()
    CAMS.clear()
    k = COPY[lang]
    steps_t = [(T["s1"], T["s1_end"]), (T["s2"], T["s2_end"]), (T["s3"], T["s3_end"]), (T["s4"], T["s4_end"] - 0.2)]
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
             f'aria-labelledby="t d" font-family="Pretendard, \'Apple SD Gothic Neo\', \'Noto Sans KR\', \'Noto Sans CJK KR\', \'Malgun Gothic\', \'Segoe UI\', sans-serif">')
    o.append(f'<title id="t">{esc(k["title"])}</title><desc id="d">{esc(k["desc"])}</desc>')
    o.append(STYLE)
    o.append(PEN)
    o.append(f'<rect class="paper" width="{W}" height="{H}"/>')
    o.append(f'<text class="h" x="32" y="40">{esc(k["title"])}</text>')
    fits(k["title"], 17, W - 64 - 150, bold=True)
    for lines in (k["node_src"], k["irsa_src"], k["podid_src"]):
        fits(lines[0], 13.5, SRC[1] - 12, bold=True)
        fits(lines[1], 12.5, SRC[1] - 12)

    # --- drawing (pen-wobbled) ---
    g = ['<g filter="url(#pen)">']
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="{dashed_d(*NODE_BOX)}"/>')
    for i in range(3):
        band(g, POD_SRC[i])
        band(g, SRC_S3[i])
        pod(g, POD_X, RY[i])
        g.append(f'<path class="ink" d="{box_d(SRC[0], RY[i], SRC[1], CARD_H)}"/>')
    bucket(g)
    px, py, pw, ph = POLICY
    g.append(f'<path class="thin" d="M{px} {py} l{pw} 0 l0 {ph} l-{pw} 0 z"/>')
    g.append('</g>')
    dia = list(g)  # the diagram: drawn once in the camera, once in the static view

    # labels
    nx, ny, nw, nh = NODE_BOX
    dia.append(f'<text class="s" x="{nx+12}" y="{ny+nh-10}" font-weight="700">{esc(k["node"])}</text>')
    dia.append(f'<text class="s" x="{SRC_L}" y="{RY[0]-34}" font-weight="700">{esc(k["col"])}</text>')
    for i, y in enumerate(RY):
        dia.append(f'<text class="s" x="{POD_X}" y="{y+33}" text-anchor="middle" font-weight="700">{esc(k["pods"][i])}</text>')
    dia.append(src_text(k["node_src"], RY[0]))
    bx, by = BUCKET
    dia.append(f'<text class="t" x="{bx}" y="{by+50}" text-anchor="middle" font-weight="600" style="font-size:14px">{esc(k["bucket"][0])}</text>')
    dia.append(f'<text class="s" x="{bx}" y="{by+67}" text-anchor="middle">{esc(k["bucket"][1])}</text>')
    fits(k["policy"], 13.5, pw - 20)
    dia.append(f'<text class="row" x="{px+12}" y="{py+23}">{esc(k["policy"])}</text>')
    strike_w = round(tw(k["policy"], 13.5) * k["strike"])
    strike = (f'<path class="pkl" style="stroke-width:2.4px" d="M{px+8} {py+18} L{px+16+strike_w} {py+19}"/>'
              f'<text class="tag halo acc" x="{px+pw-4}" y="{py+ph+16}" text-anchor="end">{esc(k["revoked"])}</text>')

    # --- motion layer ---
    m = ['<g class="motion">', '<g>', camera(CAM_KEYS)] + dia

    def hl(d, start, end, cls="trunk", after=None):
        return (f'<g opacity="0">{win(start, end, fade=0.2, after=after)}'
                f'<path class="{cls}" style="stroke-width:3px" d="{d}"/></g>')

    def podbox(y):
        return f"M{POD_X-27} {y-21} l54 0 l0 42 l-54 0 z"

    card = [box_d(SRC[0], y, SRC[1], CARD_H) for y in RY]
    # rows 2 and 3: card text swaps from node role to the new role at rollout
    for i, (swap, new) in ((1, (T["s2_swap"], k["irsa_src"])), (2, (T["s3_swap"], k["podid_src"]))):
        # node role text: shown across the loop seam (no blink at t=0), hidden from the swap to the reset
        m.append(f'<g opacity="0">'
                 + anim("opacity", [0, swap - 0.15, swap - 0.03, T["hold"] + 0.18, T["hold"] + 0.3, DUR],
                        [1, 1, 0, 0, 1, 1])
                 + f'{src_text(k["node_src"], RY[i])}</g>')
        m.append(f'<g opacity="0">{win(swap + 0.1, T["hold"], fade=0.2)}{src_text(new, RY[i])}</g>')
    roll = [(1, T["s2_roll"], T["s2_swap"], T["s2_go"], k["irsa_do"]), (2, T["s3_roll"], T["s3_swap"], T["s3_go"], k["podid_do"])]
    for i, r0, swap, go, label in roll:
        fits(label, 12, SRC[1], bold=True)
        m.append(hl(podbox(RY[i]), r0, swap + 0.3))
        m.append(hl(card[i], swap, T["hold"]))
        m.append(f'<g opacity="0">{win(r0, go, fade=0.2)}'
                 f'<text class="tag halo bl" x="{SRC_L}" y="{RY[i]-31}">{esc(label)}</text></g>')
    # revoke: strike the node role policy, legacy card turns vermilion
    m.append(f'<g opacity="0">{win(T["strike"], T["hold"], fade=0.2)}{strike}</g>')
    m.append(hl(card[0], T["s4_go"] - 0.4, T["hold"], cls="pkl"))

    def read(i, go, arrive, verdict, end):
        d, f = READ[i]
        thr0 = go + (arrive - go) * f[1]
        thr1 = thr0 + 0.2
        keys = [(0, 0), (go, 0), (thr0, f[1]), (thr1, f[2]), (arrive, 1), (DUR, 1)]
        r = ['<g>', vis([(go - 0.1, thr0), (thr1, arrive + 0.05)]), move(d, keys), ENVELOPE, '</g>']
        x, y = MARKS[i]
        mark = ok_mark(x, y, k["ok"], MARK_DY[i]) if verdict else deny_mark(x, y, k["deny"], MARK_DY[i])
        r.append(f'<g opacity="0">{win(arrive, end, fade=0.2)}{mark}</g>')
        return "".join(r)

    for i in range(3):
        m.append(read(i, T["s1_go"] + 0.15 * i, T["s1_in"] + 0.15 * i, True, T["s1_end"]))
    m.append(read(1, T["s2_go"], T["s2_in"], True, T["s2_end"]))
    m.append(read(2, T["s3_go"], T["s3_in"], True, T["s3_end"]))
    for i in range(3):
        m.append(read(i, T["s4_go"] + 0.15 * i, T["s4_in"] + 0.15 * i, i != 0, T["hold"]))

    m.append('</g>' + BANDS)  # end of camera; scene badge, captions and hint stay fixed
    # the bands cover the root title in this layer, so it is drawn again on top
    m.append(f'<text class="h halo" x="32" y="40">{esc(k["title"])}</text>')

    # scene badge, top right (fixed, outside the camera)
    scene_t = [(T["s1"], T["s2"] - 0.2), (T["s2"], T["s3"] - 0.2), (T["s3"], T["s4"] - 0.2), (T["s4"], T["hold"])]
    for name, (s0, s1) in zip(k["scenes"], scene_t):
        m.append(f'<g opacity="0">{win(s0, s1, fade=0.2)}'
                 f'<text class="h bl" x="{W-32}" y="40" text-anchor="end">{esc(name)}</text></g>')

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

    # --- static (reduced motion) layer: end state after revoke ---
    st = ['<g class="static">'] + dia + [strike, src_text(k["irsa_src"], RY[1]), src_text(k["podid_src"], RY[2])]
    st.append(f'<path class="pkl" style="stroke-width:3px" d="{card[0]}"/>')
    st.append(f'<path class="trunk" style="stroke-width:3px" d="{card[1]}"/><path class="trunk" style="stroke-width:3px" d="{card[2]}"/>')
    st.append(deny_mark(*MARKS[0], k["deny"], MARK_DY[0]) + ok_mark(*MARKS[1], k["ok"], MARK_DY[1])
              + ok_mark(*MARKS[2], k["ok"], MARK_DY[2]))
    st.append(f'<text class="h bl" x="{W-32}" y="40" text-anchor="end">{esc(k["scenes"][3])}</text>')
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    st.append(f'<text class="s" x="{W-32}" y="{H-14}" text-anchor="end">{esc(k["hint"])}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    check_camera()
    return "\n".join(o)


def check_output(svg):
    assert "—" not in svg, "em dash in output"
    for bad in ("<script", "href", "@import", "<foreignObject", "<image"):
        assert bad not in svg, bad
    assert svg.count("url(") == svg.count("url(#pen)"), "only the pen filter may be referenced"


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-security-17-eks-workload-identity-migration-anim-3.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-security-17-eks-workload-identity-migration-anim-3.svg")
        svg = build(lang)
        check_output(svg)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", MARKS)
