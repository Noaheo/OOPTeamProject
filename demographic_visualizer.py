import plotly.graph_objects as go


class DemographicVisualizer:
    """Plot prepared demographic results without calculating sales totals."""

    def plot_gender(self, data):
        """Return a gender sales bar chart from gender_sales() output."""
        sales = data["total_sales"].astype(object).where(data["total_sales"].notna(), None)
        figure = go.Figure(go.Bar(
            x=data["gender"].tolist(),
            y=sales.tolist(),
            name="Sales",
            hovertemplate="Gender: %{x}<br>Sales: %{y:,.0f} KRW<extra></extra>",
        ))
        figure.update_layout(
            title="Sales by Gender",
            xaxis_title="Gender",
            yaxis_title="Sales (KRW)",
            xaxis_type="category",
            yaxis_tickformat=",.0f",
            template="plotly_white",
        )
        return figure
