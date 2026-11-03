# Builds the Streamlit user interface and coordinates the other objects (proposal: DashboardManager).
# It does not calculate or draw anything itself: it calls methods on the objects it receives.
#
# Layout: one screen. Title and filter bar at the top, then the four sections of the proposal
# one after another: Overview (key figures), Sales Analysis, Demographic Analysis, District Comparison.
#
# Calling convention (matches SalesAnalyzer and DemographicAnalyzer on dev):
#   - An analyzer class is created with the DataFrame returned by SalesDataManager.filter_data():
#       SalesAnalyzer(filtered_data).sales_summary()
#     so DashboardManager receives the analyzer CLASSES and creates one per selection.
#     Extra inputs (e.g. the districts to compare) are passed to the method.
#   - Visualizers are created once; their methods take the analysis result and return a Plotly Figure.
#   - Every feature has a fixed slot (a Panel). A slot whose object or method is not connected yet
#     shows a "Coming soon" placeholder, and the rest of the dashboard keeps working.
#   - To add a feature, register a new Panel in PANELS and place it in one of the render_* methods
#     (Open-Closed Principle: existing panels do not change).

from dataclasses import dataclass
from html import escape

import pandas as pd
import streamlit as st

from ui_text import district_name, industry_name


ALL = "__all__"
SECTIONS = {
    "sales": ("ti-chart-line", "Sales Analysis", "How sales change over time, by day and by hour"),
    "demographic": ("ti-users", "Demographic Analysis", "Who the customers are, by gender and age"),
    "comparison": ("ti-arrows-diff", "District Comparison", "Rank every district and compare the ones you choose"),
}

