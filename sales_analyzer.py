import pandas as pd


class SalesAnalyzer:
    """Sales totals and quarterly trends."""

    def __init__(self, sales_data):
        """Keep a copy of the selected sales data."""
        self._sales_data = sales_data.copy()

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
        return (self._sales_data.groupby(["year", "quarter"], as_index=False, sort=True)
                ["당월_매출_금액"].sum(min_count=1)
                .rename(columns={"당월_매출_금액": "total_sales"}))
