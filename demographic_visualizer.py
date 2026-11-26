import pandas as pd
import plotly.graph_objects as go


class DemographicVisualizer:
    """Plot prepared demographic results without calculating sales totals."""

    _DEFAULT_PALETTE = ["#3B5BDB", "#F06595", "#12B886", "#F59F00", "#7950F2", "#228BE6"]

    def __init__(self, template="plotly_white", color_palette=None):
        self._template = template
        self._color_palette = list(color_palette) if color_palette else list(self._DEFAULT_PALETTE)

    @staticmethod
    def _clean(series):
        return series.astype(object).where(series.notna(), None).tolist()

    def plot_gender(self, data):
        """Return a gender sales bar chart from gender_sales() output."""
        sales = self._clean(data["total_sales"])
        figure = go.Figure(go.Bar(
            x=data["gender"].tolist(),
            y=sales,
            name="Sales",
            marker_color=self._color_palette[0],
            hovertemplate="Gender: %{x}<br>Sales: %{y:,.0f} KRW<extra></extra>",
        ))
        figure.update_layout(
            title="Sales by Gender",
            xaxis_title="Gender",
            yaxis_title="Sales (KRW)",
            xaxis_type="category",
            yaxis_exponentformat="B",
            template=self._template,
        )
        return figure

    def plot_age_groups(self, data):
        """Return an age-group sales bar chart, highlighting the top group."""
        sales = self._clean(data["total_sales"])
        valid_sales = [v for v in sales if v is not None]
        max_val = max(valid_sales) if valid_sales else None
        highlight = self._color_palette[0]
        colors = [
            highlight if (max_val is not None and max_val > 0 and v == max_val) else "#91A7FF"
            for v in sales
        ]
        tx = self._clean(data["total_transactions"]) if "total_transactions" in data.columns else [None] * len(data)
        shares = (
            ["N/A" if pd.isna(v) else f"{float(v):.1f}%" for v in data["sales_share"]]
            if "sales_share" in data.columns
            else ["N/A"] * len(data)
        )
        customdata = [[t if t is not None else 0, s] for t, s in zip(tx, shares)]

        figure = go.Figure(go.Bar(
            x=data["age_group"].tolist(),
            y=sales,
            marker_color=colors,
            customdata=customdata,
            name="Sales",
            hovertemplate=(
                "Age group: %{x}<br>Sales: %{y:,.0f} KRW"
                "<br>Transactions: %{customdata[0]:,.0f}"
                "<br>Share: %{customdata[1]}<extra></extra>"
            ),
        ))
        figure.update_layout(
            title="Sales by Age Group",
            xaxis_title="Age Group",
            yaxis_title="Sales (KRW)",
            xaxis_type="category",
            yaxis_exponentformat="B",
            template=self._template,
        )
        return figure

    def plot_gender_share(self, data):
        """Return a donut chart showing gender sales share."""
        figure = go.Figure()
        valid = data[data["total_sales"].notna()] if not data.empty else data
        total_valid = sum(int(v) for v in valid["total_sales"]) if not valid.empty else 0

        if valid.empty or total_valid <= 0:
            figure.update_layout(
                title="Gender Sales Share",
                template=self._template,
            )
            figure.add_annotation(
                text="No gender share data available",
                showarrow=False,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
            )
            return figure

        colors = [self._color_palette[i % len(self._color_palette)] for i in range(len(valid))]
        figure.add_trace(go.Pie(
            labels=valid["gender"].tolist(),
            values=[int(v) for v in valid["total_sales"]],
            hole=0.52,
            marker=dict(colors=colors),
            textinfo="label+percent",
            hovertemplate="Gender: %{label}<br>Sales: %{value:,.0f} KRW<br>Share: %{percent}<extra></extra>",
        ))
        figure.update_layout(
            title="Gender Sales Share",
            template=self._template,
            showlegend=True,
        )
        return figure
