import pandas as pd


class DemographicAnalyzer:
    """Demographic summaries of cleaned, already filtered sales records."""

    def __init__(self, sales_data):
        """Keep a snapshot, including any selected district, industry and period."""
        self._sales_data = sales_data.copy()

    def gender_sales(self):
        """Return Male/Female totals in KRW and transaction counts.

        Missing values are excluded from sums. An entirely missing metric stays
        missing; an empty selection returns zero totals for both genders.
        """
        rows = []
        for gender, prefix in (("Male", "남성"), ("Female", "여성")):
            row = {"gender": gender}
            for output, suffix in (("total_sales", "금액"),
                                   ("total_transactions", "건수")):
                total = (0 if self._sales_data.empty else
                         self._sales_data[f"{prefix}_매출_{suffix}"].sum(min_count=1))
                row[output] = pd.NA if pd.isna(total) else int(total)
            rows.append(row)
        result = pd.DataFrame(rows)
        return result.astype({"total_sales": "Int64", "total_transactions": "Int64"})
