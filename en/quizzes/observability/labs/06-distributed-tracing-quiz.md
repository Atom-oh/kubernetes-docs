# Observability Lab Part 6 Quiz

> **Last Updated**: September 13, 2026

1. How are whole-trace and individual-span durations distinguished?
   - A) They are always identical.
   - B) trace:duration and span:duration.
   - C) span.duration is always the intrinsic.
   - D) Count log lines.

<details>
<summary>Show answer</summary>

**Answer: B) trace:duration and span:duration.**

Explicit intrinsics use a colon; span. is the attribute scope.

</details>

---

2. Which query uses the current HTTP response status attribute?
   - A) { order by status desc }
   - B) { span.http.response.status_code >= 500 }
   - C) { duration > p99 }
   - D) { select 500 }

<details>
<summary>Show answer</summary>

**Answer: B) { span.http.response.status_code >= 500 }**

If an SDK still emits http.status_code, inspect its data and use the appropriate legacy query.

</details>

---

3. What does A >> B select?
   - A) All logs before A.
   - B) B spans that descend from A spans.
   - C) The average of A and B.
   - D) B is necessarily the same span as A.

<details>
<summary>Show answer</summary>

**Answer: B) B spans that descend from A spans.**

Place the service selector on the left and DB selector on the right to find descendant DB work.

</details>

---

4. How should SQL-style order by/limit in the old example be replaced?
   - A) Run it unchanged.
   - B) Valid TraceQL plus Grafana search sorting/limit settings.
   - C) Send it to Prometheus.
   - D) Add the DB password to the query.

<details>
<summary>Show answer</summary>

**Answer: B) Valid TraceQL plus Grafana search sorting/limit settings.**

The actual Tempo3.0.3 parser rejects those old sort/order-by/limit examples.

</details>

---

5. What does a service graph require?
   - A) Only installing Tempo.
   - B) Connected spans, a service-graphs processor, a metrics backend and datasource linking.
   - C) Only storing trace IDs as log labels.
   - D) Manually drawing red nodes.

<details>
<summary>Show answer</summary>

**Answer: B) Connected spans, a service-graphs processor, a metrics backend and datasource linking.**

Validate trace ingestion and delivery of graph metrics separately.

</details>

---

6. What can a 1.8-second DB span establish by itself?
   - A) An index is definitely missing.
   - B) The observed operation duration; its cause needs further evidence.
   - C) The network is healthy.
   - D) It is safe to sum it with all parent durations.

<details>
<summary>Show answer</summary>

**Answer: B) The observed operation duration; its cause needs further evidence.**

Check locks, pools, network and query plans; avoid double-counting overlapping spans.

</details>

---

7. How should a derived-field link expression be written in Grafana provisioning?
   - A) Remove all dollar variables with envsubst.
   - B) Escape provisioning substitution with $${__value.raw}.
   - C) Add trace IDs to every stream label.
   - D) Add time bounds as a LogQL SQL clause.

<details>
<summary>Show answer</summary>

**Answer: B) Escape provisioning substitution with $${__value.raw}.**

Actual trace-ID field names and datasource UIDs must also match.

</details>

---

8. What request does an exemplar lead to?
   - A) Necessarily the exact p99-boundary request.
   - B) A representative observation whose trace must still be retained.
   - C) A copy of every request.
   - D) Always retrievable regardless of trace sampling.

<details>
<summary>Show answer</summary>

**Answer: B) A representative observation whose trace must still be retained.**

Sampling and retention can make exemplar IDs and trace availability differ.

</details>

---

9. What does a [30d] query on the first lab day prove?
   - A) A 30-day SLO was met.
   - B) It aggregates available observations; it does not create 30 days of history.
   - C) 100% availability.
   - D) An unlimited error budget.

<details>
<summary>Show answer</summary>

**Answer: B) It aggregates available observations; it does not create 30 days of history.**

Record the actual period, denominator and missing/no-traffic intervals.

</details>

---

10. Which combination of current DB attributes and data handling is correct?
   - A) db.statement is permanently the only standard.
   - B) Inspect db.system.name/db.query.text for the actual SDK and sanitize queries.
   - C) Record every password.
   - D) Renaming a query transforms all old data.

<details>
<summary>Show answer</summary>

**Answer: B) Inspect db.system.name/db.query.text for the actual SDK and sanitize queries.**

Legacy attributes may remain in data; migration and sensitive-data handling are separate.

</details>

---

[Return to the guide](../../../labs/observability/06-distributed-tracing-lab.md)
