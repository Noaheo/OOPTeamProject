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
            "주중_매출_금액": pd.Series([300, 200, 70, 130], dtype="Int64"),
            "주말_매출_금액": pd.Series([100, 100, 30, 70], dtype="Int64"),
            "주중_매출_건수": pd.Series([30, 20, 7, 13], dtype="Int64"),
            "주말_매출_건수": pd.Series([10, 10, 3, 7], dtype="Int64"),
            "월요일_매출_금액": pd.Series([60, 40, 10, 30], dtype="Int64"),
            "화요일_매출_금액": pd.Series([60, 40, 15, 25], dtype="Int64"),
            "수요일_매출_금액": pd.Series([60, 40, 15, 25], dtype="Int64"),
            "목요일_매출_금액": pd.Series([60, 40, 15, 25], dtype="Int64"),
            "금요일_매출_금액": pd.Series([60, 40, 15, 25], dtype="Int64"),
            "토요일_매출_금액": pd.Series([50, 50, 15, 35], dtype="Int64"),
            "일요일_매출_금액": pd.Series([50, 50, 15, 35], dtype="Int64"),
            "월요일_매출_건수": pd.Series([6, 4, 1, 3], dtype="Int64"),
            "화요일_매출_건수": pd.Series([6, 4, 1, 3], dtype="Int64"),
            "수요일_매출_건수": pd.Series([6, 4, 2, 2], dtype="Int64"),
            "목요일_매출_건수": pd.Series([6, 4, 2, 2], dtype="Int64"),
            "금요일_매출_건수": pd.Series([6, 4, 1, 3], dtype="Int64"),
            "토요일_매출_건수": pd.Series([5, 5, 1, 4], dtype="Int64"),
            "일요일_매출_건수": pd.Series([5, 5, 2, 3], dtype="Int64"),
            "시간대_00~06_매출_금액": pd.Series([20, 10, 5, 5], dtype="Int64"),
            "시간대_06~11_매출_금액": pd.Series([40, 30, 10, 20], dtype="Int64"),
            "시간대_11~14_매출_금액": pd.Series([120, 90, 30, 60], dtype="Int64"),
            "시간대_14~17_매출_금액": pd.Series([80, 60, 20, 40], dtype="Int64"),
            "시간대_17~21_매출_금액": pd.Series([100, 80, 25, 55], dtype="Int64"),
            "시간대_21~24_매출_금액": pd.Series([40, 30, 10, 20], dtype="Int64"),
            "시간대_00~06_매출_건수": pd.Series([2, 1, 0, 1], dtype="Int64"),
            "시간대_06~11_매출_건수": pd.Series([4, 3, 1, 2], dtype="Int64"),
            "시간대_11~14_매출_건수": pd.Series([12, 9, 3, 6], dtype="Int64"),
            "시간대_14~17_매출_건수": pd.Series([8, 6, 2, 4], dtype="Int64"),
            "시간대_17~21_매출_건수": pd.Series([10, 8, 3, 5], dtype="Int64"),
            "시간대_21~24_매출_건수": pd.Series([4, 3, 1, 2], dtype="Int64"),
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

    def test_year_comparison_matches_quarters_and_growth(self):
        comp = SalesAnalyzer(self.sales_data).year_comparison(2024, 2025)
        self.assertEqual(comp.columns.tolist(),
                         ["quarter", "year_a", "year_b", "sales_a", "sales_b", "difference", "growth_rate"])
        self.assertEqual(len(comp), 1)
        self.assertEqual(comp.iloc[0]["quarter"], 1)
        self.assertEqual(comp.iloc[0]["sales_a"], 300)
        self.assertEqual(comp.iloc[0]["sales_b"], 400)
        self.assertEqual(comp.iloc[0]["difference"], 100)
        self.assertAlmostEqual(comp.iloc[0]["growth_rate"], 33.33, places=2)

    def test_year_comparison_empty_or_unmatched_and_invalid_years(self):
        analyzer = SalesAnalyzer(self.sales_data)
        unmatched = analyzer.year_comparison(2023, 2024)
        self.assertTrue(unmatched.empty)
        self.assertEqual(unmatched.columns.tolist(),
                         ["quarter", "year_a", "year_b", "sales_a", "sales_b", "difference", "growth_rate"])

        empty_comp = SalesAnalyzer(self.sales_data.iloc[:0]).year_comparison(2024, 2025)
        self.assertTrue(empty_comp.empty)

        for bad_a, bad_b in ((2024, 2024), (True, 2025), (2024, "2025")):
            with self.assertRaises(ValueError):
                analyzer.year_comparison(bad_a, bad_b)

    def test_year_growth_summary_totals_and_zero_baseline(self):
        summary = SalesAnalyzer(self.sales_data).year_growth_summary(2024, 2025)
        self.assertEqual(summary, {
            "year_a": 2024,
            "year_b": 2025,
            "matched_quarters": [1],
            "sales_a": 300,
            "sales_b": 400,
            "difference": 100,
            "growth_rate": 33.33,
        })

        zero_base = self.sales_data.copy()
        zero_base.loc[(zero_base["year"] == 2024) & (zero_base["quarter"] == 1), "당월_매출_금액"] = 0
        summary_zero = SalesAnalyzer(zero_base).year_growth_summary(2024, 2025)
        self.assertIsNone(summary_zero["growth_rate"])
        self.assertEqual(summary_zero["difference"], 400)

        no_match = SalesAnalyzer(self.sales_data).year_growth_summary(2023, 2025)
        self.assertEqual(no_match["matched_quarters"], [])
        self.assertIsNone(no_match["growth_rate"])

    def test_weekday_weekend_sums_and_shares(self):
        result = SalesAnalyzer(self.sales_data).weekday_weekend()
        self.assertEqual(result["day_type"].tolist(), ["Weekday", "Weekend"])
        self.assertEqual(result["total_sales"].tolist(), [700, 300])
        self.assertEqual(result["total_transactions"].tolist(), [70, 30])
        self.assertAlmostEqual(result["sales_share"].iloc[0], 70.0, places=2)
        self.assertAlmostEqual(result["sales_share"].iloc[1], 30.0, places=2)

    def test_year_growth_summary_uses_only_complete_quarter_pairs(self):
        data = pd.DataFrame({
            "year": [2024, 2024, 2024, 2025, 2025, 2025],
            "quarter": [1, 2, 3, 1, 2, 3],
            "당월_매출_금액": pd.Series([100, pd.NA, 300, 120, 200, pd.NA], dtype="Int64"),
        })
        original = data.copy(deep=True)
        analyzer = SalesAnalyzer(data)

        self.assertEqual(analyzer.year_growth_summary(2024, 2025), {
            "year_a": 2024,
            "year_b": 2025,
            "matched_quarters": [1],
            "sales_a": 100,
            "sales_b": 120,
            "difference": 20,
            "growth_rate": 20.0,
        })
        self.assertEqual(analyzer.year_comparison(2024, 2025)["quarter"].tolist(), [1, 2, 3])
        assert_frame_equal(data, original)

    def test_year_growth_summary_without_complete_pairs(self):
        for sales in ([100, pd.NA, pd.NA, 200], [pd.NA] * 4):
            with self.subTest(sales=sales):
                data = pd.DataFrame({
                    "year": [2024, 2024, 2025, 2025],
                    "quarter": [1, 2, 1, 2],
                    "당월_매출_금액": pd.Series(sales, dtype="Int64"),
                })

                self.assertEqual(SalesAnalyzer(data).year_growth_summary(2024, 2025), {
                    "year_a": 2024,
                    "year_b": 2025,
                    "matched_quarters": [],
                    "sales_a": None,
                    "sales_b": None,
                    "difference": None,
                    "growth_rate": None,
                })

    def test_year_growth_summary_keeps_complete_zero_baseline(self):
        data = pd.DataFrame({
            "year": [2024, 2024, 2025, 2025],
            "quarter": [1, 2, 1, 2],
            "당월_매출_금액": pd.Series([0, pd.NA, 100, 200], dtype="Int64"),
        })

        self.assertEqual(SalesAnalyzer(data).year_growth_summary(2024, 2025), {
            "year_a": 2024,
            "year_b": 2025,
            "matched_quarters": [1],
            "sales_a": 0,
            "sales_b": 100,
            "difference": 100,
            "growth_rate": None,
        })

    def test_weekday_weekend_shares_require_both_category_totals(self):
        for weekday, weekend in ((700, pd.NA), (pd.NA, 300), (pd.NA, pd.NA)):
            with self.subTest(weekday=weekday, weekend=weekend):
                data = self.sales_data.iloc[:1].copy()
                data["주중_매출_금액"] = pd.Series([weekday], dtype="Int64")
                data["주말_매출_금액"] = pd.Series([weekend], dtype="Int64")
                original = data.copy(deep=True)

                result = SalesAnalyzer(data).weekday_weekend()

                self.assertTrue(result["sales_share"].isna().all())
                self.assertEqual(result["total_sales"].notna().tolist(),
                                 [pd.notna(weekday), pd.notna(weekend)])
                assert_frame_equal(data, original)

    def test_weekday_weekend_zero_totals_keep_zero_shares(self):
        data = self.sales_data.copy()
        data[["주중_매출_금액", "주말_매출_금액"]] = 0

        result = SalesAnalyzer(data).weekday_weekend()

        self.assertEqual(result["total_sales"].tolist(), [0, 0])
        self.assertEqual(result["sales_share"].tolist(), [0.0, 0.0])

    def test_daily_sales_and_time_slot_sales(self):
        analyzer = SalesAnalyzer(self.sales_data)
        daily = analyzer.daily_sales()
        self.assertEqual(daily["day"].tolist(), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        self.assertEqual(daily["total_sales"].tolist(), [140, 140, 140, 140, 140, 150, 150])
        self.assertEqual(daily["total_transactions"].sum(), 100)

        slots = analyzer.time_slot_sales()
        self.assertEqual(slots["time_slot"].tolist(), [
            "00:00-06:00", "06:00-11:00", "11:00-14:00",
            "14:00-17:00", "17:00-21:00", "21:00-24:00",
        ])
        self.assertEqual(slots["total_sales"].tolist(), [40, 100, 300, 200, 260, 100])
        self.assertEqual(slots["total_transactions"].sum(), 100)

    def test_empty_data_day_and_time_breakdowns(self):
        analyzer = SalesAnalyzer(self.sales_data.iloc[:0])
        self.assertEqual(analyzer.weekday_weekend()["total_sales"].tolist(), [0, 0])
        self.assertEqual(analyzer.weekday_weekend()["sales_share"].tolist(), [0.0, 0.0])
        self.assertEqual(analyzer.daily_sales()["total_sales"].tolist(), [0] * 7)
        self.assertEqual(analyzer.time_slot_sales()["total_sales"].tolist(), [0] * 6)


if __name__ == "__main__":
    unittest.main()
