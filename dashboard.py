import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Health Facility TX_CURR Dashboard",
    page_icon="🇿🇼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 0px 24px;
        background-color: white;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        color: #31333F;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3498db !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    # Ensure this path matches your actual file location
    try:
        df = pd.read_csv('uploads/MRF_Datim.csv', encoding='utf-8-sig')
    except FileNotFoundError:
        st.error("File not found. Please check the file path 'uploads/MRF_Datim.csv'.")
        return pd.DataFrame()
        
    # Clean column names
    df.columns = df.columns.str.strip()
    
    # Calculate difference between MRF and DATIM
    df['Difference'] = df['TX_CURR _mrf'] - df['TX_CURR _datim']
    # Calculate % difference
    df['Difference_Percent'] = ((df['TX_CURR _mrf'] - df['TX_CURR _datim']) / df['TX_CURR _datim'] * 100).round(1)
    
    # Calculate absolute difference percent for concordance logic
    df['Abs_Difference_Percent'] = abs(df['Difference_Percent'])
    
    # Add concordance category
    def categorize_concordance(row):
        # If DATIM is 0 or null, can't calculate concordance
        if pd.isna(row['TX_CURR _datim']) or row['TX_CURR _datim'] == 0:
            return 'No DATIM Data'
        elif pd.isna(row['Difference_Percent']):
            return 'No DATIM Data'
        elif abs(row['Difference_Percent']) <= 5:
            return 'High Concordance (≤5%)'
        elif abs(row['Difference_Percent']) <= 10:
            return 'Moderate Concordance (5-10%)'
        else:
            return 'Low Concordance (>10%)'
    
    df['Concordance_Level'] = df.apply(categorize_concordance, axis=1)
    
    return df

df = load_data()

if df.empty:
    st.stop()

# Header
st.title("🇿🇼 TX_CURR Dashboard")
st.markdown("### Comparing DATIM and MRF Treatment Current (TX_CURR) Data")
st.markdown("---")

# Sidebar filters
st.sidebar.header("🔍 Filter Data")

