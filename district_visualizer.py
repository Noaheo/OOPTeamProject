"""Plotly charts for commercial-district ranking and comparison results."""

import pandas as pd
import plotly.graph_objects as go


class DistrictVisualizer:
    """Visualize district rankings and comparisons without performing sales calculations."""

    _DEFAULT_PALETTE = ["#3B5BDB", "#12B886", "#F59F00", "#FA5252", "#7950F2"]

    def __init__(self, template="plotly_white", color_palette=None):
        self._template = template
        self._color_palette = list(color_palette) if color_palette else list(self._DEFAULT_PALETTE)

    @staticmethod
    def _clean(series):
        return series.astype(object).where(series.notna(), None).tolist()

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
            y=self._clean(data["total_sales"]),
            customdata=codes.tolist(),
            marker_color=self._color_palette[0],
            name="Estimated sales",
            hovertemplate=(
                "District: %{x}<br>Code: %{customdata}"
                "<br>Estimated sales: %{y:,.0f} KRW<extra></extra>"
            ),
        ))
        figure.update_layout(
            title="Commercial District Sales Ranking",
            xaxis_title="Commercial district",
            yaxis_title="Estimated sales (KRW)",
            yaxis_exponentformat="B",
            xaxis_type="category",
            template=self._template,
        )
        if data.empty:
            figure.add_annotation(
                text="No ranking data for the selected filters",
                showarrow=False,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
            )
        return figure

    def plot_comparison(self, data: pd.DataFrame) -> go.Figure:
        """Return a Plotly bar chart for DistrictComparator.compare_districts()."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        required = {"district_code", "district_name", "total_sales", "difference", "percent_diff", "is_reference"}
        if not required.issubset(data.columns):
            raise ValueError(f"Missing comparison columns: {sorted(required - set(data.columns))}")

        figure = go.Figure()
        if data.empty:
            figure.update_layout(
                title="Multi-District Sales Comparison",
                xaxis_title="Commercial district",
                yaxis_title="Estimated sales (KRW)",
                yaxis_exponentformat="B",
                xaxis_type="category",
                template=self._template,
            )
            figure.add_annotation(
                text="No comparison data for the selected districts",
                showarrow=False,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
            )
            return figure

        labels = data["district_name"].fillna(data["district_code"]).astype(str).tolist()
        codes = data["district_code"].astype(str).tolist()
        ref_color = self._color_palette[0]
        other_color = self._color_palette[1 % len(self._color_palette)]
        colors = [ref_color if bool(is_ref) else other_color for is_ref in data["is_reference"]]

        bar_text = []
        diff_labels = []
        pct_labels = []
        for is_ref, diff, pct in zip(data["is_reference"], data["difference"], data["percent_diff"]):
            diff_str = "N/A" if pd.isna(diff) else f"{int(diff):+,d} KRW"
            pct_str = "N/A" if pd.isna(pct) else f"{float(pct):+.2f}%"
            diff_labels.append(diff_str)
            pct_labels.append(pct_str)
            if bool(is_ref):
                bar_text.append("Baseline")
            elif not pd.isna(pct):
                bar_text.append(f"{float(pct):+.1f}%")
            else:
                bar_text.append("")

        customdata = [[c, d, p] for c, d, p in zip(codes, diff_labels, pct_labels)]
        figure.add_trace(go.Bar(
            x=labels,
            y=self._clean(data["total_sales"]),
            marker_color=colors,
            text=bar_text,
            textposition="outside",
            customdata=customdata,
            name="Estimated sales",
            hovertemplate=(
                "District: %{x}<br>Code: %{customdata[0]}"
                "<br>Estimated sales: %{y:,.0f} KRW"
                "<br>Gap vs. baseline: %{customdata[1]}"
                "<br>Pct gap: %{customdata[2]}<extra></extra>"
            ),
        ))

        ref_rows = data[data["is_reference"].astype(bool)]
        if not ref_rows.empty:
            ref_val = ref_rows["total_sales"].iloc[0]
            if not pd.isna(ref_val):
                figure.add_hline(
                    y=int(ref_val),
                    line_dash="dash",
                    line_color=ref_color,
                    opacity=0.65,
                )

        figure.update_layout(
            title="Multi-District Sales Comparison",
            xaxis_title="Commercial district",
            yaxis_title="Estimated sales (KRW)",
            yaxis_exponentformat="B",
            xaxis_type="category",
            template=self._template,
        )
        return figure
