"""Plotly charts for commercial-district ranking results."""

import pandas as pd
import plotly.graph_objects as go


class DistrictVisualizer:
    """Visualize district rankings without performing sales calculations."""

    def plot_ranking(self, data: pd.DataFrame) -> go.Figure:
        """Return a Plotly bar chart for DistrictComparator.rank_districts()."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        required = {"rank", "district_code", "district_name", "total_sales"}
        if not required.issubset(data.columns):
            raise ValueError(f"Missing ranking columns: {sorted(required - set(data.columns))}")

        # Distinct codes in customdata allow zones with duplicate names to be identified.
        labels = data["district_name"].fillna(data["district_code"]).astype(str)
        codes = data["district_code"].astype(str)
        figure = go.Figure(go.Bar(
            x=labels.tolist(),
            y=data["total_sales"].tolist(),
            customdata=codes.tolist(),
            name="Estimated sales",
            hovertemplate=("District: %{x}<br>Code: %{customdata}"
                           "<br>Estimated sales: %{y:,.0f} KRW<extra></extra>"),
        ))
        figure.update_layout(
            title="Commercial District Sales Ranking",
            xaxis_title="Commercial district",
            yaxis_title="Estimated sales (KRW)",
            yaxis_tickformat=",.0f",
            xaxis_type="category",
            template="plotly_white",
        )
        if data.empty:
            figure.add_annotation(text="No ranking data for the selected filters",
                                  showarrow=False, x=0.5, y=0.5,
                                  xref="paper", yref="paper")
        return figure
