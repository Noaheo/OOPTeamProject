# Builds the Streamlit user interface and coordinates the other objects (proposal: DashboardManager).
# It does not calculate or draw anything itself: it calls methods on the objects it receives.
#
# Layout: common top filter bar + Overview KPI row + 4 tabs matching the proposal
# (Sales Analysis, Demographic Analysis, District Comparison, District Map).
#
# Calling convention:
#   - An analyzer class is created with the DataFrame returned by SalesDataManager.filter_data():
#       SalesAnalyzer(filtered_data).sales_summary()
#     so DashboardManager receives the analyzer CLASSES and creates one per selection.
#   - Visualizers are created once; their methods take the analysis result and return a Plotly Figure.
#   - Every feature is registered in PANELS (Open-Closed Principle). An optional teammate module
#     (such as MapVisualizer) activates automatically as soon as it is added.

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st

from ui_text import district_name, industry_name


ALL = "__all__"
SECTIONS = {
    "sales": ("ti-chart-line", "Sales Analysis", "Quarterly trends, year-over-year comparison, and day/time patterns"),
    "demographic": ("ti-users", "Demographic Analysis", "Estimated sales, transaction counts, and shares by gender and age"),
    "comparison": ("ti-arrows-diff", "District Comparison", "Rank commercial districts and compare multiple districts side by side"),
    "map": ("ti-map-pin", "District Map", "Geographic overview of commercial districts and sales scale"),
}

CLASS_NAMES = {
    "sales_analyzer": "SalesAnalyzer", "sales_visualizer": "SalesVisualizer",
    "demographic_analyzer": "DemographicAnalyzer", "demographic_visualizer": "DemographicVisualizer",
    "district_comparator": "DistrictComparator", "district_visualizer": "DistrictVisualizer",
    "map_analyzer": "MapAnalyzer", "map_visualizer": "MapVisualizer",
}


@dataclass(frozen=True)
class Panel:
    # One slot on the dashboard: which analysis method fills it and which visualizer draws it.
    title: str
    desc: str                     # plain-language description shown under the title
    analyzer: str                 # attribute name of the analysis object
    method: str
    visualizer: str | None = None
    plot: str | None = None
    shape: str = "bar"            # placeholder shape: line / bar / pie / table / map
    scope: str = ""               # badge when a filter is NOT applied, e.g. "All years"
    scope_help: str = ""


PANELS = {
    # Overview KPI cards
    "summary": Panel("Total sales · Transactions", "", "sales_analyzer", "sales_summary"),
    "yoy_growth": Panel("YoY growth", "", "sales_analyzer", "year_growth_summary"),
    "major_group": Panel("Top age group", "", "demographic_analyzer", "top_age_group"),
    # Sales Analysis
    "trend": Panel(
        "Quarterly sales trend", "Total sales in every quarter of the data",
        "sales_analyzer", "quarterly_trend", "sales_visualizer", "plot_trend", "line",
        "All years", "A trend needs every quarter, so the Year and Quarter filters are not applied.",
    ),
    "year_comparison": Panel(
        "Year-over-Year comparison", "Matching quarters across two selected years",
        "sales_analyzer", "year_comparison", "sales_visualizer", "plot_years", "bar",
        "All quarters", "Compares matching quarters across two chosen years.",
    ),
    "day_types": Panel(
        "Weekday vs. Weekend", "Sales split between weekdays and weekends",
        "sales_analyzer", "weekday_weekend", "sales_visualizer", "plot_day_types", "bar",
    ),
    "day_pattern": Panel(
        "Sales by day of week", "Which days bring in the most sales",
        "sales_analyzer", "daily_sales", "sales_visualizer", "plot_days", "bar",
    ),
    "time_pattern": Panel(
        "Sales by time of day", "When during the day sales happen",
        "sales_analyzer", "time_slot_sales", "sales_visualizer", "plot_time_slots", "bar",
    ),
    # Demographic Analysis
    "gender": Panel(
        "Sales by gender", "Estimated sales for male and female customers",
        "demographic_analyzer", "gender_sales", "demographic_visualizer", "plot_gender", "bar",
    ),
    "gender_share": Panel(
        "Gender sales share", "Share of recorded male and female sales",
        "demographic_analyzer", "gender_share", "demographic_visualizer", "plot_gender_share", "pie",
    ),
    "age": Panel(
        "Sales by age group", "Estimated sales, transaction counts, and shares from 10s to 60+",
        "demographic_analyzer", "age_group_share", "demographic_visualizer", "plot_age_groups", "bar",
    ),
    # District Comparison
    "ranking": Panel(
        "District ranking", "By total sales for the selected industry and period",
        "district_comparator", "rank_districts", "district_visualizer", "plot_ranking", "bar",
        "All districts", "A ranking compares every district, so the District filter is not applied.",
    ),
    "district_compare": Panel(
        "Multi-district comparison", "Compare 2+ districts against a baseline district",
        "district_comparator", "compare_districts", "district_visualizer", "plot_comparison", "bar",
        "Selected districts", "Compares chosen districts for the same industry and period.",
    ),
    # District Map (teammate OCP plugin slot)
    "district_map": Panel(
        "Commercial district map", "Spatial distribution and sales scale across Seoul commercial districts",
        "map_analyzer", "prepare_map_data", "map_visualizer", "plot_map", "map",
        "All districts", "A city-wide map compares every district, so the District filter is not applied.",
    ),
}