# Province filter
provinces = ['All Provinces'] + sorted(df['Province'].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Select Province", provinces)

# District filter
if selected_province != 'All Provinces':
    districts = ['All Districts'] + sorted(df[df['Province'] == selected_province]['District'].dropna().unique().tolist())
else:
    districts = ['All Districts'] + sorted(df['District'].dropna().unique().tolist())
selected_district = st.sidebar.selectbox("Select District", districts)

# Source filter
sources = ['All Sources'] + sorted(df['Source'].dropna().unique().tolist())
selected_source = st.sidebar.selectbox("Select Source", sources)

# Apply filters
filtered_df = df.copy()
if selected_province != 'All Provinces':
    filtered_df = filtered_df[filtered_df['Province'] == selected_province]
if selected_district != 'All Districts':
    filtered_df = filtered_df[filtered_df['District'] == selected_district]
if selected_source != 'All Sources':
    filtered_df = filtered_df[filtered_df['Source'] == selected_source]

# Key Metrics
st.header("📊 Summary")
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_facilities = len(filtered_df)
    st.metric("Total Health Facilities", f"{total_facilities:,}")

with col2:
    total_datim = filtered_df['TX_CURR _datim'].sum()
    st.metric("DATIM Patient Count", f"{int(total_datim):,}" if not pd.isna(total_datim) else "N/A")

with col3:
    total_mrf = filtered_df['TX_CURR _mrf'].sum()
    st.metric("MRF Patient Count", f"{int(total_mrf):,}" if not pd.isna(total_mrf) else "N/A")

with col4:
    total_diff = filtered_df['Difference'].sum()
    st.metric("Total Difference", f"{int(total_diff):,}" if not pd.isna(total_diff) else "N/A")

st.markdown("---")

# Main tabs
tab1, tab2, tab3 = st.tabs(["📊 Overview", "📋 Facility List", "🎯 Performance Analysis"])

with tab1:
    st.subheader("Data Comparison Overview")
    
    # 1. Side-by-side bars by Province
    st.markdown("#### TX_CURR by Province")
    
    province_data = filtered_df.groupby('Province')[['TX_CURR _datim', 'TX_CURR _mrf']].sum().reset_index()
    province_data = province_data.sort_values('TX_CURR _datim', ascending=False)
    
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        name='DATIM',
        x=province_data['Province'],
        y=province_data['TX_CURR _datim'],
        marker_color='#3498db',
        text=province_data['TX_CURR _datim'].apply(lambda x: f'{int(x):,}'),
        textposition='outside'
    ))
    fig1.add_trace(go.Bar(
        name='MRF',
        x=province_data['Province'],
        y=province_data['TX_CURR _mrf'],
        marker_color='#e67e22',
        text=province_data['TX_CURR _mrf'].apply(lambda x: f'{int(x):,}'),
        textposition='outside'
    ))
    
    fig1.update_layout(
        barmode='group',
        height=450,
        xaxis_title="Province",
        yaxis_title="Number of Patients on Treatment",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        font=dict(size=12)
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    st.markdown("---")
    
    # 2. Concordance and Source distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Concordance Between Data Sources")
        st.markdown("*How closely do the numbers align?*")
        
        concordance_counts = filtered_df['Concordance_Level'].value_counts().reset_index()
        concordance_counts.columns = ['Category', 'Number of Facilities']
        
        # Define order for consistency
        order = ['High Concordance (≤5%)', 'Moderate Concordance (5-10%)', 'Low Concordance (>10%)', 'No DATIM Data']
        concordance_counts['Category'] = pd.Categorical(concordance_counts['Category'], categories=order, ordered=True)
        concordance_counts = concordance_counts.sort_values('Category')
        
        fig2 = px.pie(
            concordance_counts,
            values='Number of Facilities',
            names='Category',
            color='Category',
            color_discrete_map={
                'High Concordance (≤5%)': '#2ecc71',
                'Moderate Concordance (5-10%)': '#f39c12',
                'Low Concordance (>10%)': '#e74c3c',
                'No DATIM Data': '#95a5a6'
            },
            hole=0.4
        )
        
        # --- UPDATE: Show Value and Percent in the chart ---
        fig2.update_traces(
            textposition='inside', 
            textinfo='value+percent',  # Changed to show Number + %
            hovertemplate = "<b>%{label}</b><br>Facilities: %{value}<br>Percentage: %{percent}"
        )
        # ---------------------------------------------------
        
        fig2.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig2, use_container_width=True)
        
        # Add explanation
        st.info("**Concordance** measures how close DATIM and MRF numbers are:\n\n"
                "🟢 **High**: Difference is 5% or less\n\n"
                "🟠 **Moderate**: Difference is 5-10%\n\n"
                "🔴 **Low**: Difference is more than 10%\n\n"
                "⚪ **Not Applicable**: DATIM reported zero")
    
    
    with col2:
        st.markdown("#### Facilities by Data Source")
        
        source_counts = filtered_df['Source'].value_counts().reset_index()
        source_counts.columns = ['Source', 'Count']
        
        fig3 = px.pie(
            source_counts,
            values='Count',
            names='Source',
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.4
        )
        fig3.update_traces(textposition='inside', textinfo='percent+label')
        fig3.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig3, use_container_width=True)
    
    st.markdown("---")
    
    # 3. Top 10 districts
    st.markdown("#### Top 10 Districts by Patient Count")
    
    district_data = filtered_df.groupby('District')[['TX_CURR _datim', 'TX_CURR _mrf']].sum().reset_index()
    district_data['Total'] = district_data['TX_CURR _datim'] + district_data['TX_CURR _mrf']
    district_data = district_data.nlargest(10, 'Total').sort_values('Total', ascending=True)
    
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        name='DATIM',
        y=district_data['District'],
        x=district_data['TX_CURR _datim'],
        orientation='h',
        marker_color='#3498db',
        text=district_data['TX_CURR _datim'].apply(lambda x: f'{int(x):,}'),
        textposition='inside'
    ))
    fig4.add_trace(go.Bar(
        name='MRF',
        y=district_data['District'],
        x=district_data['TX_CURR _mrf'],
        orientation='h',
        marker_color='#e67e22',
        text=district_data['TX_CURR _mrf'].apply(lambda x: f'{int(x):,}'),
        textposition='inside'
    ))
    
    fig4.update_layout(
        barmode='stack',
        height=450,
        xaxis_title="Total Patients",
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig4, use_container_width=True)

