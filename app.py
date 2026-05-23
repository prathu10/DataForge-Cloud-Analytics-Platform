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

# Optional database connection
try:
    DATABASE_URL = st.secrets.get("DATABASE_URL", os.getenv("DATABASE_URL", ""))
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = None
if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL)
    except Exception as e:
        st.warning(f"Database connection could not be created: {e}")

uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Dataset Preview")
    st.dataframe(df.head(), use_container_width=True)

    # Save to Postgres if available
    if engine is not None:
        try:
            df.to_sql("uploaded_data", engine, if_exists="replace", index=False)
            st.success("Dataset uploaded to cloud PostgreSQL database!")
        except Exception as e:
            st.warning(f"Could not save to database: {e}")
    else:
        st.info("No database configured yet. Set DATABASE_URL to save data to PostgreSQL.")

    # KPIs
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Columns", len(df.columns))
    c3.metric("Missing Values", int(df.isna().sum().sum()))

    st.divider()

    # Numeric visualization
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if numeric_cols:
        selected_num = st.selectbox("Select Numeric Column", numeric_cols)

        fig = px.histogram(
            df,
            x=selected_num,
            title=f"Distribution of {selected_num}"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Category visualization
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    if categorical_cols:
        selected_cat = st.selectbox("Select Category Column", categorical_cols)

        top_values = (
            df[selected_cat]
            .astype(str)
            .value_counts()
            .head(10)
            .reset_index()
        )
        top_values.columns = [selected_cat, "Count"]

        fig2 = px.bar(
            top_values,
            x=selected_cat,
            y="Count",
            title=f"Top values in {selected_cat}"
        )
        st.plotly_chart(fig2, use_container_width=True)

else:
    st.info("Upload a dataset to begin.")