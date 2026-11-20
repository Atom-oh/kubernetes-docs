#!/usr/bin/env python3
"""Line-art animated SVG of a CDN cache MISS then HIT for the same object.

Copies the approved prototype (gen_basics_06_part5_anim0.py): same palette
tokens, pen filter, stroke classes, font stack, caption layout, packet-tag
style and ko/en COPY structure. Reuses the motion()/packet()/anim() helpers
and the keyTimes self-check from gen_networking_expert_07_..._anim0.py.
SMIL drives motion on one shared clock; CSS only handles palette
(light/dark) and the reduced-motion static view.

Story: client A resolves the distribution name (DNS picks the POP with the
lowest latency; drawn as an off-path note) and requests /img/logo.png. The
edge POP and the regional edge cache both miss, the origin (an internal ALB
reached through a CloudFront VPC origin) returns 200 with
Cache-Control: max-age=3600, and each cache tier stores a copy on the way
back. Client B then asks the same POP for the same object: HIT, served with
Age, and the origin is not contacted. The Miss tag carries no Age field
(RFC 9111 section 5.1: Age implies the origin did not generate the response).
"""
import math
import sys

DUR = 14.0  # seconds per loop

# ---------- geometry ----------------------------------------------------------
CLIENT_A = (100, 186)
CLIENT_B = (100, 318)
POP = (340, 180)
REC = (580, 180)
ORIGIN = (836, 180)

# Cable centre lines (hand-drawn: gentle curves, never ruler straight).
A_POP = [(156, 182), (206, 160), (258, 202), (302, 180)]      # client A -> POP
POP_REC = [(378, 180), (428, 158), (486, 202), (534, 180)]    # POP -> regional cache
REC_ORG = [(626, 180), (680, 158), (722, 202), (780, 180)]    # regional cache -> origin
B_POP = [(146, 282), (196, 250), (250, 250), (302, 208)]      # client B -> POP (lower left)

DNS_BOX = (150, 58, 236, 40)  # x, y, w, h: off-path DNS note


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


# Request 1 (MISS): out to the origin and back, dwelling at each box centre.
P1_D, P1_F = motion([
    ("bez", A_POP), ("line", [A_POP[-1], POP]), ("line", [POP, POP_REC[0]]),      # 1, 2, 3
    ("bez", POP_REC), ("line", [POP_REC[-1], REC]), ("line", [REC, REC_ORG[0]]),  # 4, 5, 6
    ("bez", REC_ORG), ("line", [REC_ORG[-1], ORIGIN]),                            # 7, 8
    ("line", [ORIGIN, REC_ORG[-1]]), ("bez", rev(REC_ORG)),                       # 9, 10
    ("line", [REC_ORG[0], REC]), ("line", [REC, POP_REC[-1]]),                    # 11, 12
    ("bez", rev(POP_REC)), ("line", [POP_REC[0], POP]),                           # 13, 14
    ("line", [POP, A_POP[-1]]), ("bez", rev(A_POP)),                              # 15, 16
])
# Request 2 (HIT): client B to the same POP and back.
P2_D, P2_F = motion([
    ("bez", B_POP), ("line", [B_POP[-1], POP]),
    ("line", [POP, B_POP[-1]]), ("bez", rev(B_POP)),
])