SKELETONS = {
    "line": '<polyline points="0,95 45,70 90,80 135,48 180,60 225,30 270,42 320,18" fill="none" '
            'stroke="#D5DBE7" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
    "bar": "".join(f'<rect x="{12 + i * 44}" y="{120 - h}" width="28" height="{h}" rx="4" fill="#E3E8F1"/>'
                   for i, h in enumerate([70, 95, 55, 105, 80, 40, 88])),
    "pie": '<circle cx="160" cy="62" r="46" fill="none" stroke="#E3E8F1" stroke-width="22"/>'
           '<circle cx="160" cy="62" r="46" fill="none" stroke="#D0D8E6" stroke-width="22" '
           'stroke-dasharray="120 300" transform="rotate(-90 160 62)"/>',
    "table": "".join(f'<rect x="0" y="{8 + i * 26}" width="{w}" height="12" rx="6" fill="#E3E8F1"/>'
                     for i, w in enumerate([300, 240, 280, 200])),
    "map": '<rect x="10" y="10" width="300" height="105" rx="10" fill="#F1F4FA" stroke="#DCE3F0" stroke-width="2"/>'
           '<path d="M30,75 Q95,45 155,62 T290,48" fill="none" stroke="#D0DAE9" stroke-width="5" stroke-linecap="round"/>'
           '<circle cx="95" cy="52" r="10" fill="#CBD5E8"/><circle cx="165" cy="68" r="14" fill="#B8C7E3"/>'
           '<circle cx="235" cy="44" r="8" fill="#CBD5E8"/>',
}

STYLE = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
@import url('https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css');
:root {
  --dash-accent: #3B5BDB; --dash-ink: #1F2937; --dash-muted: #6B7280;
  --dash-canvas: #F4F6FA; --dash-navy: #1E2A4A; --dash-line: #E6E9F0;
}
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input,
.stApp button p, .stApp [data-baseweb="select"] div {
  font-family: "Pretendard", -apple-system, "Segoe UI", sans-serif;
}

