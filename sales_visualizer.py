import pandas as pd
import plotly.graph_objects as go


class SalesVisualizer:
    """Sales trend, year comparison, and day/time charts."""

    _DEFAULT_PALETTE = ["#3B5BDB", "#12B886", "#F59F00", "#FA5252", "#7950F2", "#228BE6"]

    def __init__(self, template="plotly_white", color_palette=None):
        self._template = template
        self._color_palette = list(color_palette) if color_palette else list(self._DEFAULT_PALETTE)

    @staticmethod
    def _clean(series):
        return series.astype(object).where(series.notna(), None).tolist()

    def _base_bar_figure(self, x_values, y_values, title, x_title, colors, customdata=None, hovertemplate=None):
        figure = go.Figure(go.Bar(
            x=list(x_values),
            y=y_values,
            marker_color=colors,
            customdata=customdata,
            name="Sales",
            hovertemplate=hovertemplate,
        ))
        figure.update_layout(
            title=title,
            xaxis_title=x_title,
            yaxis_title="Sales (KRW)",
            xaxis_type="category",
            yaxis_tickformat=",.0f",
            template=self._template,
        )
        return figure

    def plot_trend(self, data):
        """Plot quarterly sales."""
        periods = data["year"].astype(str) + " Q" + data["quarter"].astype(str)
        sales = self._clean(data["total_sales"])

        figure = go.Figure(go.Scatter(
            x=periods.tolist(),
            y=sales,
            mode="lines+markers",
            name="Sales",
            line=dict(color=self._color_palette[0]),
            connectgaps=False,
            hovertemplate="Period: %{x}<br>Sales: %{y:,.0f} KRW<extra></extra>",
        ))
        figure.update_layout(
            title="Quarterly Sales Trend",
            xaxis_title="Period",
            yaxis_title="Sales (KRW)",
            xaxis_type="category",
            yaxis_tickformat=",.0f",
            template=self._template,
        )
        return figure

    def plot_years(self, data):
        """Plot grouped bar chart comparing matching quarters between two years."""
        figure = go.Figure()
        if data.empty:
            figure.update_layout(
                title="Year-over-Year Sales Comparison",
                xaxis_title="Quarter",
                yaxis_title="Sales (KRW)",
                xaxis_type="category",
                yaxis_tickformat=",.0f",
                template=self._template,
            )
            figure.add_annotation(
                text="No comparable periods available",
                showarrow=False,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
            )
            return figure

        quarters = ("Q" + data["quarter"].astype(str)).tolist()
        year_a = int(data["year_a"].iloc[0])
        year_b = int(data["year_b"].iloc[0])
        color_a = self._color_palette[0]
        color_b = self._color_palette[1 % len(self._color_palette)]

        growth_labels = [
            "N/A" if pd.isna(value) else f"{float(value):+.2f}%"
            for value in data["growth_rate"]
        ]

        figure.add_trace(go.Bar(
            x=quarters,
            y=self._clean(data["sales_a"]),
            name=str(year_a),
            marker_color=color_a,
            hovertemplate=f"{year_a} %{{x}}<br>Sales: %{{y:,.0f}} KRW<extra></extra>",
        ))
        figure.add_trace(go.Bar(
            x=quarters,
            y=self._clean(data["sales_b"]),
            name=str(year_b),
            marker_color=color_b,
            customdata=growth_labels,
            hovertemplate=f"{year_b} %{{x}}<br>Sales: %{{y:,.0f}} KRW<br>YoY Growth: %{{customdata}}<extra></extra>",
        ))
        figure.update_layout(
            title=f"Year-over-Year Comparison ({year_a} vs. {year_b})",
            xaxis_title="Quarter",
            yaxis_title="Sales (KRW)",
            barmode="group",
            xaxis_type="category",
            yaxis_tickformat=",.0f",
            template=self._template,
        )
        return figure

    def plot_day_types(self, data):
        """Plot Weekday vs. Weekend sales bar chart."""
        tx = self._clean(data["total_transactions"]) if "total_transactions" in data.columns else [None] * len(data)
        shares = (
            ["N/A" if pd.isna(v) else f"{float(v):.1f}%" for v in data["sales_share"]]
            if "sales_share" in data.columns
            else ["N/A"] * len(data)
        )
        customdata = [[t if t is not None else 0, s] for t, s in zip(tx, shares)]
        colors = [self._color_palette[i % len(self._color_palette)] for i in range(len(data))]
        return self._base_bar_figure(
            x_values=data["day_type"].tolist(),
            y_values=self._clean(data["total_sales"]),
            title="Weekday vs. Weekend Sales",
            x_title="Day Type",
            colors=colors,
            customdata=customdata,
            hovertemplate=(
                "Type: %{x}<br>Sales: %{y:,.0f} KRW"
                "<br>Transactions: %{customdata[0]:,.0f}"
                "<br>Share: %{customdata[1]}<extra></extra>"
            ),
        )

    def plot_days(self, data):
        """Plot sales by day of week (Mon-Sun), highlighting weekends."""
        weekend_color = self._color_palette[1 % len(self._color_palette)]
        weekday_color = self._color_palette[0]
        colors = [weekend_color if day in ("Sat", "Sun") else weekday_color for day in data["day"]]
        tx = self._clean(data["total_transactions"]) if "total_transactions" in data.columns else [0] * len(data)
        return self._base_bar_figure(
            x_values=data["day"].tolist(),
            y_values=self._clean(data["total_sales"]),
            title="Sales by Day of Week",
            x_title="Day",
            colors=colors,
            customdata=[t if t is not None else 0 for t in tx],
            hovertemplate="Day: %{x}<br>Sales: %{y:,.0f} KRW<br>Transactions: %{customdata:,.0f}<extra></extra>",
        )

    def plot_time_slots(self, data):
        """Plot sales by time slot."""
        tx = self._clean(data["total_transactions"]) if "total_transactions" in data.columns else [0] * len(data)
        return self._base_bar_figure(
            x_values=data["time_slot"].tolist(),
            y_values=self._clean(data["total_sales"]),
            title="Sales by Time of Day",
            x_title="Time Slot",
            colors=self._color_palette[0],
            customdata=[t if t is not None else 0 for t in tx],
            hovertemplate="Time: %{x}<br>Sales: %{y:,.0f} KRW<br>Transactions: %{customdata:,.0f}<extra></extra>",
        )
