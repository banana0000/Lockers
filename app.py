import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc

# --- Load the data ---
df = pd.read_csv("LockerNYC_Reservations.csv")

# Bubble size mapping (based on locker size)
size_column = "Bubble Size"
size_map = {"S": 14, "M": 22, "L": 32, "XL": 42}
df["Bubble Size"] = (
    df["Locker Size"].astype(str)
    .str.extract(r'([SMLX]+)')[0]
    .map(size_map)
    .fillna(10)
)

# Timeline event points to visualize for each locker
timeline_points = [
    ("Delivery", "Delivery Date"),
    ("Receive", "Receive Date"),
    ("Withdraw", "Withdraw Date"),
    ("Expire", "Expire Date"),
]

# Filters (add your package/class/type column here—adjust "Type" if your data uses another name)
filter_columns = [
    "Type",           # <-- Package/class filter (adjust if needed)
    "Location Type",
    "Borough",
    "Locker Size",
    "Status",
]

# --- Sidebar creation (filters + clear button) ---
def make_sidebar():
    return html.Div(
        [
            html.H3("Filters", style={
                "marginTop": "30px",
                "marginBottom": "18px",
                "textAlign": "center"
            }),
            *[
                html.Div([
                    dbc.Label(col, style={"fontWeight": "500"}),
                    dcc.Dropdown(
                        id=f"filter-{col}",
                        options=[{"label": "All", "value": "All"}] + [
                            {"label": v, "value": v}
                            for v in sorted(df[col].dropna().unique())
                        ],
                        value="All",
                        clearable=False,
                        style={'width': '98%', "marginBottom": "18px"}
                    ),
                ], style={"marginBottom": "2px"})
                for col in filter_columns
            ],
            html.Div(
                dbc.Button(
                    "Clear All Filters",
                    id="clear-all",
                    color="secondary",
                    outline=True,
                    size="sm"
                ),
                style={"marginTop": "18px", "textAlign": "center"}
            ),
        ],
        className="sidebar",
        style={
            "background": "#f7fafc",
            "padding": "12px 16px 16px 16px",
            "boxShadow": "2px 0 14px #eaeaea",
            "zIndex": 200,
            "width": "260px",
            "flexShrink": 0,
            "height": "100vh",
            "position": "sticky",
            "top": 0,
            "overflowY": "auto",
        }
    )

# --- Main content: Map + Timeline visualization ---
def make_main_content():
    return html.Div(
        [
            html.H2(
                "NYC Locker Dashboard",
                className="mb-3 mt-4",
                style={
                    "textAlign": "left",
                    "fontWeight": "bold",
                    "marginTop": "10px",
                    "marginLeft": "48px"
                }
            ),
            html.Div([
                dbc.Card([
                    dbc.CardHeader("Locker Map"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="map-graph",
                            config={
                                "displayModeBar": True,
                                "scrollZoom": True
                            },
                            style={'height': "clamp(320px, 44vh, 520px)"}
                        )
                    ]),
                ], style={
                    "marginBottom": "16px",
                    "boxShadow": "0 6px 32px #dde",
                    "borderRadius": "18px"
                }),
                html.Div(id="timeline-container"),
            ], className="content-wrap", style={"padding": "0 18px"}),
        ],
        className="main",
        style={"flexGrow": 1, "minWidth": 0}
    )

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

server = app.server

# --- Bootstrap GRID LAYOUT: sidebar left, content right ---
app.layout = dbc.Row(
    [
        dbc.Col(make_sidebar(), width=3, style={"paddingRight": 0, "paddingLeft": 0}),
        dbc.Col(make_main_content(), width=9, style={"paddingRight": 0}),
    ],
    style={"minHeight": "100vh", "margin": 0, "background": "#2db7e4"},
)

# --- Helper: filter the dataframe based on the current filters ---
def filter_df(args):
    dff = df.copy()
    for col, v in zip(filter_columns, args):
        if v not in [None, "All"]:
            dff = dff[dff[col] == v]
    return dff

