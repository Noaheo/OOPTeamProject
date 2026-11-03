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


class DemographicIntegrationTests(unittest.TestCase):
    def test_archived_csv_totals_and_filtered_pipeline(self):
        archive_path = Path(__file__).resolve().parents[1] / "data(23~25).zip"
        expected = {gender: [0, 0] for gender in ("남성", "여성")}
        selected_expected = {gender: [0, 0] for gender in expected}
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
                            for gender in expected:
                                for index, metric in enumerate(("금액", "건수")):
                                    value = int(row[f"{gender}_매출_{metric}"])
                                    expected[gender][index] += value
                                    if key == selection:
                                        selected_expected[gender][index] += value
            manager = SalesDataManager(paths)
            manager.load_data()
            cleaned = manager.preprocess_data()
            selected = manager.filter_data(district=selection[0], industry=selection[1],
                                           year=selection[2])
            self.assertFalse(selected.empty)
            for records, reference in ((cleaned, expected), (selected, selected_expected)):
                original = records.copy(deep=True)
                result = DemographicAnalyzer(records).gender_sales()
                self.assertEqual(result["total_sales"].tolist(),
                                 [reference[g][0] for g in ("남성", "여성")])
                self.assertEqual(result["total_transactions"].tolist(),
                                 [reference[g][1] for g in ("남성", "여성")])
                figure = DemographicVisualizer().plot_gender(result)
                self.assertEqual(list(figure.data[0].y), result["total_sales"].tolist())
                figure.to_json()
                assert_frame_equal(records, original)


if __name__ == "__main__":
    unittest.main()
