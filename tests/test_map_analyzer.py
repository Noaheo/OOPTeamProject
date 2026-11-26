import csv
import io
import json
from pathlib import Path
import unittest
import zipfile

import pandas as pd
from pandas.testing import assert_frame_equal

from map_analyzer import MapAnalyzer


class MapAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.records = pd.DataFrame({
            "상권_코드": ["A", "B", "A", "C"],
            "상권_코드_명": ["New name", "Same name", "Old name", "Same name"],
            "상권_구분_코드": ["A", "D", "A", "R"],
            "year": [2025, 2025, 2024, 2025],
            "quarter": [1, 1, 4, 1],
            "당월_매출_금액": pd.Series([200, 0, 100, pd.NA], dtype="Int64"),
            "당월_매출_건수": pd.Series([20, 0, 10, pd.NA], dtype="Int64"),
        })
        self.locations = pd.DataFrame({
            "district_code": ["A", "B"],
            "latitude": [37.55, 37.60],
            "longitude": [126.98, 127.01],
        })

    def test_groups_by_code_and_keeps_latest_name(self):
        result = MapAnalyzer(self.records, self.locations).prepare_map_data()

        self.assertEqual(result["district_code"].tolist(), ["A", "B", "C"])
        self.assertEqual(result["district_name"].tolist(), ["New name", "Same name", "Same name"])
        self.assertEqual(result["district_type"].tolist(), ["Alley", "Developed", "Traditional market"])
        self.assertEqual(result["total_sales"].iloc[:2].tolist(), [300, 0])
        self.assertEqual(result["total_transactions"].iloc[:2].tolist(), [30, 0])
        self.assertEqual(result["latitude"].iloc[:2].tolist(), [37.55, 37.60])

    def test_unknown_sales_and_coordinates_stay_unknown(self):
        result = MapAnalyzer(self.records, self.locations).prepare_map_data()

        self.assertTrue(pd.isna(result.loc[2, "total_sales"]))
        self.assertTrue(pd.isna(result.loc[2, "total_transactions"]))
        self.assertTrue(pd.isna(result.loc[2, "latitude"]))
        self.assertTrue(pd.isna(result.loc[2, "longitude"]))

    def test_empty_selection_keeps_schema(self):
        result = MapAnalyzer(self.records.iloc[:0], self.locations).prepare_map_data()

        self.assertTrue(result.empty)
        self.assertEqual(result.columns.tolist(), [
            "district_code", "district_name", "district_type", "total_sales",
            "total_transactions", "latitude", "longitude",
        ])

    def test_input_snapshot_and_result_are_independent(self):
        original = self.records.copy(deep=True)
        original_locations = self.locations.copy(deep=True)
        analyzer = MapAnalyzer(self.records, self.locations)
        result = analyzer.prepare_map_data()
        assert_frame_equal(self.records, original)
        assert_frame_equal(self.locations, original_locations)

        self.records.loc[0, "당월_매출_금액"] = 999
        self.locations.loc[0, "latitude"] = 0
        result.loc[0, "total_sales"] = 999
        result.loc[0, "latitude"] = 0
        repeated = analyzer.prepare_map_data()
        self.assertEqual(repeated.loc[0, "total_sales"], 300)
        self.assertEqual(repeated.loc[0, "latitude"], 37.55)

    def test_duplicate_locations_cannot_multiply_sales(self):
        locations = pd.concat([self.locations, self.locations.iloc[:1]], ignore_index=True)

        with self.assertRaises(pd.errors.MergeError):
            MapAnalyzer(self.records, locations).prepare_map_data()

    def test_demographic_share_uses_district_totals_and_keeps_unavailable_shares(self):
        self.records["남성_매출_금액"] = pd.Series([30, 0, 10, 5], dtype="Int64")
        self.records["여성_매출_금액"] = pd.Series([10, 0, 50, pd.NA], dtype="Int64")

        groups = [("Male", "남성"), ("Female", "여성")]
        data = MapAnalyzer(self.records, self.locations).prepare_demographic_map_data(groups, "Male")
        by_code = data.set_index("district_code")
        self.assertEqual(by_code.loc["A", "sales_share"], 40)
        self.assertEqual(by_code.loc["A", "group_sales"], 40)
        self.assertEqual(by_code.loc["B", "sales_share"], 0)
        self.assertTrue(pd.isna(by_code.loc["C", "sales_share"]))

    def test_comparison_keeps_selected_district_without_sales(self):
        districts = pd.DataFrame({
            "district_code": ["A", "B"],
            "district_name": ["New name", "Same name"],
            "total_sales": pd.Series([300, pd.NA], dtype="Int64"),
        })
        data = MapAnalyzer(self.records[self.records["상권_코드"].eq("A")], self.locations)
        prepared = data.prepare_map_data(districts).set_index("district_code")

        self.assertEqual(prepared.index.tolist(), ["A", "B"])
        self.assertEqual(prepared.loc["B", "latitude"], 37.60)
        self.assertTrue(pd.isna(prepared.loc["B", "total_sales"]))
        self.assertTrue(pd.isna(prepared.loc["B", "total_transactions"]))

    def test_bundled_locations_cover_every_archived_district(self):
        project = Path(__file__).resolve().parents[1]
        codes = set()
        with zipfile.ZipFile(project / "data(23~25).zip") as archive:
            for name in archive.namelist():
                if name.endswith(".csv"):
                    with archive.open(name) as source:
                        rows = csv.DictReader(io.TextIOWrapper(source, encoding="cp949"))
                        codes.update(row["상권_코드"] for row in rows)

        locations = pd.read_csv(project / "assets" / "district_locations.csv", dtype={"district_code": "string"})
        self.assertEqual(set(locations["district_code"]), codes)
        self.assertTrue(locations["district_code"].is_unique)
        self.assertTrue(locations["latitude"].between(37.3, 37.8).all())
        self.assertTrue(locations["longitude"].between(126.7, 127.3).all())

        boundaries = json.loads((project / "assets" / "district_boundaries.geojson").read_text(encoding="utf-8"))
        boundary_codes = [feature["properties"]["district_code"] for feature in boundaries["features"]]
        self.assertEqual(len(boundary_codes), len(codes))
        self.assertEqual(set(boundary_codes), codes)


if __name__ == "__main__":
    unittest.main()
