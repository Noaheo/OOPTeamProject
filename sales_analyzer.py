import pandas as pd


class SalesAnalyzer:
    """Sales totals, trends, year comparisons, and day/time breakdowns."""

    _DAY_TYPES = [("Weekday", "주중"), ("Weekend", "주말")]
    _DAYS = [
        ("Mon", "월요일"), ("Tue", "화요일"), ("Wed", "수요일"), ("Thu", "목요일"),
        ("Fri", "금요일"), ("Sat", "토요일"), ("Sun", "일요일"),
    ]
    _TIME_SLOTS = [
        ("00:00-06:00", "시간대_00~06"),
        ("06:00-11:00", "시간대_06~11"),
        ("11:00-14:00", "시간대_11~14"),
        ("14:00-17:00", "시간대_14~17"),
        ("17:00-21:00", "시간대_17~21"),
        ("21:00-24:00", "시간대_21~24"),
    ]

    def __init__(self, sales_data):
        """Keep a copy of the selected sales data."""
        self._sales_data = sales_data.copy()

    def _sum_groups(self, groups, label_col):
        """Aggregate sales amount and transaction count for each (label, prefix) pair."""
        rows = []
        for label, prefix in groups:
            row = {label_col: label}
            for output, suffix in (("total_sales", "금액"), ("total_transactions", "건수")):
                total = (
                    0
                    if self._sales_data.empty
                    else self._sales_data[f"{prefix}_매출_{suffix}"].sum(min_count=1)
                )
                row[output] = pd.NA if pd.isna(total) else int(total)
            rows.append(row)
        result = pd.DataFrame(rows)
        return result.astype({"total_sales": "Int64", "total_transactions": "Int64"})

    @staticmethod
    def _validate_year(year, name):
        if isinstance(year, bool) or not isinstance(year, int):
            raise ValueError(f"{name} must be an integer year")

    def sales_summary(self):
        """Return total sales and transaction counts."""
        if self._sales_data.empty:
            return {"total_sales": 0, "total_transactions": 0}

        sales = self._sales_data["당월_매출_금액"].sum(min_count=1)
        transactions = self._sales_data["당월_매출_건수"].sum(min_count=1)
        return {
            "total_sales": None if pd.isna(sales) else int(sales),
            "total_transactions": None if pd.isna(transactions) else int(transactions),
        }

    def quarterly_trend(self):
        """Sum sales by year and quarter."""
        return (
            self._sales_data.groupby(["year", "quarter"], as_index=False, sort=True)[
                "당월_매출_금액"
            ]
            .sum(min_count=1)
            .rename(columns={"당월_매출_금액": "total_sales"})
        )

    def year_comparison(self, year_a=2024, year_b=2025):
        """Compare matching quarters between two years and compute YoY growth (%)."""
        self._validate_year(year_a, "year_a")
        self._validate_year(year_b, "year_b")
        if year_a == year_b:
            raise ValueError("year_a and year_b must be different years")

        columns = ["quarter", "year_a", "year_b", "sales_a", "sales_b", "difference", "growth_rate"]
        empty = pd.DataFrame({
            "quarter": pd.Series(dtype="int64"),
            "year_a": pd.Series(dtype="int64"),
            "year_b": pd.Series(dtype="int64"),
            "sales_a": pd.Series(dtype="Int64"),
            "sales_b": pd.Series(dtype="Int64"),
            "difference": pd.Series(dtype="Int64"),
            "growth_rate": pd.Series(dtype="float64"),
        })
        if self._sales_data.empty:
            return empty[columns]

        df_a = self._sales_data[self._sales_data["year"] == year_a]
        df_b = self._sales_data[self._sales_data["year"] == year_b]
        matched_quarters = sorted(
            set(df_a["quarter"].dropna().astype(int)) & set(df_b["quarter"].dropna().astype(int))
        )
        if not matched_quarters:
            return empty[columns]

        rows = []
        for quarter in matched_quarters:
            raw_a = df_a.loc[df_a["quarter"] == quarter, "당월_매출_금액"].sum(min_count=1)
            raw_b = df_b.loc[df_b["quarter"] == quarter, "당월_매출_금액"].sum(min_count=1)
            sales_a = pd.NA if pd.isna(raw_a) else int(raw_a)
            sales_b = pd.NA if pd.isna(raw_b) else int(raw_b)

            if pd.isna(sales_a) or pd.isna(sales_b):
                diff = pd.NA
                growth = float("nan")
            else:
                diff = sales_b - sales_a
                growth = float("nan") if sales_a == 0 else round(diff / sales_a * 100, 2)

            rows.append({
                "quarter": int(quarter),
                "year_a": year_a,
                "year_b": year_b,
                "sales_a": sales_a,
                "sales_b": sales_b,
                "difference": diff,
                "growth_rate": growth,
            })

        result = pd.DataFrame(rows, columns=columns)
        return result.astype({
            "quarter": "int64",
            "year_a": "int64",
            "year_b": "int64",
            "sales_a": "Int64",
            "sales_b": "Int64",
            "difference": "Int64",
            "growth_rate": "float64",
        })

    def year_growth_summary(self, year_a=2024, year_b=2025):
        """Summarize growth for quarters with known sales in both years."""
        comparison = self.year_comparison(year_a, year_b).dropna(subset=["sales_a", "sales_b"])
        if comparison.empty:
            return {
                "year_a": year_a,
                "year_b": year_b,
                "matched_quarters": [],
                "sales_a": None,
                "sales_b": None,
                "difference": None,
                "growth_rate": None,
            }

        sales_a = int(comparison["sales_a"].sum())
        sales_b = int(comparison["sales_b"].sum())
        diff = sales_b - sales_a
        growth = None if sales_a == 0 else round(diff / sales_a * 100, 2)

        return {
            "year_a": year_a,
            "year_b": year_b,
            "matched_quarters": [int(q) for q in comparison["quarter"].tolist()],
            "sales_a": sales_a,
            "sales_b": sales_b,
            "difference": diff,
            "growth_rate": growth,
        }

    def weekday_weekend(self):
        """Return weekday vs. weekend sales totals, transaction counts, and sales shares (%)."""
        result = self._sum_groups(self._DAY_TYPES, "day_type")
        total = result["total_sales"].sum(min_count=len(result))
        shares = []
        for value in result["total_sales"]:
            if pd.isna(value) or pd.isna(total):
                shares.append(float("nan"))
            elif int(total) == 0:
                shares.append(0.0)
            else:
                shares.append(round(int(value) / int(total) * 100, 2))
        result["sales_share"] = pd.Series(shares, dtype="float64")
        return result

    def daily_sales(self):
        """Return sales totals and transaction counts for each day of the week."""
        return self._sum_groups(self._DAYS, "day")

    def time_slot_sales(self):
        """Return sales totals and transaction counts for each time slot."""
        return self._sum_groups(self._TIME_SLOTS, "time_slot")
