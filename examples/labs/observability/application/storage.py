"""Service-owned tables and transactional outbox for synthetic lab events."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, Integer, JSON, MetaData, String, Table,
    create_engine, func, insert, select, update,
)
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
orders = Table(
    "lab_orders", metadata,
    Column("id", String(36), primary_key=True),
    Column("customer_id", String(64), nullable=False),
    Column("product_id", String(64), nullable=False),
    Column("quantity", Integer, nullable=False),
)
payments = Table(
    "lab_payments", metadata,
    Column("order_id", String(36), primary_key=True),
    Column("amount_cents", Integer, nullable=False),
    Column("method", String(32), nullable=False),
)
outbox = Table(
    "lab_outbox", metadata,
    Column("id", String(36), primary_key=True),
    Column("event_type", String(32), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("traceparent", String(256), nullable=False),
    Column("created_at", String(64), nullable=False),
    Column("published", Boolean, nullable=False, default=False),
)
inbox = Table(
    "lab_inbox", metadata,
    Column("consumer", String(32), primary_key=True),
    Column("event_id", String(36), primary_key=True),
    Column("event_type", String(32), nullable=False),
    Column("payload", JSON, nullable=False),
)


class Store:
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True, hide_parameters=True)

    def initialize(self):
        # Run as an explicit migration/init step before starting replicas.
        metadata.create_all(self.engine)

    def close(self):
        self.engine.dispose()

    def ready(self):
        with self.engine.connect() as connection:
            # Also confirms initialization, not just database connectivity.
            connection.execute(select(outbox.c.id).limit(0))

    @staticmethod
    def _event(connection, event_type, payload, traceparent):
        connection.execute(insert(outbox).values(
            id=str(uuid4()), event_type=event_type, payload=payload,
            traceparent=traceparent, created_at=datetime.now(timezone.utc).isoformat(),
            published=False,
        ))

    def create_order(self, customer_id, product_id, quantity, traceparent):
        if type(quantity) is not int or not 1 <= quantity <= 100:
            raise ValueError("quantity must be between one and one hundred")
        row = {
            "id": str(uuid4()), "customer_id": customer_id,
            "product_id": product_id, "quantity": quantity,
        }
        with self.engine.begin() as connection:
            connection.execute(insert(orders).values(**row))
            self._event(
                connection, "order.created",
                {"order_id": row["id"], "quantity": quantity}, traceparent,
            )
        return row

    def get_order(self, order_id):
        with self.engine.connect() as connection:
            row = connection.execute(select(orders).where(orders.c.id == order_id)).mappings().first()
        return dict(row) if row else None

    def record_payment(self, order_id, amount_cents, method, traceparent):
        if type(amount_cents) is not int or not 0 < amount_cents <= 100_000_000:
            raise ValueError("invalid synthetic payment amount")
        row = {"order_id": order_id, "amount_cents": amount_cents, "method": method}
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(payments).values(**row))
                self._event(connection, "payment.completed", {"order_id": order_id}, traceparent)
        except IntegrityError:
            with self.engine.connect() as connection:
                existing = connection.execute(
                    select(payments).where(payments.c.order_id == order_id)
                ).mappings().first()
            if not existing or dict(existing) != row:
                raise ValueError("conflicting synthetic payment") from None
        return {"order_id": order_id, "status": "completed", "synthetic": True}

    def pending_events(self, limit=20):
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(outbox).where(outbox.c.published.is_(False))
                .order_by(outbox.c.created_at, outbox.c.id).limit(limit)
            ).mappings().all()
        return [dict(row) for row in rows]

    def mark_published(self, event_id):
        with self.engine.begin() as connection:
            connection.execute(
                update(outbox).where(outbox.c.id == event_id).values(published=True)
            )

    def consume(self, consumer, event):
        if consumer not in ("notification", "analytics"):
            raise ValueError("unknown lab consumer")
        if event["event_type"] not in ("order.created", "payment.completed"):
            raise ValueError("unknown lab event")
        # The persisted notification/analytics record is the entire synthetic
        # effect. This does not send email, charge a card or claim those external
        # side effects can be made atomic with this transaction.
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(inbox).values(
                    consumer=consumer, event_id=event["id"],
                    event_type=event["event_type"], payload=event["payload"],
                ))
        except IntegrityError:
            with self.engine.connect() as connection:
                prior = connection.execute(select(inbox).where(
                    inbox.c.consumer == consumer, inbox.c.event_id == event["id"],
                )).mappings().first()
            if not prior or prior["event_type"] != event["event_type"] or prior["payload"] != event["payload"]:
                raise ValueError("conflicting duplicate event") from None
            return False
        return True

    def consumed_count(self, consumer):
        with self.engine.connect() as connection:
            return connection.execute(
                select(func.count()).select_from(inbox).where(inbox.c.consumer == consumer)
            ).scalar_one()
