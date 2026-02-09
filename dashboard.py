import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Health Facility TX_CURR Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    </style>
    """, unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('uploads/MRF_Datim.csv')
    
    # Clean column names (remove extra spaces)
    df.columns = df.columns.str.strip()
    
    # Calculate variance between DATIM and MRF
    df['Variance'] = df['TX_CURR _mrf'] - df['TX_CURR _datim']
    df['Variance_Percent'] = ((df['TX_CURR _mrf'] - df['TX_CURR _datim']) / df['TX_CURR _datim'] * 100).round(2)
    
    # Add concordance category
    def categorize_concordance(row):
        if pd.isna(row['Variance_Percent']):
            return 'Missing Data'
        elif abs(row['Variance_Percent']) <= 5:
            return 'High Concordance (≤5%)'
        elif abs(row['Variance_Percent']) <= 10:
            return 'Moderate Concordance (5-10%)'
        else:
            return 'Low Concordance (>10%)'
    
    df['Concordance'] = df.apply(categorize_concordance, axis=1)
    
    return df

df = load_data()

# Title and description
st.title("🏥 Health Facility TX_CURR Dashboard")
st.markdown("### Comparing DATIM and MRF Treatment Current (TX_CURR) Data")
st.markdown("---")

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Province filter
provinces = ['All'] + sorted(df['Province'].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Select Province", provinces)

# District filter
if selected_province != 'All':
    districts = ['All'] + sorted(df[df['Province'] == selected_province]['District'].dropna().unique().tolist())
else:
    districts = ['All'] + sorted(df['District'].dropna().unique().tolist())
selected_district = st.sidebar.selectbox("Select District", districts)

# Source filter
sources = ['All'] + sorted(df['Source'].dropna().unique().tolist())
selected_source = st.sidebar.selectbox("Select Source", sources)

# Filter data
filtered_df = df.copy()
if selected_province != 'All':
    filtered_df = filtered_df[filtered_df['Province'] == selected_province]
if selected_district != 'All':
    filtered_df = filtered_df[filtered_df['District'] == selected_district]
if selected_source != 'All':
    filtered_df = filtered_df[filtered_df['Source'] == selected_source]

# Key Metrics
st.header("📊 Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_facilities = len(filtered_df)
    st.metric("Total Facilities", f"{total_facilities:,}")

with col2:
    total_datim = filtered_df['TX_CURR _datim'].sum()
    st.metric("Total TX_CURR (DATIM)", f"{int(total_datim):,}" if not pd.isna(total_datim) else "N/A")

with col3:
    total_mrf = filtered_df['TX_CURR _mrf'].sum()
    st.metric("Total TX_CURR (MRF)", f"{int(total_mrf):,}" if not pd.isna(total_mrf) else "N/A")

with col4:
    total_variance = filtered_df['Variance'].sum()
    st.metric("Total Variance", f"{int(total_variance):,}" if not pd.isna(total_variance) else "N/A")

with col5:
    avg_variance_pct = filtered_df['Variance_Percent'].mean()
    st.metric("Avg Variance %", f"{avg_variance_pct:.1f}%" if not pd.isna(avg_variance_pct) else "N/A")

st.markdown("---")

# Main visualizations
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🗺️ Geographic Analysis", "📊 Facility Details", "📉 Concordance Analysis"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        # DATIM vs MRF Comparison by Province
        st.subheader("TX_CURR by Province")
        province_data = filtered_df.groupby('Province')[['TX_CURR _datim', 'TX_CURR _mrf']].sum().reset_index()
        province_data = province_data.melt(id_vars='Province', var_name='Source', value_name='TX_CURR')
        province_data['Source'] = province_data['Source'].map({'TX_CURR _datim': 'DATIM', 'TX_CURR _mrf': 'MRF'})
        
        fig1 = px.bar(province_data, x='Province', y='TX_CURR', color='Source',
                     barmode='group', title="DATIM vs MRF by Province",
                     color_discrete_map={'DATIM': '#1f77b4', 'MRF': '#ff7f0e'})
        fig1.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Variance Distribution
        st.subheader("Variance Distribution")
        variance_data = filtered_df[filtered_df['Variance_Percent'].notna()]
        fig2 = px.histogram(variance_data, x='Variance_Percent', nbins=30,
                           title="Distribution of Variance Percentage",
                           labels={'Variance_Percent': 'Variance (%)', 'count': 'Number of Facilities'})
        fig2.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="0% Variance")
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Source Distribution
        st.subheader("Facilities by Source")
        source_counts = filtered_df['Source'].value_counts().reset_index()
        source_counts.columns = ['Source', 'Count']
        fig3 = px.pie(source_counts, values='Count', names='Source',
                     title="Distribution by Data Source",
                     color_discrete_sequence=px.colors.qualitative.Set3)
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # Concordance Categories
        st.subheader("Data Concordance")
        concordance_counts = filtered_df['Concordance'].value_counts().reset_index()
        concordance_counts.columns = ['Concordance', 'Count']
        fig4 = px.pie(concordance_counts, values='Count', names='Concordance',
                     title="Concordance Categories",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig4.update_layout(height=400)
        st.plotly_chart(fig4, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        # TX_CURR by District
        st.subheader("TX_CURR by District (Top 15)")
        district_data = filtered_df.groupby('District')[['TX_CURR _datim', 'TX_CURR _mrf']].sum().reset_index()
        district_data['Total'] = district_data['TX_CURR _datim'] + district_data['TX_CURR _mrf']
        district_data = district_data.nlargest(15, 'Total')
        
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(name='DATIM', x=district_data['District'], y=district_data['TX_CURR _datim'],
                             marker_color='#1f77b4'))
        fig5.add_trace(go.Bar(name='MRF', x=district_data['District'], y=district_data['TX_CURR _mrf'],
                             marker_color='#ff7f0e'))
        fig5.update_layout(barmode='stack', title="Top 15 Districts by TX_CURR",
                          xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig5, use_container_width=True)
    
    with col2:
        # Variance by District
        st.subheader("Average Variance by District")
        district_variance = filtered_df.groupby('District')['Variance_Percent'].mean().reset_index()
        district_variance = district_variance.sort_values('Variance_Percent', ascending=False).head(15)
        
        fig6 = px.bar(district_variance, x='Variance_Percent', y='District',
                     orientation='h', title="Top 15 Districts by Avg Variance %",
                     color='Variance_Percent', color_continuous_scale='RdYlGn_r')
        fig6.update_layout(height=500)
        st.plotly_chart(fig6, use_container_width=True)
    
    # Map visualization (placeholder - requires geocoding)
    st.subheader("Geographic Distribution")
    province_summary = filtered_df.groupby('Province').agg({
        'Facility Name': 'count',
        'TX_CURR _datim': 'sum',
        'TX_CURR _mrf': 'sum',
        'Variance': 'sum'
    }).reset_index()
    province_summary.columns = ['Province', 'Facilities', 'DATIM Total', 'MRF Total', 'Variance']
    
    st.dataframe(province_summary, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Facility-Level Data")
    
    # Search functionality
    search_term = st.text_input("🔍 Search for a facility", "")
    
    # Prepare display dataframe
    display_df = filtered_df[['Facility Name', 'Province', 'District', 'Source', 
                               'TX_CURR _datim', 'TX_CURR _mrf', 'Variance', 
                               'Variance_Percent', 'Concordance']].copy()
    
    if search_term:
        display_df = display_df[display_df['Facility Name'].str.contains(search_term, case=False, na=False)]
    
    # Sort options
    sort_by = st.selectbox("Sort by", ['Facility Name', 'Variance', 'Variance_Percent', 
                                        'TX_CURR _datim', 'TX_CURR _mrf'])
    sort_order = st.radio("Order", ['Ascending', 'Descending'], horizontal=True)
    
    display_df = display_df.sort_values(by=sort_by, ascending=(sort_order == 'Ascending'))
    
    # Display table
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    # Download button
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name="facility_data_filtered.csv",
        mime="text/csv"
    )
    
    # Scatter plot
    st.subheader("DATIM vs MRF Scatter Plot")
    scatter_df = filtered_df.dropna(subset=['TX_CURR _datim', 'TX_CURR _mrf'])
    fig7 = px.scatter(scatter_df, x='TX_CURR _datim', y='TX_CURR _mrf',
                     hover_data=['Facility Name', 'District', 'Province'],
                     color='Concordance',
                     title="DATIM vs MRF TX_CURR Comparison",
                     labels={'TX_CURR _datim': 'DATIM TX_CURR', 'TX_CURR _mrf': 'MRF TX_CURR'},
                     color_discrete_map={
                         'High Concordance (≤5%)': 'green',
                         'Moderate Concordance (5-10%)': 'orange',
                         'Low Concordance (>10%)': 'red',
                         'Missing Data': 'gray'
                     })
    
    # Add diagonal line (perfect agreement)
    max_val = max(scatter_df['TX_CURR _datim'].max(), scatter_df['TX_CURR _mrf'].max())
    fig7.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val],
                             mode='lines', name='Perfect Agreement',
                             line=dict(color='black', dash='dash')))
    
    fig7.update_layout(height=500)
    st.plotly_chart(fig7, use_container_width=True)

with tab4:
    st.subheader("Data Quality and Concordance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Concordance by Province
        st.markdown("#### Concordance by Province")
        concordance_province = pd.crosstab(filtered_df['Province'], 
                                          filtered_df['Concordance'], 
                                          normalize='index') * 100
        
        fig8 = px.bar(concordance_province, barmode='stack',
                     title="Concordance Distribution by Province",
                     labels={'value': 'Percentage (%)', 'Province': 'Province'},
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig8.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig8, use_container_width=True)
    
    with col2:
        # Facilities with highest variance
        st.markdown("#### Top 10 Facilities by Absolute Variance")
        top_variance = filtered_df.nlargest(10, 'Variance')[['Facility Name', 'District', 'Variance', 'Variance_Percent']]
        st.dataframe(top_variance, hide_index=True, use_container_width=True)
    
    # Missing data analysis
    st.subheader("Missing Data Analysis")
    col3, col4 = st.columns(2)
    
    with col3:
        missing_stats = pd.DataFrame({
            'Field': ['TX_CURR DATIM', 'TX_CURR MRF', 'MRF Province', 'MRF District', 'MRF Facility'],
            'Missing Count': [
                filtered_df['TX_CURR _datim'].isna().sum(),
                filtered_df['TX_CURR _mrf'].isna().sum(),
                filtered_df['MRF_Province'].isna().sum(),
                filtered_df['MRF_District'].isna().sum(),
                filtered_df['MRF_Facility'].isna().sum()
            ]
        })
        missing_stats['Percentage'] = (missing_stats['Missing Count'] / len(filtered_df) * 100).round(2)
        
        st.dataframe(missing_stats, hide_index=True, use_container_width=True)
    
    with col4:
        fig9 = px.bar(missing_stats, x='Field', y='Percentage',
                     title="Missing Data by Field",
                     labels={'Percentage': 'Missing Data (%)'},
                     color='Percentage', color_continuous_scale='Reds')
        fig9.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig9, use_container_width=True)
    
    # Statistical Summary
    st.subheader("Statistical Summary")
    summary_stats = filtered_df[['TX_CURR _datim', 'TX_CURR _mrf', 'Variance', 'Variance_Percent']].describe()
    st.dataframe(summary_stats, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Health Facility TX_CURR Dashboard | Data Source: MRF-DATIM Comparison</p>
    </div>
    """, unsafe_allow_html=True)