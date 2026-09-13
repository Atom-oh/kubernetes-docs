"""Run only against your own lab; pass its endpoint with --host."""

from locust import HttpUser, between, task


def json_object(response):
    try:
        body = response.json()
        return body if isinstance(body, dict) else {}
    except ValueError:
        return {}


class OrderUser(HttpUser):
    wait_time = between(0.5, 1)

    @task
    def order_flow(self):
        with self.client.post(
            "/orders",
            json={
                "customer_id": "synthetic-load-test",
                "product_id": "product-A",
                "quantity": 1,
            },
            name="POST /orders",
            timeout=5,
            catch_response=True,
        ) as response:
            order_id = json_object(response).get("id")
            valid_id = (
                type(order_id) is int and 0 < order_id <= 2**53 - 1
            ) or (isinstance(order_id, str) and bool(order_id))
            if response.status_code != 201 or not valid_id:
                response.failure("order response must be 201 with a valid id")
                return
            response.success()

        with self.client.post(
            "/payments",
            json={
                "order_id": order_id,
                "amount": 10.99,
                "payment_method": "credit_card",
            },
            name="POST /payments",
            timeout=5,
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201) or json_object(response).get(
                "status"
            ) != "completed":
                response.failure("payment was not completed")
            else:
                response.success()

        from urllib.parse import quote

        with self.client.get(
            f"/orders/{quote(str(order_id), safe='')}",
            name="GET /orders/:id",
            timeout=5,
            catch_response=True,
        ) as response:
            if response.status_code != 200 or json_object(response).get("id") != order_id:
                response.failure("response did not contain the created order")
            else:
                response.success()
