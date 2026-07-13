"""Query ttobak's AgentCore Gateway Web Search connector for fresh
Kubernetes/EKS/CNCF ecosystem news and write results to feeds/web-search.json
for the digest prompt to read alongside the RSS feeds.

SigV4-signed JSON-RPC POST, not an MCP client -- see
Atom-oh/ttobak backend/python/crawler/news_crawler.py::_gateway_web_search
for the reference implementation this mirrors (same account/IAM role, no
extra grant needed).

WEB_SEARCH_GATEWAY_URL unset -> skip gracefully (empty results file), same
convention as ttobak's own caller.
"""
import json
import os
import re
import sys
from urllib.request import Request, urlopen

import boto3.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

GATEWAY_URL = os.environ.get("WEB_SEARCH_GATEWAY_URL", "")
GATEWAY_REGION = os.environ.get("WEB_SEARCH_GATEWAY_REGION", "us-east-1")
TOOL_NAME = "ttobak-web-search-tool___WebSearch"
TIMEOUT_SECONDS = 15
MAX_RESULTS_PER_QUERY = 4
OUTPUT_PATH = "feeds/web-search.json"

# One query per major project this site covers, plus a couple of
# general/catch-all queries. Add a project here as new content sections are
# added; keep each query narrow (project + "release"/"update") so results
# stay on-topic instead of generic ecosystem noise.
QUERIES = [
    "Kubernetes new release this week",
    "Amazon EKS new feature announcement",
    "CNCF project news this week",
    "Kubernetes security CVE this week",
    "Istio service mesh release",
    "Cilium release",
    "Karpenter release",
    "KEDA release",
    "Kubernetes descheduler update",
    "Prometheus release",
    "VictoriaMetrics release",
    "ClickHouse release",
    "Grafana Mimir release",
    "Grafana Tempo release",
    "Grafana release",
    "Calico release",
    "NVIDIA GPU Kubernetes update",
    "vLLM release",
    "Kubeflow release",
    "MLflow release",
    "KubeRay release",
]

# Mirrors ttobak's news_crawler.py::_sanitize_snippet -- open web search has
# no domain allowlist, so a SEO-planted payload could carry prompt-injection
# instructions into the digest's `claude -p` step otherwise.
_DIRECTIVE_RE = re.compile(
    r"^\s*(system|assistant|user|instructions?)\s*:|ignore (all )?previous|이전 지시.*무시",
    re.IGNORECASE,
)


def _sanitize_snippet(text):
    if not text:
        return text
    text = text.replace("<article>", "").replace("</article>", "").replace("```", "'''")
    cleaned = []
    for line in text.splitlines():
        if _DIRECTIVE_RE.search(line):
            line = "[quoted] " + line
        cleaned.append(line)
    return "\n".join(cleaned)


def _sigv4_post(body_json):
    session = boto3.session.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise RuntimeError("no AWS credentials available for SigV4 signing")
    request = AWSRequest(
        method="POST",
        url=GATEWAY_URL,
        data=body_json,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )
    SigV4Auth(credentials, "bedrock-agentcore", GATEWAY_REGION).add_auth(request)
    prepared = request.prepare()
    body = prepared.body.encode("utf-8") if isinstance(prepared.body, str) else prepared.body
    req = Request(prepared.url, data=body, headers=dict(prepared.headers), method="POST")
    with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.read().decode("utf-8")


def _search(query):
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": TOOL_NAME,
            "arguments": {"query": query[:200], "maxResults": MAX_RESULTS_PER_QUERY},
        },
    })
    try:
        parsed = json.loads(_sigv4_post(body))
        if "error" in parsed:
            print(f"::warning::gateway JSON-RPC error for '{query}': {parsed['error']}", file=sys.stderr)
            return []
        result = parsed.get("result", parsed)
        if result.get("isError"):
            print(f"::warning::gateway returned isError for '{query}'", file=sys.stderr)
            return []
        content = result.get("content", [])
        text_block = next((b for b in content if b.get("type") == "text" and "text" in b), None)
        if text_block is None:
            print(f"::warning::no text content block for '{query}'", file=sys.stderr)
            return []
        results = json.loads(text_block["text"]).get("results", [])
        for r in results:
            r["title"] = _sanitize_snippet(r.get("title", ""))
            r["text"] = _sanitize_snippet(r.get("text", ""))
        return [r for r in results if r.get("url")]
    except Exception as e:
        print(f"::warning::web search failed for '{query}': {e}", file=sys.stderr)
        return []


def main():
    os.makedirs("feeds", exist_ok=True)
    if not GATEWAY_URL:
        print("::warning::WEB_SEARCH_GATEWAY_URL not set, skipping web search enrichment", file=sys.stderr)
        with open(OUTPUT_PATH, "w") as f:
            json.dump({"queries": [], "results": []}, f)
        return

    all_results = []
    for query in QUERIES:
        all_results.append({"query": query, "results": _search(query)})

    with open(OUTPUT_PATH, "w") as f:
        json.dump({"queries": QUERIES, "results": all_results}, f, ensure_ascii=False, indent=2)
    total = sum(len(r["results"]) for r in all_results)
    print(f"wrote {total} web search results across {len(QUERIES)} queries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
