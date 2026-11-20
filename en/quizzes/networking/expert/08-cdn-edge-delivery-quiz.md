# 08. CDN and Edge Delivery Design Quiz

> **Last Updated**: November 19, 2026

Return to the [workbook](../../../networking/expert/08-cdn-edge-delivery.md).
Choose one answer per question and explain which rule in the workbook supports it.
These are design reasoning exercises, not claims that a distribution was built.

1. A POP misses on a request. In which case does the POP send it **directly to the origin** instead of asking the regional edge cache?
   - A) A `GET` for an image that has never been requested before.
   - B) A `POST` to an API path.
   - C) A `HEAD` for a cached stylesheet whose TTL has expired.

<details>
<summary>Show Answer</summary>

**Answer: B) A `POST` to an API path.**

**Explanation:** Proxy HTTP methods (`PUT`, `POST`, `PATCH`, `OPTIONS`, `DELETE`) go directly from the POP to the origin and do not pass through regional edge caches. Dynamic requests and S3 origins in the same Region as the optimal regional edge cache also skip it. A first-time `GET` is exactly what the regional edge cache is for.

</details>

2. A distribution uses the default cache key. Two viewers request `/content/stories/example-story.html` with different query strings, `User-Agent` values and `session_id` cookies. What happens to the second request?
   - A) It is a cache hit, because by default the key contains only the distribution domain name and the URL path.
   - B) It is a miss, because the query string differs.
   - C) It is a miss, because cookies are always part of the cache key.

<details>
<summary>Show Answer</summary>

**Answer: A) It is a cache hit, because by default the key contains only the distribution domain name and the URL path.**

**Explanation:** Query strings, headers and cookies are not in the default cache key. A cache policy adds them only when they change the response; an origin request policy forwards values to the origin without splitting the cache.

</details>

3. The origin sends `Cache-Control: max-age=600, s-maxage=86400`. The cache policy has minimum TTL 0 and maximum TTL 3600. How long does CloudFront cache the object, and how long do browsers?
   - A) CloudFront 600 seconds, browsers 86,400 seconds.
   - B) CloudFront 86,400 seconds, browsers 600 seconds.
   - C) CloudFront 3,600 seconds, browsers 600 seconds.

<details>
<summary>Show Answer</summary>

**Answer: C) CloudFront 3,600 seconds, browsers 600 seconds.**

**Explanation:** With both directives present and minimum TTL 0, CloudFront caches for the lesser of `s-maxage` and the maximum TTL, while browsers use `max-age`. RFC 9111 gives `s-maxage` priority in shared caches; the distribution's maximum TTL still caps it.

</details>

4. The cache policy's minimum TTL is 300 seconds, and the origin sends `Cache-Control: no-cache` for account pages. What does CloudFront do, and how do you stop it serving an old copy when the origin is unreachable?
   - A) CloudFront never caches `no-cache` responses, so nothing needs to change.
   - B) CloudFront caches the object for the minimum TTL despite `no-cache`, and can serve the earlier copy if the origin is unreachable; adding `Cache-Control: stale-if-error=0` prevents that.
   - C) CloudFront caches it for the default TTL of 24 hours.

<details>
<summary>Show Answer</summary>

**Answer: B) CloudFront caches the object for the minimum TTL despite `no-cache`, and can serve the earlier copy if the origin is unreachable; adding `Cache-Control: stale-if-error=0` prevents that.**

**Explanation:** The Developer Guide warns that a minimum TTL above 0 wins over `no-cache`, `no-store` and `private`. For content that must not be reused, set the minimum TTL to 0 for that behavior, or at least add `stale-if-error=0`.

</details>

5. The origin sends `Cache-Control: max-age=3600, stale-while-revalidate=600`. What happens to a request 65 minutes after the object was cached?
   - A) CloudFront serves the stale copy at once and fetches a fresh one from the origin in the background.
   - B) CloudFront blocks the viewer until the origin returns a fresh copy.
   - C) CloudFront returns `504` because the object is stale.

<details>
<summary>Show Answer</summary>

**Answer: A) CloudFront serves the stale copy at once and fetches a fresh one from the origin in the background.**

**Explanation:** After the one-hour lifetime, `stale-while-revalidate=600` lets CloudFront serve the stale copy for up to 10 minutes while it revalidates asynchronously (RFC 5861). Stale content is served only up to the lesser of the directive and the maximum TTL.

</details>

6. After a bad deployment you invalidate `/app.js`. Some users behind a corporate proxy still get the old file. What prevents this next time?
   - A) Invalidate `/*` instead of `/app.js`.
   - B) Lower the minimum TTL to 0.
   - C) Use versioned file names (for example `app.3f9c.js`) and update the page that references them.

<details>
<summary>Show Answer</summary>

**Answer: C) Use versioned file names (for example `app.3f9c.js`) and update the page that references them.**