with tab2:
    st.subheader("Complete Facility List")
    st.markdown("*Search, sort, and export facility data*")
    
    # Search box
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 Search for a facility by name", "", key="search").strip()
    with col2:
        st.write("")  # Spacer
        show_all = st.checkbox("Show all columns", value=False)
    
    # Prepare display dataframe
    if show_all:
        display_df = filtered_df[['Facility Name', 'Province', 'District', 'Source', 
                                   'TX_CURR _datim', 'TX_CURR _mrf', 'Difference', 
                                   'Difference_Percent', 'Concordance_Level']].copy()
    else:
        display_df = filtered_df[['Facility Name', 'Province', 'District', 
                                   'TX_CURR _datim', 'TX_CURR _mrf', 'Difference',
                                   'Concordance_Level']].copy()
    
    # --- FIXED: Robust Search ---
    if search_term:
        mask = display_df['Facility Name'].astype(str).str.contains(search_term, case=False, na=False)
        display_df = display_df[mask]
    
    # Sort options
    col1, col2 = st.columns([2, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by", 
            ['Facility Name', 'TX_CURR _datim', 'TX_CURR _mrf', 'Difference'],
            key="sort_select"
        )
    with col2:
        sort_order = st.radio("Order", ['Highest first', 'Lowest first'], horizontal=True, key="sort_order")
    
    # --- FIXED: Sort Logic ---
    is_ascending = (sort_order == 'Lowest first')
    display_df = display_df.sort_values(by=sort_by, ascending=is_ascending)
    
    # --- FIXED: Dynamic Key to prevent Stuck Table ---
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=450,
        key=f"fac_table_{sort_by}_{sort_order}_{len(display_df)}",
        column_config={
            "Facility Name": st.column_config.TextColumn("Facility", width="medium"),
            "Province": st.column_config.TextColumn("Province", width="small"),
            "District": st.column_config.TextColumn("District", width="small"),
            "TX_CURR _datim": st.column_config.NumberColumn("DATIM Count", format="%d"),
            "TX_CURR _mrf": st.column_config.NumberColumn("MRF Count", format="%d"),
            "Difference": st.column_config.NumberColumn("Difference", format="%d"),
            "Concordance_Level": st.column_config.TextColumn("Concordance", width="medium")
        }
    )
    
    # Download button
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download this data as CSV",
        data=csv,
        file_name=f"facility_data_{selected_province}_{selected_district}.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("Performance Analysis")
    
    # Not applicable section
    not_applicable_df = filtered_df[filtered_df['Concordance_Level'] == 'No DATIM Data']
    if len(not_applicable_df) > 0:
        with st.expander(f"ℹ️ Facilities Not Providing HIV Treatment ({len(not_applicable_df)} facilities)", expanded=False):
            st.markdown("*These facilities reported zero in DATIM*")
            na_display = not_applicable_df[['Facility Name', 'Province', 'District', 'TX_CURR _datim', 'TX_CURR _mrf']].copy()
            st.dataframe(na_display, hide_index=True, use_container_width=True, height=300)
            
            csv_na = na_display.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download list of non-HIV facilities", data=csv_na, file_name="facilities_non_hiv.csv", mime="text/csv")
        st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🌟 Top 10 Facilities with High Concordance")
        high_concordance = filtered_df[filtered_df['Abs_Difference_Percent'].notna()].copy()
        high_concordance = high_concordance.nsmallest(10, 'Abs_Difference_Percent')
        
        high_display = high_concordance[['Facility Name', 'District', 'TX_CURR _datim', 'TX_CURR _mrf', 'Difference_Percent']].copy()
        high_display.columns = ['Facility', 'District', 'DATIM', 'MRF', 'Diff %']
        
        st.dataframe(
            high_display, hide_index=True, use_container_width=True,
            column_config={"Diff %": st.column_config.NumberColumn("Diff %", format="%.1f%%")}
        )
        
        fig_high = go.Figure()
        fig_high.add_trace(go.Bar(
            x=high_concordance['Facility Name'],
            y=high_concordance['Abs_Difference_Percent'],
            marker_color='#2ecc71',
            text=high_concordance['Abs_Difference_Percent'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside'
        ))
        fig_high.update_layout(title="Difference Percentage (Lower is Better)", height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig_high, use_container_width=True)
    
    with col2:
        st.markdown("#### ⚠️ Top 10 Facilities with Low Concordance")
        low_concordance = filtered_df[filtered_df['Abs_Difference_Percent'].notna()].copy()
        low_concordance = low_concordance.nlargest(10, 'Abs_Difference_Percent')
        
        low_display = low_concordance[['Facility Name', 'District', 'TX_CURR _datim', 'TX_CURR _mrf', 'Difference_Percent']].copy()
        low_display.columns = ['Facility', 'District', 'DATIM', 'MRF', 'Diff %']
        
        st.dataframe(
            low_display, hide_index=True, use_container_width=True,
            column_config={"Diff %": st.column_config.NumberColumn("Diff %", format="%.1f%%")}
        )
        
        fig_low = go.Figure()
        fig_low.add_trace(go.Bar(
            x=low_concordance['Facility Name'],
            y=low_concordance['Abs_Difference_Percent'],
            marker_color='#e74c3c',
            text=low_concordance['Abs_Difference_Percent'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside'
        ))
        fig_low.update_layout(title="Difference Percentage (Needs Review)", height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig_low, use_container_width=True)
    
    st.markdown("---")
    
    # Concordance by Province Chart
    concordance_province = pd.crosstab(filtered_df['Province'], filtered_df['Concordance_Level'])
    concordance_province_pct = concordance_province.div(concordance_province.sum(axis=1), axis=0) * 100
    
    fig5 = go.Figure()
    for category in ['High Concordance (≤5%)', 'Moderate Concordance (5-10%)', 'Low Concordance (>10%)', 'No DATIM Data']:
        if category in concordance_province_pct.columns:
            fig5.add_trace(go.Bar(
                name=category,
                x=concordance_province_pct.index,
                y=concordance_province_pct[category],
                marker_color={'High Concordance (≤5%)': '#2ecc71', 'Moderate Concordance (5-10%)': '#f39c12',
                              'Low Concordance (>10%)': '#e74c3c', 'No DATIM Data': '#95a5a6'}[category]
            ))
    fig5.update_layout(barmode='stack', height=400, xaxis_title="Province", yaxis_title="Percentage (%)")
    st.plotly_chart(fig5, use_container_width=True)
    
    st.markdown("---")
    
    # Scatter plot
    scatter_df = filtered_df.dropna(subset=['TX_CURR _datim', 'TX_CURR _mrf'])
    fig6 = px.scatter(
        scatter_df, x='TX_CURR _datim', y='TX_CURR _mrf', color='Concordance_Level',
        hover_data=['Facility Name', 'District', 'Difference_Percent'],
        color_discrete_map={'High Concordance (≤5%)': '#2ecc71', 'Moderate Concordance (5-10%)': '#f39c12',
                            'Low Concordance (>10%)': '#e74c3c', 'No DATIM Data': '#95a5a6'},
        height=500
    )
    max_val = max(scatter_df['TX_CURR _datim'].max(), scatter_df['TX_CURR _mrf'].max())
    fig6.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val], mode='lines', name='Perfect', line=dict(color='gray', dash='dash')))
    st.plotly_chart(fig6, use_container_width=True)
    
    st.markdown("---")
    
    # Summary Statistics
    st.markdown("#### Summary Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        summary_stats = filtered_df[['TX_CURR _datim', 'TX_CURR _mrf', 'Difference']].describe().round(0)
        st.dataframe(summary_stats, use_container_width=True)
    
    with col2:
        # --- UPDATE: Better Metrics Display ---
        st.markdown("**Concordance Summary**")
        
        # Filter out No DATIM Data for percentage calculation to be meaningful
        valid_data = filtered_df[filtered_df['Concordance_Level'] != 'No DATIM Data']
        total_valid = len(valid_data)
        
        if total_valid > 0:
            high = len(valid_data[valid_data['Concordance_Level'] == 'High Concordance (≤5%)'])
            mod = len(valid_data[valid_data['Concordance_Level'] == 'Moderate Concordance (5-10%)'])
            low = len(valid_data[valid_data['Concordance_Level'] == 'Low Concordance (>10%)'])
            
            # Using columns for better layout
            m1, m2, m3 = st.columns(3)
            
            with m1:
                st.metric(
                    label="High (≤5%)", 
                    value=f"{high}",
                    delta=f"{high/total_valid*100:.1f}%",
                    delta_color="normal" # Green
                )
            with m2:
                st.metric(
                    label="Moderate (5-10%)", 
                    value=f"{mod}",
                    delta=f"{mod/total_valid*100:.1f}%",
                    delta_color="off" # Grey/Neutral
                )
            with m3:
                st.metric(
                    label="Low (>10%)", 
                    value=f"{low}",
                    delta=f"-{low/total_valid*100:.1f}%", # Negative sign makes it red
                    delta_color="inverse" # Red
                )
        else:
            st.info("No data available")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>Health Facility TX_CURR Dashboard</div>", unsafe_allow_html=True)