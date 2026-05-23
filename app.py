import os
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

# -------------------------------------------------
# Page setup
# -------------------------------------------------
st.set_page_config(
    page_title="Cloud Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------
# Custom styling
# -------------------------------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        .hero-card {
            padding: 1.2rem 1.4rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(148, 163, 184, 0.25);
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }

        .metric-card {
            padding: 1rem 1rem;
            border-radius: 16px;
            background: white;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }

        .small-muted {
            color: #64748b;
            font-size: 0.92rem;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid rgba(148, 163, 184, 0.18);
            padding: 16px 16px 12px 16px;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        .stButton button {
            border-radius: 12px;
            padding: 0.55rem 1rem;
            font-weight: 600;
        }

        .stDownloadButton button {
            border-radius: 12px;
            padding: 0.55rem 1rem;
            font-weight: 600;
        }

        .insight-box {
            background: white;
            border-radius: 16px;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Utility helpers
# -------------------------------------------------
def read_csv_safely(file_obj: object) -> pd.DataFrame:
    """Read CSV robustly with fallback encodings."""
    encodings = ["latin1", "utf-8", "cp1252"]
    last_error = None

    for enc in encodings:
        try:
            return pd.read_csv(file_obj, encoding=enc)
        except Exception as e:
            last_error = e
            try:
                file_obj.seek(0)
            except Exception:
                pass

    raise last_error  # type: ignore[misc]


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first matching column name from a list of candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def money_format(value: float) -> str:
    return f"${value:,.0f}"


def safe_group_sum(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    out = df.groupby(group_col, as_index=False)[value_col].sum()
    return out.sort_values(value_col, ascending=False)


# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown(
    """
    <div class="hero-card">
        <h1 style="margin-bottom:0.2rem;">Cloud Analytics Platform</h1>
        <div class="small-muted">
            A polished cloud-connected analytics dashboard built with Python, SQL, PostgreSQL, Streamlit, and Plotly.
        </div>
        <div class="small-muted" style="margin-top:0.35rem;">
            Upload a CSV, explore business metrics, run SQL queries, inspect data quality, and export filtered results.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# Database connection
# -------------------------------------------------
try:
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", ""))
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        st.sidebar.success("Cloud PostgreSQL connected")
    except Exception as e:
        st.sidebar.warning(f"DB connection issue: {e}")
else:
    st.sidebar.info("No DATABASE_URL configured yet.")

# -------------------------------------------------
# File upload
# -------------------------------------------------
uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file is None:
    st.info("Upload a dataset to begin.")
    st.stop()

# Read and clean data
df = read_csv_safely(uploaded_file)
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# Normalize common date columns if present
for date_col in ["order_date", "ship_date", "date", "created_at"]:
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# Try to save to cloud database
if engine is not None:
    try:
        df.to_sql("uploaded_data", engine, if_exists="replace", index=False)
        st.sidebar.success("Saved to cloud PostgreSQL")
    except Exception as e:
        st.sidebar.warning(f"Could not save to database: {e}")

# -------------------------------------------------
# Detect columns
# -------------------------------------------------
sales_col = find_col(df, ["sales", "revenue", "amount", "total_sales"])
profit_col = find_col(df, ["profit", "margin", "net_profit"])
region_col = find_col(df, ["region", "state", "country", "location"])
category_col = find_col(df, ["category", "segment", "department"])
date_col = find_col(df, ["order_date", "date", "created_at", "ship_date"])
product_col = find_col(df, ["product_name", "product", "item_name", "sku"])

# -------------------------------------------------
# Sidebar filters
# -------------------------------------------------
st.sidebar.header("Filters")

filtered_df = df.copy()

if region_col:
    region_options = sorted(df[region_col].dropna().astype(str).unique().tolist())
    selected_regions = st.sidebar.multiselect(
        "Region",
        region_options,
        default=region_options,
    )
    filtered_df = filtered_df[filtered_df[region_col].astype(str).isin(selected_regions)]

if category_col:
    category_options = sorted(df[category_col].dropna().astype(str).unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Category",
        category_options,
        default=category_options,
    )
    filtered_df = filtered_df[filtered_df[category_col].astype(str).isin(selected_categories)]

if date_col and pd.api.types.is_datetime64_any_dtype(df[date_col]):
    min_date = df[date_col].min()
    max_date = df[date_col].max()

    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date.date(), max_date.date()),
        )

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df[date_col].dt.date >= start_date) &
                (filtered_df[date_col].dt.date <= end_date)
            ]

st.sidebar.divider()
st.sidebar.caption("Tip: use the SQL tab to query the saved `uploaded_data` table.")

# -------------------------------------------------
# KPI calculations
# -------------------------------------------------
total_sales = filtered_df[sales_col].sum() if sales_col and sales_col in filtered_df.columns else 0
total_profit = filtered_df[profit_col].sum() if profit_col and profit_col in filtered_df.columns else 0
avg_sales = filtered_df[sales_col].mean() if sales_col and sales_col in filtered_df.columns else 0

top_region = "N/A"
if region_col and sales_col and not filtered_df.empty:
    region_sales = safe_group_sum(filtered_df, region_col, sales_col)
    if not region_sales.empty:
        top_region = str(region_sales.iloc[0][region_col])

top_category = "N/A"
if category_col and sales_col and not filtered_df.empty:
    category_sales = safe_group_sum(filtered_df, category_col, sales_col)
    if not category_sales.empty:
        top_category = str(category_sales.iloc[0][category_col])

filtered_rows = len(filtered_df)
duplicate_rows = int(filtered_df.duplicated().sum())
missing_values = int(filtered_df.isna().sum().sum())

# -------------------------------------------------
# KPI cards
# -------------------------------------------------
st.subheader("Executive Summary")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Sales", money_format(total_sales))
k2.metric("Total Profit", money_format(total_profit))
k3.metric("Average Sales", f"{avg_sales:,.2f}")
k4.metric("Top Region", top_region)

k5, k6, k7, k8 = st.columns(4)
k5.metric("Top Category", top_category)
k6.metric("Filtered Rows", f"{filtered_rows:,}")
k7.metric("Duplicates", f"{duplicate_rows:,}")
k8.metric("Missing Values", f"{missing_values:,}")

# -------------------------------------------------
# Tabs
# -------------------------------------------------
tab_overview, tab_charts, tab_sql, tab_quality, tab_data = st.tabs(
    ["Overview", "Charts", "SQL Query", "Data Quality", "Data"]
)

# -------------------------------------------------
# Overview tab
# -------------------------------------------------
with tab_overview:
    st.markdown("### Auto Insights")

    insights = []
    if top_region != "N/A":
        insights.append(f"Top region by sales: **{top_region}**")
    if top_category != "N/A":
        insights.append(f"Top category by sales: **{top_category}**")

    if sales_col and sales_col in filtered_df.columns and not filtered_df.empty:
        insights.append(f"Highest single sale value: **{money_format(filtered_df[sales_col].max())}**")
        insights.append(f"Median sale value: **{money_format(filtered_df[sales_col].median())}**")

    if profit_col and profit_col in filtered_df.columns and not filtered_df.empty:
        insights.append(f"Average profit value: **{money_format(filtered_df[profit_col].mean())}**")

    if insights:
        for item in insights[:5]:
            st.markdown(f"- {item}")
    else:
        st.info("No insights available for this dataset.")

    st.markdown("### What this dashboard does")
    st.write(
        "This dashboard turns raw CSV data into a cloud-connected analytics experience with filtering, "
        "business KPIs, trend charts, SQL querying, and downloadable outputs."
    )

# -------------------------------------------------
# Charts tab
# -------------------------------------------------
with tab_charts:
    st.markdown("### Business Charts")

    col_left, col_right = st.columns(2)

    with col_left:
        if region_col and sales_col and not filtered_df.empty:
            sales_by_region = safe_group_sum(filtered_df, region_col, sales_col)
            fig_region = px.bar(
                sales_by_region,
                x=region_col,
                y=sales_col,
                title="Total Sales by Region",
                text_auto=".2s",
            )
            fig_region.update_layout(
                template="plotly_white",
                xaxis_title="Region",
                yaxis_title="Sales",
                height=430,
            )
            st.plotly_chart(fig_region, use_container_width=True)
        else:
            st.info("No region/sales columns found for regional sales chart.")

    with col_right:
        if category_col and profit_col and not filtered_df.empty:
            profit_by_category = safe_group_sum(filtered_df, category_col, profit_col)
            fig_category = px.bar(
                profit_by_category,
                x=category_col,
                y=profit_col,
                title="Total Profit by Category",
                text_auto=".2s",
            )
            fig_category.update_layout(
                template="plotly_white",
                xaxis_title="Category",
                yaxis_title="Profit",
                height=430,
            )
            st.plotly_chart(fig_category, use_container_width=True)
        else:
            st.info("No category/profit columns found for category profit chart.")

    if date_col and sales_col and pd.api.types.is_datetime64_any_dtype(filtered_df[date_col]):
        trend_df = (
            filtered_df.dropna(subset=[date_col])
            .groupby(date_col, as_index=False)[sales_col]
            .sum()
            .sort_values(date_col)
        )

        if not trend_df.empty:
            fig_trend = px.line(
                trend_df,
                x=date_col,
                y=sales_col,
                title="Sales Trend Over Time",
                markers=True,
            )
            fig_trend.update_layout(
                template="plotly_white",
                xaxis_title="Date",
                yaxis_title="Sales",
                height=450,
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No valid dates found for trend chart.")
    else:
        st.info("No date column available for trend chart.")

    if product_col and sales_col and not filtered_df.empty:
        top_products = (
            filtered_df.groupby(product_col, as_index=False)[sales_col]
            .sum()
            .sort_values(sales_col, ascending=False)
            .head(10)
        )
        if not top_products.empty:
            fig_products = px.bar(
                top_products,
                x=sales_col,
                y=product_col,
                orientation="h",
                title="Top 10 Products by Sales",
                text_auto=".2s",
            )
            fig_products.update_layout(
                template="plotly_white",
                yaxis={"autorange": "reversed"},
                xaxis_title="Sales",
                yaxis_title="Product",
                height=450,
            )
            st.plotly_chart(fig_products, use_container_width=True)

# -------------------------------------------------
# SQL tab
# -------------------------------------------------
with tab_sql:
    st.markdown("### Run SQL on Cloud Database")
    st.caption("Query the `uploaded_data` table stored in PostgreSQL.")

    sql_default = """
SELECT region, SUM(sales) AS total_sales
FROM uploaded_data
GROUP BY region
ORDER BY total_sales DESC
""".strip()

    query = st.text_area("Write SQL query", value=sql_default, height=150)

    if st.button("Run Query", type="primary"):
        if engine is not None:
            try:
                result = pd.read_sql_query(query, engine)
                st.success("Query executed successfully.")
                st.dataframe(result, use_container_width=True)
            except Exception as e:
                st.error(f"Query failed: {e}")
        else:
            st.error("Database connection is not available.")

# -------------------------------------------------
# Data quality tab
# -------------------------------------------------
with tab_quality:
    st.markdown("### Data Quality Summary")

    q1, q2, q3 = st.columns(3)
    q1.metric("Total Rows", f"{len(df):,}")
    q2.metric("Duplicate Rows", f"{duplicate_rows:,}")
    q3.metric("Total Missing Values", f"{missing_values:,}")

    missing_counts = df.isna().sum().sort_values(ascending=False)
    missing_df = missing_counts.reset_index()
    missing_df.columns = ["column", "missing_count"]
    missing_df = missing_df[missing_df["missing_count"] > 0]

    st.markdown("#### Missing Values by Column")
    if not missing_df.empty:
        fig_missing = px.bar(
            missing_df,
            x="column",
            y="missing_count",
            title="Missing Values by Column",
        )
        fig_missing.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_missing, use_container_width=True)
    else:
        st.success("No missing values found in the dataset.")

    st.markdown("#### Column Types")
    dtype_df = df.dtypes.astype(str).reset_index()
    dtype_df.columns = ["column", "dtype"]
    st.dataframe(dtype_df, use_container_width=True)

# -------------------------------------------------
# Data tab
# -------------------------------------------------
with tab_data:
    st.markdown("### Filtered Data")
    st.dataframe(filtered_df, use_container_width=True)

    st.divider()
    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered CSV",
        data=csv_data,
        file_name="filtered_data.csv",
        mime="text/csv",
    )

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.divider()
st.caption(
    "Built with Python • Streamlit • Plotly • SQL • PostgreSQL • Cloud Analytics"
)