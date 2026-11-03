# OOPTeamProject
Seoul Commercial District Sales Analysis Dashboard

## Sales demo

Install the sales modules' dependencies:

```sh
python -m pip install pandas plotly
```

Extract the 2024 and 2025 CSV files from `data(23~25).zip`. Load and clean them
with `SalesDataManager`, then pass the selected records to `SalesAnalyzer`:

```python
from data_manager import SalesDataManager
from sales_analyzer import SalesAnalyzer
from sales_visualizer import SalesVisualizer

manager = SalesDataManager(["path/to/2024.csv", "path/to/2025.csv"])
manager.load_data()
manager.preprocess_data()
sales_data = manager.filter_data(year=[2024, 2025])

analyzer = SalesAnalyzer(sales_data)
summary = analyzer.sales_summary()
trend = analyzer.quarterly_trend()
figure = SalesVisualizer().plot_trend(trend)
```

`SalesAnalyzer` keeps a copy of the cleaned input, including the manager's `year`
and `quarter` columns. It does not load CSV files or change the supplied table.

- `sales_summary()` returns `{"total_sales": int, "total_transactions": int}`.
  Sales are in KRW. Transactions are the sum of `당월_매출_건수`, not the row count.
  An empty selection returns both totals as zero.
- `quarterly_trend()` returns a DataFrame with `year`, `quarter` and `total_sales`
  columns, sorted by year and quarter. It sums `당월_매출_금액` separately for each
  year and quarter. Only observed quarters are included; an empty selection
  returns the same columns with no rows.
- `SalesVisualizer().plot_trend(trend)` returns a Plotly `Figure` with labels such
  as `2024 Q1`, sales in KRW, and hover values. It preserves the result order and
  does not change the trend table. `DashboardManager` handles displaying it.

Totals sum available metric values. For a nonempty selection with an entirely
missing metric, the summary returns `None`; a quarter with entirely missing sales
keeps a pandas missing value and appears as a gap in the chart.

This demo includes only the summary and quarterly trend. The other sales methods
from the project proposal are planned for the final project.

Run the checks from the repository root:

```sh
python -m unittest discover -s tests -v
```

The tests cover known sample totals, chronological grouping across years,
empty selections, missing metrics, input preservation, and Plotly output.
Integration tests extract the archived 2024–2025 CSV files to a temporary
directory, run the full data-manager-to-chart pipeline, and compare its results
with totals calculated independently using Python's CSV reader.
