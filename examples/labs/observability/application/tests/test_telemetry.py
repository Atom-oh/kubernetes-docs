import unittest,sys,json,io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from telemetry import Telemetry
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
class TelemetryTest(unittest.TestCase):
 def test_span_log_and_exemplar_share_trace(self):
  exporter=InMemorySpanExporter();out=io.StringIO();t=Telemetry('order-service','test-r1',exporter=exporter,log_stream=out)
  with t.server_span('POST /orders',{}) as span:
   t.record_http('POST /orders',201,.02,span)
   headers=t.inject();self.assertIn('traceparent',headers);t.log('INFO','request_complete',span)
  spans=exporter.get_finished_spans();self.assertEqual(len(spans),1);trace=f'{spans[0].context.trace_id:032x}';log=json.loads(out.getvalue());self.assertEqual(log['trace_id'],trace);self.assertEqual(log['service'],'order-service');self.assertIn(trace,t.metrics().decode());t.close()
 def test_propagation_between_service_providers(self):
  a=InMemorySpanExporter();b=InMemorySpanExporter();left=Telemetry('api-gateway','r1',exporter=a,log_stream=io.StringIO());right=Telemetry('order-service','r1',exporter=b,log_stream=io.StringIO())
  with left.server_span('POST /orders',{}):
   with right.server_span('POST /orders',left.inject()):pass
  x=a.get_finished_spans()[0];y=b.get_finished_spans()[0];self.assertEqual(x.context.trace_id,y.context.trace_id);self.assertEqual(y.parent.span_id,x.context.span_id);left.close();right.close()
if __name__=='__main__':unittest.main()
