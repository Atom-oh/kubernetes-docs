import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Only run against a lab that you own. Start with the two-iteration smoke test.
const baseURL = (__ENV.BASE_URL || '').replace(/\/+$/, '');
if (!/^https?:\/\/[^/]+(?:\/.*)?$/.test(baseURL)) {
  throw new Error('Set BASE_URL to the HTTP(S) endpoint of your lab.');
}
const profile = __ENV.LOAD_PROFILE || 'smoke';
if (!['smoke', 'scale'].includes(profile)) {
  throw new Error('LOAD_PROFILE must be smoke or scale.');
}
const flowFailed = new Rate('flow_failed');

export const options = {
  ...(profile === 'scale'
    ? {
        stages: [
          { duration: '30s', target: 5 },
          { duration: '60s', target: 5 },
          { duration: '15s', target: 20 },
          { duration: '30s', target: 20 },
          { duration: '15s', target: 5 },
          { duration: '30s', target: 0 },
        ],
      }
    : { vus: 1, iterations: 2 }),
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(95)', 'p(99)'],
  thresholds: {
    // Acceptance criteria for this synthetic exercise, not a measured SLO.
    checks: ['rate==1'],
    flow_failed: ['rate==0'],
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
  },
};

function decode(response) {
  try {
    return response.json();
  } catch (_) {
    return null;
  }
}

export default function () {
  const headers = { 'Content-Type': 'application/json' };
  const order = http.post(
    `${baseURL}/orders`,
    JSON.stringify({
      customer_id: 'synthetic-load-test',
      product_id: 'product-A',
      quantity: 1,
    }),
    { headers, tags: { name: 'POST /orders' }, timeout: '5s' },
  );
  const created = decode(order);
  const validID =
    created &&
    ((typeof created.id === 'number' && Number.isSafeInteger(created.id) && created.id > 0) ||
      (typeof created.id === 'string' && created.id.length > 0));
  if (!check(order, { 'order created with id': (r) => r.status === 201 && !!validID })) {
    flowFailed.add(true);
    sleep(0.1);
    return;
  }

  const payment = http.post(
    `${baseURL}/payments`,
    JSON.stringify({ order_id: created.id, amount: 10.99, payment_method: 'credit_card' }),
    { headers, tags: { name: 'POST /payments' }, timeout: '5s' },
  );
  const paid = decode(payment);
  const paymentOK = check(payment, {
    'payment completed': (r) =>
      [200, 201].includes(r.status) && paid?.status === 'completed',
  });

  const read = http.get(`${baseURL}/orders/${encodeURIComponent(created.id)}`, {
    tags: { name: 'GET /orders/:id' },
    timeout: '5s',
  });
  const stored = decode(read);
  const readOK = check(read, {
    'created order retrieved': (r) => r.status === 200 && stored?.id === created.id,
  });
  flowFailed.add(!(paymentOK && readOK));
  sleep(0.5);
}

export function handleSummary(data) {
  const metrics = data.metrics;
  const failed = metrics.flow_failed?.values.rate;
  const p99 = metrics.http_req_duration?.values['p(99)'];
  return {
    stdout:
      `Requests: ${metrics.http_reqs?.values.count ?? 0}\n` +
      `Failed flows: ${failed === undefined ? 'no samples' : `${failed * 100}%`}\n` +
      `HTTP p99: ${p99 === undefined ? 'no samples' : `${p99.toFixed(2)} ms`}\n`,
    [__ENV.SUMMARY_PATH || 'k6-summary.json']: JSON.stringify(data, null, 2),
  };
}
