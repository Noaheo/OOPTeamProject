import pandas as pd


class SalesAnalyzer:
    """Analyze a cleaned DataFrame supplied by SalesDataManager."""

    def __init__(self, sales_data):
        self._sales_data = sales_data.copy()

    def sales_summary(self):
        """Return total_sales (KRW) and total_transactions as a dictionary.

        Sum available values; an entirely missing metric returns None.
        An empty selection returns zero for both totals.
        """
        if self._sales_data.empty:
            return {"total_sales": 0, "total_transactions": 0}

        sales = self._sales_data["당월_매출_금액"].sum(min_count=1)
        transactions = self._sales_data["당월_매출_건수"].sum(min_count=1)
        return {
            "total_sales": None if pd.isna(sales) else int(sales),
            "total_transactions": None if pd.isna(transactions) else int(transactions),
        }
