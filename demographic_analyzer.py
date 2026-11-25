import pandas as pd


class DemographicAnalyzer:
    """Demographic summaries of cleaned, already filtered sales records."""

    _GENDERS = [("Male", "남성"), ("Female", "여성")]
    _AGE_GROUPS = [
        ("10s", "연령대_10"),
        ("20s", "연령대_20"),
        ("30s", "연령대_30"),
        ("40s", "연령대_40"),
        ("50s", "연령대_50"),
        ("60+", "연령대_60_이상"),
    ]

    def __init__(self, sales_data):
        """Keep a snapshot, including any selected district, industry and period."""
        self._sales_data = sales_data.copy()

    def _sum_groups(self, groups, label_col):
        """Aggregate sales amount and transaction counts for each (label, prefix) pair."""
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
    def _add_shares(frame):
        """Append sales_share and transaction_share (%) columns to a demographic summary table."""
        result = frame.copy()
        for source_col, share_col in (
            ("total_sales", "sales_share"),
            ("total_transactions", "transaction_share"),
        ):
            total = result[source_col].sum(min_count=1)
            shares = []
            for value in result[source_col]:
                if pd.isna(value):
                    shares.append(float("nan"))
                elif pd.isna(total) or int(total) == 0:
                    shares.append(0.0)
                else:
                    shares.append(round(int(value) / int(total) * 100, 2))
            result[share_col] = pd.Series(shares, dtype="float64")
        return result

    def gender_sales(self):
        """Return Male/Female totals in KRW and transaction counts.

        Missing values are excluded from sums. An entirely missing metric stays
        missing; an empty selection returns zero totals for both genders.
        """
        return self._sum_groups(self._GENDERS, "gender")

    def age_group_sales(self):
        """Return age-group totals (10s to 60+) in KRW and transaction counts."""
        return self._sum_groups(self._AGE_GROUPS, "age_group")

    def gender_share(self):
        """Return gender totals along with percentage shares."""
        return self._add_shares(self.gender_sales())

    def age_group_share(self):
        """Return age-group totals along with percentage shares."""
        return self._add_shares(self.age_group_sales())

    def top_age_group(self):
        """Return the age group with the highest estimated sales, or None if unavailable."""
        shares = self.age_group_share()
        valid = shares[shares["total_sales"].notna() & (shares["total_sales"] > 0)]
        if valid.empty:
            return None
        top_idx = valid["total_sales"].astype("int64").idxmax()
        row = valid.loc[top_idx]
        return {
            "age_group": str(row["age_group"]),
            "total_sales": int(row["total_sales"]),
            "total_transactions": (
                None if pd.isna(row["total_transactions"]) else int(row["total_transactions"])
            ),
            "sales_share": float(row["sales_share"]),
        }
