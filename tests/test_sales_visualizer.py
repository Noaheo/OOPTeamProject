import json
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal
import plotly.graph_objects as go

from sales_visualizer import SalesVisualizer


class SalesVisualizerTests(unittest.TestCase):
    def setUp(self):
        self.trend = pd.DataFrame({
            "year": [2024, 2024, 2025],
            "quarter": [1, 4, 1],
            "total_sales": pd.Series([300, 300, 400], dtype="Int64"),
        })

    def test_plot_returns_labeled_line_figure(self):
        figure = SalesVisualizer().plot_trend(self.trend)

        self.assertIsInstance(figure, go.Figure)
        self.assertEqual(list(figure.data[0].x), ["2024 Q1", "2024 Q4", "2025 Q1"])
        self.assertEqual(list(figure.data[0].y), [300, 300, 400])
        self.assertEqual(figure.data[0].mode, "lines+markers")
        self.assertEqual(figure.layout.xaxis.title.text, "Period")
        self.assertEqual(figure.layout.yaxis.title.text, "Sales (KRW)")
        self.assertIn("%{y:,.0f} KRW", figure.data[0].hovertemplate)

    def test_plot_does_not_modify_input(self):
        original = self.trend.copy(deep=True)

        SalesVisualizer().plot_trend(self.trend)

        assert_frame_equal(self.trend, original)

    def test_plot_for_empty_selection(self):
        figure = SalesVisualizer().plot_trend(self.trend.iloc[:0])

        self.assertIsInstance(figure, go.Figure)
        self.assertEqual(len(figure.data[0].x), 0)
        self.assertEqual(len(figure.data[0].y), 0)
        self.assertEqual(figure.layout.yaxis.title.text, "Sales (KRW)")

    def test_plot_for_one_quarter(self):
        figure = SalesVisualizer().plot_trend(self.trend.iloc[:1])

        self.assertEqual(list(figure.data[0].x), ["2024 Q1"])
        self.assertEqual(list(figure.data[0].y), [300])

    def test_plot_serializes_missing_sales_as_gaps(self):
        self.trend.loc[1, "total_sales"] = pd.NA
        figure = SalesVisualizer().plot_trend(self.trend)
        serialized = json.loads(figure.to_json())

        self.assertEqual(serialized["data"][0]["y"], [300, None, 400])
        self.assertFalse(figure.data[0].connectgaps)


if __name__ == "__main__":
    unittest.main()
