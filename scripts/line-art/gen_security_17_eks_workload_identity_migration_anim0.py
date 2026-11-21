#!/usr/bin/env python3
"""Draw the three EKS credential paths as an animated, bilingual line-art SVG."""

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLUG = "security-17-eks-workload-identity-migration-anim-0.svg"

COPY = {
    "ko": {
        "title": "EKS Pod 자격 증명은 어디서 오는가",
        "desc": "AWS SDK의 자격 증명 조회(파랑)와 임시 자격 증명 반환(초록).",
        "node": "노드 인스턴스 프로파일",
        "node_role": "노드 역할",
        "irsa_role": "IRSA 역할",
        "pod_role": "Pod Identity 역할",
        "imds": "노드 역할 자격 증명 조회",
        "oidc": "IAM OIDC 신뢰 · aud / sub",
        "tags": "EKS association · 요청 태그",
        "via_agent": "EKS Auth와 Agent를 거쳐 반환",
        "return": "임시 역할 자격 증명이 SDK로 반환",
        "signed": "각 Pod가 받은 자격 증명으로 S3 API 요청에 서명",
    },
    "en": {
        "title": "Where EKS Pods get AWS credentials",
        "desc": "The AWS SDK requests credentials (blue) and receives temporary credentials (green).",
        "node": "Node instance profile",
        "node_role": "Node role",
        "irsa_role": "IRSA role",
        "pod_role": "Pod Identity role",
        "imds": "Retrieve node-role credentials",
        "oidc": "IAM OIDC trust · aud / sub",
        "tags": "EKS association · request tags",
        "via_agent": "Returns via EKS Auth and the Agent",
        "return": "Temporary role credentials return to the SDK",
        "signed": "Each Pod signs the S3 API request using its returned credentials",
    },
}


def label(x, y, value, style="small", anchor="middle"):
    return (
        f'<text x="{x}" y="{y}" class="{style}" text-anchor="{anchor}">'
        f"{escape(value)}</text>"
    )


def card(x, y, width, title, subtitle=None):
    block = (
        f'<rect x="{x}" y="{y - 20}" width="{width}" height="40" rx="9" class="card"/>'
        + label(x + width / 2, y + (5 if subtitle is None else -2), title, "card-label")
    )
    if subtitle is not None:
        block += label(x + width / 2, y + 13, subtitle, "detail")
    return block


def link(start, end, y, kind="request"):
    offset = 8 if end > start else -8
    return (
        f'<path class="link {kind}" marker-end="url(#{kind}-arrow)" '
        f'd="M{start} {y} Q{(start + end) / 2} {y + offset} {end} {y}"/>'
    )


def pulse(start, end, y, kind):
    offset = 8 if end > start else -8
    d = f"M{start} {y} Q{(start + end) / 2} {y + offset} {end} {y}"
    timing = "0;.1;.55;1" if kind == "request" else "0;.5;.65;1"
    visibility = "1;1;0;0" if kind == "request" else "0;0;1;0"
    positions = "0;0;1;1" if kind == "request" else "0;0;0;1"
    return (
        f'<circle r="5" class="pulse {kind}" opacity="0">'
        f'<animate attributeName="opacity" values="{visibility}" keyTimes="{timing}" '
        'dur="5.5s" repeatCount="indefinite"/>'
        f'<animateMotion dur="5.5s" path="{d}" keyPoints="{positions}" '
        f'keyTimes="{timing}" calcMode="linear" repeatCount="indefinite"/>'
        "</circle>"
    )


def lane(y, name, cards, role, request_label, trust=None, return_label=None):
    end = cards[-1][0] + cards[-1][1]
    pieces = [
        label(28, y - 32, name, "heading", "start"),
        card(28, y, 123, "Pod / AWS SDK"),
    ]
    left = 151
    for x, width, title, subtitle in cards:
        pieces.extend([link(left + 4, x - 5, y), card(x, y, width, title, subtitle)])
        left = x + width
    pieces.extend([
        label((151 + cards[0][0]) / 2, y - 9, request_label, "detail"),
        label(end + 17, y - 1, role, "card-label", "start"),
        link(end - 12, 92, y + 40, "response"),
        pulse(154, end - 10, y, "request"),
        pulse(end - 12, 92, y + 40, "response"),
    ])
    if trust:
        pieces.append(label(end + 17, y + 15, trust, "detail", "start"))
    if return_label:
        pieces.append(label(420, y + 32, return_label, "detail"))
    return "\n".join(pieces)


def render(lang):
    copy = COPY[lang]
    lanes = [
        lane(110, copy["node"], [(402, 160, "EC2 IMDSv2", "169.254.169.254")],
             copy["node_role"], copy["imds"]),
        lane(225, "IRSA", [(402, 188, "AWS STS", "AssumeRoleWithWebIdentity")],
             copy["irsa_role"], "Projected token", copy["oidc"]),
        lane(340, "EKS Pod Identity", [(302, 149, "Pod Identity Agent", "169.254.170.23"),
             (484, 171, "EKS Auth", "AssumeRoleForPodIdentity"), (686, 87, "STS", "AssumeRole")],
             copy["pod_role"], "Projected token", copy["tags"], copy["via_agent"]),
    ]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 480" role="img" xml:lang="{lang}"
  aria-labelledby="title desc">
<title id="title">{escape(copy["title"])}</title>
<desc id="desc">{escape(copy["desc"])} {escape(copy["signed"])}</desc>
<style>
  :root {{ --paper:#fffdf8; --card:#fff; --ink:#282419; --rule:#b2a792; --blue:#145c88; --green:#286342; }}
  @media (prefers-color-scheme:dark) {{
    :root {{ --paper:#21211f; --card:#2b2b29; --ink:#f6efdc; --rule:#918771; --blue:#86c8f1; --green:#99d5ac; }}
  }}
  @media (prefers-reduced-motion:reduce) {{ .pulse {{ display:none; }} }}
  text {{ fill:var(--ink); font-family:"Pretendard","Noto Sans KR",system-ui,sans-serif; }}
  .paper {{ fill:var(--paper); stroke:var(--rule); }}
  .card {{ fill:var(--card); stroke:var(--rule); stroke-width:1.4; }}
  .title {{ font-size:25px; font-weight:700; }}
  .heading {{ font-size:19px; font-weight:700; }}
  .card-label {{ font-size:14px; font-weight:700; }}
  .small {{ font-size:14px; }}
  .detail {{ font-size:12px; }}
  .link {{ fill:none; stroke-width:1.8; }}
  .link.request {{ stroke:var(--blue); }}
  .link.response {{ stroke:var(--green); stroke-dasharray:5 4; }}
  .pulse.request, .request-arrow {{ fill:var(--blue); }}
  .pulse.response, .response-arrow {{ fill:var(--green); }}
</style>
<defs>
  <marker id="request-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
    <path d="M0 0 L7 3.5 L0 7Z" class="request-arrow"/>
  </marker>
  <marker id="response-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
    <path d="M0 0 L7 3.5 L0 7Z" class="response-arrow"/>
  </marker>
</defs>
<rect x="1" y="1" width="998" height="478" rx="15" class="paper"/>
{label(28, 39, copy["title"], "title", "start")}
{"".join(lanes)}
{label(503, 409, copy["return"], "small")}
<path d="M28 426 Q500 429 972 426" fill="none" class="link response"/>
{label(500, 454, copy["signed"], "heading")}
</svg>
'''


if __name__ == "__main__":
    for language in COPY:
        out = ROOT / language / ".gitbook" / "assets" / f"{language}-{SLUG}"
        out.write_text(render(language), encoding="utf-8")
