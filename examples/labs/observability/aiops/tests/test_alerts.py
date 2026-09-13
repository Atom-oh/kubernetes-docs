import json,unittest,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alerts import normalize_event
TOPIC='arn:aws:sns:us-east-1:123456789012:lab-input'
def event(payload,message='test-message',topic=TOPIC):
 return {'Records':[{'EventSource':'aws:sns','Sns':{'TopicArn':topic,'MessageId':message,'Message':json.dumps(payload)}}]}
class Alerts(unittest.TestCase):
 def test_lowercase_alertmanager(self):
  p={'alerts':[{'status':'firing','labels':{'alertname':'HighLatency','service':'order-service'},'startsAt':'2026-09-13T00:00:00Z'},{'status':'resolved','labels':{'alertname':'HighLatency','service':'order-service'}}]}
  rows=normalize_event(event(p),TOPIC,{'HighLatency'}, {'order-service'}, {})
  self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['alerts']),1)
 def test_capitalized_alertmanager(self):
  p={'Alerts':[{'Status':'firing','Labels':{'alertname':'HighLatency','service':'order-service'},'StartsAt':'2026-09-13T00:00:00Z'}]}
  self.assertEqual(normalize_event(event(p),TOPIC,{'HighLatency'}, {'order-service'}, {})[0]['alerts'][0]['service'],'order-service')
 def test_cloudwatch_alarm_and_ok(self):
  p={'AlarmName':'lab-queue-backlog','NewStateValue':'ALARM','StateChangeTime':'2026-09-13T00:00:00Z'}
  self.assertEqual(len(normalize_event(event(p),TOPIC,set(),{'order-service'},{'lab-queue-backlog':'order-service'})[0]['alerts']),1)
  p['NewStateValue']='OK';self.assertEqual(normalize_event(event(p),TOPIC,set(),{'order-service'},{'lab-queue-backlog':'order-service'})[0]['alerts'],[])
 def test_reject_other_topic(self):
  with self.assertRaises(ValueError):normalize_event(event({},topic=TOPIC+'-output'),TOPIC,set(),set(),{})
 def test_reject_unknown_format(self):
  with self.assertRaises(ValueError):normalize_event(event({'analysis':'do not recurse'}),TOPIC,set(),set(),{})
 def test_reject_unknown_service(self):
  p={'alerts':[{'status':'firing','labels':{'alertname':'HighLatency','service':'unexpected'}}]}
  with self.assertRaises(ValueError):normalize_event(event(p),TOPIC,{'HighLatency'},{'order-service'},{})
 def test_preserve_multiple_records(self):
  e=event({'alerts':[]});e['Records']+=event({'Alerts':[]},message='second')['Records'];self.assertEqual(len(normalize_event(e,TOPIC,set(),set(),{})),2)
 def test_reject_malformed_json(self):
  e=event({});e['Records'][0]['Sns']['Message']='<not-json>'
  with self.assertRaises(ValueError):normalize_event(e,TOPIC,set(),set(),{})
 def test_ignore_raw_annotations(self):
  p={'alerts':[{'status':'firing','labels':{'alertname':'HighLatency','service':'order-service','customer':'private'},'annotations':{'description':'secret text'}}]}
  result=normalize_event(event(p),TOPIC,{'HighLatency'},{'order-service'},{})
  self.assertNotIn('secret text',json.dumps(result));self.assertNotIn('private',json.dumps(result))
if __name__=='__main__':unittest.main()
