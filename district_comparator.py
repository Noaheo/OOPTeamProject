"""Commercial-district ranking and comparison from cleaned Seoul Open Data sales records."""

from collections.abc import Iterable
import pandas as pd


class DistrictComparator:
    """Calculate district rankings and multi-district gaps; leave chart rendering to DistrictVisualizer.

    Input is a DataFrame from SalesDataManager.filter_data(industry=..., year=...).
    For a city-wide ranking or multi-district comparison, do NOT pre-filter to a single district.
    If multiple quarters are selected, totals are summed across those quarters.
    """

    _REQUIRED = ("상권_코드", "상권_코드_명", "당월_매출_금액")

    def __init__(
        self,
        sales_data: pd.DataFrame,
        category: str | None = None,
        period: str | None = None,
        reference_district: str | None = None,
    ):
        if not isinstance(sales_data, pd.DataFrame):
            raise TypeError("sales_data must be a pandas DataFrame")
        missing = [column for column in self._REQUIRED if column not in sales_data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        self._sales_data = sales_data.copy()
        self._category = category
        self._period = period
        self._reference_district = reference_district

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
        totals = (
            frame.groupby("상권_코드", as_index=False, sort=False)["당월_매출_금액"]
            .sum(min_count=1)
        )
        names = (
            frame.dropna(subset=["상권_코드_명"])
            .drop_duplicates(subset=["상권_코드"], keep="last")[["상권_코드", "상권_코드_명"]]
        )
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

    def compare_districts(self, ids, reference_id: str | None = None) -> pd.DataFrame:
        """Compare 2 or more districts and compute absolute and percentage gaps vs. a reference district.

        Result columns: district_code, district_name, total_sales, difference, percent_diff, is_reference.
        """
        if isinstance(ids, (str, bytes)) or not isinstance(ids, Iterable):
            raise ValueError("ids must be an iterable of 2 or more district codes")

        unique_ids = []
        seen = set()
        for item in ids:
            code = str(item).strip()
            if code and code not in seen:
                seen.add(code)
                unique_ids.append(code)

        if len(unique_ids) < 2:
            raise ValueError("Select at least 2 distinct district codes to compare")

        if reference_id is None:
            resolved_ref = str(self._reference_district).strip() if self._reference_district is not None else unique_ids[0]
        else:
            resolved_ref = str(reference_id).strip()

        if resolved_ref not in seen:
            raise ValueError(f"reference_id '{resolved_ref}' must be one of the selected district codes")
        self._reference_district = resolved_ref

        frame = self._sales_data[list(self._REQUIRED)].copy()
        frame["상권_코드"] = frame["상권_코드"].astype(str).str.strip()
        frame = frame[frame["상권_코드"].isin(unique_ids)]
        if not frame.empty:
            frame["당월_매출_금액"] = pd.to_numeric(frame["당월_매출_금액"], errors="raise")
            totals_df = (
                frame.groupby("상권_코드", as_index=False, sort=False)["당월_매출_금액"]
                .sum(min_count=1)
            )
            names_df = (
                frame.dropna(subset=["상권_코드_명"])
                .drop_duplicates(subset=["상권_코드"], keep="last")[["상권_코드", "상권_코드_명"]]
            )
            sales_map = dict(zip(totals_df["상권_코드"], totals_df["당월_매출_금액"]))
            name_map = dict(zip(names_df["상권_코드"], names_df["상권_코드_명"]))
        else:
            sales_map = {}
            name_map = {}

        raw_ref = sales_map.get(resolved_ref, pd.NA)
        ref_sales = pd.NA if pd.isna(raw_ref) else int(raw_ref)

        rows = []
        for code in unique_ids:
            raw_sales = sales_map.get(code, pd.NA)
            total_sales = pd.NA if pd.isna(raw_sales) else int(raw_sales)
            name = name_map.get(code)
            if pd.isna(name) or not str(name).strip():
                name = code

            if pd.isna(total_sales) or pd.isna(ref_sales):
                difference = pd.NA
                percent_diff = float("nan")
            else:
                difference = total_sales - ref_sales
                percent_diff = float("nan") if ref_sales == 0 else round(difference / ref_sales * 100, 2)

            rows.append({
                "district_code": code,
                "district_name": str(name),
                "total_sales": total_sales,
                "difference": difference,
                "percent_diff": percent_diff,
                "is_reference": code == resolved_ref,
            })

        columns = ["district_code", "district_name", "total_sales", "difference", "percent_diff", "is_reference"]
        result = pd.DataFrame(rows, columns=columns)
        result["_sort_sales"] = pd.to_numeric(result["total_sales"], errors="coerce")
        result = (
            result.sort_values(
                ["_sort_sales", "district_code"],
                ascending=[False, True],
                na_position="last",
                kind="stable",
            )
            .drop(columns=["_sort_sales"])
            .reset_index(drop=True)
        )
        return result.astype({
            "district_code": "object",
            "district_name": "object",
            "total_sales": "Int64",
            "difference": "Int64",
            "percent_diff": "float64",
            "is_reference": "bool",
        })
