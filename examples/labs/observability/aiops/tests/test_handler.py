import unittest,sys,json
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aws_lambda_powertools.utilities.idempotency import BasePersistenceLayer
from aws_lambda_powertools.utilities.idempotency.exceptions import IdempotencyItemAlreadyExistsError,IdempotencyItemNotFoundError
from handler import Reporter
class Memory(BasePersistenceLayer):
 def __init__(self):super().__init__();self.records={}
 def _get_record(self,idempotency_key):
  key=idempotency_key
  if key not in self.records:raise IdempotencyItemNotFoundError
  return self.records[key]
 def _put_record(self,data_record):
  record=data_record
  if record.idempotency_key in self.records:raise IdempotencyItemAlreadyExistsError
  self.records[record.idempotency_key]=record
 def _update_record(self,data_record):self.records[data_record.idempotency_key]=data_record
 def _delete_record(self,data_record):self.records.pop(data_record.idempotency_key,None)
class Handler(unittest.TestCase):
 def setup_reporter(self):
  settings={'input_topic':'arn:aws:sns:us-east-1:123456789012:input','output_topic':'arn:aws:sns:us-east-1:123456789012:output','catalog':{'order-service':{'queue':'orders','log_group':'/lab/orders'}},'allowed_alerts':{'HighLatency'},'alarm_services':{},'model_id':'configured-model'}
  clients={k:Mock() for k in ['sns','bedrock','logs','cloudwatch']};store=Memory();reporter=Reporter(settings,clients,store);context=Mock();context.get_remaining_time_in_millis.return_value=180000
  event={'Records':[{'EventSource':'aws:sns','Sns':{'TopicArn':settings['input_topic'],'MessageId':'one','Message':json.dumps({'alerts':[{'status':'firing','labels':{'alertname':'HighLatency','service':'order-service'}}]})}}]}
  return reporter,clients,store,context,event
 def test_real_powertools_duplicate_skips_analysis_and_publish(self):
  rep,clients,store,ctx,event=self.setup_reporter()
  with patch('handler.collect_metrics',return_value=[]),patch('handler.collect_logs',return_value={'status':'complete','error_records':2}),patch('handler.analyze',return_value='Hypothesis') as model:
   first=rep.handle(event,ctx);second=rep.handle(event,ctx);self.assertEqual(first,second);self.assertEqual(model.call_count,1);self.assertEqual(clients['sns'].publish.call_count,1)
  message=json.loads(clients['sns'].publish.call_args.kwargs['Message']);self.assertTrue(message['human_review_required']);self.assertEqual(message['kind'],'diagnostic-result')
 def test_same_topic_rejected(self):
  rep,clients,store,ctx,event=self.setup_reporter();settings=dict(rep.settings,output_topic=rep.settings['input_topic'])
  with self.assertRaises(ValueError):Reporter(settings,clients,Memory())
 def test_resolved_does_not_publish(self):
  rep,clients,store,ctx,event=self.setup_reporter();event['Records'][0]['Sns']['Message']=json.dumps({'alerts':[{'status':'resolved'}]});result=rep.handle(event,ctx);self.assertEqual(result['records'][0]['status'],'no_firing_alerts');clients['sns'].publish.assert_not_called()
 def test_publish_failure_allows_retry(self):
  rep,clients,store,ctx,event=self.setup_reporter();clients['sns'].publish.side_effect=[RuntimeError('synthetic failure'),{'MessageId':'result'}]
  with patch('handler.collect_metrics',return_value=[]),patch('handler.collect_logs',return_value={'status':'no_data'}),patch('handler.analyze',return_value='Insufficient telemetry'):
   with self.assertRaises(RuntimeError):rep.handle(event,ctx)
   self.assertEqual(store.records,{})
   self.assertEqual(rep.handle(event,ctx)['records'][0]['status'],'report_published')
 def test_low_time_budget_stops_before_sources(self):
  rep,clients,store,ctx,event=self.setup_reporter();ctx.get_remaining_time_in_millis.return_value=1000
  with self.assertRaises(RuntimeError):rep.handle(event,ctx)
  clients['sns'].publish.assert_not_called();self.assertEqual(store.records,{})
if __name__=='__main__':unittest.main()
