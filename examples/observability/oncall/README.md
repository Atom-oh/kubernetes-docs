# OnCall migration and contract examples

Grafana OnCall OSS was archived on 2026-03-24. These files support review and
migration of an existing installation; they are not a recommendation or complete
installation recipe for a new production OSS deployment.

`inventory.py` makes GET requests only, keeps the raw OnCall Authorization header,
checks pagination origin/collection/count, refuses redirects, verifies TLS and
writes a new mode0600 file. The output can contain personal data and secret
integration URLs. It is not a full database/key/history backup or an atomic
snapshot. Tests use synthetic loopback HTTPS, with no real account access.

Run with a protected token file and the actual OnCall API origin:

```bash
python inventory.py --base-url https://oncall.example.com \
  --token-file /secure/input/oncall-api-token \
  --output /secure/output/oncall-inventory.json
```

For Grafana service-account-token authentication, supply the required
`--stack-url`. Do not add a Bearer prefix to the documented OnCall API header.
An integration webhook URL is a separate credential/protocol.

The JSON examples describe versioned public API contracts. Replace all IDs and
review dates, permissions and the installed API version. Create/verify a shift
separately, then reference its ID in a web schedule's `shifts` list. An override is
an on_call_shifts object type; it is not the old nested schedules/id/overrides
request shown in the original guide. No POST/create/notification was executed.

The Alertmanager example uses current `matchers`, defines both receivers, and
reads a generated integration URL from a file. No universal API bearer token,
webhook URL path or payload shape is invented. Test the selected integration's
actual firing/resolved behavior and retain a fallback response process.
