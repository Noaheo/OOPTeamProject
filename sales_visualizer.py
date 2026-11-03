import plotly.graph_objects as go


class SalesVisualizer:
    """Create Plotly figures from prepared sales analysis results."""

    def plot_trend(self, data):
        """Return a line chart for SalesAnalyzer.quarterly_trend() output."""
        periods = data["year"].astype(str) + " Q" + data["quarter"].astype(str)
        sales = data["total_sales"].astype(object).where(data["total_sales"].notna(), None)

        figure = go.Figure(go.Scatter(
            x=periods.tolist(),
            y=sales.tolist(),
            mode="lines+markers",
            name="Sales",
            connectgaps=False,
            hovertemplate="Period: %{x}<br>Sales: %{y:,.0f} KRW<extra></extra>",
        ))
        figure.update_layout(
            title="Quarterly Sales Trend",
            xaxis_title="Period",
            yaxis_title="Sales (KRW)",
            xaxis_type="category",
            yaxis_tickformat=",.0f",
            template="plotly_white",
        )
        return figure
