"""Commercial-district ranking from cleaned Seoul Open Data sales records."""

import pandas as pd


class DistrictComparator:
    """Calculate sales rankings; leave chart rendering to DistrictVisualizer.

    Input is a DataFrame from SalesDataManager.filter_data(industry=..., year=...).
    For a city-wide ranking, do NOT pre-filter to a single district.
    If multiple quarters are selected, totals are summed across those quarters.
    """

    _REQUIRED = ("상권_코드", "상권_코드_명", "당월_매출_금액")

    def __init__(self, sales_data: pd.DataFrame):
        if not isinstance(sales_data, pd.DataFrame):
            raise TypeError("sales_data must be a pandas DataFrame")
        missing = [column for column in self._REQUIRED if column not in sales_data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        self._sales_data = sales_data.copy()

    def rank_districts(self, n: int = 5, order: str = "top") -> pd.DataFrame:
        """Return the n highest- or lowest-sales districts.

        Parameters:
            n: Number of districts (usually 5 or 10).
            order: 'top' for highest sales or 'bottom' for lowest sales.

        Result columns: rank, district_code, district_name, total_sales.
        Rows with no available sales amount are excluded from ranking.
        Ties are resolved deterministically by district code (ascending).
        """
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("n must be a positive integer")
        if order not in ("top", "bottom"):
            raise ValueError("order must be 'top' or 'bottom'")

        columns = ["rank", "district_code", "district_name", "total_sales"]
        if self._sales_data.empty:
            return pd.DataFrame(columns=columns)

        frame = self._sales_data[list(self._REQUIRED)].copy()
        frame["당월_매출_금액"] = pd.to_numeric(frame["당월_매출_금액"], errors="raise")
        # Group by stable code; do not split a district when its displayed name changes.
        totals = (frame.groupby("상권_코드", as_index=False, sort=False)
                  ["당월_매출_금액"].sum(min_count=1))
        names = (frame.dropna(subset=["상권_코드_명"])
                 .drop_duplicates(subset=["상권_코드"], keep="last")
                 [["상권_코드", "상권_코드_명"]])
        totals = totals.merge(names, on="상권_코드", how="left")
        totals = totals.dropna(subset=["당월_매출_금액"])
        totals = totals.sort_values(
            ["당월_매출_금액", "상권_코드"],
            ascending=[order == "bottom", True],
            kind="stable",
        ).head(n).reset_index(drop=True)
        result = totals.rename(columns={
            "상권_코드": "district_code",
            "상권_코드_명": "district_name",
            "당월_매출_금액": "total_sales",
        })
        result.insert(0, "rank", range(1, len(result) + 1))
        return result[columns]
