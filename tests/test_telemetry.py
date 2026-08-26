"""
Unit tests for ApiPatch Anonymous Telemetry module.
"""

import os
import uuid
import unittest
from unittest.mock import patch, MagicMock
from apipatch.telemetry import (
    is_telemetry_enabled,
    get_anonymous_id,
    track_cli_event,
    _send_payload_async
)


class TestTelemetry(unittest.TestCase):

    def test_is_telemetry_enabled_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(is_telemetry_enabled())

    def test_is_telemetry_opt_out_do_not_track(self):
        with patch.dict(os.environ, {"DO_NOT_TRACK": "1"}):
            self.assertFalse(is_telemetry_enabled())

    def test_is_telemetry_opt_out_apipatch_env(self):
        with patch.dict(os.environ, {"APIPATCH_NO_TELEMETRY": "true"}):
            self.assertFalse(is_telemetry_enabled())

    def test_get_anonymous_id(self):
        anon_id = get_anonymous_id()
        self.assertIsInstance(anon_id, str)
        self.assertTrue(len(anon_id) > 10)
        # Check consistent cached return
        self.assertEqual(get_anonymous_id(), anon_id)

    @patch("apipatch.telemetry._send_payload_async")
    def test_track_cli_event(self, mock_send):
        with patch.dict(os.environ, {}, clear=True):
            track_cli_event("scan", {"files_count": 5})
            import time
            time.sleep(0.1)
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args["event"], "cli_command")
            self.assertEqual(call_args["properties"]["command"], "scan")
            self.assertEqual(call_args["properties"]["files_count"], 5)

    @patch("urllib.request.urlopen")
    def test_send_payload_async_silent_on_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Network unreachable")
        # Must not raise any exception
        _send_payload_async({"test": "data"})


if __name__ == "__main__":
    unittest.main()
