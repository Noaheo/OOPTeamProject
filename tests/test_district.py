"""Tests for DistrictComparator and DistrictVisualizer; no external network or CSV needed."""

import json
import unittest

import pandas as pd
import plotly.graph_objects as go
from pandas.testing import assert_frame_equal

from district_comparator import DistrictComparator
from district_visualizer import DistrictVisualizer


class DistrictDemoTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({
            "상권_코드": ["A", "B", "C", "D", "E", "F", "A", "B"],
            "상권_코드_명": ["Area A", "Area B", "Area C", "Area D",
                           "Area E", "Area F", "Area A", "Area B"],
            "당월_매출_금액": pd.Series([100, 500, 300, 200, 400, 50, 60, 20], dtype="Int64"),
            "year": [2025] * 8,
            "quarter": [1, 1, 1, 1, 1, 1, 2, 2],
        })

    def test_top_five_sums_quarters_and_sorts(self):
        result = DistrictComparator(self.data).rank_districts(5, "top")
        self.assertEqual(result["district_code"].tolist(), ["B", "E", "C", "D", "A"])
        self.assertEqual(result["total_sales"].tolist(), [520, 400, 300, 200, 160])
        self.assertEqual(result["rank"].tolist(), [1, 2, 3, 4, 5])

    def test_bottom_and_n_larger_than_available(self):
        result = DistrictComparator(self.data).rank_districts(10, "bottom")
        self.assertEqual(len(result), 6)
        self.assertEqual(result.iloc[0]["district_code"], "F")

    def test_tied_sales_use_district_code(self):
        self.data.loc[self.data["상권_코드"] == "F", "당월_매출_금액"] = 200
        result = DistrictComparator(self.data).rank_districts(10, "top")
        self.assertEqual(result.iloc[1]["district_code"], "E")

    def test_empty_data(self):
        result = DistrictComparator(self.data.iloc[:0]).rank_districts()
        self.assertEqual(result.columns.tolist(),
                         ["rank", "district_code", "district_name", "total_sales"])
        self.assertTrue(result.empty)
        self.assertIsInstance(DistrictVisualizer().plot_ranking(result), go.Figure)

    def test_missing_sales_excluded_not_counted_as_zero(self):
        frame = self.data.copy()
        frame.loc[frame["상권_코드"] == "F", "당월_매출_금액"] = pd.NA
        result = DistrictComparator(frame).rank_districts(10, "bottom")
        self.assertNotIn("F", result["district_code"].tolist())

    def test_reject_invalid_arguments(self):
        obj = DistrictComparator(self.data)
        for invalid in (0, -2, True, 2.5):
            with self.assertRaises(ValueError):
                obj.rank_districts(invalid)
        with self.assertRaises(ValueError):
            obj.rank_districts(5, "highest")
        with self.assertRaises(ValueError):
            DistrictComparator(pd.DataFrame({"other": [1]}))

    def test_visualizer_output_and_unchanged_input(self):
        ranked = DistrictComparator(self.data).rank_districts()
        before = ranked.copy(deep=True)
        figure = DistrictVisualizer().plot_ranking(ranked)
        self.assertIsInstance(figure, go.Figure)
        self.assertEqual(len(figure.data), 1)
        self.assertEqual(len(figure.data[0].x), 5)
        assert_frame_equal(ranked, before)

    def test_does_not_change_original_data(self):
        before = self.data.copy(deep=True)
        DistrictComparator(self.data).rank_districts()
        assert_frame_equal(self.data, before)

    def test_compare_districts_gaps_and_reference_switch(self):
        comp = DistrictComparator(self.data, category="CS100001", period="2025 Q1-Q2")
        res = comp.compare_districts(["A", "B", "D"], reference_id="D")
        self.assertEqual(res["district_code"].tolist(), ["B", "D", "A"])
        self.assertEqual(res["total_sales"].tolist(), [520, 200, 160])
        self.assertEqual(res["difference"].tolist(), [320, 0, -40])
        self.assertEqual(res["percent_diff"].tolist(), [160.0, 0.0, -20.0])
        self.assertEqual(res["is_reference"].tolist(), [False, True, False])

        res_b = comp.compare_districts(["A", "B"], reference_id="B")
        self.assertEqual(res_b["difference"].tolist(), [0, -360])

    def test_compare_districts_missing_and_zero_baseline(self):
        frame = self.data.copy()
        frame.loc[frame["상권_코드"] == "F", "당월_매출_금액"] = 0
        comp = DistrictComparator(frame)
        res = comp.compare_districts(["A", "F", "Z"], reference_id="F")
        row_a = res[res["district_code"] == "A"].iloc[0]
        row_z = res[res["district_code"] == "Z"].iloc[0]
        self.assertEqual(row_a["difference"], 160)
        self.assertTrue(pd.isna(row_a["percent_diff"]))
        self.assertTrue(pd.isna(row_z["total_sales"]))
        self.assertTrue(pd.isna(row_z["difference"]))

    def test_compare_districts_validation_errors(self):
        comp = DistrictComparator(self.data)
        for bad_ids in (["A"], ["A", "A"], [], "AB"):
            with self.assertRaises(ValueError):
                comp.compare_districts(bad_ids)
        with self.assertRaises(ValueError):
            comp.compare_districts(["A", "B"], reference_id="C")

    def test_plot_comparison_output_empty_and_immutability(self):
        comp_df = DistrictComparator(self.data).compare_districts(["A", "B", "D"], reference_id="D")
        before = comp_df.copy(deep=True)
        fig = DistrictVisualizer().plot_comparison(comp_df)
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(list(fig.data[0].x), ["Area B", "Area D", "Area A"])
        self.assertEqual(list(fig.data[0].text), ["+160.0%", "Baseline", "-20.0%"])
        fig.to_json()
        assert_frame_equal(comp_df, before)

        empty_fig = DistrictVisualizer().plot_comparison(comp_df.iloc[:0])
        self.assertEqual(len(empty_fig.data), 0)
        self.assertTrue(len(empty_fig.layout.annotations) > 0)

        na_df = comp_df.copy()
        na_df.loc[0, "total_sales"] = pd.NA
        na_fig = DistrictVisualizer().plot_comparison(na_df)
        self.assertIsNone(json.loads(na_fig.to_json())["data"][0]["y"][0])


if __name__ == "__main__":
    unittest.main()