# --- MAP CALLBACK: Update map based on filters ---
@app.callback(
    Output("map-graph", "figure"),
    [Input(f"filter-{col}", "value") for col in filter_columns],
)
def update_map(*filter_values):
    dff = filter_df(filter_values)
    fig = px.scatter_mapbox(
        dff,
        lat="Latitude",
        lon="longitude",
        color="Location Type",
        size=size_column,
        hover_name="Address",
        size_max=28,
        zoom=11,
        height=395,
        mapbox_style="open-street-map",
        center={
            "lat": dff["Latitude"].mean() if not dff.empty else 40.73,
            "lon": dff["longitude"].mean() if not dff.empty else -73.98
        }
    )
    fig.update_traces(marker=dict(opacity=0.45))
    fig.update_layout(margin=dict(l=0, r=0, t=18, b=0))
    return fig

# --- TIMELINE CALLBACK: Update timeline after marker click or filters ---
@app.callback(
    Output("timeline-container", "children"),
    [Input("map-graph", "clickData")]
    + [Input(f"filter-{col}", "value") for col in filter_columns],
)
def show_timeline_chart(clickData, *filter_values):
    dff = filter_df(filter_values)
    if not clickData or not clickData.get("points"):
        return html.Div([
            html.Div(
                "Click a marker to see the timeline!",
                style={
                    "fontSize": "20px",
                    "margin": "24px 0 12px 16px",
                    "color": "#267",
                    "fontWeight": "500"
                }
            )
        ])
    point = clickData["points"][0]
    addr = point.get("hovertext") or point.get("Address")
    row = dff[dff["Address"] == addr]
    if row.empty:
        return html.Div("No data for this locker.")
    r = row.iloc[0]
    # Collect timeline points; at least 2 needed
    timeline_data = []
    for label, col in timeline_points:
        dt = r.get(col)
        if pd.notnull(dt) and str(dt).strip() and str(dt).lower() != "nan":
            timeline_data.append((label, pd.to_datetime(dt)))
    if len(timeline_data) < 2:
        return html.Div([
            html.H4(
                r["Locker Name"] if "Locker Name" in r and pd.notnull(r["Locker Name"]) else r["Address"],
                style={"fontWeight": "bold", "marginLeft": "16px"}
            ),
            html.Div(
                "No timeline available for this locker.",
                style={"margin": "8px 0 14px 20px"}
            )
        ])
    timeline_data.sort(key=lambda x: x[1])
    df_tl = pd.DataFrame({
        "Step": [x[0] for x in timeline_data],
        "Date": [x[1] for x in timeline_data],
        "y": 1
    })
    timeline_fig = px.scatter(
        df_tl, x="Date", y="y", text="Step", color="Step",
        color_discrete_sequence=px.colors.qualitative.Safe,
        labels={"y": ""}
    )
    timeline_fig.update_traces(
        marker=dict(size=24, opacity=0.81),
        textposition='top center',
        textfont=dict(size=13)
    )
    timeline_fig.update_layout(
        height=120,
        margin=dict(l=25, r=25, t=6, b=10),
        yaxis=dict(showticklabels=False, showgrid=False, range=[0.9, 1.1]),
        xaxis_title="Event Timeline",
        showlegend=False
    )
    return html.Div([
        html.H4(
            r["Locker Name"] if "Locker Name" in r and pd.notnull(r["Locker Name"]) else r["Address"],
            style={"fontWeight": "bold", "marginLeft": "16px"}
        ),
        dcc.Graph(figure=timeline_fig, style={'height': '140px'})
    ])

# --- CLEAR ALL CALLBACK: Reset all filter dropdowns to "All" ---
@app.callback(
    [Output(f"filter-{col}", "value") for col in filter_columns],
    Input("clear-all", "n_clicks"),
    prevent_initial_call=True
)
def clear_all(n_clicks):
    return ["All"] * len(filter_columns)

if __name__ == "__main__":
    app.run(debug=True)