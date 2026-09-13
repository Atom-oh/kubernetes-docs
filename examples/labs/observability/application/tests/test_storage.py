import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import Store, orders
from sqlalchemy import select, func
from unittest.mock import patch
class Storage(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store('sqlite:///'+str(Path(self.temp.name)/'lab.db'));self.store.initialize()
 def tearDown(self):self.store.close();self.temp.cleanup()
 def test_order_and_event_commit_together(self):
  order=self.store.create_order('synthetic','product-A',1,'trace-context');self.assertEqual(self.store.get_order(order['id'])['id'],order['id']);events=self.store.pending_events();self.assertEqual(len(events),1);self.assertEqual(events[0]['payload']['order_id'],order['id']);self.assertEqual(events[0]['traceparent'],'trace-context')
 def test_invalid_order_does_not_leave_event(self):
  with self.assertRaises(ValueError):self.store.create_order('synthetic','product-A',0,'')
  self.assertEqual(self.store.pending_events(),[])
 def test_outbox_failure_rolls_back_order(self):
  with patch.object(Store, '_event', side_effect=RuntimeError('synthetic outbox failure')):
   with self.assertRaises(RuntimeError):self.store.create_order('synthetic','product-A',1,'')
  with self.store.engine.connect() as connection:
   self.assertEqual(connection.execute(select(func.count()).select_from(orders)).scalar_one(),0)
  self.assertEqual(self.store.pending_events(),[])
 def test_payment_idempotency_and_conflict(self):
  order=self.store.create_order('synthetic','product-A',1,'');a=self.store.record_payment(order['id'],1099,'credit_card','');b=self.store.record_payment(order['id'],1099,'credit_card','');self.assertEqual(a,b);self.assertEqual(len(self.store.pending_events()),2)
  with self.assertRaises(ValueError):self.store.record_payment(order['id'],2099,'credit_card','')
 def test_outbox_only_marked_after_publish(self):
  self.store.create_order('synthetic','product-A',1,'');event=self.store.pending_events()[0];self.store.mark_published(event['id']);self.assertEqual(self.store.pending_events(),[])
 def test_each_consumer_deduplicates_event(self):
  self.store.create_order('synthetic','product-A',1,'');event=self.store.pending_events()[0];self.assertTrue(self.store.consume('notification',event));self.assertFalse(self.store.consume('notification',event));self.assertTrue(self.store.consume('analytics',event));self.assertEqual(self.store.consumed_count('notification'),1);self.assertEqual(self.store.consumed_count('analytics'),1)
if __name__=='__main__':unittest.main()
