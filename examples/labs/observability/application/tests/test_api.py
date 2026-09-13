import unittest,tempfile,sys,io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from storage import Store
from telemetry import Telemetry
from api import create_app
class API(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store('sqlite:///'+str(Path(self.temp.name)/'api.db'));self.store.initialize();self.telemetry=Telemetry('order-service','test',log_stream=io.StringIO());self.client=TestClient(create_app('order-service',self.store,self.telemetry))
 def tearDown(self):self.client.close();self.store.close();self.telemetry.close();self.temp.cleanup()
 def test_create_read_missing(self):
  r=self.client.post('/orders',json={'customer_id':'synthetic','product_id':'product-A','quantity':1});self.assertEqual(r.status_code,201);i=r.json()['id'];self.assertEqual(self.client.get('/orders/'+i).json()['id'],i);self.assertEqual(self.client.get('/orders/missing').status_code,404)
 def test_validation_and_health(self):
  self.assertEqual(self.client.post('/orders',json={'customer_id':'x','product_id':'y','quantity':0}).status_code,422);self.assertEqual(self.client.get('/health').status_code,200)
 def test_readiness_detects_uninitialized_database(self):
  uninitialized=Store('sqlite:///'+str(Path(self.temp.name)/'empty.db'));client=TestClient(create_app('order-service',uninitialized,self.telemetry))
  try:self.assertEqual(client.get('/health').status_code,200);self.assertEqual(client.get('/ready').status_code,503)
  finally:client.close();uninitialized.close()
 def test_metrics_route_is_bounded(self):
  self.client.get('/orders/unknown-one');self.client.get('/orders/unknown-two');body=self.client.get('/metrics').text;self.assertIn('/orders/{order_id}',body);self.assertNotIn('unknown-one',body);self.assertNotIn('unknown-two',body)
if __name__=='__main__':unittest.main()
