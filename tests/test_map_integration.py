import csv
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from pandas.testing import assert_frame_equal

from data_manager import SalesDataManager
from map_analyzer import MapAnalyzer
from map_visualizer import MapVisualizer


class MapIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.scopes = [
            {},
            {"year": 2025},
            {"industry": "CS100001", "year": 2024, "quarter": 1},
            {"district": "3001492", "industry": "CS100001", "year": 2025, "quarter": 2},
        ]
        cls.expected = [{} for _ in cls.scopes]
        paths = []
        archive_path = Path(__file__).resolve().parents[1] / "data(23~25).zip"
        with zipfile.ZipFile(archive_path) as archive:
            for name in archive.namelist():
                if not name.endswith(".csv"):
                    continue
                path = Path(cls.directory.name) / Path(name).name
                with archive.open(name) as source, path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                paths.append(path)
                with path.open(encoding="cp949", newline="") as source:
                    for row in csv.DictReader(source):
                        selection = {
                            "year": int(row["기준_년분기_코드"][:4]),
                            "quarter": int(row["기준_년분기_코드"][4]),
                            "industry": row["서비스_업종_코드"],
                            "district": row["상권_코드"],
                        }
                        for scope, expected in zip(cls.scopes, cls.expected):
                            if all(selection[key] == value for key, value in scope.items()):
                                totals = expected.setdefault(row["상권_코드"], [0, 0])
                                totals[0] += int(row["당월_매출_금액"])
                                totals[1] += int(row["당월_매출_건수"])
        cls.manager = SalesDataManager(paths)
        cls.manager.load_data()
        cls.manager.preprocess_data()

    def test_district_totals_and_map_points_match_raw_csv(self):
        for scope, expected in zip(self.scopes, self.expected):
            with self.subTest(scope=scope):
                records = self.manager.filter_data(**scope)
                original = records.copy(deep=True)
                prepared = MapAnalyzer(records).prepare_map_data()
                before_plot = prepared.copy(deep=True)
                actual = {
                    row.district_code: [int(row.total_sales), int(row.total_transactions)]
                    for row in prepared.itertuples(index=False)
                }
                self.assertEqual(actual, expected)
                self.assertFalse(prepared[["latitude", "longitude"]].isna().any().any())

                figure = MapVisualizer().plot_map(prepared)
                points = {
                    code: [int(detail[3].replace(",", "")), int(detail[4].replace(",", ""))]
                    for trace in figure.data
                    for code, detail in zip(trace.ids, trace.customdata)
                }
                self.assertEqual(points, expected)
                self.assertEqual(sum(len(trace.ids) for trace in figure.data), len(expected))
                figure.to_json()
                assert_frame_equal(prepared, before_plot)
                assert_frame_equal(records, original)

    def test_empty_filtered_chain(self):
        records = self.manager.filter_data(district="missing-district")
        prepared = MapAnalyzer(records).prepare_map_data()
        figure = MapVisualizer().plot_map(prepared)

        self.assertTrue(prepared.empty)
        self.assertEqual(len(figure.data), 0)
        self.assertTrue(figure.layout.annotations)
        figure.to_json()


if __name__ == "__main__":
    unittest.main()
