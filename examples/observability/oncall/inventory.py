#!/usr/bin/env python3
"""Export a bounded, read-only OnCall API inventory to a private local file."""
import argparse
import json
import os
from pathlib import Path
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request

COLLECTIONS = (
    "teams", "users", "integrations", "schedules", "on_call_shifts",
    "escalation_chains", "escalation_policies", "routes",
)


class InventoryError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def origin(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise InventoryError("Use an HTTPS URL without embedded credentials")
    return parsed.scheme, parsed.hostname, parsed.port or 443


def export_collection(opener, base_url, token, collection, *, stack_url=None,
                      max_pages=100, timeout=15):
    if collection not in COLLECTIONS:
        raise InventoryError("Collection is not in the read-only inventory allowlist")
    parsed_base = urllib.parse.urlsplit(base_url)
    if parsed_base.query or parsed_base.fragment or parsed_base.path not in ("", "/"):
        raise InventoryError("Base URL must be the OnCall origin, without path/query/fragment")
    expected_origin = origin(base_url)
    expected_path = "/api/v1/" + collection + "/"
    url = urllib.parse.urljoin(base_url, expected_path)
    headers = {"Authorization": token, "Accept": "application/json"}
    if stack_url:
        origin(stack_url)
        headers["X-Grafana-URL"] = stack_url
    if not token or any(ch in token for ch in "\r\n"):
        raise InventoryError("Token file must contain one nonempty token")
    seen = set()
    output = []
    expected_count = None
    total_bytes = 0
    for _ in range(max_pages):
        parsed = urllib.parse.urlsplit(url)
        if origin(url) != expected_origin or parsed.path.rstrip("/") != expected_path.rstrip("/") or parsed.fragment:
            raise InventoryError("Pagination changed the API origin or collection")
        if url in seen:
            raise InventoryError("Pagination loop detected")
        seen.add(url)
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    raise InventoryError("Inventory request did not return HTTP200")
                body = response.read(5 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            raise InventoryError(f"Inventory request failed with HTTP{error.code}; no automatic retry") from error
        except urllib.error.URLError as error:
            raise InventoryError("Inventory connection or TLS validation failed") from error
        if len(body) > 5 * 1024 * 1024:
            raise InventoryError("Inventory page exceeds the configured size bound")
        total_bytes += len(body)
        if total_bytes > 10 * 1024 * 1024:
            raise InventoryError("Inventory collection exceeds10MiB; export a narrower scope separately")
        try:
            page = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InventoryError("Inventory page is not valid JSON") from error
        if (not isinstance(page, dict) or not isinstance(page.get("results"), list)
                or "next" not in page or type(page.get("count")) is not int or page["count"] < 0):
            raise InventoryError("Inventory response lacks valid count/results/next fields")
        if not all(isinstance(item, dict) for item in page["results"]):
            raise InventoryError("Inventory results must contain objects")
        if expected_count is None:
            expected_count = page["count"]
        elif page["count"] != expected_count:
            raise InventoryError("Collection changed during pagination; retry during a stable window")
        output.extend(page["results"])
        next_page = page.get("next")
        if next_page is None:
            if len(output) != expected_count:
                raise InventoryError("Pagination ended before the declared item count was exported")
            return output
        if not isinstance(next_page, str) or not next_page:
            raise InventoryError("Pagination next must be a URL string or null")
        url = urllib.parse.urljoin(url, next_page)
    raise InventoryError("Pagination exceeded the configured page bound")


def write_private_json(destination, value):
    destination = Path(destination)
    # Refuse overwriting a trusted previous inventory until the new one is complete.
    if destination.exists():
        raise InventoryError("Output already exists; choose a new private filename")
    descriptor, temporary = tempfile.mkstemp(prefix=".oncall-inventory-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link creation fails if another process created the destination.
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--stack-url", help="Required when the selected API authentication uses a Grafana service-account token")
    parser.add_argument("--ca-file", help="Private CA bundle when required; TLS verification stays enabled")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 1000:
        parser.error("--max-pages must be between1 and1000")
    token = args.token_file.read_text().strip()
    context = ssl.create_default_context(cafile=args.ca_file)
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    try:
        result = {
            "scope": "Read-only inventory; not a complete database/key/history backup or atomic migration snapshot",
            "collections": {
                collection: export_collection(opener, args.base_url, token, collection,
                                              stack_url=args.stack_url, max_pages=args.max_pages)
                for collection in COLLECTIONS
            },
        }
        write_private_json(args.output, result)
    except (InventoryError, OSError) as error:
        parser.exit(1, f"Inventory failed: {error}\n")
    print("Private inventory written; protect integration URLs and personal data in the output.")


if __name__ == "__main__":
    main()
