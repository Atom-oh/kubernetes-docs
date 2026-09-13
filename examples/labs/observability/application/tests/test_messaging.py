import unittest,tempfile,sys,io,json
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import Store
from telemetry import Telemetry
from messaging import Publisher,Consumer
class Messaging(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store('sqlite:///'+str(Path(self.temp.name)/'queue.db'));self.store.initialize();self.t=Telemetry('order-service','native',log_stream=io.StringIO());self.store.create_order('synthetic','product-A',1,'');self.event=self.store.pending_events()[0]
 def tearDown(self):self.t.close();self.store.close();self.temp.cleanup()
 def test_publish_then_mark(self):
  sns=Mock();Publisher(self.store,sns,'arn:aws:sns:us-east-1:123456789012:events',self.t).once();self.assertEqual(self.store.pending_events(),[]);payload=json.loads(sns.publish.call_args.kwargs['Message']);self.assertEqual(payload['id'],self.event['id']);self.assertIn('traceparent',payload)
 def test_failed_publish_keeps_outbox(self):
  sns=Mock();sns.publish.side_effect=RuntimeError('synthetic transport failure')
  with self.assertRaises(RuntimeError):Publisher(self.store,sns,'topic',self.t).once()
  self.assertEqual(len(self.store.pending_events()),1)
 def test_consumer_unwraps_and_deduplicates(self):
  q=Mock();body=json.dumps({'Type':'Notification','Message':json.dumps(self.event),'TopicArn':'topic'});q.receive_message.return_value={'Messages':[{'Body':body,'ReceiptHandle':'receipt'}]};consumer=Consumer(self.store,q,'queue','notification','topic',self.t);consumer.once();consumer.once();self.assertEqual(self.store.consumed_count('notification'),1);self.assertEqual(q.delete_message.call_count,2)
 def test_invalid_message_does_not_ack_or_block_later_message(self):
  q=Mock();q.receive_message.return_value={'Messages':[{'Body':'not-json','ReceiptHandle':'bad'},{'Body':json.dumps({'Type':'Notification','Message':json.dumps(self.event),'TopicArn':'topic'}),'ReceiptHandle':'good'}]};consumer=Consumer(self.store,q,'queue','analytics','topic',self.t);consumer.once();self.assertEqual(self.store.consumed_count('analytics'),1);q.delete_message.assert_called_once_with(QueueUrl='queue',ReceiptHandle='good')
if __name__=='__main__':unittest.main()
