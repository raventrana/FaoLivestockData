import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set page configuration
st.set_page_config(page_title="FAO Livestock & Crop Production Dashboard", layout="wide")

# --- DATA LOADING (with caching so it stays fast) ---
# NEW CODE (Correct Path)
GITHUB_USERNAME = "raventrana"
REPO_NAME = "FaoLivestockData"
FILE_PATH = "Production_Crops_Livestock_E_All_Data.csv.gz"
CSV_URL = f"https://raw.githubusercontent.com/ { GITHUB_USERNAME } / { REPO_NAME } /main/ { FILE_PATH } "

@st.cache_data
def load_and_clean_data(url):
    # Load dataset
    # NEW CODE
df = pd.read_csv(url, compression='gzip', low_memory=False)
    
    # Identify year columns (Y1961 - Y2024)
    year_cols = [col for col in df.columns if col.startswith('Y') and col[1:].isdigit() and len(col) == 5]
    
    # Clean types and fill missing values with 0
    for col in year_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    # Standardize string codes
    df['Area Code (M49)'] = df['Area Code (M49)'].astype(str).str.replace("'", "", regex=False)
    df['Item Code (CPC)'] = df['Item Code (CPC)'].astype(str).str.replace("'", "", regex=False)
    
    # Rename columns for programmatic friendliness
    df = df.rename(columns={
        'Area': 'Area_Name', 'Item': 'Item_Name', 
        'Element': 'Element_Name', 'Unit': 'Unit_Name'
    })
    return df, year_cols

# Load data
try:
    df, year_columns = load_and_clean_data(CSV_URL)
except Exception as e:
    st.error(f"Failed to load dataset from GitHub. Verify your URL. Error: {e}")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Dashboard Controls")

# Filter by Element Type (Production, Yield, etc.)
element_types = df['Element_Name'].unique().tolist()
selected_element = st.sidebar.selectbox("Select Metric Type", element_types, index=element_types.index('Production') if 'Production' in element_types else 0)

# Filter by Geographic Area
unique_areas = sorted(df['Area_Name'].unique().tolist())
selected_area = st.sidebar.selectbox("Select Country / Region", unique_areas, index=unique_areas.index('World') if 'World' in unique_areas else 0)

# Filter data based on choices before grabbing unique items
filtered_by_area_element = df[(df['Area_Name'] == selected_area) & (df['Element_Name'] == selected_element)]

# Multi-select for items (Defaulting to top 3 items available)
available_items = sorted(filtered_by_area_element['Item_Name'].unique().tolist())
default_items = filtered_by_area_element['Item_Name'].value_counts().head(3).index.tolist()
selected_items = st.sidebar.multiselect("Select Items to Compare", available_items, default=default_items)

# --- MAIN DASHBOARD LAYOUT ---
st.title("🌾 FAO Global Livestock & Crop Production Analytics")
st.markdown(f"Exploring **{selected_element}** trends for **{selected_area}** (1961–2024)")

if not selected_items:
    st.warning("Please select at least one item from the sidebar to visualize.")
    st.stop()

# Final dataset filtering based on item selection
final_df = filtered_by_area_element[filtered_by_area_element['Item_Name'].isin(selected_items)]

# --- TRANSFORM DATA FOR VISUALIZATION ---
melted_df = final_df.melt(id_vars=['Item_Name', 'Unit_Name'], value_vars=year_columns, var_name='Year', value_name='Value')
melted_df['Year'] = melted_df['Year'].str[1:].astype(int)
aggregated_df = melted_df.groupby(['Item_Name', 'Year', 'Unit_Name'])['Value'].sum().reset_index()

# Layout Split into two columns for metrics and time series
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("Key Takeaways")
    total_items = len(selected_items)
    unit_used = aggregated_df['Unit_Name'].iloc[0] if not aggregated_df.empty else "units"
    st.metric(label="Items Compared", value=total_items)
    st.caption(f"Reporting Unit: **{unit_used}**")

with col2:
    # Plot 1: Time Series Trend
    st.subheader("Historical Timeline (1961 - 2024)")
    fig1, ax1 = plt.subplots(figsize=(12, 5.5))
    sns.lineplot(x='Year', y='Value', hue='Item_Name', data=aggregated_df, marker='o', palette='tab10', ax=ax1)
    ax1.set_ylabel(f"Volume ({unit_used})")
    ax1.grid(True, linestyle='--', alpha=0.5)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
    st.pyplot(fig1)

st.write("---")

# Row 2: Correlation Matrix & Data Preview
col3, col4 = st.columns(2)

with col3:
    st.subheader("Item Correlation Matrix")
    if len(selected_items) > 1:
        pivot_df = aggregated_df.pivot(index='Year', columns='Item_Name', values='Value')
        corr_matrix = pivot_df.corr()
        
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5, ax=ax2)
        st.pyplot(fig2)
    else:
        st.info("Select multiple items in the sidebar to view cross-item correlations.")

with col4:
    st.subheader("Raw Data Preview")
    st.dataframe(aggregated_df.sort_values(by='Year', ascending=False), use_container_width=True, height=350)
