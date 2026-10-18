import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

spec = importlib.util.spec_from_file_location(
    "bedrock_translation", Path(__file__).resolve().parents[1] / "bedrock-translation.py")
translation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translation)


def response(text="translated", status="completed", model=translation.MODEL):
    return {
        "model": model, "status": status,
        "output": [
            {"type": "reasoning", "content": [{"type": "output_text", "text": "hidden reasoning"}]},
            {"type": "message", "status": "completed", "content": [{"type": "output_text", "text": text}]},
        ],
    }


class TranslationTests(unittest.TestCase):
    def test_only_completed_message_text_is_used(self):
        self.assertEqual(translation.response_text(response(), translation.MODEL), "translated")

    def test_capped_failed_empty_and_refused_responses_are_rejected(self):
        for data in [response(status="incomplete"), response(status="failed"), response(text=""),
                     {**response(), "error": {"message": "provider error"}}]:
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                translation.response_text(data, translation.MODEL)
        refused = response()
        refused["output"][1]["content"] = [{"type": "refusal", "refusal": "no"}]
        with self.assertRaisesRegex(RuntimeError, "refused"):
            translation.response_text(refused, translation.MODEL)
        for status in ["incomplete", None]:
            data = response()
            data["output"][1]["status"] = status
            with self.subTest(message_status=status), self.assertRaisesRegex(RuntimeError, "Incomplete"):
                translation.response_text(data, translation.MODEL)

    def test_different_model_is_fatal_instead_of_silent_fallback(self):
        with self.assertRaises(translation.ConfigurationError):
            translation.response_text(response(model="another-model"), translation.MODEL)

    def test_failed_response_preserves_prior_file_and_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory) / "source.md", Path(directory) / "target.md"
            src.write_text("# English\n\n```yaml\nkind: Pod\n```\n")
            dst.write_text("# Previous\n")
            with self.assertRaises(RuntimeError):
                translation.translate_document(src, dst, "cn", call=Mock(side_effect=RuntimeError("incomplete")))
            self.assertEqual(dst.read_text(), "# Previous\n")
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["source.md", "target.md"])

    def test_large_document_goes_in_body_and_utf8_output_is_written_without_wrappers(self):
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory) / "source.md", Path(directory) / "jp/page.md"
            source = "# Source\n\n" + "Source paragraph.\n" * 9000
            src.write_text(source)
            call = Mock(return_value="# 日本語\n\n```yaml\nkind: Pod\n```\n")
            translation.translate_document(src, dst, "jp", call=call)
            self.assertEqual(dst.read_text(), "# 日本語\n\n```yaml\nkind: Pod\n```\n")
            self.assertIn(source, call.call_args.args[0])
            self.assertEqual(call.call_args.args[1], 65536)

    def call_with_transport(self, transport, credentials=True, environ=None):
        # Unit tests don't require AWS packages or credentials. The live
        # preflight separately exercises the actual SDK signing and IAM access.
        session = Mock()
        session.get_credentials.return_value = Mock() if credentials else None
        request = Mock()
        request.prepare.return_value.headers = {"Authorization": "fixture-signature"}
        aws_request = Mock(return_value=request)
        signer = Mock()
        modules = {
            "boto3": types.SimpleNamespace(Session=Mock(return_value=session)),
            "botocore.auth": types.SimpleNamespace(SigV4Auth=signer),
            "botocore.awsrequest": types.SimpleNamespace(AWSRequest=aws_request),
            "botocore.exceptions": types.SimpleNamespace(BotoCoreError=type("BotoCoreError", (Exception,), {})),
        }
        with patch.dict(sys.modules, modules), patch.dict(os.environ, environ or {}, clear=True), \
             patch.object(translation.urllib.request, "urlopen", transport):
            result = translation.complete("public source document", 4096)
        return result, aws_request, signer

    def test_mantle_route_model_sigv4_and_provider_default_parameters(self):
        transport = MagicMock()
        transport.return_value.__enter__.return_value = io.BytesIO(json.dumps(response()).encode())
        result, request, signer = self.call_with_transport(transport)
        self.assertEqual(result, "translated")
        args = request.call_args.kwargs
        self.assertEqual(args["url"], "https://bedrock-mantle.us-east-1.api.aws/openai/v1/responses")
        payload = json.loads(args["data"])
        self.assertEqual(payload["model"], "openai.gpt-6-luna")
        self.assertEqual(payload["max_output_tokens"], 4096)
        self.assertNotIn("temperature", payload)
        self.assertNotIn("reasoning", payload)
        self.assertEqual(signer.call_args.args[1:], ("bedrock-mantle", "us-east-1"))

    def test_missing_credentials_and_wrong_model_configuration_stop_before_http(self):
        for credentials, env in [(False, {}), (True, {"TRANSLATION_MODEL": "gpt-6-luna"})]:
            transport = Mock()
            with self.subTest(env=env), self.assertRaises(translation.ConfigurationError):
                self.call_with_transport(transport, credentials, env)
            transport.assert_not_called()

    def test_access_denied_and_unavailable_model_errors_are_fatal(self):
        for status, message in [(403, "Access denied"), (404, "Model not found"),
                                (400, "The model is not available")]:
            error = urllib.error.HTTPError("https://fixture.invalid", status, "error", {}, io.BytesIO(message.encode()))
            with self.subTest(status=status), self.assertRaises(translation.ConfigurationError):
                self.call_with_transport(Mock(side_effect=error))

    def test_throttling_remains_retryable(self):
        error = urllib.error.HTTPError("https://fixture.invalid", 429, "retry", {}, io.BytesIO(b"Throttling"))
        with self.assertRaises(RuntimeError) as caught:
            self.call_with_transport(Mock(side_effect=error))
        self.assertNotIsInstance(caught.exception, translation.ConfigurationError)


if __name__ == "__main__":
    unittest.main()
