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

    def test_custom_template_and_palette(self):
        vis = SalesVisualizer(template="plotly_dark", color_palette=["#111111", "#222222"])
        self.assertEqual(vis._template, "plotly_dark")
        self.assertEqual(vis._color_palette, ["#111111", "#222222"])
        fig = vis.plot_trend(self.trend)
        self.assertEqual(fig.data[0].line.color, "#111111")

    def test_plot_years_grouped_bars_and_empty_annotation(self):
        comp = pd.DataFrame({
            "quarter": [1, 2],
            "year_a": [2024, 2024],
            "year_b": [2025, 2025],
            "sales_a": pd.Series([100, 200], dtype="Int64"),
            "sales_b": pd.Series([120, pd.NA], dtype="Int64"),
            "difference": pd.Series([20, pd.NA], dtype="Int64"),
            "growth_rate": [20.0, float("nan")],
        })
        fig = SalesVisualizer().plot_years(comp)
        self.assertEqual(len(fig.data), 2)
        self.assertEqual(fig.layout.barmode, "group")
        self.assertEqual(list(fig.data[0].x), ["Q1", "Q2"])
        serialized = json.loads(fig.to_json())
        self.assertEqual(serialized["data"][1]["y"], [120, None])

        empty_fig = SalesVisualizer().plot_years(comp.iloc[:0])
        self.assertEqual(len(empty_fig.data), 0)
        self.assertTrue(len(empty_fig.layout.annotations) > 0)

    def test_plot_day_types_days_and_time_slots(self):
        vis = SalesVisualizer()
        day_types = pd.DataFrame({
            "day_type": ["Weekday", "Weekend"],
            "total_sales": pd.Series([700, 300], dtype="Int64"),
            "total_transactions": pd.Series([70, 30], dtype="Int64"),
            "sales_share": [70.0, 30.0],
        })
        fig_dt = vis.plot_day_types(day_types)
        self.assertEqual(list(fig_dt.data[0].x), ["Weekday", "Weekend"])
        fig_dt.to_json()

        days = pd.DataFrame({
            "day": ["Mon", "Sat", "Sun"],
            "total_sales": pd.Series([100, 200, pd.NA], dtype="Int64"),
            "total_transactions": pd.Series([10, 20, pd.NA], dtype="Int64"),
        })
        fig_days = vis.plot_days(days)
        self.assertEqual(list(fig_days.data[0].marker.color), [
            vis._color_palette[0], vis._color_palette[1], vis._color_palette[1],
        ])
        self.assertEqual(json.loads(fig_days.to_json())["data"][0]["y"], [100, 200, None])

        slots = pd.DataFrame({
            "time_slot": ["00:00-06:00", "11:00-14:00"],
            "total_sales": pd.Series([50, 300], dtype="Int64"),
            "total_transactions": pd.Series([5, 30], dtype="Int64"),
        })
        fig_slots = vis.plot_time_slots(slots)
        self.assertEqual(list(fig_slots.data[0].x), ["00:00-06:00", "11:00-14:00"])
        fig_slots.to_json()

    def test_transaction_tooltips_preserve_missing_zero_and_large_counts(self):
        cases = (
            ("plot_day_types", "day_type", ["Weekday", "Weekend"]),
            ("plot_days", "day", ["Mon", "Sat"]),
            ("plot_time_slots", "time_slot", ["00:00-06:00", "11:00-14:00"]),
        )
        vis = SalesVisualizer()
        for method, column, labels in cases:
            for transactions, sales, expected in (
                ([pd.NA, 0], [100, 200], ["N/A", "0"]),
                ([1234, 0], [100, pd.NA], ["1,234", "0"]),
            ):
                with self.subTest(method=method, expected=expected):
                    data = pd.DataFrame({
                        column: labels,
                        "total_sales": pd.Series(sales, dtype="Int64"),
                        "total_transactions": pd.Series(transactions, dtype="Int64"),
                    })
                    original = data.copy(deep=True)
                    figure = getattr(vis, method)(data)
                    trace = json.loads(figure.to_json())["data"][0]
                    tooltip_counts = ([row[0] for row in trace["customdata"]]
                                      if method == "plot_day_types" else trace["customdata"])

                    self.assertEqual(tooltip_counts, expected)
                    self.assertEqual(trace["y"], [None if pd.isna(value) else value for value in sales])
                    placeholder = "%{customdata[0]}" if method == "plot_day_types" else "%{customdata}"
                    self.assertIn(f"Transactions: {placeholder}", trace["hovertemplate"])
                    assert_frame_equal(data, original)

    def test_transaction_tooltips_when_counts_are_not_supplied(self):
        vis = SalesVisualizer()
        for method, column, labels in (
            ("plot_day_types", "day_type", ["Weekday", "Weekend"]),
            ("plot_days", "day", ["Mon", "Sat"]),
            ("plot_time_slots", "time_slot", ["00:00-06:00", "11:00-14:00"]),
        ):
            with self.subTest(method=method):
                data = pd.DataFrame({column: labels, "total_sales": [100, 200]})
                original = data.copy(deep=True)
                trace = json.loads(getattr(vis, method)(data).to_json())["data"][0]
                tooltip_counts = ([row[0] for row in trace["customdata"]]
                                  if method == "plot_day_types" else trace["customdata"])

                self.assertEqual(tooltip_counts, ["N/A", "N/A"])
                assert_frame_equal(data, original)


if __name__ == "__main__":
    unittest.main()
