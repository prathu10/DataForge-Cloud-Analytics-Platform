import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(
    page_title="Cloud Analytics Platform",
    layout="wide"
)

st.title("Cloud Analytics Platform")
st.markdown("Interactive analytics dashboard using Python, SQL, PostgreSQL, and Streamlit")
st.caption("Cloud-hosted PostgreSQL analytics with interactive filters, SQL queries, and business insights.")

# -----------------------------
# Database connection
# -----------------------------
try:
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", ""))
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
        st.success("Connected to Cloud PostgreSQL Database")
    except Exception as e:
        st.warning(f"Database connection could not be created: {e}")
else:
    st.info("No database configured yet. Set DATABASE_URL to save data to PostgreSQL.")

# -----------------------------
# File upload
# -----------------------------
uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding="latin1")

    # Clean column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Try parsing order_date if present
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # Save to cloud database
    if engine is not None:
        try:
            df.to_sql("uploaded_data", engine, if_exists="replace", index=False)
            st.success("Dataset uploaded to cloud PostgreSQL database!")
        except Exception as e:
            st.warning(f"Could not save to database: {e}")

    st.subheader("Dataset Preview")
    st.dataframe(df.head(), use_container_width=True)

    # -----------------------------
    # Sidebar filters
    # -----------------------------
    st.sidebar.header("Filters")

    filtered_df = df.copy()

    if "region" in df.columns:
        region_options = sorted(df["region"].dropna().astype(str).unique().tolist())
        selected_regions = st.sidebar.multiselect(
            "Region",
            region_options,
            default=region_options
        )
        filtered_df = filtered_df[filtered_df["region"].astype(str).isin(selected_regions)]

    if "category" in df.columns:
        category_options = sorted(df["category"].dropna().astype(str).unique().tolist())
        selected_categories = st.sidebar.multiselect(
            "Category",
            category_options,
            default=category_options
        )
        filtered_df = filtered_df[filtered_df["category"].astype(str).isin(selected_categories)]

    if "order_date" in df.columns:
        min_date = df["order_date"].min()
        max_date = df["order_date"].max()

        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.sidebar.date_input(
                "Order Date Range",
                value=(min_date.date(), max_date.date())
            )

            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (filtered_df["order_date"].dt.date >= start_date) &
                    (filtered_df["order_date"].dt.date <= end_date)
                ]

    # -----------------------------
    # Business KPIs
    # -----------------------------
    total_sales = filtered_df["sales"].sum() if "sales" in filtered_df.columns else 0
    total_profit = filtered_df["profit"].sum() if "profit" in filtered_df.columns else 0
    avg_sales = filtered_df["sales"].mean() if "sales" in filtered_df.columns else 0

    top_region = "N/A"
    if "region" in filtered_df.columns and "sales" in filtered_df.columns and not filtered_df.empty:
        region_sales = filtered_df.groupby("region")["sales"].sum()
        if not region_sales.empty:
            top_region = region_sales.idxmax()

    top_category = "N/A"
    if "category" in filtered_df.columns and "sales" in filtered_df.columns and not filtered_df.empty:
        category_sales = filtered_df.groupby("category")["sales"].sum()
        if not category_sales.empty:
            top_category = category_sales.idxmax()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sales", f"${total_sales:,.0f}")
    c2.metric("Total Profit", f"${total_profit:,.0f}")
    c3.metric("Average Sales", f"${avg_sales:,.2f}")
    c4.metric("Top Region", top_region)

    c5, c6, _, _ = st.columns(4)
    c5.metric("Top Category", top_category)
    c6.metric("Rows", f"{len(filtered_df):,}")

    st.divider()

    # -----------------------------
    # Business insights and charts
    # -----------------------------
    st.subheader("Business Insights")

    left_col, right_col = st.columns(2)

    with left_col:
        if "region" in filtered_df.columns and "sales" in filtered_df.columns and not filtered_df.empty:
            sales_by_region = filtered_df.groupby("region", as_index=False)["sales"].sum()
            fig_region = px.bar(
                sales_by_region,
                x="region",
                y="sales",
                title="Total Sales by Region"
            )
            st.plotly_chart(fig_region, use_container_width=True)
        else:
            st.info("No region or sales column found for regional sales chart.")

    with right_col:
        if "category" in filtered_df.columns and "profit" in filtered_df.columns and not filtered_df.empty:
            profit_by_category = filtered_df.groupby("category", as_index=False)["profit"].sum()
            fig_category = px.bar(
                profit_by_category,
                x="category",
                y="profit",
                title="Total Profit by Category"
            )
            st.plotly_chart(fig_category, use_container_width=True)
        else:
            st.info("No category or profit column found for category profit chart.")

    if "order_date" in filtered_df.columns and "sales" in filtered_df.columns:
        df_trend = (
            filtered_df.dropna(subset=["order_date"])
            .groupby("order_date", as_index=False)["sales"].sum()
            .sort_values("order_date")
        )

        if not df_trend.empty:
            fig_trend = px.line(
                df_trend,
                x="order_date",
                y="sales",
                title="Sales Trend Over Time"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No valid order_date values found for trend chart.")
    else:
        st.info("No order_date or sales column found for trend chart.")

    if "product_name" in filtered_df.columns and "sales" in filtered_df.columns:
        top_products = (
            filtered_df.groupby("product_name", as_index=False)["sales"].sum()
            .sort_values("sales", ascending=False)
            .head(10)
        )
        fig_products = px.bar(
            top_products,
            x="sales",
            y="product_name",
            orientation="h",
            title="Top 10 Products by Sales"
        )
        fig_products.update_layout(yaxis={"autorange": "reversed"})
        st.plotly_chart(fig_products, use_container_width=True)

    # -----------------------------
    # Insights summary
    # -----------------------------
    st.subheader("Auto Insights")

    insights = []

    if top_region != "N/A":
        insights.append(f"Top region by sales: {top_region}")

    if top_category != "N/A":
        insights.append(f"Top category by sales: {top_category}")

    if "sales" in filtered_df.columns and not filtered_df.empty:
        max_sale = filtered_df["sales"].max()
        insights.append(f"Highest single sale value: ${max_sale:,.2f}")

    if "profit" in filtered_df.columns and not filtered_df.empty:
        avg_profit = filtered_df["profit"].mean()
        insights.append(f"Average profit value: ${avg_profit:,.2f}")

    if insights:
        for item in insights[:4]:
            st.write(f"- {item}")
    else:
        st.info("No insights available for this dataset.")

    # -----------------------------
    # SQL query box
    # -----------------------------
    st.divider()
    st.subheader("Run SQL on Cloud Database")

    sql_default = "SELECT * FROM uploaded_data LIMIT 10"

    query = st.text_area(
        "Write SQL query for the uploaded_data table",
        value=sql_default,
        height=120
    )

    if st.button("Run Query"):
        if engine is not None:
            try:
                result = pd.read_sql_query(query, engine)
                st.dataframe(result, use_container_width=True)
            except Exception as e:
                st.error(f"Query failed: {e}")
        else:
            st.error("Database connection is not available.")

    # -----------------------------
    # Download filtered data
    # -----------------------------
    st.divider()
    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered CSV",
        data=csv_data,
        file_name="filtered_data.csv",
        mime="text/csv"
    )

else:
    st.info("Upload a dataset to begin.")