CLASS_NAMES = {
    "sales_analyzer": "SalesAnalyzer", "sales_visualizer": "SalesVisualizer",
    "demographic_analyzer": "DemographicAnalyzer", "demographic_visualizer": "DemographicVisualizer",
    "district_comparator": "DistrictComparator", "district_visualizer": "DistrictVisualizer",
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
    shape: str = "bar"            # placeholder shape: line / bar / pie / table
    scope: str = ""               # badge when a filter is NOT applied, e.g. "All years"
    scope_help: str = ""


# Only features that have an owner in the proposal's class design. Method names follow the code on dev
# (sales_summary, quarterly_trend, gender_sales, rank_districts) and the proposal for the rest.
# If a teammate uses a different name, change it here only.
PANELS = {
    # Key-figure cards
    "summary": Panel("Total sales · Transactions", "", "sales_analyzer", "sales_summary"),
    "growth": Panel("Change vs. previous period", "", "sales_analyzer", "calculate_growth_rate"),
    "major_group": Panel("Main customer group", "", "demographic_analyzer",
                         "find_major_customer_group"),
    # Sales Analysis
    "trend": Panel("Quarterly sales trend", "Total sales in every quarter of the data",
                   "sales_analyzer", "quarterly_trend", "sales_visualizer", "plot_trend", "line",
                   "All years", "A trend needs every quarter, so the Year and Quarter filters are not applied."),
    "day_pattern": Panel("Sales by day of week", "Which days bring in the most sales",
                         "sales_analyzer", "analyze_time_pattern", "sales_visualizer",
                         "plot_day_pattern", "bar"),
    "time_pattern": Panel("Sales by time of day", "When during the day sales happen",
                          "sales_analyzer", "analyze_time_pattern", "sales_visualizer",
                          "plot_time_pattern", "bar"),
    # Demographic Analysis
    "gender": Panel("Sales share by gender", "Male vs. female customers",
                    "demographic_analyzer", "gender_sales", "demographic_visualizer",
                    "plot_gender", "pie"),
    "age": Panel("Sales by age group", "From 10s to 60+",
                 "demographic_analyzer", "analyze_age", "demographic_visualizer", "plot_age", "bar"),
    # District Comparison
    "ranking": Panel("District ranking", "By total sales for the selected industry and period",
                     "district_comparator", "rank_districts", "district_visualizer",
                     "plot_ranking", "bar",
                     "All districts", "A ranking compares every district, so the District filter is not applied."),
    "compare": Panel("Sales of chosen districts", "Same industry and period for each district",
                     "district_comparator", "compare_districts", "district_visualizer",
                     "plot_comparison", "bar"),
    "difference": Panel("Difference", "Gap to the highest-selling district",
                        "district_comparator", "calculate_difference", shape="table"),
}

# Panels in each section; a section is shown when at least one of them is ready.
SECTION_PANELS = {
    "sales": ["trend", "day_pattern", "time_pattern"],
    "demographic": ["gender", "age"],
    "comparison": ["ranking", "compare", "difference"],
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
.dash-sec { display: flex; align-items: baseline; gap: .5rem; flex-wrap: wrap; margin: 2rem 0 .7rem;
  padding-top: 1.2rem; border-top: 1px solid #DDE2EC; }
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

    def previous_period(self):
        # The period that the change rate is compared against: previous quarter, or previous year.
        if self.quarter is None:
            return self.year - 1, None
        return (self.year, self.quarter - 1) if self.quarter > 1 else (self.year - 1, 4)


class DashboardManager:
    # Responsible for the user interface and the workflow between objects

    def __init__(self, data_manager,
                 sales_analyzer=None, sales_visualizer=None,
                 demographic_analyzer=None, demographic_visualizer=None,
                 district_comparator=None, district_visualizer=None):
        # Dependency injection from app.py: analyzer classes (created per data selection)
        # and visualizer objects. None = not merged yet.
        self.data_manager = data_manager
        self.sales_analyzer = sales_analyzer
        self.sales_visualizer = sales_visualizer
        self.demographic_analyzer = demographic_analyzer
        self.demographic_visualizer = demographic_visualizer
        self.district_comparator = district_comparator
        self.district_visualizer = district_visualizer
        self._district_names = {}
        self._industry_names = {}
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

        # Only features that a team class already provides are shown; a section with
        # nothing ready yet is left out. New methods appear automatically once merged.
        self.render_overview(filters)
        for key, render in (("sales", self.render_sales_analysis),
                            ("demographic", self.render_demographic_analysis),
                            ("comparison", self.render_comparison)):
            if any(self._ready(panel) for panel in SECTION_PANELS[key]):
                self._section(key)
                render(filters)

    # ------------------------------------------------------------------
    # Filter bar at the top of every page
    # ------------------------------------------------------------------
    def render_filters(self):
        industries = self.data_manager.get_industry_options()
        self._industry_names = {code: industry_name(code, name)
                                for code, name in zip(industries.iloc[:, 0], industries.iloc[:, 1])}
        districts = self.data_manager.get_district_options()
        self._district_names = {code: district_name(name)
                                for code, name in zip(districts.iloc[:, 0], districts.iloc[:, 1])}
        periods = self.data_manager.get_period_options()
        years = sorted(periods["year"].unique().tolist(), reverse=True)

        with self._card():
            ind_col, dist_col, year_col, quarter_col = st.columns([3, 3, 1.3, 1.3])
            industry = ind_col.selectbox(
                "Industry", [ALL] + sorted(self._industry_names, key=self._industry_names.get),
                format_func=lambda code: self._industry_names.get(code, "All industries"),
                key="f_industry")
            district = dist_col.selectbox(
                "District", [ALL] + sorted(self._district_names, key=self._district_names.get),
                format_func=lambda code: self._district_names.get(code, "All districts"),
                key="f_district", help="Type to search, e.g. Gangnam.")
            year = year_col.selectbox("Year", years, key="f_year")
            quarters = sorted(periods.loc[periods["year"] == year, "quarter"].tolist())
            quarter = quarter_col.selectbox(
                "Quarter", [ALL] + quarters, format_func=lambda q: "All" if q == ALL else f"Q{q}",
                key="f_quarter")

        return FilterState(
            district=None if district == ALL else district,
            district_name=self._district_names.get(district, "All districts"),
            industry=None if industry == ALL else industry,
            industry_name=self._industry_names.get(industry, "All industries"),
            year=int(year),
            quarter=None if quarter == ALL else int(quarter),
        )

    # ------------------------------------------------------------------
    # Overview — key figures (total sales, transactions, change vs. previous period, main customers)
    # ------------------------------------------------------------------
    def render_overview(self, filters):
        # Key figures for the current selection
        data = self._period_data(filters)
        if data.empty:
            st.warning("No data for the selected filters. Try changing them.")
            return

        prev_year, prev_quarter = filters.previous_period()
        cards = []   # (panel key, labels, arguments)
        if self._ready("summary"):
            cards.append(("summary", ["Total sales", "Transactions"], (data,)))
        if self._ready("growth"):
            previous = self.data_manager.filter_data(
                district=filters.district, industry=filters.industry,
                year=prev_year, quarter=prev_quarter)
            cards.append(("growth", [f"Change vs. {self._period_text(prev_year, prev_quarter)}"],
                          (data, previous)))
        if self._ready("major_group"):
            cards.append(("major_group", ["Main customer group"], (data,)))
        if not cards:
            return
        columns = iter(st.columns(sum(len(labels) for _, labels, _ in cards)))
        for key, labels, args in cards:
            self._render_kpi(key, *args, labels=labels, columns=[next(columns) for _ in labels])

    # ------------------------------------------------------------------
    # Sales Analysis — quarterly trend, day of week and time of day
    # ------------------------------------------------------------------
    def render_sales_analysis(self, filters):
        trend_data = self._trend_data(filters)
        data = self._period_data(filters)
        self._row([("trend", 1, lambda: self._render_panel("trend", trend_data))])
        self._row([("day_pattern", 1, lambda: self._render_panel("day_pattern", data)),
                   ("time_pattern", 1, lambda: self._render_panel("time_pattern", data))])

    # ------------------------------------------------------------------
    # Demographic Analysis — gender share and age groups
    # ------------------------------------------------------------------
    def render_demographic_analysis(self, filters):
        data = self._period_data(filters)
        self._row([("gender", 2, lambda: self._render_panel("gender", data)),
                   ("age", 3, lambda: self._render_panel("age", data))])

    # ------------------------------------------------------------------
    # District Comparison — ranking (Top/Bottom 5/10) and chosen districts side by side
    # ------------------------------------------------------------------
    def render_comparison(self, filters):
        compare_keys = [k for k in ("compare", "difference") if self._ready(k)]
        parts = []
        if self._ready("ranking"):
            parts.append((2, lambda: self._render_ranking(filters)))
        if compare_keys:
            parts.append((3, lambda: self._render_chosen(filters, compare_keys)))
        columns = st.columns([w for w, _ in parts]) if len(parts) > 1 else [st.container()]
        for column, (_, draw) in zip(columns, parts):
            with column:
                draw()

    def _render_ranking(self, filters):
        with self._card():
            left, right = st.columns(2)
            direction = left.radio("Rank", ["Top", "Bottom"], horizontal=True)
            count = right.radio("Show", [5, 10], horizontal=True)
        # DistrictComparator(data).rank_districts(n, "top" | "bottom")
        self._render_panel("ranking", self._ranking_data(filters), count, direction.lower(),
                           title=f"{direction} {count} districts")

    def _render_chosen(self, filters, keys):
        with self._card():
            st.markdown('<div class="dash-panel-title">Districts to compare</div>'
                        '<div class="dash-panel-desc">Choose 2 to 5. The selected industry and '
                        'period apply to all of them.</div>', unsafe_allow_html=True)
            chosen = self._pick_districts()
        compare_data = self._compare_data(filters, chosen)
        for key in keys:
            self._render_panel(key, compare_data, chosen)

    def _row(self, items):
        # items: (panel key, width, draw function). Ready panels share the row; one fills it alone.
        items = [(width, draw) for key, width, draw in items if self._ready(key)]
        if not items:
            return
        columns = st.columns([w for w, _ in items]) if len(items) > 1 else [st.container()]
        for column, (_, draw) in zip(columns, items):
            with column:
                draw()

    def _pick_districts(self):
        # The chosen districts feed the comparison chart, the difference table and the customer mix.
        chosen = st.multiselect(
            "Districts to compare", sorted(self._district_names, key=self._district_names.get),
            max_selections=5,
            format_func=self._district_names.get, placeholder="Type a district name, e.g. Gangnam",
            key="compare_widget", label_visibility="collapsed")
        return chosen

    # ------------------------------------------------------------------
    # Panel rendering
    # ------------------------------------------------------------------
    def _render_panel(self, key, data, *extra, title=None, transform=None):
        # Draws one card: analysis method -> (optional transform) -> visualizer -> chart.
        panel = PANELS[key]
        with self._card():
            scope = (f'<span class="dash-scope" title="{escape(panel.scope_help)}">'
                     f'{escape(panel.scope)}</span>' if panel.scope else "")
            st.markdown(f'<div class="dash-head"><span class="dash-panel-title">'
                        f'{escape(title or panel.title)}</span>{scope}</div>'
                        f'<div class="dash-panel-desc">{escape(panel.desc)}</div>',
                        unsafe_allow_html=True)

            if not self._has(panel.analyzer, panel.method) or (
                    panel.plot and not self._has(panel.visualizer, panel.plot)):
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
                    st.plotly_chart(self._fit(figure), use_container_width=True,
                                    config={"displayModeBar": False})
                return
            self._show_result(result)

    def _render_kpi(self, key, *args, labels, columns=None):
        # Key-figure cards. Each label gets one column; pending cards keep the same size.
        panel = PANELS[key]
        columns = columns or ([st.container()] if len(labels) == 1 else st.columns(len(labels)))
        ready = self._has(panel.analyzer, panel.method)
        result = self._analyze(panel, *args) if ready else None
        if not ready or result is None:
            values = [("—", "Coming soon", True)] * len(labels)
        elif isinstance(result, dict):
            # Use our labels when the sizes match (e.g. total_sales -> "Total sales")
            if len(result) != len(labels):
                labels = [str(k).replace("_", " ").capitalize() for k in result][:len(columns)]
            values = [(self._format(v), "", False) for v in list(result.values())[:len(columns)]]
        else:
            values = [(self._format(result), "", False)]
        for col, label, (value, sub, empty) in zip(columns, labels, values):
            col.markdown(
                f'<div class="dash-kpi"><div class="dash-kpi-label">{escape(label)}</div>'
                f'<div class="dash-kpi-value{" empty" if empty else ""}">{escape(value)}</div>'
                f'<div class="dash-kpi-sub">{escape(sub) or "&nbsp;"}</div></div>',
                unsafe_allow_html=True)

    def _placeholder(self, panel, hint=None):
        # Grey outline of the future chart.
        status = (f'<span class="dash-owner">{escape(hint)}</span>' if hint
                  else '<span class="dash-soon">Coming soon</span>')
        st.markdown(
            f'<div class="dash-skeleton"><svg viewBox="0 0 320 125" preserveAspectRatio="none">'
            f'{SKELETONS.get(panel.shape, SKELETONS["bar"])}</svg></div>'
            f'<div class="dash-pending-row">{status}</div>',
            unsafe_allow_html=True)

    def _render_header(self):
        # Title, plus data period and size from SalesDataManager's validation report.
        report = self.data_manager.validation_report()
        periods = report.get("available_periods", [])
        span = (f"{periods[0][:4]} Q{periods[0][4]} – {periods[-1][:4]} Q{periods[-1][4]}"
                if periods else "-")
        st.markdown(
            '<div class="dash-title">Seoul Commercial District Sales Analysis Dashboard</div>'
            f'<div class="dash-subtitle">Estimated sales, {span} · '
            f'{report.get("district_count", 0):,} districts · {report.get("industry_count", 0):,} industries · '
            'Source: Seoul Commercial District Analysis Service</div>',
            unsafe_allow_html=True)

    def _section(self, key):
        icon, title, desc = SECTIONS[key]
        st.markdown(f'<div class="dash-sec"><i class="ti {icon}"></i><span>{title}</span>'
                    f'<em>{escape(desc)}</em></div>', unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Data and call helpers
    # ------------------------------------------------------------------
    def _period_data(self, filters):
        return self.data_manager.filter_data(
            district=filters.district, industry=filters.industry,
            year=filters.year, quarter=filters.quarter)

    def _trend_data(self, filters):
        # A trend needs every quarter, so year / quarter are not applied.
        return self.data_manager.filter_data(district=filters.district, industry=filters.industry)

    def _ranking_data(self, filters):
        # A ranking compares every district, so the district filter is not applied.
        return self.data_manager.filter_data(
            industry=filters.industry, year=filters.year, quarter=filters.quarter)

    def _compare_data(self, filters, chosen):
        # None until at least two districts are chosen.
        if len(chosen) < 2:
            return None
        return self.data_manager.filter_data(
            district=list(chosen), industry=filters.industry,
            year=filters.year, quarter=filters.quarter)

    @staticmethod
    def _period_text(year, quarter):
        return f"{year} Q{quarter}" if quarter else str(year)

    @staticmethod
    def _top(ranking, direction, count):
        # Assumes the ranking is sorted by sales, highest first; only the shown rows are kept.
        if not isinstance(ranking, pd.DataFrame):
            return ranking
        return ranking.head(count) if direction == "Top" else ranking.tail(count).iloc[::-1]

    def _has(self, attr, method):
        return getattr(getattr(self, attr), method, None) is not None

    def _ready(self, key):
        # A panel is ready when its analysis method (and chart method, if it has one) exists.
        panel = PANELS[key]
        return self._has(panel.analyzer, panel.method) and (
            panel.plot is None or self._has(panel.visualizer, panel.plot))

    def _analyze(self, panel, data, *extra):
        # Create the analyzer with the selected data, then call the method: SalesAnalyzer(data).sales_summary()
        label = self._label(panel.analyzer, panel.method)
        analyzer = self._safe_call(getattr(self, panel.analyzer), data, label=label)
        if analyzer is None:
            return None
        return self._safe_call(getattr(analyzer, panel.method), *extra, label=label)

    @staticmethod
    def _fit(figure):
        # Same look for every chart in a card: the card already shows the title.
        try:
            figure.update_layout(title=None, margin=dict(l=8, r=8, t=8, b=8),
                                 height=figure.layout.height or 320)
        except Exception:
            pass
        return figure

    @staticmethod
    def _label(attr, method):
        return f"{CLASS_NAMES.get(attr, attr)}.{method}()"

    @staticmethod
    def _safe_call(func, *args, label):
        # Keeps the rest of the page working when a teammate's method raises an error.
        try:
            return func(*args)
        except Exception as error:
            st.error(f"This section could not be loaded ({label}): {error}")
            return None

    @staticmethod
    def _format(value):
        # Short form for large numbers in the cards: 92,659,000,000,000 -> 92.66T
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
    def _show_result(result):
        if isinstance(result, (pd.DataFrame, pd.Series)):
            st.dataframe(result, use_container_width=True, hide_index=True)
        elif isinstance(result, dict):
            st.dataframe(pd.Series(result, name="value"), use_container_width=True)
        else:
            st.write(result)
