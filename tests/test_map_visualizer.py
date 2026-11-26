import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal
import plotly.graph_objects as go

from map_visualizer import MapVisualizer


class MapVisualizerTests(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.visualizer = MapVisualizer(Path(self._temporary.name) / "missing.geojson")
        self.data = pd.DataFrame({
            "district_code": ["001", "002", "003", "004", "005"],
            "district_name": ["강남역", "홍대입구역", "시장", "관광특구", "상권"],
            "district_type": ["Alley", "Developed", "Traditional market", "Tourist zone", "Alley"],
            "total_sales": pd.Series([1000000, 4000000, 0, pd.NA, 3000000], dtype="Int64"),
            "total_transactions": pd.Series([100, 0, 0, pd.NA, 20], dtype="Int64"),
            "latitude": [37.50, 37.55, 37.60, 37.57, float("nan")],
            "longitude": [127.00, 126.92, 127.02, 126.99, float("nan")],
        })

    @staticmethod
    def _points(figure):
        return {code: (lat, lon, list(detail), text)
                for trace in figure.data
                for code, lat, lon, detail, text in zip(
                    trace.ids, trace.lat, trace.lon, trace.customdata, trace.text)}

    def test_plot_returns_scattermap_with_one_area_scale(self):
        figure = self.visualizer.plot_map(self.data)
        scaled = [trace for trace in figure.data if trace.marker.sizeref is not None]

        self.assertIsInstance(figure, go.Figure)
        self.assertTrue(all(trace.type == "scattermap" for trace in figure.data))
        self.assertEqual(len(scaled), 2)
        self.assertEqual({trace.marker.sizeref for trace in scaled}, {2 * 4000000 / 44 ** 2})
        self.assertTrue(all(trace.marker.sizemode == "area" for trace in scaled))
        self.assertTrue(all(trace.marker.sizemin == 4 for trace in scaled))
        self.assertEqual(figure.layout.height, 600)
        self.assertEqual(figure.layout.map.style, "carto-positron")
        self.assertEqual(figure.layout.map.zoom, 10.3)

    def test_hover_preserves_codes_coordinates_and_exact_values(self):
        figure = self.visualizer.plot_map(self.data)
        points = self._points(figure)

        self.assertEqual(set(points), {"001", "002", "003", "004"})
        self.assertEqual(points["001"][:2], (37.50, 127.00))
        self.assertEqual(points["001"][2][3:], ["1,000,000", "100"])
        self.assertEqual(points["001"][3], "Gangnam Station")
        self.assertEqual(points["001"][2][1], "강남역")
        self.assertEqual(points["002"][2][4], "0")

    def test_zero_and_unavailable_sales_are_distinct(self):
        figure = self.visualizer.plot_map(self.data)
        traces = {trace.name: trace for trace in figure.data}

        self.assertEqual(list(traces["Zero sales"].ids), ["003"])
        self.assertEqual(traces["Zero sales"].customdata[0][3], "0")
        self.assertEqual(list(traces["Sales unavailable"].ids), ["004"])
        self.assertEqual(list(traces["Sales unavailable"].customdata[0][3:]), ["N/A", "N/A"])
        self.assertNotEqual(traces["Zero sales"].marker.color,
                            traces["Sales unavailable"].marker.color)

    def test_invalid_coordinates_are_omitted_and_reported(self):
        self.data.loc[0, "latitude"] = float("inf")
        self.data.loc[2, "latitude"] = 91
        self.data.loc[3, "longitude"] = 181
        figure = self.visualizer.plot_map(self.data)

        self.assertEqual(set(self._points(figure)), {"002"})
        notes = " ".join(annotation.text for annotation in figure.layout.annotations)
        self.assertIn("1 of 5 districts located", notes)
        self.assertIn("4 omitted: no valid location", notes)

    def test_empty_selection(self):
        figure = self.visualizer.plot_map(self.data.iloc[:0])

        self.assertEqual(len(figure.data), 0)
        self.assertIn("No sales data", figure.layout.annotations[0].text)
        figure.to_json()

    def test_all_unmapped_has_no_fabricated_points(self):
        self.data[["latitude", "longitude"]] = float("nan")
        figure = self.visualizer.plot_map(self.data)

        self.assertEqual(len(figure.data), 0)
        self.assertTrue(any("No mapped districts" in item.text for item in figure.layout.annotations))

    def test_all_unknown_sales(self):
        self.data["total_sales"] = pd.Series([pd.NA] * 5, dtype="Int64")
        figure = self.visualizer.plot_map(self.data)

        self.assertEqual([trace.name for trace in figure.data], ["Sales unavailable"])
        self.assertTrue(any("Sales totals are unavailable" in item.text for item in figure.layout.annotations))
        self.assertTrue(all(detail[3] == "N/A" for detail in figure.data[0].customdata))

    def test_all_zero_sales(self):
        self.data["total_sales"] = pd.Series([0] * 5, dtype="Int64")
        figure = self.visualizer.plot_map(self.data)

        self.assertEqual([trace.name for trace in figure.data], ["Zero sales"])
        self.assertTrue(any("zero recorded sales" in item.text for item in figure.layout.annotations))

    def test_input_and_prepared_totals_are_preserved(self):
        self.data.loc[1, "district_name"] = self.data.loc[0, "district_name"]
        self.data.attrs["period"] = "2024-2025"
        original = self.data.copy(deep=True)
        figure = self.visualizer.plot_map(self.data)
        points = self._points(figure)

        assert_frame_equal(self.data, original)
        self.assertEqual(self.data.attrs, {"period": "2024-2025"})
        self.assertEqual(points["001"][2][3], "1,000,000")
        self.assertEqual(points["002"][2][3], "4,000,000")
        self.assertEqual(len(points), 4)
        go.Figure(json.loads(figure.to_json()))

    def test_offline_outlines_use_only_embedded_geojson(self):
        path = Path(self._temporary.name) / "boundaries.geojson"
        boundaries = {"type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {}, "geometry": {
                "type": "Polygon", "coordinates": [[[126.8, 37.4], [127.2, 37.4],
                                                       [127.2, 37.7], [126.8, 37.4]]],
            },
        }]}
        path.write_text(json.dumps(boundaries), encoding="utf-8")
        figure = MapVisualizer(path).plot_map(self.data)
        buttons = figure.layout.updatemenus[0].buttons

        self.assertEqual([button.label for button in buttons], ["Street map", "Offline outlines"])
        offline = buttons[1].args[0]
        self.assertEqual(offline["map.style"], "white-bg")
        self.assertTrue(all(layer["source"] == boundaries for layer in offline["map.layers"]))
        self.assertTrue(all(layer["below"] == "traces" for layer in offline["map.layers"]))
        go.Figure(json.loads(figure.to_json()))

    def test_missing_boundary_file_has_no_offline_menu(self):
        figure = self.visualizer.plot_map(self.data)

        self.assertEqual(len(figure.layout.updatemenus), 0)


if __name__ == "__main__":
    unittest.main()