# Timeline (seconds): travel, dwell, travel ...
T = {
    "p1_on": 0.3, "p1_go": 0.9, "p1_pop": 1.9, "p1_pop_go": 2.5, "p1_rec": 3.5, "p1_rec_go": 4.0,
    "p1_org": 5.0, "p1_org_go": 5.7, "p1_rec2": 6.6, "p1_rec2_go": 7.0, "p1_pop2": 7.9,
    "p1_pop2_go": 8.2, "p1_cli": 9.0, "p1_off": 9.2,
    "p2_on": 9.4, "p2_go": 9.6, "p2_pop": 10.4, "p2_pop_go": 11.0, "p2_cli": 11.8,
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
        "title": "CDN 캐시: 같은 객체를 두 번 요청하면 MISS 다음 HIT",
        "desc": ("클라이언트 A가 배포 이름을 조회하면 DNS가 지연이 가장 낮은 엣지 POP을 답한다. A가 GET /img/logo.png를 "
                 "보내면 POP은 그 캐시 키의 객체가 없어 MISS이고 리전 엣지 캐시에 묻는다. 리전 엣지 캐시도 MISS이므로 "
                 "VPC 오리진을 거쳐 internal ALB인 오리진에 요청한다. 오리진은 200과 Cache-Control: max-age=3600을 "
                 "돌려주고, 응답이 돌아오는 길에 리전 엣지 캐시와 POP이 각각 사본을 저장한다. A는 x-cache: Miss from "
                 "cloudfront를 받는다. 이어서 클라이언트 B가 같은 POP에 같은 객체를 요청하면 HIT이며, POP이 Age: 42와 "
                 "x-cache: Hit from cloudfront로 바로 응답하고 오리진에는 요청이 가지 않는다."),
        "cliA": ["클라이언트 A", "첫 요청"],
        "cliB": ["클라이언트 B", "같은 POP"],
        "pop": ["엣지 POP", "엣지 캐시"],
        "rec": ["리전 엣지 캐시", "중간 계층"],
        "org": ["오리진", "internal ALB (VPC 오리진)"],
        "dns": ["DNS 조회 (데이터 경로 밖)", "지연이 가장 낮은 POP 주소를 답한다"],
        "copy": "사본 저장",
        "steps": [
            "① DNS가 지연이 가장 낮은 POP을 답하고, 클라이언트 A가 GET /img/logo.png를 보낸다",
            "② 엣지 POP: 이 캐시 키의 객체가 없어 MISS → 리전 엣지 캐시도 MISS",
            "③ 오리진(VPC 오리진 뒤 internal ALB)이 200과 Cache-Control: max-age=3600을 돌려준다",
            "④ 돌아오는 길에 리전 캐시와 POP이 사본을 저장, A는 x-cache: Miss from cloudfront를 받는다",
            "⑤ 클라이언트 B, 같은 POP: HIT, Age: 42로 엣지에서 바로 응답하고 오리진은 요청을 받지 않는다",
        ],
        "hint": "패킷 위 꼬리표: 지금 바뀐 헤더 값",
    },
    "en": {
        "title": "CDN cache: the same object requested twice, MISS then HIT",
        "desc": ("Client A resolves the distribution name and DNS answers with the edge POP that has the lowest latency. "
                 "A sends GET /img/logo.png. The POP has no object for that cache key, so it is a MISS and the POP asks "
                 "the regional edge cache. The regional edge cache misses too and requests the object from the origin, "
                 "an internal ALB reached through a VPC origin. The origin returns 200 with Cache-Control: max-age=3600, "
                 "and on the way back the regional edge cache and the POP each store a copy. A receives x-cache: Miss "
                 "from cloudfront. Then client B asks the same POP for the same object: it is a HIT, the POP answers at "
                 "once with Age: 42 and x-cache: Hit from cloudfront, and no request reaches the origin."),
        "cliA": ["Client A", "first request"],
        "cliB": ["Client B", "same POP"],
        "pop": ["Edge POP", "edge cache"],
        "rec": ["Regional edge cache", "mid tier"],
        "org": ["Origin", "internal ALB (VPC origin)"],
        "dns": ["DNS lookup (off the data path)", "answers with the lowest-latency POP"],
        "copy": "copy stored",
        "steps": [
            "① DNS answers with the lowest-latency POP; client A sends GET /img/logo.png",
            "② Edge POP: no object for this cache key → MISS; the regional edge cache misses too",
            "③ The origin (an internal ALB behind a VPC origin) returns 200 with Cache-Control: max-age=3600",
            "④ On the way back the regional cache and the POP store a copy; A gets x-cache: Miss from cloudfront",
            "⑤ Client B, same POP: HIT, served from the edge with Age: 42; the origin receives no request",
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


def cache_box(g, x, y, racks):
    """Cache site: a cage with `racks` shelves of disks."""
    w = 38 if racks == 1 else 46
    g.append(f'<path class="ink" d="M{x-w} {y-38} q0 -4 4 -4 l{2*w-8} 1 q5 0 5 5 l-1 72 q0 4 -4 4 l-{2*w-8} -1 q-4 0 -4 -4 z"/>')
    cols = [x] if racks == 1 else [x - 18, x + 18]
    for cx in cols:
        for i in range(4):
            yy = y - 28 + i * 16
            g.append(f'<path class="thin" d="M{cx-14} {yy} l28 1 l0 9 l-28 0 z"/>')
        g.append(f'<circle class="fillink" cx="{cx+8}" cy="{y-24}" r="1.8"/>')


def copy_icon(x, y):
    """Stored object: a small page with a folded corner (blue: something changed)."""
    return (f'<path class="trunk" stroke-width="1.8" d="M{x} {y} l14 0 l6 6 l0 18 l-20 0 z M{x+14} {y} l0 6 l6 0"/>'
            f'<path class="trunk" d="M{x+4} {y+12} l11 0 M{x+4} {y+17} l9 0"/>')


def build(lang):
    ANIMS.clear()
    k = COPY[lang]
    W, H = 960, 500
    steps_t = [(T["p1_on"], T["p1_pop"]), (T["p1_pop"], T["p1_rec_go"] + 0.4),
               (T["p1_org"], T["p1_org_go"] + 0.2), (T["p1_org_go"] + 0.2, T["p1_off"]),
               (T["p2_on"], T["p2_cli"] + 0.5)]
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
    for path in (A_POP, POP_REC, REC_ORG, B_POP):
        for dy in (-2.5, 2.5):
            g.append(f'<path class="cable" d="{c([(x, y + dy) for x, y in path])}"/>')
    laptop(g, *CLIENT_A)
    laptop(g, *CLIENT_B)
    cache_box(g, *POP, racks=1)
    cache_box(g, *REC, racks=2)
    # origin: dashed VPC boundary around a load balancer (box fanning out to targets)
    x, y = ORIGIN
    g.append(f'<path class="thin" stroke-dasharray="3 6" d="M{x-62} {y-44} q0 -6 6 -6 l114 1 q6 0 6 6 l-1 82 q0 6 -6 6 l-113 -1 q-6 0 -6 -6 z"/>')
    g.append(f'<path class="ink" d="M{x-30} {y-16} q0 -4 4 -4 l26 0 q4 0 4 4 l0 32 q0 4 -4 4 l-26 0 q-4 0 -4 -4 z"/>')
    g.append(f'<path class="thin" d="M{x+4} {y} q14 -2 22 -20 M{x+4} {y} l26 0 M{x+4} {y} q14 2 22 20"/>')
    g.append(f'<path class="thin" d="M{x+28} {y-26} l10 0 l0 10 l-10 0 z M{x+32} {y-5} l10 0 l0 10 l-10 0 z M{x+28} {y+16} l10 0 l0 10 l-10 0 z"/>')
    # DNS note: off the data path, dotted leader down to client A
    bx, by, bw, bh = DNS_BOX
    g.append(f'<path class="thin" stroke-dasharray="2 5" d="M{bx} {by} l{bw} 1 l-1 {bh} l-{bw-1} -1 z"/>')
    g.append(f'<path class="thin" stroke-dasharray="2 5" d="M{bx+20} {by+bh} q-6 20 -16 44"/>')
    g.append('</g>')
    o.extend(g)

    # labels
    for (x, y), (n, sub) in ((CLIENT_A, k["cliA"]),):
        o.append(f'<text class="t" x="{x}" y="{y+48}" text-anchor="middle" font-weight="600">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+66}" text-anchor="middle">{esc(sub)}</text>')
    x, y = CLIENT_B
    o.append(f'<text class="t" x="{x+66}" y="{y+2}" font-weight="600">{esc(k["cliB"][0])}</text>')
    o.append(f'<text class="s" x="{x+66}" y="{y+20}">{esc(k["cliB"][1])}</text>')
    for (x, y), (n, sub) in ((POP, k["pop"]), (REC, k["rec"]), (ORIGIN, k["org"])):
        o.append(f'<text class="t" x="{x}" y="{y+64}" text-anchor="middle" font-weight="600">{esc(n)}</text>')
        o.append(f'<text class="s" x="{x}" y="{y+82}" text-anchor="middle">{esc(sub)}</text>')
    o.append(f'<text class="s" x="{bx+10}" y="{by+16}" font-weight="700">{esc(k["dns"][0])}</text>')
    o.append(f'<text class="s" x="{bx+10}" y="{by+32}">{esc(k["dns"][1])}</text>')

    # cached copies: appear when the response passes each tier, persist to the end
    rec_copy = (REC[0] + 52, REC[1] - 66)
    pop_copy = (POP[0] + 44, POP[1] - 66)

    def copy_mark(pos):
        x, y = pos
        return copy_icon(x, y) + f'<text class="s bl" x="{x+26}" y="{y+16}">{esc(k["copy"])}</text>'

    # --- motion layer ---
    m = ['<g class="motion">']
    m.append(f'<g opacity="0">{win(T["p1_rec2"], T["hold"], fade=0.2)}{copy_mark(rec_copy)}</g>')
    m.append(f'<g opacity="0">{win(T["p1_pop2"], T["hold"], fade=0.2)}{copy_mark(pop_copy)}</g>')

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
        (T["p1_rec"], f[5]), (T["p1_rec_go"], f[5]), (T["p1_org"], f[8]), (T["p1_org_go"], f[8]),
        (T["p1_rec2"], f[11]), (T["p1_rec2_go"], f[11]), (T["p1_pop2"], f[14]), (T["p1_pop2_go"], f[14]),
        (T["p1_cli"], 1), (DUR, 1)],
        T["p1_on"], T["p1_off"], [
        ("GET /img/logo.png", T["p1_on"], T["p1_pop"] - 0.1, "acc", 0, -24, "middle"),
        ("MISS · cache key /img/logo.png", T["p1_pop"] + 0.1, T["p1_rec"] - 0.1, "bl", 0, -58, "middle"),
        ("regional cache: MISS", T["p1_rec"] + 0.1, T["p1_org"] - 0.1, "bl", 0, -58, "middle"),
        ("200 OK\nCache-Control: max-age=3600", T["p1_org"] + 0.1, T["p1_pop2"] - 0.1, "acc", -12, -76, "end"),
        ("x-cache: Miss from cloudfront\nCache-Control: max-age=3600", T["p1_pop2"] + 0.1, T["p1_pop2_go"] + 0.35, "acc", 10, -60, "end"),
    ]))
    f2 = P2_F
    m.append(packet(P2_D, [
        (0, 0), (T["p2_go"], 0), (T["p2_pop"], f2[2]), (T["p2_pop_go"], f2[2]), (T["p2_cli"], 1), (DUR, 1)],
        T["p2_on"], T["hold"], [
        ("GET /img/logo.png", T["p2_on"], T["p2_pop"] - 0.1, "acc", 0, -24, "middle"),
        ("x-cache: Hit from cloudfront\nAge: 42", T["p2_pop"] + 0.1, T["p2_pop_go"] + 0.3, "bl", 10, -60, "end"),
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
    st = ['<g class="static">', copy_mark(rec_copy), copy_mark(pop_copy)]
    for i, txt in enumerate(k["steps"]):
        st.append(f'<text class="cap" x="40" y="{cy0 + i * 22}">{esc(txt)}</text>')
    for (x, y, label) in ((CLIENT_A[0] - 8, 134, "①"), (POP[0] - 40, 128, "②"), (ORIGIN[0] - 8, 118, "③"),
                          (REC[0] - 24, 128, "④"), (B_POP[1][0] + 10, 240, "⑤")):
        st.append(f'<text class="tag acc" x="{x}" y="{y}" font-size="16">{label}</text>')
    st.append('</g>')
    o.extend(st)
    o.append('</svg>')
    check_anims()
    return "\n".join(o)


if __name__ == "__main__":
    # Writes <repo>/<lang>/.gitbook/assets/<lang>-networking-expert-08-cdn-edge-delivery-anim-0.svg
    import os
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..")
    for lang in ("ko", "en"):
        path = os.path.join(root, lang, ".gitbook", "assets",
                            f"{lang}-networking-expert-08-cdn-edge-delivery-anim-0.svg")
        svg = build(lang)
        assert "\u2014" not in svg, "em dash in output"
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok", [round(x, 3) for x in P1_F], [round(x, 3) for x in P2_F])
