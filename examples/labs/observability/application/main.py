"""Run one synthetic lab role; initialize its database explicitly first."""

import argparse
import os
import threading

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import SQLAlchemyError
import uvicorn

from api import create_app
from db_config import load_database_url
from messaging import Consumer, Publisher
from storage import Store
from telemetry import Telemetry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "serve"])
    parser.add_argument("--role", default=os.getenv("LAB_ROLE", "order-service"))
    parser.add_argument("--database-url-file", default=os.getenv("DATABASE_URL_FILE"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    store = None
    if args.command == "init-db" or args.role != "api-gateway":
        if not args.database_url_file:
            parser.error("Use --database-url-file with a private file or mounted Secret")
        store = Store(load_database_url(args.database_url_file))
    if args.command == "init-db":
        try:
            store.initialize()
        finally:
            store.close()
        return

    telemetry = Telemetry(
        args.role, os.getenv("LAB_REVISION", "local"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"),
    )
    stop = threading.Event()
    worker = None
    try:
        if args.role in ("order-service", "payment-service", "notification", "analytics"):
            topic = os.environ["EVENT_TOPIC_ARN"]
            config = Config(connect_timeout=2, read_timeout=8,
                            retries={"mode": "standard", "total_max_attempts": 2})
            session = boto3.Session()
            if args.role in ("order-service", "payment-service"):
                processor = Publisher(store, session.client("sns", config=config), topic, telemetry)
            else:
                processor = Consumer(
                    store, session.client("sqs", config=config),
                    os.environ["QUEUE_URL"], args.role, topic, telemetry,
                )

            def process():
                while not stop.is_set():
                    try:
                        processor.once()
                    except (ClientError, BotoCoreError, SQLAlchemyError, ValueError):
                        telemetry.log("ERROR", "background_iteration_failed")
                    stop.wait(1)

            worker = threading.Thread(target=process, name="lab-events", daemon=True)
            worker.start()
        app = create_app(
            args.role, store, telemetry,
            order_url=os.getenv("ORDER_SERVICE_URL"),
            payment_url=os.getenv("PAYMENT_SERVICE_URL"),
            delay_ms=int(os.getenv("LAB_DELAY_MS", "0")),
        )
        uvicorn.run(app, host=args.host, port=args.port, access_log=False, log_level="warning")
    finally:
        stop.set()
        if worker is not None:
            worker.join(timeout=20)
        telemetry.close()
        if store is not None:
            store.close()


if __name__ == "__main__":
    main()