**Explanation:** An invalidation removes the object only from POPs and regional edge caches; browser and corporate proxy caches keep the old copy until it expires there. A new name is a new cache key for every cache. Versioning is also cheaper: no invalidation charge, while a `/*` path still counts as one invalidation path.

</details>

7. You run `curl -sI` twice against the same asset. Both responses say `x-cache: Miss from cloudfront`, and `x-amz-cf-pop` differs between them. What is the most likely explanation?
   - A) The two requests reached different POPs, and each edge location caches only the objects it received.
   - B) The distribution's caching is broken.
   - C) `HEAD` requests are never cached.

<details>
<summary>Show Answer</summary>

**Answer: A) The two requests reached different POPs, and each edge location caches only the objects it received.**

**Explanation:** Neither DNS nor anycast steering guarantees that consecutive requests reach the same POP. Compare `x-amz-cf-pop` before drawing conclusions; eviction, cache key contents and the origin's `Cache-Control` are the other causes the Knowledge Center lists.

</details>

8. A response shows `x-cache: Hit from cloudfront`, `date: Thu, 19 Nov 2026 09:00:00 GMT` and `age: 7200`. What can you conclude?
   - A) The origin generated this response two hours ago and the edge served its stored copy; `date` plus `age` is roughly now, 11:00 GMT.
   - B) The origin was contacted for this request and took 7,200 ms to answer.
   - C) The object will expire in 7,200 seconds.

<details>
<summary>Show Answer</summary>

**Answer: A) The origin generated this response two hours ago and the edge served its stored copy; `date` plus `age` is roughly now, 11:00 GMT.**

**Explanation:** RFC 9111 defines `Age` as the seconds since the response was generated or validated at the origin, and its presence implies the origin did not generate the response for this request. Remaining freshness is the lifetime (from `s-maxage` or `max-age`, within the TTL settings) minus `Age`, not `Age` itself.

</details>

9. An internal ALB is a CloudFront VPC origin. Which inbound security group source is the **most restrictive** choice the Developer Guide offers?
   - A) The CloudFront managed prefix list `com.amazonaws.global.cloudfront.origin-facing`.
   - B) The service-managed security group `CloudFront-VPCOrigins-Service-SG`.
   - C) The VPC CIDR.

<details>
<summary>Show Answer</summary>

**Answer: B) The service-managed security group `CloudFront-VPCOrigins-Service-SG`.**

**Explanation:** The managed prefix list contains all CloudFront origin-facing servers, so it admits any distribution; the VPC origin service group restricts traffic to your distributions and exists only after the VPC origin is created. Do not edit that group or create one with the same name prefix. The VPC CIDR is not the CloudFront source at all.

</details>

10. An internet client resolves the internal ALB's DNS name and tries to connect. Why does it fail even before any security group rule is evaluated?
   - A) The DNS name of an internal load balancer does not resolve outside the VPC.
   - B) The nodes of an internal load balancer have only private IP addresses, so nothing on the internet routes to them; the name resolves publicly, but to those private addresses.
   - C) CloudFront blocks the client.

<details>
<summary>Show Answer</summary>

**Answer: B) The nodes of an internal load balancer have only private IP addresses, so nothing on the internet routes to them; the name resolves publicly, but to those private addresses.**

**Explanation:** The ELB guide states that an internal load balancer's DNS name is publicly resolvable to the nodes' private IPs, so only clients with access to the VPC can reach it. That is a routing property, so it holds even if a security group rule is later loosened. CloudFront is not in this client's path at all.

</details>

11. A reviewer objects that the VPC behind a VPC origin has an internet gateway attached. Which statement is correct?
   - A) The internet gateway is required; it denotes that the VPC can receive internet traffic but is not used to route to the origin, and no route table change is needed.
   - B) The internet gateway means the origin subnet must become public.
   - C) The internet gateway must be removed for a VPC origin to work.

<details>
<summary>Show Answer</summary>

**Answer: A) The internet gateway is required; it denotes that the VPC can receive internet traffic but is not used to route to the origin, and no route table change is needed.**

**Explanation:** CloudFront reaches the origin through a service-managed ENI in the private subnet. The origin stays in a private subnet without a public address; the internet gateway is only a VPC-level prerequisite.

</details>

12. Origin Shield is enabled. In standard logs, which field and value show that Origin Shield, not a POP or regional cache, served a request?
   - A) `x-edge-result-type` = `RefreshHit`.
   - B) `x-edge-detailed-result-type` = `OriginShieldHit`.
   - C) `x-edge-result-type` = `Miss`.

<details>
<summary>Show Answer</summary>

**Answer: B) `x-edge-detailed-result-type` = `OriginShieldHit`.**

**Explanation:** `x-edge-detailed-result-type` repeats `x-edge-result-type` except in cases such as Origin Shield hits. A request routed to the regional edge cache that is itself acting as Origin Shield is logged as `Hit`, not `OriginShieldHit`.

</details>

Completion: explain every answer with a rule from the workbook, and attach your header observations or label the work **design review**.
