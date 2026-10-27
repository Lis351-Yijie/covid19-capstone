import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="COVID-19 Global Dashboard",
    page_icon="🌍",
    layout="wide"
)

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "CSSEGISandData/COVID-19/master/"
    "csse_covid_19_data/csse_covid_19_time_series/"
)

DATASETS = {
    "Confirmed Cases": "time_series_covid19_confirmed_global.csv",
    "Deaths": "time_series_covid19_deaths_global.csv"
}


@st.cache_data
def load_data(filename):
    raw = pd.read_csv(BASE_URL + filename)

    date_columns = list(raw.columns[4:])

    raw[date_columns] = (
        raw[date_columns]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    country_data = (
        raw.groupby("Country/Region")[date_columns]
        .sum()
        .reset_index()
    )

    df = country_data.melt(
        id_vars="Country/Region",
        var_name="Date",
        value_name="Cumulative"
    )

    df = df.rename(
        columns={"Country/Region": "Country"}
    )

    df["Date"] = pd.to_datetime(
        df["Date"], format="%m/%d/%y"
    )

    df = df.sort_values(
        ["Country", "Date"]
    ).reset_index(drop=True)

    df["Daily"] = (
        df.groupby("Country")["Cumulative"]
        .diff()
        .fillna(df["Cumulative"])
    )

    df["7-Day Average"] = (
        df.groupby("Country")["Daily"]
        .transform(
            lambda x: x.rolling(
                window=7, min_periods=1
            ).mean()
        )
    )

    return df


st.title("🌍 COVID-19 Global Dashboard")

st.markdown(
    "Explore and compare historical COVID-19 "
    "trends across countries using data from "
    "Johns Hopkins University CSSE."
)

st.info(
    "Historical dataset: January 22, 2020 "
    "to March 9, 2023. This dashboard "
    "does not display current COVID-19 data."
)

# Sidebar controls
st.sidebar.header("Dashboard Controls")

data_type = st.sidebar.radio(
    "Select Data Type",
    ["Confirmed Cases", "Deaths"]
)

try:
    df = load_data(DATASETS[data_type])
except Exception as error:
    st.error("Unable to load the COVID-19 dataset.")
    st.exception(error)
    st.stop()

countries = sorted(df["Country"].unique())

default_countries = [
    country for country in ["US", "India", "Brazil"]
    if country in countries
]

selected_countries = st.sidebar.multiselect(
    "Add or Remove Countries",
    options=countries,
    default=default_countries
)

count_type = st.sidebar.radio(
    "Display Mode",
    ["Daily", "Cumulative", "7-Day Average"]
)

chart_type = st.sidebar.selectbox(
    "Chart Type",
    ["Line Chart", "Bar Chart"]
)

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if not selected_countries:
    st.warning(
        "Please select at least one country "
        "from the sidebar."
    )
    st.stop()

if len(date_range) != 2:
    st.warning("Please select a start and end date.")
    st.stop()

start_date, end_date = date_range

filtered = df[
    (df["Country"].isin(selected_countries)) &
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("No data found for the selection.")
    st.stop()

st.subheader("Overview")

latest = (
    filtered.sort_values("Date")
    .groupby("Country")
    .tail(1)
)

total_count = int(latest["Cumulative"].sum())
latest_daily = int(latest["Daily"].sum())

col1, col2, col3 = st.columns(3)

col1.metric(
    "Selected Countries",
    len(selected_countries)
)

col2.metric(
    "Cumulative Total at End Date",
    f"{total_count:,}"
)

col3.metric(
    "Daily Change at End Date",
    f"{latest_daily:,}"
)

st.caption(
    "Totals are summed across selected countries. "
    "Daily changes may be negative due to "
    "historical reporting corrections."
)

st.subheader(f"{count_type} — {data_type}")

if chart_type == "Line Chart":
    fig = px.line(
        filtered,
        x="Date",
        y=count_type,
        color="Country",
        title=f"{count_type} {data_type} by Country"
    )
else:
    fig = px.bar(
        filtered,
        x="Date",
        y=count_type,
        color="Country",
        barmode="group",
        title=f"{count_type} {data_type} by Country"
    )

fig.update_layout(
    template="plotly_white",
    hovermode="x unified",
    height=520,
    xaxis_title="Date",
    yaxis_title=f"{count_type} {data_type}",
    legend_title="Country"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.subheader("Country Comparison")

comparison = latest[
    ["Country", "Cumulative", "Daily", "7-Day Average"]
].sort_values(
    "Cumulative", ascending=False
)

st.dataframe(
    comparison,
    use_container_width=True,
    hide_index=True
)

st.subheader("Download Data")

download_data = filtered[
    ["Country", "Date", "Cumulative",
     "Daily", "7-Day Average"]
].copy()

csv = download_data.to_csv(index=False)

st.download_button(
    label="Download Filtered CSV",
    data=csv,
    file_name="covid19_filtered_data.csv",
    mime="text/csv"
)

st.markdown("---")

st.markdown(
    "**Data Source:** "
    "[Johns Hopkins University CSSE COVID-19 "
    "Time Series](https://github.com/"
    "CSSEGISandData/COVID-19/tree/master/"
    "csse_covid_19_data/csse_covid_19_time_series)"
)

st.caption(
    "Daily counts are calculated as differences "
    "between consecutive cumulative reports. "
    "Negative corrections are retained. "
    "The 7-day average is calculated before "
    "applying the selected date filter."
)
