from html import escape
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from ui_text import district_name as english_district_name


class MapVisualizer:
    """Sales bubbles at commercial district locations."""

    _COLORS = {
        "Alley": "#3B5BDB",
        "Developed": "#12B886",
        "Traditional market": "#F59F00",
        "Tourist zone": "#F06595",
    }

    def __init__(self, boundaries_path=None):
        self._boundaries_path = (Path(boundaries_path) if boundaries_path is not None
                                 else Path(__file__).parent / "assets" / "district_boundaries.geojson")

    def _figure(self):
        figure = go.Figure()
        figure.update_layout(
            title="Seoul Commercial District Sales",
            template="plotly_white",
            height=600,
            margin=dict(l=8, r=8, t=16, b=8),
            map=dict(style="carto-positron", center=dict(lat=37.56, lon=126.99),
                     zoom=10.3, uirevision="seoul-district-sales"),
            legend=dict(title="District type", x=0.015, y=0.98, xanchor="left",
                        yanchor="top", bgcolor="rgba(255,255,255,0.92)",
                        bordercolor="#E2E8F0", borderwidth=1, font=dict(size=11)),
            hoverlabel=dict(bgcolor="white", font=dict(color="#1F2937", size=12)),
        )
        self._add_basemap_menu(figure)
        return figure

    def plot_map(self, data, reference_code=None):
        """Plot district sales, optionally highlighting a comparison baseline."""
        figure = self._figure()
        if data.empty:
            figure.add_annotation(text="No sales data for this selection", showarrow=False,
                                  x=0.5, y=0.5, xref="paper", yref="paper", bgcolor="white")
            return figure

        located = self._located_districts(data, figure)
        positive = located.loc[located["total_sales"].gt(0).fillna(False)]

        # Every district type uses the same scale so bubble areas remain comparable.
        sizeref = 2 * float(positive["total_sales"].max()) / 44 ** 2 if not positive.empty else 1
        reference = located.loc[located["district_code"].eq(reference_code)]
        positive = positive.drop(index=reference.index, errors="ignore")
        types = list(self._COLORS) + sorted(set(positive["district_type"]) - self._COLORS.keys())
        for district_type in types:
            rows = positive.loc[positive["district_type"] == district_type]
            if not rows.empty:
                rows = rows.sort_values("total_sales", ascending=False, kind="stable")
                figure.add_trace(self._trace(rows, district_type,
                                            self._COLORS.get(district_type, "#7950F2"), sizeref))

        zero = located.loc[located["total_sales"].eq(0).fillna(False)]
        unavailable = located.loc[located["total_sales"].isna()]
        for subset, label, color in ((zero, "Zero sales", "#64748B"),
                                     (unavailable, "Sales unavailable", "#CBD5E1")):
            others = subset.drop(index=reference.index, errors="ignore")
            if not others.empty:
                figure.add_trace(self._trace(others, label, color))
        if not reference.empty:
            reference_has_sales = reference["total_sales"].gt(0).fillna(False).any()
            trace = self._trace(reference, "Reference district", "#9333EA",
                                sizeref if reference_has_sales else None)
            if not reference_has_sales:
                trace.marker.size = 12
            figure.add_trace(trace)
            figure.update_layout(legend_title_text="Map legend")

        self._add_coverage_note(figure, data, located, "Bubble area shows sales")
        message = None
        if located.empty:
            message = "No mapped districts for this selection"
        elif len(unavailable) == len(located):
            message = "Sales totals are unavailable for all located districts"
        elif len(zero) == len(located):
            message = "All located districts have zero recorded sales"
        if message:
            self._add_message(figure, message)
        return figure

    def plot_demographic_map(self, data, group):
        """Colour district markers by the selected customer group's sales share."""
        figure = self._figure()
        located = self._located_districts(data, figure)
        known = located.loc[located["sales_share"].notna()]
        unknown = located.loc[located["sales_share"].isna()]
        figure.update_layout(legend_title_text=None)
        if not unknown.empty:
            trace = self._trace(unknown, "Share unavailable", "#94A3B8", demographic_group=group)
            trace.marker.size = 9
            figure.add_trace(trace)
        if not known.empty:
            trace = self._trace(known, group, "#3B5BDB", demographic_group=group)
            trace.showlegend = False
            trace.marker = dict(
                size=11, color=known["sales_share"].astype(float).tolist(), opacity=0.85,
                colorscale=["#b9d6f5", "#4e90db", "#102a72"], cmin=0, cmax=100, showscale=True,
                colorbar=dict(title="Sales share", ticksuffix="%", len=0.55, thickness=12),
            )
            figure.add_trace(trace)

        self._add_coverage_note(figure, data, located, "Colour shows the sales share")
        if located.empty:
            self._add_message(figure, "No mapped districts for this selection")
        elif known.empty:
            self._add_message(figure, "No sales shares available for this group")
        return figure

    @staticmethod
    def _located_districts(data, figure):
        latitude = pd.to_numeric(data["latitude"], errors="coerce")
        longitude = pd.to_numeric(data["longitude"], errors="coerce")
        valid = latitude.between(-90, 90) & longitude.between(-180, 180)
        located = data.loc[valid].copy().reset_index(drop=True)
        located["latitude"] = latitude.loc[valid].tolist()
        located["longitude"] = longitude.loc[valid].tolist()
        located["district_type"] = located["district_type"].fillna("Other")
        if len(located) == 1:
            district = located.iloc[0]
            figure.update_layout(map_center=dict(lat=district.latitude, lon=district.longitude),
                                 map_zoom=12.8, map_uirevision=f"district-{district.district_code}")
        return located

    @staticmethod
    def _add_coverage_note(figure, data, located, measure):
        missing_locations = len(data) - len(located)
        note = f"{len(located):,} of {len(data):,} districts located · {measure}"
        if missing_locations:
            note += f"<br>{missing_locations:,} omitted: no valid location"
        figure.add_annotation(
            text=note, showarrow=False, x=0.015, y=0.02, xref="paper", yref="paper",
            xanchor="left", yanchor="bottom", align="left", borderpad=7,
            bgcolor="rgba(255,255,255,0.94)", bordercolor="#E2E8F0", borderwidth=1,
            font=dict(size=11, color="#92400E" if missing_locations else "#475569"),
        )

    @staticmethod
    def _add_message(figure, text):
        figure.add_annotation(text=text, showarrow=False, x=0.5, y=0.5,
                              xref="paper", yref="paper", bgcolor="white", borderpad=8)

    @staticmethod
    def _trace(rows, label, color, sizeref=None, demographic_group=None):
        names, details = [], []
        for row in rows.itertuples(index=False):
            original = str(row.district_name) if pd.notna(row.district_name) else str(row.district_code)
            names.append(escape(english_district_name(original)))
            sales = "N/A" if pd.isna(row.total_sales) else f"{int(row.total_sales):,}"
            transactions = "N/A" if pd.isna(row.total_transactions) else f"{int(row.total_transactions):,}"
            details.append([str(row.district_code), escape(original), escape(str(row.district_type)),
                            sales, transactions])
            if demographic_group:
                group_sales = "N/A" if pd.isna(row.group_sales) else f"{int(row.group_sales):,} KRW"
                share = "N/A" if pd.isna(row.sales_share) else f"{row.sales_share:.2f}%"
                details[-1] += [group_sales, share]
        hover = ("<b>%{text}</b><br>%{customdata[1]}<br>Code: %{customdata[0]}"
                 "<br>Type: %{customdata[2]}")
        if demographic_group:
            hover += (f"<br>{escape(demographic_group)} sales: %{{customdata[5]}}"
                      "<br>Sales share: %{customdata[6]}")
        else:
            hover += "<br>Sales: %{customdata[3]} KRW<br>Transactions: %{customdata[4]}"
        return go.Scattermap(
            lat=rows["latitude"].tolist(), lon=rows["longitude"].tolist(),
            ids=rows["district_code"].astype(str).tolist(), text=names, customdata=details,
            name=label, mode="markers", showlegend=True,
            marker=dict(color=color, opacity=0.82, symbol="circle",
                        size=[int(v) for v in rows["total_sales"]] if sizeref is not None else 5,
                        sizemode="area", sizeref=sizeref, sizemin=4),
            hovertemplate=hover + "<extra></extra>",
        )

    def _add_basemap_menu(self, figure):
        if not self._boundaries_path.is_file():
            return
        with self._boundaries_path.open(encoding="utf-8") as source:
            boundaries = json.load(source)
        layers = [
            dict(sourcetype="geojson", source=boundaries, type="fill", color="#E2E8F0",
                 opacity=0.4, below="traces"),
            dict(sourcetype="geojson", source=boundaries, type="line", color="#94A3B8",
                 line=dict(width=1), below="traces"),
        ]
        figure.update_layout(updatemenus=[dict(
            type="dropdown", direction="down", x=0.985, y=0.87,
            xanchor="right", yanchor="top", bgcolor="white", bordercolor="#CBD5E1",
            font=dict(size=11, color="#334155"), pad=dict(l=0, r=0, t=0, b=0),
            buttons=[
                dict(label="Street map", method="relayout",
                     args=[{"map.style": "carto-positron", "map.layers": []}]),
                dict(label="Offline outlines", method="relayout",
                     args=[{"map.style": "white-bg", "map.layers": layers}]),
            ],
        )])
