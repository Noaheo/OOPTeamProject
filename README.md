# OOPTeamProject
Seoul Commercial District Sales Analysis and Comparison Dashboard

## Project Overview
An interactive object-oriented web dashboard built with Python, pandas, Plotly, and Streamlit to analyze estimated card sales across Seoul's commercial districts (`서울시 상권분석서비스(추정매출-상권)`). Users can filter by industry, district, year, and quarter to inspect key KPIs, multi-year sales trends, weekday/time-slot patterns, gender and age-group demographics, district rankings, multi-district comparisons, and an extensible district map view.

## How to Run

### 1. Install Dependencies
From the repository root:

```sh
python -m pip install -r requirements.txt
```

### 2. Data Placement & Launch Dashboard
On the first launch, `app.py` automatically extracts `data(23~25).zip` into `data/` if `data/` contains no `.csv` files. You can also place the source CSV files directly in `data/` before starting.

```sh
python -m streamlit run app.py
```

On Windows 10/11 x64, you can instead download `run_local.bat` and double-click it. No preinstalled Python or Git is needed. The launcher checks the current `dev` commit, downloads the project and a private Python runtime, installs dependencies, and opens the local dashboard. Internet is required for the first setup and new versions. Each version has a separate cache; if GitHub is unavailable, the last fully prepared version can be used. Keep the launcher window open while using the dashboard; press Ctrl+C to stop it.

### 3. Run Unit & Integration Tests
From the repository root:

```sh
python -m unittest discover -s tests -v
```

## Data Used
- **Primary Dataset**: Seoul Open Data — Commercial District Sales Estimates (`서울시 상권분석서비스(추정매출-상권)`), covering 2023–2025 (`261,157` rows, `1,587` commercial districts, `63` service industries, `55` source columns).
- **Columns Processed**: `7` identifier columns (`기준_년분기_코드`, `상권_구분_코드*`, `상권_코드*`, `서비스_업종_코드*`) and `48` sales amount/transaction count columns (total, weekday/weekend, Mon–Sun, 6 time slots, gender, and age groups 10s–60+), plus derived `year` and `quarter` integer columns.
- **Map Reference**: Bundled official Seoul commercial-area geometry covers all `1,587` archived district codes. Locations and simplified outlines were prepared in WGS84; no API key or coordinate lookup is needed at runtime. See [map data sources and preparation](assets/README.md). These are spatial reference outlines, not quarter-specific historical boundaries.

## Class Design and Object Interactions
The application separates data preparation, domain analysis, Plotly visualization, and UI coordination across dedicated classes:

1. **`SalesDataManager`** (`data_manager.py`): Loads CP949/UTF-8-SIG CSV files, normalizes header aliases, validates 55 required columns and integer metrics (`Int64`), removes exact duplicates, detects conflicting keys, and provides filtered DataFrame copies via `filter_data()`.
2. **`SalesAnalyzer`** (`sales_analyzer.py`): Keeps a snapshot copy and computes `sales_summary()`, `quarterly_trend()`, `year_comparison(year_a, year_b)`, `year_growth_summary(year_a, year_b)`, `weekday_weekend()`, `daily_sales()`, and `time_slot_sales()`.
3. **`SalesVisualizer`** (`sales_visualizer.py`): Generates Plotly `Figure` objects (`plot_trend()`, `plot_years()`, `plot_day_types()`, `plot_days()`, `plot_time_slots()`) using configurable `_template` and `_color_palette` without performing calculations.
4. **`DemographicAnalyzer`** (`demographic_analyzer.py`): Computes `gender_sales()`, `age_group_sales()`, `gender_share()`, `age_group_share()`, and `top_age_group()`.
5. **`DemographicVisualizer`** (`demographic_visualizer.py`): Generates Plotly `Figure` objects (`plot_gender()`, `plot_gender_share()`, `plot_age_groups()`) from prepared demographic tables.
6. **`DistrictComparator`** (`district_comparator.py`): Computes city-wide rankings via `rank_districts(n, order)` and multi-district absolute/percentage gaps against a baseline district via `compare_districts(ids, reference_id)`.
7. **`DistrictVisualizer`** (`district_visualizer.py`): Renders ranking and comparison charts via `plot_ranking()` and `plot_comparison()`.
8. **`DashboardManager`** (`dashboard_manager.py`, launched by `app.py`): Coordinates all injected modules via a `PANELS` registry (Open-Closed Principle), builds the top filter bar, Overview KPIs, and four tabs (`Sales Analysis`, `Demographic Analysis`, `District Comparison`, `District Map`), and handles empty selections and module errors gracefully.
9. **`MapAnalyzer`** (`map_analyzer.py`): Copies the filtered records, sums sales and transaction counts by district code, selects the latest district name, and joins bundled locations. `prepare_map_data()` returns `district_code`, `district_name`, `district_type`, `total_sales`, `total_transactions`, `latitude`, and `longitude`. Unknown totals and unmapped codes are retained.
10. **`MapVisualizer`** (`map_visualizer.py`): `plot_map(data)` returns a Plotly `Figure` from that prepared table. Circle area represents sales on one shared scale; colours distinguish district types. Zero and unknown sales remain separate, and omitted locations are reported.

Year-growth totals use only quarters with known sales in both years; `matched_quarters` lists those quarters. A share is unavailable when any category needed for its denominator is unknown. Charts display missing transaction counts as `N/A` and retain actual zero counts.

### Object Flow
`app.py` (loads/caches `SalesDataManager` and imports team classes) → `DashboardManager.render_filters()` → `SalesDataManager.filter_data()` → Domain Analyzers/Comparator (`SalesAnalyzer`, `DemographicAnalyzer`, `DistrictComparator`) → Domain Visualizers (`SalesVisualizer`, `DemographicVisualizer`, `DistrictVisualizer`) → `DashboardManager` Streamlit tabs, KPIs, charts, and tables.

## Dashboard Features
- **Common Filters & Overview**: Industry, District, Year, and Quarter selectors with KPI cards for Total Sales, Transactions, YoY Growth (shown automatically when the previous year has comparable quarters), and Top Age Group.
- **Sales Analysis Tab**: Quarterly sales trend (`All years` scope), Year-over-Year grouped comparison chart & quarterly table, Weekday vs. Weekend split, Day-of-Week bar chart, and Time-of-Day bar chart.
- **Demographic Analysis Tab**: Gender sales bar chart, Gender share donut chart, Age-group sales bar chart (highlighting the leading group), and formatted breakdown tables with transaction counts and shares (%).
- **District Comparison Tab**: TOP/BOTTOM 5 or 10 district rankings (`All districts` scope) with table, plus Multi-District Comparison (select 2+ districts and a reference baseline district) showing absolute KRW gaps and percentage gaps.
- **District Map Tab**: Interactive Seoul sales bubbles for all districts in the selected industry, year and quarter. The District filter is intentionally excluded, as shown by the `All districts` badge. Drag to pan, scroll to zoom, and hover for district names, codes, sales in KRW and transaction counts. The `Street map` view uses CARTO tiles and needs internet; `Offline outlines` uses bundled geometry without external map requests. No Mapbox token is needed.

### Map Interface

```python
from map_analyzer import MapAnalyzer
from map_visualizer import MapVisualizer

records = manager.filter_data(industry="CS100001", year=2025, quarter=1)
map_data = MapAnalyzer(records).prepare_map_data()
figure = MapVisualizer().plot_map(map_data)
```

`app.py` discovers both map classes automatically. The source sales DataFrame and the prepared map table are preserved. Empty selections return a labeled figure; missing coordinates are reported instead of placing points at guessed locations.
