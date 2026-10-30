"""Render Vega, since Streamlit AppTest does not execute browser chart JavaScript.

Install requirements-test.txt to include these renderer checks in the test suite.
"""
import copy
import unittest
from collections import Counter

try:
    import vl_convert as vlc
except ImportError:
    vlc = None

from leakprobe.ui.monitoring import _network_map_spec


@unittest.skipIf(vlc is None, "Install requirements-test.txt for JavaScript chart-runtime tests")
class NetworkSchematicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from leakprobe.ui.data_access import load_network_layout
        cls.layout = load_network_layout()

    def assert_renderable(self, spec, version="5.20"):
        compiled = vlc.vegalite_to_vega(spec, vl_version=version)

        def check_scope(scope):
            counts = Counter(signal["name"] for signal in scope.get("signals", []))
            self.assertEqual({name: count for name, count in counts.items() if count > 1}, {})
            for mark in scope.get("marks", []):
                check_scope(mark)

        check_scope(compiled)
        svg = vlc.vegalite_to_svg(spec, vl_version=version)
        self.assertIn("<svg", svg)
        self.assertIn("#dc2626", svg) if spec["layer"][-1]["data"]["values"] else None
        self.assertTrue(any(signal["name"] == "network_view_x" for signal in compiled["signals"]))
        self.assertTrue(any(signal["name"] == "network_view_y" for signal in compiled["signals"]))

    def test_real_network_renders_for_candidate_and_normal_states(self):
        for candidate in ("202", None, "unknown-pipe"):
            with self.subTest(candidate=candidate):
                self.assert_renderable(_network_map_spec(self.layout, candidate))

    def test_compact_map_renders_with_older_vega_lite(self):
        spec = _network_map_spec(self.layout, "202")
        spec["height"] = 330
        self.assert_renderable(spec, version="5.8")

    def test_empty_background_layer_still_renders(self):
        layout = copy.deepcopy(self.layout)
        layout["pipes"] = [pipe for pipe in layout["pipes"] if pipe["id"] == "202"]
        self.assert_renderable(_network_map_spec(layout, "202"))

    def test_monitoring_workspace_highlight_renders_in_both_runtimes(self):
        from leakprobe.ui.monitoring_views import workspace_map_spec
        for version in ("5.8", "5.20"):
            for candidate in ("202", None):
                with self.subTest(version=version, candidate=candidate):
                    svg = vlc.vegalite_to_svg(workspace_map_spec(self.layout, candidate), vl_version=version)
                    self.assertIn("<svg", svg)
                    if candidate:
                        self.assertIn("#bd541d", svg)

    def test_old_top_level_selection_reproduces_reported_failure(self):
        spec = _network_map_spec(self.layout, "202")
        spec["params"] = spec["layer"][0].pop("params")
        with self.assertRaisesRegex(ValueError, "Duplicate signal name"):
            vlc.vegalite_to_svg(spec, vl_version="5.20")


if __name__ == "__main__":
    unittest.main()
