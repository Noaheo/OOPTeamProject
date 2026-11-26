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

    def prepare_map_data(self, districts=None):
        """Return district totals and coordinates, keeping unmapped districts."""
        frame = self._sales_data
        if districts is not None:
            frame = frame.loc[frame["상권_코드"].isin(districts["district_code"])]
        totals = self._district_totals(frame).astype({
            "total_sales": "Int64", "total_transactions": "Int64",
        })
        if districts is not None:
            totals = districts[["district_code", "district_name", "total_sales"]].merge(
                totals.drop(columns=["district_name", "total_sales"]),
                on="district_code", how="left", validate="one_to_one",
            )
            totals = totals.astype({"total_sales": "Int64", "total_transactions": "Int64"})
        return self._with_locations(totals)

    def prepare_demographic_map_data(self, groups, group):
        """Return the selected group's share of recorded sales in each district."""
        sales_columns = [f"{prefix}_매출_금액" for _, prefix in groups]
        group_column = f"{dict(groups)[group]}_매출_금액"
        totals = self._district_totals(self._sales_data, sales_columns)
        recorded_sales = totals[sales_columns].sum(axis=1, min_count=len(sales_columns))
        share = totals[group_column].div(recorded_sales.mask(recorded_sales.eq(0))).mul(100)
        totals["sales_share"] = share.mask(recorded_sales.eq(0) & recorded_sales.notna(), 0).round(2)
        totals["group_sales"] = totals[group_column]
        return self._with_locations(totals.drop(columns=sales_columns))

    def _district_totals(self, frame, extra_metrics=()):
        frame = frame.copy()
        frame["상권_코드"] = frame["상권_코드"].astype("string").str.strip()
        metrics = ["당월_매출_금액", "당월_매출_건수", *extra_metrics]
        totals = frame.groupby("상권_코드", as_index=False, sort=True)[metrics].sum(min_count=1)

        order = [column for column in ("year", "quarter") if column in frame.columns]
        ordered = frame.sort_values(order, kind="stable") if order else frame
        names = ordered.drop_duplicates("상권_코드", keep="last")[[
            "상권_코드", "상권_코드_명", "상권_구분_코드",
        ]].copy()
        names["district_type"] = names["상권_구분_코드"].map(self._TYPES).fillna("Other")
        return totals.merge(names.drop(columns="상권_구분_코드"), on="상권_코드", how="left",
                            validate="one_to_one").rename(columns={
            "상권_코드": "district_code",
            "상권_코드_명": "district_name",
            "당월_매출_금액": "total_sales",
            "당월_매출_건수": "total_transactions",
        })
    def _with_locations(self, totals):
        result = totals.merge(
            self._locations[["district_code", "latitude", "longitude"]],
            on="district_code", how="left", validate="one_to_one",
        )
        result["district_name"] = result["district_name"].fillna(result["district_code"])
        result["district_type"] = result["district_type"].fillna("Other")
        columns = [
            "district_code", "district_name", "district_type", "total_sales",
            "total_transactions", "latitude", "longitude",
        ]
        return result[columns + [column for column in ("sales_share", "group_sales") if column in result]]
