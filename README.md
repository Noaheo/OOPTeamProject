# OOPTeamProject
Seoul Commercial District Sales Analysis Dashboard

## Sales demo

Install the sales modules' dependencies:

```sh
python -m pip install pandas plotly
```

Extract the 2024 and 2025 CSV files from `data(23~25).zip`. Load and clean them with `SalesDataManager`, then pass the selected records to `SalesAnalyzer`:

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

`SalesAnalyzer` keeps a copy of the cleaned input, including the manager's `year` and `quarter` columns. It does not load CSV files or change the supplied table.

- `sales_summary()` returns `{"total_sales": int, "total_transactions": int}`. Sales are in KRW. Transactions are the sum of `당월_매출_건수`, not the row count. An empty selection returns both totals as zero.
- `quarterly_trend()` returns a DataFrame with `year`, `quarter` and `total_sales` columns, sorted by year and quarter. It sums `당월_매출_금액` separately for each year and quarter. Only observed quarters are included; an empty selection returns the same columns with no rows.
- `SalesVisualizer().plot_trend(trend)` returns a Plotly `Figure` with labels such as `2024 Q1`, sales in KRW, and hover values. It preserves the result order and does not change the trend table. `DashboardManager` handles displaying it.

Totals sum available metric values. For a nonempty selection with an entirely missing metric, the summary returns `None`; a quarter with entirely missing sales keeps a pandas missing value and appears as a gap in the chart.

This demo includes only the summary and quarterly trend. The other sales methods from the project proposal are planned for the final project.

Run the checks from the repository root:

```sh
python -m unittest discover -s tests -v
```

The tests cover known sample totals, chronological grouping across years, empty selections, missing metrics, input preservation, and Plotly output. Integration tests extract the archived 2024–2025 CSV files to a temporary directory, run the full data-manager-to-chart pipeline, and compare its results with totals calculated independently using Python's CSV reader.

## Gender sales demo

Install the dependencies with `python -m pip install pandas plotly`.
Extract the 2024 and 2025 CSVs from `data(23~25).zip` to a local directory.
Load and preprocess them, then pass selected district, industry and year records to the analyzer:

```python
from data_manager import SalesDataManager
from demographic_analyzer import DemographicAnalyzer
from demographic_visualizer import DemographicVisualizer

manager = SalesDataManager(["path/to/2024.csv", "path/to/2025.csv"])
manager.load_data()
manager.preprocess_data()
selected = manager.filter_data(year=[2024, 2025])
# Optionally pass district="district_code" and industry="industry_code".
gender_data = DemographicAnalyzer(selected).gender_sales()
gender_figure = DemographicVisualizer().plot_gender(gender_data)
```

`gender_sales()` returns a new DataFrame with two rows, `Male` then `Female`, and columns `gender`, `total_sales` (KRW), and `total_transactions` (transaction count). The two numeric columns use pandas nullable `Int64`. It sums the original `남성_매출_금액`, `여성_매출_금액`, `남성_매출_건수`, and `여성_매출_건수` columns and preserves the supplied data. Filters belong to `SalesDataManager`; the analyzer keeps a snapshot and does not apply additional filters.

Missing values are excluded from totals; an entirely missing metric remains missing rather than becoming zero. An empty selection returns two rows of zero totals. `plot_gender()` returns a Plotly bar Figure without changing its input; missing sales serialize as null rather than zero. The dashboard can display it with `st.plotly_chart(gender_figure)` and show transaction counts in a table. This branch does not implement a Streamlit dashboard or age-group analysis.

Run `python -m unittest discover -s tests -v` to include the gender unit tests and the real 2024–2025 CSV integration check. The latter independently checks both gender amounts and counts, including district/industry/year filtering.