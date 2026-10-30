import unittest

from leakprobe.net3_tools import Net3Investigation, dispatch_net3


class FullChannelToolTests(unittest.TestCase):
    def test_observation_tool_returns_all_required_channels(self):
        session = Net3Investigation()
        result = dispatch_net3(session, "get_observations", {})

        self.assertEqual(result["pressure_channel_count"], 92)
        self.assertEqual(result["flow_channel_count"], 117)
        first = result["readings"][0]
        self.assertEqual(sum(name.startswith("pressure_") for name in first), 92)
        self.assertEqual(sum(name.startswith("flow_") for name in first), 117)

    def test_schema_and_tool_allowlist_reject_other_requests(self):
        session = Net3Investigation()
        self.assertIn("error", dispatch_net3(session, "shell", {}))
        self.assertIn("error", dispatch_net3(session, "get_observations", {"path": "/etc/passwd"}))


if __name__ == "__main__":
    unittest.main()
