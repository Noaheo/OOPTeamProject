import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from sales_analyzer import SalesAnalyzer


class SalesAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.sales_data = pd.DataFrame({
            "year": [2025, 2024, 2024, 2024],
            "quarter": [1, 4, 1, 1],
            "당월_매출_금액": pd.Series([400, 300, 100, 200], dtype="Int64"),
            "당월_매출_건수": pd.Series([40, 30, 10, 20], dtype="Int64"),
        })

    def test_summary_sums_sales_and_transaction_counts(self):
        summary = SalesAnalyzer(self.sales_data).sales_summary()

        self.assertEqual(summary, {"total_sales": 1000, "total_transactions": 100})
        self.assertIsInstance(summary["total_sales"], int)
        self.assertIsInstance(summary["total_transactions"], int)

    def test_summary_for_empty_selection(self):
        summary = SalesAnalyzer(self.sales_data.iloc[:0]).sales_summary()

        self.assertEqual(summary, {"total_sales": 0, "total_transactions": 0})

    def test_summary_does_not_modify_input(self):
        original = self.sales_data.copy(deep=True)

        SalesAnalyzer(self.sales_data).sales_summary()

        assert_frame_equal(self.sales_data, original)

    def test_constructor_keeps_a_snapshot(self):
        analyzer = SalesAnalyzer(self.sales_data)
        self.sales_data.loc[0, "당월_매출_금액"] = 9999

        self.assertEqual(analyzer.sales_summary()["total_sales"], 1000)

    def test_summary_sums_available_metrics(self):
        self.sales_data.loc[0, ["당월_매출_금액", "당월_매출_건수"]] = pd.NA

        self.assertEqual(SalesAnalyzer(self.sales_data).sales_summary(),
                         {"total_sales": 600, "total_transactions": 60})

    def test_summary_preserves_entirely_missing_metrics(self):
        self.sales_data["당월_매출_금액"] = pd.Series([pd.NA] * 4, dtype="Int64")

        self.assertEqual(SalesAnalyzer(self.sales_data).sales_summary(),
                         {"total_sales": None, "total_transactions": 100})

    def test_trend_groups_and_sorts_by_year_and_quarter(self):
        trend = SalesAnalyzer(self.sales_data).quarterly_trend()
        expected = pd.DataFrame({
            "year": [2024, 2024, 2025],
            "quarter": [1, 4, 1],
            "total_sales": pd.Series([300, 300, 400], dtype="Int64"),
        })

        assert_frame_equal(trend, expected)

    def test_trend_for_empty_selection(self):
        trend = SalesAnalyzer(self.sales_data.iloc[:0]).quarterly_trend()

        self.assertTrue(trend.empty)
        self.assertEqual(trend.columns.tolist(), ["year", "quarter", "total_sales"])

    def test_trend_preserves_missing_quarter_totals(self):
        self.sales_data.loc[[0, 2], "당월_매출_금액"] = pd.NA
        trend = SalesAnalyzer(self.sales_data).quarterly_trend()

        self.assertEqual(trend["total_sales"].iloc[:2].tolist(), [200, 300])
        self.assertTrue(pd.isna(trend["total_sales"].iloc[2]))

    def test_trend_does_not_modify_input_or_share_result(self):
        original = self.sales_data.copy(deep=True)
        analyzer = SalesAnalyzer(self.sales_data)
        trend = analyzer.quarterly_trend()
        trend.loc[0, "total_sales"] = 9999

        assert_frame_equal(self.sales_data, original)
        self.assertEqual(analyzer.quarterly_trend()["total_sales"].tolist(),
                         [300, 300, 400])


if __name__ == "__main__":
    unittest.main()
