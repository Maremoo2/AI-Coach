import io
import json
import unittest
from unittest.mock import patch

from ai_coach.language import expand_reply


class LanguageTests(unittest.TestCase):
    def test_no_consent_means_no_network(self):
        def denied(*args, **kwargs):
            self.fail("Network called without consent")
        result = expand_reply("hello", "grounded", opener=denied)
        self.assertEqual(result["mode"], "DETERMINISTIC_COACH")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "AI_COACH_MODEL": "test-model"})
    def test_only_language_context_sent_and_storage_disabled(self):
        def fake(request, timeout):
            body = json.loads(request.data)
            self.assertFalse(body["store"])
            self.assertNotIn("tools", body)
            self.assertEqual(set(json.loads(body["input"])), {"question", "grounded_answer"})
            return io.BytesIO(json.dumps({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "Støttende svar"}]}]}).encode())
        result = expand_reply("hello", "grounded", consent=True, opener=fake)
        self.assertEqual(result["mode"], "LLM_LANGUAGE_ONLY")
        self.assertFalse(result["plan_changed"])

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "AI_COACH_MODEL": "test-model"})
    def test_timeout_falls_back_without_leaking_credentials(self):
        def timeout(*args, **kwargs):
            raise TimeoutError("secret")
        result = expand_reply("hello", "grounded", consent=True, opener=timeout)
        self.assertEqual(result["message"], "grounded")
        self.assertNotIn("secret", json.dumps(result))
