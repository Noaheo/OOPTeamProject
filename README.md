# OOPTeamProject
Seoul Commercial District Sales Analysis Dashboard

## Gender sales demo

Install the dependencies with `python -m pip install pandas plotly`.
Extract the 2024 and 2025 CSVs from `data(23~25).zip` to a local directory.
Load and preprocess them, then pass selected district, industry and year records
to the analyzer:

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

`gender_sales()` returns a new DataFrame with two rows, `Male` then `Female`, and
columns `gender`, `total_sales` (KRW), and `total_transactions` (transaction count).
The two numeric columns use pandas nullable `Int64`. It sums the original
`남성_매출_금액`, `여성_매출_금액`, `남성_매출_건수`, and `여성_매출_건수`
columns and preserves the supplied data. Filters belong to `SalesDataManager`;
the analyzer keeps a snapshot and does not apply additional filters.

Missing values are excluded from totals; an entirely missing metric remains
missing rather than becoming zero. An empty selection returns two rows of zero
totals. `plot_gender()` returns a Plotly bar Figure without changing its input;
missing sales serialize as null rather than zero. The dashboard can display it
with `st.plotly_chart(gender_figure)` and show transaction counts in a table.
This branch does not implement a Streamlit dashboard or age-group analysis.

Run `python -m unittest discover -s tests -v` to include the gender unit tests
and the real 2024–2025 CSV integration check. The latter independently checks
both gender amounts and counts, including district/industry/year filtering.
