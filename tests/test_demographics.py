import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import pandas as pd
from pandas.testing import assert_frame_equal

from data_manager import SalesDataManager
from demographic_analyzer import DemographicAnalyzer
from demographic_visualizer import DemographicVisualizer


class DemographicTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({
            "남성_매출_금액": pd.Series([100, 250, pd.NA], dtype="Int64"),
            "여성_매출_금액": pd.Series([200, 300, 0], dtype="Int64"),
            "남성_매출_건수": pd.Series([2, 3, pd.NA], dtype="Int64"),
            "여성_매출_건수": pd.Series([4, 5, 0], dtype="Int64"),
            "연령대_10_매출_금액": pd.Series([10, 20, 0], dtype="Int64"),
            "연령대_20_매출_금액": pd.Series([100, 150, 0], dtype="Int64"),
            "연령대_30_매출_금액": pd.Series([120, 200, pd.NA], dtype="Int64"),
            "연령대_40_매출_금액": pd.Series([40, 80, 0], dtype="Int64"),
            "연령대_50_매출_금액": pd.Series([20, 60, 0], dtype="Int64"),
            "연령대_60_이상_매출_금액": pd.Series([10, 40, 0], dtype="Int64"),
            "연령대_10_매출_건수": pd.Series([1, 2, 0], dtype="Int64"),
            "연령대_20_매출_건수": pd.Series([2, 3, 0], dtype="Int64"),
            "연령대_30_매출_건수": pd.Series([2, 4, pd.NA], dtype="Int64"),
            "연령대_40_매출_건수": pd.Series([1, 2, 0], dtype="Int64"),
            "연령대_50_매출_건수": pd.Series([1, 1, 0], dtype="Int64"),
            "연령대_60_이상_매출_건수": pd.Series([1, 1, 0], dtype="Int64"),
        })

    def test_known_totals_and_chart(self):
        result = DemographicAnalyzer(self.data).gender_sales()
        self.assertEqual(result.to_dict("records"), [
            {"gender": "Male", "total_sales": 350, "total_transactions": 5},
            {"gender": "Female", "total_sales": 500, "total_transactions": 9},
        ])
        chart = DemographicVisualizer().plot_gender(result)
        self.assertEqual(chart.data[0].type, "bar")
        self.assertEqual(list(chart.data[0].x), ["Male", "Female"])
        self.assertEqual(list(chart.data[0].y), [350, 500])
        self.assertEqual(chart.layout.yaxis.title.text, "Sales (KRW)")
        self.assertIn("KRW", chart.data[0].hovertemplate)
        chart.to_json()

    def test_empty_selection_returns_zero(self):
        result = DemographicAnalyzer(self.data.iloc[:0]).gender_sales()
        self.assertEqual(result["total_sales"].tolist(), [0, 0])
        self.assertEqual(result["total_transactions"].tolist(), [0, 0])
        self.assertEqual(list(DemographicVisualizer().plot_gender(result).data[0].y), [0, 0])

    def test_entirely_missing_metric_stays_missing(self):
        self.data["남성_매출_금액"] = pd.Series([pd.NA] * 3, dtype="Int64")
        self.data["여성_매출_건수"] = pd.Series([pd.NA] * 3, dtype="Int64")
        result = DemographicAnalyzer(self.data).gender_sales()
        self.assertTrue(pd.isna(result.loc[0, "total_sales"]))
        self.assertTrue(pd.isna(result.loc[1, "total_transactions"]))
        self.assertEqual(result.loc[0, "total_transactions"], 5)
        chart = DemographicVisualizer().plot_gender(result)
        self.assertEqual(json.loads(chart.to_json())["data"][0]["y"], [None, 500])

    def test_preserves_input_snapshot_and_results(self):
        original = self.data.copy(deep=True)
        analyzer = DemographicAnalyzer(self.data)
        result = analyzer.gender_sales()
        before_plot = result.copy(deep=True)
        DemographicVisualizer().plot_gender(result)
        assert_frame_equal(result, before_plot)
        assert_frame_equal(self.data, original)
        self.data.loc[0, "남성_매출_금액"] = 9999
        result.loc[0, "total_sales"] = 8888
        self.assertEqual(analyzer.gender_sales().loc[0, "total_sales"], 350)

    def test_large_integer_sales_remain_exact(self):
        self.data["남성_매출_금액"] = pd.Series([2**53, 1, 0], dtype="Int64")
        result = DemographicAnalyzer(self.data).gender_sales()
        self.assertEqual(result.loc[0, "total_sales"], 2**53 + 1)

    def test_visualizer_accepts_empty_result_table(self):
        result = DemographicAnalyzer(self.data).gender_sales().iloc[:0]
        figure = DemographicVisualizer().plot_gender(result)
        self.assertEqual(len(figure.data[0].x), 0)
        figure.to_json()

    def test_age_group_sales_and_shares(self):
        analyzer = DemographicAnalyzer(self.data)
        age_sales = analyzer.age_group_sales()
        self.assertEqual(age_sales["age_group"].tolist(), ["10s", "20s", "30s", "40s", "50s", "60+"])
        self.assertEqual(age_sales["total_sales"].tolist(), [30, 250, 320, 120, 80, 50])
        self.assertEqual(age_sales["total_transactions"].tolist(), [3, 5, 6, 3, 2, 2])

        age_shares = analyzer.age_group_share()
        self.assertAlmostEqual(age_shares["sales_share"].sum(), 100.0, places=1)
        self.assertAlmostEqual(age_shares.loc[2, "sales_share"], round(320 / 850 * 100, 2), places=2)

    def test_gender_share_and_top_age_group(self):
        analyzer = DemographicAnalyzer(self.data)
        g_share = analyzer.gender_share()
        self.assertAlmostEqual(g_share.loc[0, "sales_share"], round(350 / 850 * 100, 2), places=2)
        self.assertAlmostEqual(g_share.loc[1, "sales_share"], round(500 / 850 * 100, 2), places=2)

        top = analyzer.top_age_group()
        self.assertEqual(top["age_group"], "30s")
        self.assertEqual(top["total_sales"], 320)
        self.assertEqual(top["total_transactions"], 6)
        self.assertAlmostEqual(top["sales_share"], round(320 / 850 * 100, 2), places=2)

    def test_top_age_group_returns_none_when_empty_or_zero(self):
        self.assertIsNone(DemographicAnalyzer(self.data.iloc[:0]).top_age_group())
        zero_df = self.data.copy()
        for col in [c for c in zero_df.columns if c.startswith("연령대_")]:
            zero_df[col] = pd.Series([0, 0, 0], dtype="Int64")
        self.assertIsNone(DemographicAnalyzer(zero_df).top_age_group())

    def test_plot_age_groups_and_plot_gender_share(self):
        analyzer = DemographicAnalyzer(self.data)
        vis = DemographicVisualizer()

        age_fig = vis.plot_age_groups(analyzer.age_group_share())
        self.assertEqual(list(age_fig.data[0].x), ["10s", "20s", "30s", "40s", "50s", "60+"])
        self.assertEqual(age_fig.data[0].marker.color[2], vis._color_palette[0])
        age_fig.to_json()

        share_fig = vis.plot_gender_share(analyzer.gender_share())
        self.assertEqual(share_fig.data[0].type, "pie")
        self.assertEqual(list(share_fig.data[0].labels), ["Male", "Female"])
        share_fig.to_json()

        empty_share_fig = vis.plot_gender_share(analyzer.gender_share().iloc[:0])
        self.assertEqual(len(empty_share_fig.data), 0)
        self.assertTrue(len(empty_share_fig.layout.annotations) > 0)


