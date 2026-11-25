import tempfile
from pathlib import Path
import unittest

import pandas as pd
import plotly.graph_objects as go

from dashboard_manager import DashboardManager, FilterState, PANELS
from data_manager import METRIC_COLUMNS, SalesDataManager
from demographic_analyzer import DemographicAnalyzer
from demographic_visualizer import DemographicVisualizer
from district_comparator import DistrictComparator
from district_visualizer import DistrictVisualizer
from sales_analyzer import SalesAnalyzer
from sales_visualizer import SalesVisualizer


class _MockMapVisualizer:
    def __init__(self):
        self.received_rows = None

    def plot_map(self, data):
        self.received_rows = len(data)
        return go.Figure(go.Scatter(x=[127.0], y=[37.5], mode="markers"))


class DashboardIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tempdir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tempdir.cleanup)

        rows = []
        for year, multiplier in ((2023, 100), (2024, 150)):
            for quarter in (1, 2):
                for code, name, factor in (("D001", "강남역", 3), ("D002", "홍대입구역", 2)):
                    row = {
                        "기준_년분기_코드": f"{year}{quarter}",
                        "상권_구분_코드": "A",
                        "상권_구분_코드_명": "발달상권",
                        "상권_코드": code,
                        "상권_코드_명": name,
                        "서비스_업종_코드": "CS100001",
                        "서비스_업종_코드_명": "한식음식점",
                    }
                    for col in METRIC_COLUMNS:
                        row[col] = str(multiplier * factor)
                    rows.append(row)

        csv_path = Path(cls._tempdir.name) / "sample.csv"
        pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")

        cls.manager = SalesDataManager([csv_path])
        cls.manager.load_data()
        cls.manager.preprocess_data()

    def _build_dashboard(self, map_visualizer=None):
        return DashboardManager(
            self.manager,
            sales_analyzer=SalesAnalyzer,
            sales_visualizer=SalesVisualizer(),
            demographic_analyzer=DemographicAnalyzer,
            demographic_visualizer=DemographicVisualizer(),
            district_comparator=DistrictComparator,
            district_visualizer=DistrictVisualizer(),
            map_visualizer=map_visualizer,
        )

    def test_all_core_panels_ready_and_map_slot_toggles(self):
        dash_no_map = self._build_dashboard()
        for key in PANELS:
            if key == "district_map":
                self.assertFalse(dash_no_map._ready(key))
            else:
                self.assertTrue(dash_no_map._ready(key), f"Expected panel {key} to be ready")

        dash_with_map = self._build_dashboard(map_visualizer=_MockMapVisualizer())
        self.assertTrue(dash_with_map._ready("district_map"))

    def test_yoy_growth_available_for_2024_and_missing_for_earliest_year_2023(self):
        yoy_2024 = self.manager.filter_data(year=[2023, 2024], quarter=1)
        res_2024 = SalesAnalyzer(yoy_2024).year_growth_summary(2023, 2024)
        self.assertEqual(res_2024["matched_quarters"], [1])
        self.assertAlmostEqual(res_2024["growth_rate"], 50.0, places=2)

        yoy_2023 = self.manager.filter_data(year=[2022, 2023], quarter=1)
        res_2023 = SalesAnalyzer(yoy_2023).year_growth_summary(2022, 2023)
        self.assertEqual(res_2023["matched_quarters"], [])
        self.assertIsNone(res_2023["growth_rate"])

    def test_localize_districts_preserves_original_dataframe(self):
        dash = self._build_dashboard()
        dash._district_names = {"D001": "Gangnam Station", "D002": "Hongdaeipgu Station"}
        ranking = DistrictComparator(self.manager.filter_data(year=2024)).rank_districts(5, "top")
        original = ranking.copy(deep=True)
        localized = dash._localize_districts(ranking)

        self.assertEqual(ranking["district_name"].tolist(), ["강남역", "홍대입구역"])
        self.assertEqual(localized["district_name"].tolist(), ["Gangnam Station", "Hongdaeipgu Station"])
        pd.testing.assert_frame_equal(ranking, original)

    def test_filter_scopes_feed_map_and_comparison(self):
        dash = self._build_dashboard(map_visualizer=_MockMapVisualizer())
        filters = FilterState(
            district="D001",
            district_name="Gangnam Station",
            industry="CS100001",
            industry_name="Korean Restaurant",
            year=2024,
            quarter=1,
        )
        self.assertEqual(len(dash._period_data(filters)), 1)
        self.assertEqual(len(dash._trend_data(filters)), 4)
        self.assertEqual(len(dash._ranking_data(filters)), 2)


if __name__ == "__main__":
    unittest.main()
