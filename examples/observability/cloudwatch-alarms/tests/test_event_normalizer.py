import copy
import importlib.util
from pathlib import Path
import unittest


module_path = Path(__file__).resolve().parents[1] / "event_normalizer.py"
spec = importlib.util.spec_from_file_location("event_normalizer", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def event():
    return {
        "source": "aws.cloudwatch",
        "detail-type": "CloudWatch Alarm State Change",
        "account": "123456789012",
        "region": "ap-northeast-2",
        "resources": [
            "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:EKS-Node-HighCPU"
        ],
        "detail": {
            "alarmName": "EKS-Node-HighCPU",
            "state": {"value": "ALARM"},
            "configuration": {
                "metrics": [
                    {"id": "expression", "expression": "m1"},
                    {
                        "id": "m1",
                        "metricStat": {
                            "metric": {
                                "namespace": "ContainerInsights",
                                "name": "node_cpu_utilization",
                                "dimensions": {"ClusterName": "example-cluster"},
                            },
                            "period": 300,
                            "stat": "Average",
                        },
                    },
                ]
            },
        },
    }


class EventNormalizerTests(unittest.TestCase):
    def normalize(self, payload):
        return module.normalize_alarm_event(
            payload,
            expected_account="123456789012",
            expected_region="ap-northeast-2",
        )

    def test_actual_eventbridge_dimensions_are_a_mapping(self):
        result = self.normalize(event())
        self.assertEqual(
            result["metrics"][0]["dimensions"], {"ClusterName": "example-cluster"}
        )
        self.assertEqual(result["state"], "ALARM")
        self.assertNotIn("action", result)

    def test_expression_query_is_not_assumed_to_be_a_metric(self):
        result = self.normalize(event())
        self.assertEqual(len(result["metrics"]), 1)
        self.assertEqual(result["metrics"][0]["name"], "node_cpu_utilization")

    def test_composite_alarm_has_no_metric_configuration(self):
        payload = event()
        payload["detail"]["configuration"] = {"alarmRule": 'ALARM("child")'}
        self.assertEqual(self.normalize(payload)["metrics"], [])

    def test_recovery_is_preserved_without_dispatching_an_action(self):
        payload = event()
        payload["detail"]["state"]["value"] = "OK"
        self.assertEqual(self.normalize(payload)["state"], "OK")

    def test_wrong_account_region_source_and_type_are_rejected(self):
        for key, value in (
            ("account", "111122223333"),
            ("region", "us-east-1"),
            ("source", "example.app"),
            ("detail-type", "CloudWatch Alarm Configuration Change"),
        ):
            with self.subTest(key=key):
                payload = event()
                payload[key] = value
                with self.assertRaises(ValueError):
                    self.normalize(payload)

    def test_resource_must_match_the_named_alarm(self):
        payload = event()
        payload["resources"][0] += "-another-alarm"
        with self.assertRaises(ValueError):
            self.normalize(payload)

    def test_sns_dimension_list_is_not_accepted_as_eventbridge_format(self):
        payload = event()
        payload["detail"]["configuration"]["metrics"][1]["metricStat"]["metric"][
            "dimensions"
        ] = [{"name": "ClusterName", "value": "example-cluster"}]
        with self.assertRaises(ValueError):
            self.normalize(payload)

    def test_unknown_state_and_incomplete_metric_are_rejected(self):
        payload = event()
        payload["detail"]["state"]["value"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            self.normalize(payload)
        payload = event()
        del payload["detail"]["configuration"]["metrics"][1]["metricStat"]["metric"][
            "namespace"
        ]
        with self.assertRaises(ValueError):
            self.normalize(payload)

    def test_input_is_not_mutated(self):
        payload = event()
        original = copy.deepcopy(payload)
        self.normalize(payload)
        self.assertEqual(payload, original)


if __name__ == "__main__":
    unittest.main()
