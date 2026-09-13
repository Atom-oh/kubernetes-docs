import unittest,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence import collect_logs, collect_metrics
class Evidence(unittest.TestCase):
 def test_logs_wait_until_complete(self):
  client=Mock();client.start_query.return_value={'queryId':'query-1'};client.get_query_results.side_effect=[{'status':'Running','results':[]},{'status':'Complete','results':[[{'field':'error_records','value':'3'}]]}]
  now=datetime.now(timezone.utc);result=collect_logs(client,'/lab/orders','order-service',now-timedelta(minutes=15),now,sleep=lambda _:None)
  self.assertEqual(result['status'],'complete');self.assertEqual(result['error_records'],3);client.stop_query.assert_not_called()
 def test_timeout_cancels_query(self):
  client=Mock();client.start_query.return_value={'queryId':'query-1'};client.get_query_results.return_value={'status':'Running','results':[]}
  now=datetime.now(timezone.utc);result=collect_logs(client,'/lab/orders','order-service',now-timedelta(minutes=15),now,sleep=lambda _:None,polls=2)
  self.assertEqual(result['status'],'timeout');self.assertNotIn('error_records',result);client.stop_query.assert_called_once_with(queryId='query-1')
 def test_failed_is_not_zero_errors(self):
  client=Mock();client.start_query.return_value={'queryId':'query-1'};client.get_query_results.return_value={'status':'Failed','results':[]};now=datetime.now(timezone.utc)
  result=collect_logs(client,'/lab/orders','order-service',now-timedelta(minutes=15),now,sleep=lambda _:None);self.assertEqual(result['status'],'failed');self.assertNotIn('error_records',result)
 def test_empty_query_results_not_invented(self):
  client=Mock();client.start_query.return_value={'queryId':'query-1'};client.get_query_results.return_value={'status':'Complete','results':[]};now=datetime.now(timezone.utc)
  result=collect_logs(client,'/lab/orders','order-service',now-timedelta(minutes=15),now,sleep=lambda _:None);self.assertEqual(result['status'],'no_data');self.assertNotIn('error_records',result)
 def test_service_cannot_inject_query(self):
  with self.assertRaises(ValueError):collect_logs(Mock(),'/lab/orders','x" | fields @message',datetime.now(timezone.utc),datetime.now(timezone.utc))
 def test_metrics_real_values_and_utc_json(self):
  client=Mock();now=datetime.now(timezone.utc);client.get_paginator.return_value.paginate.return_value=[{'MetricDataResults':[{'Id':'queue_visible','StatusCode':'Complete','Timestamps':[now],'Values':[5]}]}]
  result=collect_metrics(client,{'queue':'lab-orders'},now-timedelta(minutes=15),now);self.assertEqual(result[0]['samples'][0]['value'],5);self.assertEqual(result[0]['samples'][0]['timestamp'],now.isoformat())
if __name__=='__main__':unittest.main()
