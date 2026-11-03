import csv
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from pandas.testing import assert_frame_equal
import plotly.graph_objects as go

from data_manager import SalesDataManager
from sales_analyzer import SalesAnalyzer
from sales_visualizer import SalesVisualizer


class SalesIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csv_directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(csv_directory.cleanup)
        archive_path = Path(__file__).resolve().parents[1] / "data(23~25).zip"
        paths = []
        cls.expected = {}
        with zipfile.ZipFile(archive_path) as archive:
            for year in (2024, 2025):
                member = next(name for name in archive.namelist()
                              if str(year) in name and name.endswith(".csv"))
                path = Path(csv_directory.name) / f"sales_{year}.csv"
                with archive.open(member) as source, path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                paths.append(path)

                # Compute an independent reference directly from the raw CSV.
                with path.open(encoding="cp949", newline="") as source:
                    for row in csv.DictReader(source):
                        period = row["기준_년분기_코드"]
                        key = (int(period[:4]), int(period[4]))
                        totals = cls.expected.setdefault(key, [0, 0])
                        totals[0] += int(row["당월_매출_금액"])
                        totals[1] += int(row["당월_매출_건수"])

        cls.manager = SalesDataManager(paths)
        cls.manager.load_data()
        cls.cleaned = cls.manager.preprocess_data()

    def test_full_pipeline_matches_raw_csv_totals(self):
        analyzer = SalesAnalyzer(self.cleaned)
        summary = analyzer.sales_summary()
        trend = analyzer.quarterly_trend()
        figure = SalesVisualizer().plot_trend(trend)
        periods = [(year, quarter) for year in (2024, 2025) for quarter in range(1, 5)]
        sales = [self.expected[key][0] for key in periods]

        self.assertEqual(sorted(self.expected), periods)
        self.assertEqual(summary, {
            "total_sales": sum(sales),
            "total_transactions": sum(totals[1] for totals in self.expected.values()),
        })
        self.assertEqual(trend.to_dict("records"), [
            {"year": year, "quarter": quarter, "total_sales": self.expected[(year, quarter)][0]}
            for year, quarter in periods
        ])
        self.assertIsInstance(figure, go.Figure)
        self.assertEqual(list(figure.data[0].x), [f"{year} Q{quarter}" for year, quarter in periods])
        self.assertEqual(list(figure.data[0].y), sales)
        figure.to_json()
        assert_frame_equal(self.cleaned, self.manager.processed_data())

    def test_filtered_pipeline(self):
        first_record = self.cleaned.iloc[0]
        selected = self.manager.filter_data(district=first_record["상권_코드"],
                                            industry=first_record["서비스_업종_코드"],
                                            year=[2024, 2025])
        analyzer = SalesAnalyzer(selected)
        trend = analyzer.quarterly_trend()
        figure = SalesVisualizer().plot_trend(trend)

        self.assertFalse(trend.empty)
        self.assertEqual(analyzer.sales_summary()["total_sales"],
                         int(selected["당월_매출_금액"].sum()))
        self.assertEqual(list(figure.data[0].y), trend["total_sales"].tolist())

    def test_empty_filtered_pipeline(self):
        selected = self.manager.filter_data(district=[])
        analyzer = SalesAnalyzer(selected)
        trend = analyzer.quarterly_trend()
        figure = SalesVisualizer().plot_trend(trend)

        self.assertEqual(analyzer.sales_summary(), {"total_sales": 0, "total_transactions": 0})
        self.assertTrue(trend.empty)
        self.assertIsInstance(figure, go.Figure)
        self.assertEqual(len(figure.data[0].x), 0)
        figure.to_json()


if __name__ == "__main__":
    unittest.main()
