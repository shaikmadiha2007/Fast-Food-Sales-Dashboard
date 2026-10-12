from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------- Page setup -----------------------------
st.set_page_config(
    page_title="Fast Food Sales | Dashboard",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Styling -----------------------------
st.markdown("""
<style>

div[data-testid="stMetric"] {
    background: #25282f;
    padding: 22px 20px;
    border-radius: 16px;
    box-shadow: 0 5px 18px rgba(0, 0, 0, 0.15);
    min-height: 125px;
}

div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #3a291f, #29282b);
    border: 1px solid #ff8c42;
    border-left: 5px solid #ff8c42;
}

div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #302747, #29282f);
    border: 1px solid #b69cff;
    border-left: 5px solid #b69cff;
}

div[data-testid="stHorizontalBlock"] > div:nth-child(3) div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1d3932, #252b2c);
    border: 1px solid #40d6a0;
    border-left: 5px solid #40d6a0;
}

div[data-testid="stHorizontalBlock"] > div:nth-child(4) div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #42252f, #2d272e);
    border: 1px solid #ff7b9c;
    border-left: 5px solid #ff7b9c;
}

div[data-testid="stMetricLabel"] {
    color: #e0e0e5;
    font-weight: 700;
}

div[data-testid="stMetricValue"] {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
}
</style>

""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🍔 Fast Food Sales Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Explore sales, customer choices, payment methods, and sales timing. Sidebar filters update every chart.</div>', unsafe_allow_html=True)
st.write("")

# ----------------------------- Data loading -----------------------------
DEFAULT_PATH = Path(__file__).parent / "data" / "Balaji Fast Food Sales.csv"

@st.cache_data
def read_csv_file(file_bytes=None, file_path=None):
    if file_bytes is not None:
        import io
        return pd.read_csv(io.BytesIO(file_bytes))
    return pd.read_csv(file_path)

uploaded_file = st.sidebar.file_uploader(
    "Upload sales CSV", type=["csv"],
    help="Upload the Balaji Fast Food Sales CSV, or place it in the project's data folder."
)

try:
    if uploaded_file is not None:
        raw = read_csv_file(file_bytes=uploaded_file.getvalue())
        data_source = uploaded_file.name
    elif DEFAULT_PATH.exists():
        raw = read_csv_file(file_path=DEFAULT_PATH)
        data_source = DEFAULT_PATH.name
    else:
        st.info("Upload your sales CSV using the sidebar, or place **Balaji Fast Food Sales.csv** inside the `data` folder.")
        st.code("fast_food_dashboard/\\n├── app.py\\n├── requirements.txt\\n└── data/\\n    └── Balaji Fast Food Sales.csv")
        st.stop()
except Exception as exc:
    st.error(f"Could not read the CSV file: {exc}")
    st.stop()

# Normalize column names to make the app tolerant of spaces/capitalization.
data = raw.copy()
data.columns = [str(c).strip().lower().replace(" ", "_") for c in data.columns]

required = ["transaction_amount", "quantity"]
missing = [col for col in required if col not in data.columns]
if missing:
    st.error(
        "The uploaded CSV does not contain the expected columns: "
        + ", ".join(missing)
        + ". Please upload the Balaji Fast Food Sales dataset."
    )
    st.write("Columns found:", list(data.columns))
    st.stop()

# Handle dates safely; this dataset may use either date or transaction_date.
date_col = next((c for c in ["date", "transaction_date"] if c in data.columns), None)
if date_col:
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce", dayfirst=False)
    data = data.dropna(subset=[date_col])
    data["year"] = data[date_col].dt.year
    data["month"] = data[date_col].dt.to_period("M").astype(str)

for col in ["transaction_amount", "quantity"]:
    data[col] = pd.to_numeric(data[col], errors="coerce")
data = data.dropna(subset=["transaction_amount", "quantity"])
data = data[data["transaction_amount"] >= 0]
if data.empty:
    st.warning("There are no valid sales records to display.")
    st.stop()

# Friendly defaults when optional columns aren't available.
for col in ["item_name", "item_type", "transaction_type", "received_by", "time_of_sale"]:
    if col not in data.columns:
        data[col] = "Unknown"
    data[col] = data[col].fillna("Unknown").astype(str)

# ----------------------------- Sidebar global filters -----------------------------
st.sidebar.markdown("---")
st.sidebar.header("🎛️ Dashboard Filters")
filtered = data.copy()

def add_multiselect_filter(frame, column, label):
    values = sorted(frame[column].dropna().astype(str).unique().tolist())
    selected = st.sidebar.multiselect(label, values, default=values, key=f"filter_{column}")
    if selected:
        return frame[frame[column].astype(str).isin(selected)]
    return frame.iloc[0:0]

filtered = add_multiselect_filter(filtered, "item_type", "Item category")
filtered = add_multiselect_filter(filtered, "item_name", "Item name")
filtered = add_multiselect_filter(filtered, "transaction_type", "Payment method")
filtered = add_multiselect_filter(filtered, "received_by", "Received by")
filtered = add_multiselect_filter(filtered, "time_of_sale", "Time of sale")

if date_col and not data.empty:
    min_date = data[date_col].min().date()
    max_date = data[date_col].max().date()
    chosen_dates = st.sidebar.date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if isinstance(chosen_dates, (tuple, list)) and len(chosen_dates) == 2:
        start_date, end_date = chosen_dates
        filtered = filtered[
            (filtered[date_col].dt.date >= start_date) &
            (filtered[date_col].dt.date <= end_date)
        ]

st.sidebar.caption(f"Source: {data_source}")
if st.sidebar.button("Reset filters", use_container_width=True):
    st.rerun()

if filtered.empty:
    st.warning("No records match these filters. Select more options in the sidebar.")
    st.stop()

# ----------------------------- KPIs -----------------------------
total_sales = filtered["transaction_amount"].sum()
total_items = filtered["quantity"].sum()
transactions = (
    filtered["transaction_id"].nunique()
    if "transaction_id" in filtered.columns
    else len(filtered)
)
avg_sale = total_sales / transactions if transactions else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Total Sales", f"₹{total_sales:,.2f}")
c2.metric("🧾 Transactions", f"{transactions:,}")
c3.metric("🍟 Items Sold", f"{total_items:,.0f}")
c4.metric("📈 Average Sale", f"₹{avg_sale:,.2f}")

st.markdown("### Sales overview")
left, right = st.columns(2)

with left:
    if date_col:
        trend = filtered.groupby("month", as_index=False)["transaction_amount"].sum()
        trend = trend.sort_values("month")
        fig = px.line(
            trend, x="month", y="transaction_amount", markers=True,
            title="Sales Trend by Month",
            labels={"month": "Month", "transaction_amount": "Sales amount"},
        )
    else:
        trend = filtered.groupby("time_of_sale", as_index=False)["transaction_amount"].sum()
        fig = px.line(
            trend, x="time_of_sale", y="transaction_amount", markers=True,
            title="Sales by Time of Sale",
            labels={"time_of_sale": "Time of sale", "transaction_amount": "Sales amount"},
        )
    fig.update_traces(line_width=3)
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), height=370)
    st.plotly_chart(fig, use_container_width=True)

with right:
    payment = filtered.groupby("transaction_type", as_index=False)["transaction_amount"].sum()
    fig = px.bar(
        payment, x="transaction_type", y="transaction_amount", color="transaction_type",
        title="Sales by Payment Method",
        labels={"transaction_type": "Payment method", "transaction_amount": "Sales amount"},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=55, b=10), height=370)
    fig.update_yaxes(tickprefix="₹")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Product performance")
left, right = st.columns(2)

with left:
    category = filtered.groupby("item_type", as_index=False).agg(
        quantity=("quantity", "sum"), sales=("transaction_amount", "sum")
    ).sort_values("sales", ascending=False)
    fig = px.pie(
        category, names="item_type", values="sales", hole=0.48,
        title="Sales Share by Item Category",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), height=390)
    st.plotly_chart(fig, use_container_width=True)

with right:
    products = filtered.groupby("item_name", as_index=False).agg(
        quantity=("quantity", "sum"), sales=("transaction_amount", "sum")
    ).sort_values("quantity", ascending=False).head(10)
    fig = px.bar(
        products.sort_values("quantity"), x="quantity", y="item_name",
        orientation="h", color="quantity", title="Top 10 Items by Quantity Sold",
        labels={"quantity": "Quantity sold", "item_name": "Item"},
        color_continuous_scale="Sunset",
    )
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=10, r=10, t=55, b=10), height=390)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Sales patterns")
left, right = st.columns(2)
with left:
    timing = filtered.groupby("time_of_sale", as_index=False).agg(
        transactions=("quantity", "size"), sales=("transaction_amount", "sum")
    ).sort_values("sales", ascending=False)
    fig = px.bar(
        timing, x="time_of_sale", y="transactions", color="time_of_sale",
        title="Transactions by Time of Sale",
        labels={"time_of_sale": "Time of sale", "transactions": "Number of transactions"},
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=55, b=10), height=350)
    st.plotly_chart(fig, use_container_width=True)

with right:
    staff = filtered.groupby("received_by", as_index=False)["transaction_amount"].sum().sort_values(
        "transaction_amount", ascending=False
    )
    fig = px.bar(
        staff, x="received_by", y="transaction_amount", color="received_by",
        title="Sales by Staff Member",
        labels={"received_by": "Received by", "transaction_amount": "Sales amount"},
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=55, b=10), height=350)
    fig.update_yaxes(tickprefix="₹")
    st.plotly_chart(fig, use_container_width=True)

with st.expander("🔎 View filtered data"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data as CSV", csv, "filtered_fast_food_sales.csv", "text/csv")

st.caption("Built with Streamlit, Pandas, and Plotly. All charts use the same sidebar-filtered dataset.")
