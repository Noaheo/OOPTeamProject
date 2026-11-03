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


if __name__ == "__main__":
    unittest.main()