/* Canvas and white cards */
.stApp, [data-testid="stHeader"] { background: var(--dash-canvas); }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 3.2rem; max-width: 1280px; }
[class*="st-key-card-"] { background: #FFFFFF; border: none !important; border-radius: 14px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, .06); padding: 1rem 1.1rem; }

[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }

/* Page title and filter bar */
.dash-title { font-size: 1.6rem; font-weight: 700; color: var(--dash-ink); margin: 0; }
.dash-sec { display: flex; align-items: baseline; gap: .5rem; flex-wrap: wrap; margin: .8rem 0 .7rem; }
.dash-sec i { color: var(--dash-accent); font-size: 1.2rem; align-self: center; }
.dash-sec span { font-size: 1.2rem; font-weight: 700; color: var(--dash-ink); }
.dash-sec em { font-style: normal; font-size: .85rem; color: var(--dash-muted); }
.dash-subtitle { font-size: .88rem; color: var(--dash-muted); margin: .15rem 0 .9rem; }

/* Cards */
.dash-head { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.dash-panel-title { font-size: 1rem; font-weight: 700; color: var(--dash-ink); }
.dash-panel-desc { font-size: .8rem; color: var(--dash-muted); margin: .1rem 0 .4rem; }
.dash-scope { font-size: .7rem; font-weight: 600; color: #495057; background: #F1F3F5;
  border-radius: 999px; padding: .1rem .55rem; cursor: help; }

.dash-kpi { background: #FFFFFF; border-radius: 14px; padding: 1rem 1.2rem; height: 100%;
  box-shadow: 0 1px 2px rgba(16, 24, 40, .05); }
.dash-kpi-label { font-size: .8rem; font-weight: 600; color: var(--dash-muted); }
.dash-kpi-value { font-size: 1.65rem; font-weight: 700; color: var(--dash-ink); line-height: 1.45;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dash-kpi-value.empty { color: #CBD2DF; }
.dash-kpi-sub { font-size: .75rem; color: var(--dash-muted); }

.dash-skeleton svg { width: 100%; height: 150px; display: block; margin: .4rem 0 .6rem; }
.dash-pending-row { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.dash-soon { font-size: .75rem; font-weight: 600; color: #6B7280; background: #F1F3F5;
  border-radius: 999px; padding: .15rem .6rem; }
.dash-owner { font-size: .78rem; color: var(--dash-muted); }
.dash-note { font-size: .78rem; color: #B35C00; margin: .2rem 0 .4rem; }
</style>
"""


@dataclass(frozen=True)
class FilterState:
    # Conditions selected in the filter bar. None means "all".
    district: str | None
    district_name: str
    industry: str | None
    industry_name: str
    year: int
    quarter: int | None

    def period_label(self):
        return f"{self.year} " + (f"Q{self.quarter}" if self.quarter else "(all quarters)")


class DashboardManager:
    # Responsible for the user interface and the workflow between objects

    def __init__(
        self,
        data_manager,
        sales_analyzer=None,
        sales_visualizer=None,
        demographic_analyzer=None,
        demographic_visualizer=None,
        district_comparator=None,
        district_visualizer=None,
        map_analyzer=None,
        map_visualizer=None,
    ):
        # Dependency injection from app.py: analyzer classes (created per data selection)
        # and visualizer objects. None = not merged yet.
        self.data_manager = data_manager
        self.sales_analyzer = sales_analyzer
        self.sales_visualizer = sales_visualizer
        self.demographic_analyzer = demographic_analyzer
        self.demographic_visualizer = demographic_visualizer
        self.district_comparator = district_comparator
        self.district_visualizer = district_visualizer
        self.map_analyzer = map_analyzer
        self.map_visualizer = map_visualizer
        self._district_names = {}
        self._industry_names = {}
        self._available_years = []
        self._filter_state = None
        self._cards = 0

    def _card(self):
        # White card (a bordered container with a unique key so the CSS above can style it).
        self._cards += 1
        return st.container(border=True, key=f"card-{self._cards}")

    # ------------------------------------------------------------------
    # Whole page
    # ------------------------------------------------------------------
    def run(self):
        st.markdown(STYLE, unsafe_allow_html=True)
        self._render_header()
        filters = self.render_filters()
        self._filter_state = filters
        self.render_overview(filters)

        tab_sales, tab_demo, tab_comp, tab_map = st.tabs([
            "Sales Analysis",
            "Demographic Analysis",
            "District Comparison",
            "District Map",
        ])
        with tab_sales:
            self._section("sales")
            self.render_sales_analysis(filters)
        with tab_demo:
            self._section("demographic")
            self.render_demographics(filters)
        with tab_comp:
            self._section("comparison")
            self.render_comparison(filters)
        with tab_map:
            self._section("map")
            self.render_map(filters)

    # ------------------------------------------------------------------
    # Filter bar at the top of every page
    # ------------------------------------------------------------------
    def render_filters(self):
        industries = self.data_manager.get_industry_options()
        self._industry_names = {
            code: industry_name(code, name)
            for code, name in zip(industries.iloc[:, 0], industries.iloc[:, 1])
        }
        districts = self.data_manager.get_district_options()
        self._district_names = {
            code: district_name(name)
            for code, name in zip(districts.iloc[:, 0], districts.iloc[:, 1])
        }
        periods = self.data_manager.get_period_options()
        years = sorted(periods["year"].unique().tolist(), reverse=True)
        self._available_years = [int(y) for y in years]

        with self._card():
            ind_col, dist_col, year_col, quarter_col = st.columns([3, 3, 1.3, 1.3])
            industry = ind_col.selectbox(
                "Industry",
                [ALL] + sorted(self._industry_names, key=self._industry_names.get),
                format_func=lambda code: self._industry_names.get(code, "All industries"),
                key="f_industry",
            )
            district = dist_col.selectbox(
                "District",
                [ALL] + sorted(self._district_names, key=self._district_names.get),
                format_func=lambda code: self._district_names.get(code, "All districts"),
                key="f_district",
                help="Type to search, e.g. Gangnam.",
            )
            year = year_col.selectbox("Year", years, key="f_year")
            quarters = sorted(periods.loc[periods["year"] == year, "quarter"].tolist())
            quarter = quarter_col.selectbox(
                "Quarter",
                [ALL] + quarters,
                format_func=lambda q: "All" if q == ALL else f"Q{q}",
                key="f_quarter",
            )

        return FilterState(
            district=None if district == ALL else district,
            district_name=self._district_names.get(district, "All districts"),
            industry=None if industry == ALL else industry,
            industry_name=self._industry_names.get(industry, "All industries"),
            year=int(year),
            quarter=None if quarter == ALL else int(quarter),
        )

    # ------------------------------------------------------------------
    # Overview — key figures (total sales, transactions, YoY growth, top age group)
    # ------------------------------------------------------------------
    def render_overview(self, filters):
        data = self._period_data(filters)
        if data.empty:
            st.warning("No data for the selected filters. Try changing them.")
            return

        kpi_items = []  # (label, value, sub, empty)
        if self._ready("summary"):
            summary = self._analyze(PANELS["summary"], data)
            if isinstance(summary, dict):
                kpi_items.append((
                    "Total sales",
                    self._format(summary.get("total_sales")),
                    filters.period_label(),
                    summary.get("total_sales") is None,
                ))
                kpi_items.append((
                    "Transactions",
                    self._format(summary.get("total_transactions")),
                    filters.period_label(),
                    summary.get("total_transactions") is None,
                ))

        prev_year = filters.year - 1
        if prev_year in self._available_years and self._ready("yoy_growth"):
            yoy_data = self.data_manager.filter_data(
                district=filters.district,
                industry=filters.industry,
                year=[prev_year, filters.year],
                quarter=filters.quarter,
            )
            yoy_result = self._analyze(PANELS["yoy_growth"], yoy_data, prev_year, filters.year)
            if isinstance(yoy_result, dict) and yoy_result.get("growth_rate") is not None:
                mq = yoy_result.get("matched_quarters", [])
                if filters.quarter:
                    sub = f"vs. {prev_year} Q{filters.quarter}"
                elif mq == [1, 2, 3, 4]:
                    sub = f"vs. {prev_year} (Q1-Q4)"
                else:
                    sub = f"vs. {prev_year} (" + ", ".join(f"Q{q}" for q in mq) + ")"
                kpi_items.append((
                    "YoY growth",
                    f"{yoy_result['growth_rate']:+.2f}%",
                    sub,
                    False,
                ))

        if self._ready("major_group"):
            top_age = self._analyze(PANELS["major_group"], data)
            if isinstance(top_age, dict) and top_age.get("age_group"):
                share = top_age.get("sales_share")
                sub = f"{share:.1f}% of age sales" if share is not None and not pd.isna(share) else ""
                kpi_items.append(("Top age group", str(top_age["age_group"]), sub, False))
            else:
                kpi_items.append(("Top age group", "No data", "No age sales recorded", True))

        if not kpi_items:
            return

        columns = st.columns(len(kpi_items))
        for col, (label, value, sub, empty) in zip(columns, kpi_items):
            col.markdown(
                f'<div class="dash-kpi"><div class="dash-kpi-label">{escape(label)}</div>'
                f'<div class="dash-kpi-value{" empty" if empty else ""}">{escape(value)}</div>'
                f'<div class="dash-kpi-sub">{escape(sub) or "&nbsp;"}</div></div>',
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------
    # Sales Analysis — quarterly trend, YoY comparison, day type, weekday, time slot
    # ------------------------------------------------------------------
    def render_sales_analysis(self, filters):
        trend_data = self._trend_data(filters)
        data = self._period_data(filters)
        self._row([("trend", 1, lambda: self._render_panel("trend", trend_data))])
        self._row([
            ("year_comparison", 3, lambda: self._render_year_comparison_card(filters)),
            ("day_types", 2, lambda: self._render_panel("day_types", data)),
        ])
        self._row([
            ("day_pattern", 1, lambda: self._render_panel("day_pattern", data)),
            ("time_pattern", 1, lambda: self._render_panel("time_pattern", data)),
        ])

    def _render_year_comparison_card(self, filters):
        panel = PANELS["year_comparison"]
        with self._card():
            self._card_header(panel)
            if not self._ready("year_comparison"):
                self._placeholder(panel)
                return

            years = self._available_years or sorted(
                self.data_manager.get_period_options()["year"].unique().tolist(), reverse=True
            )
            if len(years) < 2:
                st.info("At least two years of data are needed for year-over-year comparison.")
                return

            default_b = filters.year if filters.year in years else years[0]
            default_a = (
                default_b - 1
                if (default_b - 1) in years
                else next(y for y in years if y != default_b)
            )
            col_a, col_b = st.columns(2)
            year_a = col_a.selectbox(
                "Base year", years, index=years.index(default_a), key="yoy_year_a"
            )
            year_b = col_b.selectbox(
                "Compare year", years, index=years.index(default_b), key="yoy_year_b"
            )
            if year_a == year_b:
                st.info("Select two different years to compare.")
                return

            yoy_data = self.data_manager.filter_data(
                district=filters.district,
                industry=filters.industry,
                year=[int(year_a), int(year_b)],
            )
            result = self._analyze(panel, yoy_data, int(year_a), int(year_b))
            if result is None:
                return

            plot = getattr(self.sales_visualizer, panel.plot)
            figure = self._safe_call(plot, result, label=self._label(panel.visualizer, panel.plot))
            if figure is not None:
                st.plotly_chart(self._fit(figure), width="stretch", config={"displayModeBar": False})

            if not result.empty:
                display = pd.DataFrame({
                    "Quarter": ["Q" + str(q) for q in result["quarter"]],
                    f"{year_a} Sales (KRW)": [self._format_int(v) for v in result["sales_a"]],
                    f"{year_b} Sales (KRW)": [self._format_int(v) for v in result["sales_b"]],
                    "Difference (KRW)": [self._format_signed_int(v) for v in result["difference"]],
                    "Growth (%)": [self._format_pct(v, signed=True) for v in result["growth_rate"]],
                })
                st.dataframe(display, width="stretch", hide_index=True)

    # ------------------------------------------------------------------
    # Demographic Analysis — gender sales/share, age-group sales/share
    # ------------------------------------------------------------------
    def render_demographics(self, filters):
        data = self._period_data(filters)
        if data.empty:
            st.info("No demographic data for the selected filters.")
            return

        self._row([
            ("gender", 3, lambda: self._render_panel("gender", data)),
            ("gender_share", 2, lambda: self._render_panel("gender_share", data)),
        ])

        if self._has("demographic_analyzer", "gender_share"):
            gender_tbl = self._safe_call(
                lambda: self.demographic_analyzer(data).gender_share(),
                label="DemographicAnalyzer.gender_share()",
            )
            if gender_tbl is not None and not gender_tbl.empty:
                with self._card():
                    st.markdown('<div class="dash-panel-title">Gender sales breakdown</div>', unsafe_allow_html=True)
                    st.dataframe(
                        self._format_demographic_table(gender_tbl, "gender", "Gender"),
                        width="stretch",
                        hide_index=True,
                    )

        if self._ready("age"):
            panel = PANELS["age"]
            with self._card():
                self._card_header(panel)
                age_tbl = self._analyze(panel, data)
                if age_tbl is not None:
                    plot = getattr(self.demographic_visualizer, panel.plot)
                    figure = self._safe_call(plot, age_tbl, label=self._label(panel.visualizer, panel.plot))
                    if figure is not None:
                        st.plotly_chart(self._fit(figure), width="stretch", config={"displayModeBar": False})
                    if not age_tbl.empty:
                        st.dataframe(
                            self._format_demographic_table(age_tbl, "age_group", "Age Group"),
                            width="stretch",
                            hide_index=True,
                        )

    def render_demographic_analysis(self, filters):
        """Backwards-compatible alias for render_demographics."""
        self.render_demographics(filters)

    # ------------------------------------------------------------------
    # District Comparison — rankings (Top/Bottom 5/10) & multi-district comparison
    # ------------------------------------------------------------------
    def render_comparison(self, filters):
        ranking_data = self._ranking_data(filters)
        if self._ready("ranking"):
            self._render_ranking(ranking_data)
        if self._ready("district_compare"):
            self._render_multi_district(filters, ranking_data)

    def _render_ranking(self, ranking_data):
        panel = PANELS["ranking"]
        with self._card():
            left, right = st.columns(2)
            direction = left.radio("Rank", ["Top", "Bottom"], horizontal=True, key="rank_dir")
            count = right.radio("Show", [5, 10], horizontal=True, key="rank_count")

        with self._card():
            self._card_header(panel, title=f"{direction} {count} districts")
            result = self._analyze(panel, ranking_data, count, direction.lower())
            if result is None:
                return
            localized = self._localize_districts(result)
            plot = getattr(self.district_visualizer, panel.plot)
            figure = self._safe_call(plot, localized, label=self._label(panel.visualizer, panel.plot))
            if figure is not None:
                st.plotly_chart(self._fit(figure), width="stretch", config={"displayModeBar": False})
            if not localized.empty:
                table = pd.DataFrame({
                    "Rank": localized["rank"].tolist(),
                    "Code": localized["district_code"].tolist(),
                    "District": localized["district_name"].tolist(),
                    "Estimated Sales (KRW)": [self._format_int(v) for v in localized["total_sales"]],
                })
                st.dataframe(table, width="stretch", hide_index=True)

    def _render_multi_district(self, filters, ranking_data):
        panel = PANELS["district_compare"]
        with self._card():
            self._card_header(panel)
            all_codes = sorted(self._district_names, key=self._district_names.get)
            if len(all_codes) < 2:
                st.info("At least 2 districts are required for comparison.")
                return

            default_ids = []
            if not ranking_data.empty:
                top_df = self._safe_call(
                    lambda: self.district_comparator(ranking_data).rank_districts(3, "top"),
                    label="DistrictComparator.rank_districts()",
                )
                if top_df is not None and not top_df.empty:
                    default_ids = [c for c in top_df["district_code"].tolist() if c in self._district_names]
            if len(default_ids) < 2:
                default_ids = all_codes[:2]

            sel_col, ref_col = st.columns([2, 1])
            selected_ids = sel_col.multiselect(
                "Select 2 or more districts",
                all_codes,
                default=default_ids,
                format_func=lambda c: self._district_names.get(c, c),
                key="comp_districts",
            )
            if len(selected_ids) < 2:
                st.info("Select at least 2 districts to compare.")
                return

            ref_id = ref_col.selectbox(
                "Reference (baseline) district",
                selected_ids,
                format_func=lambda c: self._district_names.get(c, c),
                key="comp_reference",
            )

            comparator = self._safe_call(
                lambda: self.district_comparator(
                    ranking_data,
                    category=filters.industry,
                    period=filters.period_label(),
                    reference_district=ref_id,
                ),
                label="DistrictComparator()",
            )
            if comparator is None:
                return
            comp_result = self._safe_call(
                lambda: comparator.compare_districts(selected_ids, ref_id),
                label="DistrictComparator.compare_districts()",
            )
            if comp_result is None:
                return

            localized = self._localize_districts(comp_result)
            plot = getattr(self.district_visualizer, panel.plot)
            figure = self._safe_call(plot, localized, label=self._label(panel.visualizer, panel.plot))
            if figure is not None:
                st.plotly_chart(self._fit(figure), width="stretch", config={"displayModeBar": False})

            table = pd.DataFrame({
                "Code": localized["district_code"].tolist(),
                "District": localized["district_name"].tolist(),
                "Estimated Sales (KRW)": [self._format_int(v) for v in localized["total_sales"]],
                "Gap vs. Baseline (KRW)": [self._format_signed_int(v) for v in localized["difference"]],
                "Gap (%)": [self._format_pct(v, signed=True) for v in localized["percent_diff"]],
                "Role": ["Baseline" if bool(r) else "Compared" for r in localized["is_reference"]],
            })
            st.dataframe(table, width="stretch", hide_index=True)

    # ------------------------------------------------------------------
    # District Map — OCP plugin slot for teammate's MapVisualizer / MapAnalyzer
    # ------------------------------------------------------------------
    def render_map(self, filters):
        panel = PANELS["district_map"]
        data = self._ranking_data(filters)
        with self._card():
            self._card_header(panel)
            if not self._ready("district_map"):
                self._placeholder(
                    panel,
                    hint="Teammate slot ready: add map_visualizer.py with MapVisualizer.plot_map(data)",
                )
                st.caption(
                    "Integration contract: DashboardManager passes all-district filtered DataFrame "
                    "for the selected industry and period to MapVisualizer.plot_map(data) "
                    "(or MapAnalyzer(data).prepare_map_data() -> MapVisualizer.plot_map())."
                )
                return

            prepared = (
                self._analyze(panel, data)
                if self._has("map_analyzer", "prepare_map_data")
                else data
            )
            if prepared is None:
                return

            figure = self._safe_call(
                self.map_visualizer.plot_map,
                prepared,
                label="MapVisualizer.plot_map()",
            )
            if figure is not None:
                st.plotly_chart(self._fit(figure), width="stretch", config={"displayModeBar": False, "scrollZoom": True})
                st.caption(
                    "Circle area shows estimated sales; colours show district type. Hover for details. "
                    "Street maps need internet; choose Offline outlines to use the bundled boundaries. "
                    "Geographic data: Seoul Metropolitan Government / Seoul Credit Guarantee Foundation."
                )

    # ------------------------------------------------------------------
    # Panel & layout helpers
    # ------------------------------------------------------------------
    def _row(self, items):
        # items: (panel key, width, draw function). Ready panels share the row; one fills it alone.
        items = [(width, draw) for key, width, draw in items if self._ready(key)]
        if not items:
            return
        columns = st.columns([w for w, _ in items]) if len(items) > 1 else [st.container()]
        for column, (_, draw) in zip(columns, items):
            with column:
                draw()

    def _card_header(self, panel, title=None):
        scope = (
            f'<span class="dash-scope" title="{escape(panel.scope_help)}">'
            f'{escape(panel.scope)}</span>'
            if panel.scope
            else ""
        )
        st.markdown(
            f'<div class="dash-head"><span class="dash-panel-title">'
            f'{escape(title or panel.title)}</span>{scope}</div>'
            f'<div class="dash-panel-desc">{escape(panel.desc)}</div>',
            unsafe_allow_html=True,
        )

    def _render_panel(self, key, data, *extra, title=None, transform=None):
        # Draws one card: analysis method -> (optional transform) -> visualizer -> chart.
        panel = PANELS[key]
        with self._card():
            self._card_header(panel, title=title)
            if not self._has(panel.analyzer, panel.method) or (
                panel.plot and not self._has(panel.visualizer, panel.plot)
            ):
                self._placeholder(panel)
                return
            if data is None:
                self._placeholder(panel, hint="Choose at least 2 districts to see this.")
                return
            result = self._analyze(panel, data, *extra)
            if result is None:
                return
            if transform is not None:
                result = transform(result)

            if panel.plot:
                plot = getattr(getattr(self, panel.visualizer), panel.plot)
                figure = self._safe_call(plot, result, label=self._label(panel.visualizer, panel.plot))
                if figure is not None:
                    st.plotly_chart(self._fit(figure), width="stretch", config={"displayModeBar": False})
                return
            self._show_result(result)

    def _placeholder(self, panel, hint=None):
        status = (
            f'<span class="dash-owner">{escape(hint)}</span>'
            if hint
            else '<span class="dash-soon">Coming soon</span>'
        )
        st.markdown(
            f'<div class="dash-skeleton"><svg viewBox="0 0 320 125" preserveAspectRatio="none">'
            f'{SKELETONS.get(panel.shape, SKELETONS["bar"])}</svg></div>'
            f'<div class="dash-pending-row">{status}</div>',
            unsafe_allow_html=True,
        )

    def _render_header(self):
        report = self.data_manager.validation_report()
        periods = report.get("available_periods", [])
        span = (
            f"{periods[0][:4]} Q{periods[0][4]} – {periods[-1][:4]} Q{periods[-1][4]}"
            if periods
            else "-"
        )
        st.markdown(
            '<div class="dash-title">Seoul Commercial District Sales Analysis Dashboard</div>'
            f'<div class="dash-subtitle">Estimated sales, {span} · '
            f'{report.get("district_count", 0):,} districts · {report.get("industry_count", 0):,} industries · '
            'Source: Seoul Commercial District Analysis Service</div>',
            unsafe_allow_html=True,
        )

    def _section(self, key):
        icon, title, desc = SECTIONS[key]
        st.markdown(
            f'<div class="dash-sec"><i class="ti {icon}"></i><span>{title}</span>'
            f'<em>{escape(desc)}</em></div>',
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Data and call helpers
    # ------------------------------------------------------------------
    def _period_data(self, filters):
        return self.data_manager.filter_data(
            district=filters.district,
            industry=filters.industry,
            year=filters.year,
            quarter=filters.quarter,
        )

    def _trend_data(self, filters):
        # A trend needs every quarter, so year / quarter are not applied.
        return self.data_manager.filter_data(district=filters.district, industry=filters.industry)

    def _ranking_data(self, filters):
        # A ranking compares every district, so the district filter is not applied.
        return self.data_manager.filter_data(
            industry=filters.industry, year=filters.year, quarter=filters.quarter
        )

    def _localize_districts(self, df):
        # Apply English romanized district names on a copy for UI display without altering comparator output.
        localized = df.copy()
        if "district_name" in localized.columns and "district_code" in localized.columns:
            localized["district_name"] = [
                self._district_names.get(code)
                or (district_name(str(name)) if pd.notna(name) and str(name).strip() else str(code))
                for code, name in zip(localized["district_code"], localized["district_name"])
            ]
        return localized

    def _format_demographic_table(self, df, label_col, label_title):
        return pd.DataFrame({
            label_title: df[label_col].tolist(),
            "Estimated Sales (KRW)": [self._format_int(v) for v in df["total_sales"]],
            "Transactions": [self._format_int(v) for v in df["total_transactions"]],
            "Sales Share (%)": [self._format_pct(v) for v in df["sales_share"]],
            "Transaction Share (%)": [self._format_pct(v) for v in df["transaction_share"]],
        })

    def _has(self, attr, method):
        return getattr(getattr(self, attr), method, None) is not None

    def _ready(self, key):
        panel = PANELS[key]
        if key == "district_map":
            return self._has("map_visualizer", "plot_map")
        return self._has(panel.analyzer, panel.method) and (
            panel.plot is None or self._has(panel.visualizer, panel.plot)
        )

    def _analyze(self, panel, data, *extra):
        label = self._label(panel.analyzer, panel.method)
        analyzer = self._safe_call(getattr(self, panel.analyzer), data, label=label)
        if analyzer is None:
            return None
        return self._safe_call(getattr(analyzer, panel.method), *extra, label=label)

    @staticmethod
    def _fit(figure):
        try:
            figure.update_layout(
                title=None,
                margin=dict(l=8, r=8, t=16, b=8),
                height=figure.layout.height or 340,
            )
        except Exception:
            pass
        return figure

    @staticmethod
    def _label(attr, method):
        return f"{CLASS_NAMES.get(attr, attr)}.{method}()"

    @staticmethod
    def _safe_call(func, *args, label):
        try:
            return func(*args)
        except Exception as error:
            st.error(f"This section could not be loaded ({label}): {error}")
            return None

    @staticmethod
    def _format(value):
        if value is None or (not isinstance(value, str) and pd.isna(value)):
            return "No data"
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)) or hasattr(value, "__int__"):
            number = float(value)
            for limit, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
                if abs(number) >= limit:
                    return f"{number / limit:,.2f}{unit}"
            return f"{number:,.0f}" if number == int(number) else f"{number:,.2f}"
        return str(value)

    @staticmethod
    def _format_int(value):
        if value is None or pd.isna(value):
            return "N/A"
        return f"{int(value):,}"

    @staticmethod
    def _format_signed_int(value):
        if value is None or pd.isna(value):
            return "N/A"
        return f"{int(value):+,}"

    @staticmethod
    def _format_pct(value, signed=False):
        if value is None or pd.isna(value):
            return "N/A"
        return f"{float(value):+.2f}%" if signed else f"{float(value):.2f}%"

    @staticmethod
    def _show_result(result):
        if isinstance(result, (pd.DataFrame, pd.Series)):
            st.dataframe(result, width="stretch", hide_index=True)
        elif isinstance(result, dict):
            st.dataframe(pd.Series(result, name="value"), width="stretch")
        else:
            st.write(result)