class DemographicIntegrationTests(unittest.TestCase):
    def test_archived_csv_totals_and_filtered_pipeline(self):
        archive_path = Path(__file__).resolve().parents[1] / "data(23~25).zip"
        groups = ("남성", "여성", "연령대_10", "연령대_20", "연령대_30", "연령대_40", "연령대_50", "연령대_60_이상")
        expected = {group: [0, 0] for group in groups}
        selected_expected = {group: [0, 0] for group in groups}
        selection = None
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            with zipfile.ZipFile(archive_path) as archive:
                for year in (2024, 2025):
                    member = next(n for n in archive.namelist()
                                  if str(year) in n and n.endswith(".csv"))
                    path = Path(directory) / f"sales_{year}.csv"
                    with archive.open(member) as source, path.open("wb") as target:
                        shutil.copyfileobj(source, target)
                    paths.append(path)
                    # Independent reference: raw CSV reader, without pandas.
                    with path.open(encoding="cp949", newline="") as source:
                        for row in csv.DictReader(source):
                            key = (row["상권_코드"], row["서비스_업종_코드"],
                                   int(row["기준_년분기_코드"][:4]))
                            if selection is None:
                                selection = key
                            for group in groups:
                                for index, metric in enumerate(("금액", "건수")):
                                    value = int(row[f"{group}_매출_{metric}"])
                                    expected[group][index] += value
                                    if key == selection:
                                        selected_expected[group][index] += value
            manager = SalesDataManager(paths)
            manager.load_data()
            cleaned = manager.preprocess_data()
            selected = manager.filter_data(district=selection[0], industry=selection[1],
                                           year=selection[2])
            self.assertFalse(selected.empty)
            for records, reference in ((cleaned, expected), (selected, selected_expected)):
                original = records.copy(deep=True)
                analyzer = DemographicAnalyzer(records)
                result = analyzer.gender_sales()
                self.assertEqual(result["total_sales"].tolist(),
                                 [reference[g][0] for g in ("남성", "여성")])
                self.assertEqual(result["total_transactions"].tolist(),
                                 [reference[g][1] for g in ("남성", "여성")])

                age_result = analyzer.age_group_sales()
                age_keys = ("연령대_10", "연령대_20", "연령대_30", "연령대_40", "연령대_50", "연령대_60_이상")
                self.assertEqual(age_result["total_sales"].tolist(), [reference[g][0] for g in age_keys])
                self.assertEqual(age_result["total_transactions"].tolist(), [reference[g][1] for g in age_keys])

                vis = DemographicVisualizer()
                figure = vis.plot_gender(result)
                self.assertEqual(list(figure.data[0].y), result["total_sales"].tolist())
                figure.to_json()
                vis.plot_age_groups(analyzer.age_group_share()).to_json()
                vis.plot_gender_share(analyzer.gender_share()).to_json()
                assert_frame_equal(records, original)


if __name__ == "__main__":
    unittest.main()
