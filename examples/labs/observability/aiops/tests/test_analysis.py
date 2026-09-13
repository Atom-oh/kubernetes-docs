import unittest,sys,json
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import analyze
class Analysis(unittest.TestCase):
 def test_bounded_converse_and_text(self):
  client=Mock();client.converse.return_value={'stopReason':'end_turn','output':{'message':{'content':[{'text':'Hypothesis: queue backlog.'}]}}}
  result=analyze(client,'configured-model',{'service':'order-service','metrics':[{'status':'complete','samples':[{'value':3}]}],'logs':{'status':'complete','error_records':2}})
  self.assertEqual(result,'Hypothesis: queue backlog.');kwargs=client.converse.call_args.kwargs;self.assertEqual(kwargs['inferenceConfig']['maxTokens'],1024);self.assertNotIn('toolConfig',kwargs)
 def test_truncation_not_success(self):
  client=Mock();client.converse.return_value={'stopReason':'max_tokens','output':{'message':{'content':[{'text':'Incomplete...'}]}}}
  with self.assertRaises(RuntimeError):analyze(client,'configured-model',{'logs':{'status':'complete','error_records':1}})
 def test_no_evidence_no_model_call(self):
  client=Mock();result=analyze(client,'configured-model',{'metrics':[],'logs':{'status':'no_data'}});self.assertIn('Insufficient',result);client.converse.assert_not_called()
 def test_managed_prompt_arn_rejected(self):
  with self.assertRaises(ValueError):analyze(Mock(),'arn:aws:bedrock:us-east-1:123456789012:prompt/ABC:1',{})
if __name__=='__main__':unittest.main()
