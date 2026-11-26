from pathlib import Path

import pandas as pd


class MapAnalyzer:
    """Combine district sales with their map locations."""

    _LOCATION_FILE = Path(__file__).parent / "assets" / "district_locations.csv"
    _TYPES = {
        "A": "Alley",
        "D": "Developed",
        "R": "Traditional market",
        "U": "Tourist zone",
    }

    def __init__(self, sales_data, locations=None):
        """Keep a copy of the selected records and district locations."""
        self._sales_data = sales_data.copy()
        self._locations = (
            pd.read_csv(self._LOCATION_FILE, dtype={"district_code": "string"})
            if locations is None else locations.copy()
        )
        self._locations["district_code"] = self._locations["district_code"].astype("string").str.strip()

    def prepare_map_data(self):
        """Return district totals and coordinates, keeping unmapped districts."""
        frame = self._sales_data.copy()
        frame["상권_코드"] = frame["상권_코드"].astype("string").str.strip()
        metrics = ["당월_매출_금액", "당월_매출_건수"]
        totals = frame.groupby("상권_코드", as_index=False, sort=True)[metrics].sum(min_count=1)

        order = [column for column in ("year", "quarter") if column in frame.columns]
        ordered = frame.sort_values(order, kind="stable") if order else frame
        names = ordered.drop_duplicates("상권_코드", keep="last")[[
            "상권_코드", "상권_코드_명", "상권_구분_코드",
        ]].copy()
        names["district_type"] = names["상권_구분_코드"].map(self._TYPES).fillna("Other")
        result = totals.merge(names, on="상권_코드", how="left", validate="one_to_one").rename(columns={
            "상권_코드": "district_code",
            "상권_코드_명": "district_name",
            "당월_매출_금액": "total_sales",
            "당월_매출_건수": "total_transactions",
        })
        result = result.merge(
            self._locations[["district_code", "latitude", "longitude"]],
            on="district_code", how="left", validate="one_to_one",
        )
        result["district_name"] = result["district_name"].fillna(result["district_code"])
        columns = [
            "district_code", "district_name", "district_type", "total_sales",
            "total_transactions", "latitude", "longitude",
        ]
        return result[columns].astype({"total_sales": "Int64", "total_transactions": "Int64"})
