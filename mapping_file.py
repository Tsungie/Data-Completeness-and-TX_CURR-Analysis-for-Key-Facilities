import pandas as pd
import re
from difflib import SequenceMatcher

# ---------------------------------------------------------
# 1. SETUP: File Paths & Loading
# ---------------------------------------------------------
file_facility_list = "uploads/Facility List and Reporting Sources.csv"
file_mapping = "uploads/MRF_DATIM_MAPPING_FILE.xlsx"
file_concordance = "uploads/Q4_MRF and DATIM Concordance Analysis.xlsx"

print("Loading files...")

# Load Facility List (CSV)
df_list = pd.read_csv(file_facility_list)

# Load Mapping File (Excel)
df_map = pd.read_excel(file_mapping, sheet_name=0) 

# Load DATIM TX_CURR (Excel)
try:
    df_datim = pd.read_excel(file_concordance, sheet_name='DATIM TXCURR')
except ValueError:
    print("Sheet 'DATIM TXCURR' not found. Checking available sheets...")
    xl = pd.ExcelFile(file_concordance)
    print(xl.sheet_names)
    raise

# Load MRF Aggregated Data (Excel)
try:
    df_mrf_raw = pd.read_excel(file_concordance, sheet_name='MRF Q4 Aggregated')
except ValueError:
    print("Sheet 'MRF Q4 Aggregated' not found.")
    raise

# Clean headers
df_list.columns = df_list.columns.str.strip()
df_map.columns = df_map.columns.str.strip()
df_datim.columns = df_datim.columns.str.strip()
df_mrf_raw.columns = df_mrf_raw.columns.str.strip()

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS: Cleaning & Normalization
# ---------------------------------------------------------
def simplify_name(name):
    if not isinstance(name, str): return ""
    name = name.lower()
    name = re.sub(r'-\s*\d+\s*-', '', name) 
    name = re.sub(r'\d+', '', name)
    tokens = ["clinic", "hospital", "mission", "centre", "poly", "rural", "health", 
              "council", "satellite", "rehabilitation", "infectious", "disease", 
              "provincial", "district", "general", "central", "primary", "care", 
              "family", "services", "unit", "post", "base"]
    for token in tokens: name = name.replace(token, "")
    name = re.sub(r'[^a-z\s]', '', name)
    name = " ".join(name.split())
    if "ubh" in name: return "ubh"
    return name

def get_id(name):
    if not isinstance(name, str): return None
    match = re.search(r'-\s*(\d{6})\s*-', name)
    if match: return match.group(1)
    return None

# Map Provinces
province_map = {
    'Bulawayo': 'Bulawayo Metropolitan',
    'Harare': 'Harare Metropolitan',
    'Mash. Central': 'Mashonaland Central',
    'Mash. East': 'Mashonaland East',
    'Mash. West': 'Mashonaland West',
    'Mat. North': 'Matabeleland North',
    'Mat. South': 'Matabeleland South',
    'Midlands': 'Midlands',
    'Manicaland': 'Manicaland',
    'Masvingo': 'Masvingo'
}
df_list['Std_Province'] = df_list['Province'].map(province_map).fillna(df_list['Province'])

# Apply normalization
df_list['Simple_Name'] = df_list['Facility Name'].apply(simplify_name)
df_list['ID'] = df_list['Facility Name'].apply(get_id)
df_map['Simple_Name'] = df_map['Facility'].apply(simplify_name)
df_datim['Simple_Name'] = df_datim['Facility'].apply(simplify_name)
df_datim['ID'] = df_datim['Facility'].apply(get_id)

# ---------------------------------------------------------
# 3. CORE LOGIC: Matching & Extraction
# ---------------------------------------------------------
print("Starting facility matching...")

mrf_tx_list = []
datim_tx_list = []
matched_map_name = []
matched_datim_name = []

for index, row in df_list.iterrows():
    # --- MRF MATCHING ---
    prov_subset = df_map[df_map['Province'] == row['Std_Province']]
    if prov_subset.empty: prov_subset = df_map 
    
    best_mrf_score = 0
    best_mrf_val = 0
    best_mrf_name = "None"
    target = row['Simple_Name']
    
    # UBH Logic
    if "united bulawayo" in row['Facility Name'].lower() or "ubh" in row['Facility Name'].lower():
        for idx, m_row in prov_subset.iterrows():
             if "unitedbulawayo" in m_row['Simple_Name'] or "ubh" == m_row['Simple_Name']:
                 best_mrf_score = 1.0
                 best_mrf_val = m_row['MRF TX_CURR']
                 best_mrf_name = m_row['Facility']
                 break

    # Fuzzy Logic
    if best_mrf_score < 1.0:
        for idx, m_row in prov_subset.iterrows():
            score = SequenceMatcher(None, target, m_row['Simple_Name']).ratio()
            if score > best_mrf_score:
                best_mrf_score = score
                best_mrf_val = m_row['MRF TX_CURR']
                best_mrf_name = m_row['Facility']
    
    if best_mrf_score > 0.65:
        mrf_tx_list.append(best_mrf_val)
        matched_map_name.append(best_mrf_name)
    else:
        mrf_tx_list.append(0) 
        matched_map_name.append("No Match")
        
    # --- DATIM MATCHING ---
    d_tx = None
    d_name = "None"
    
    if row['ID']:
        id_match = df_datim[df_datim['ID'] == row['ID']]
        if not id_match.empty:
            d_tx = id_match.iloc[0]['TX_CURR']
            d_name = id_match.iloc[0]['Facility']
    
    if d_tx is None:
        best_datim_score = 0
        if "united bulawayo" in row['Facility Name'].lower() or "ubh" in row['Facility Name'].lower():
             ubh_match = df_datim[df_datim['Facility'].str.lower().str.contains("ubh|united bulawayo")]
             if not ubh_match.empty:
                 d_tx = ubh_match.iloc[0]['TX_CURR']
                 d_name = ubh_match.iloc[0]['Facility']
                 best_datim_score = 1.0
        
        if best_datim_score < 1.0:
            for idx, d_row in df_datim.iterrows():
                score = SequenceMatcher(None, target, d_row['Simple_Name']).ratio()
                if score > best_datim_score:
                    best_datim_score = score
                    pot_tx = d_row['TX_CURR']
                    pot_name = d_row['Facility']
            
            if best_datim_score > 0.65:
                d_tx = pot_tx
                d_name = pot_name
    
    if d_tx is None: d_tx = 0
    datim_tx_list.append(d_tx)
    matched_datim_name.append(d_name)

df_list['MRF TX_CURR'] = mrf_tx_list
df_list['DATIM TX_CURR'] = datim_tx_list
df_list['Mapped_MRF_Name'] = matched_map_name
df_list['Mapped_DATIM_Name'] = matched_datim_name

# Clean up temp columns
df_list.drop(columns=['Simple_Name', 'ID', 'Std_Province'], inplace=True)

# ---------------------------------------------------------
# 4. SUMMARY & EXPORT
# ---------------------------------------------------------
# Calculate Sums
sum_mrf_204 = df_list['MRF TX_CURR'].sum()
sum_datim_204 = df_list['DATIM TX_CURR'].sum()

# Calculate National Totals from original files
total_mrf_national = df_mrf_raw['TX_CURR'].sum()
total_datim_national = df_datim['TX_CURR'].sum()

# Calculate Proportions
prop_mrf = (sum_mrf_204 / total_mrf_national * 100) if total_mrf_national else 0
prop_datim = (sum_datim_204 / total_datim_national * 100) if total_datim_national else 0

# Create Summary Rows
summary_rows = pd.DataFrame([
    {"Facility Name": ""}, # Spacer
    {"Facility Name": "--- SUMMARY ---"},
    {"Facility Name": "TOTAL (204 Sites)", "MRF TX_CURR": sum_mrf_204, "DATIM TX_CURR": sum_datim_204},
    {"Facility Name": "NATIONAL TOTAL", "MRF TX_CURR": total_mrf_national, "DATIM TX_CURR": total_datim_national},
    {"Facility Name": "PROPORTION (%)", "MRF TX_CURR": prop_mrf, "DATIM TX_CURR": prop_datim}
])

# Append Summary to Main DataFrame
df_final = pd.concat([df_list, summary_rows], ignore_index=True)

# Print to Console
print("-" * 30)
print(f"Total Facilities Processed: {len(df_list)}")
print(f"Total MRF TX_CURR (204 Sites): {sum_mrf_204:,.0f}")
print(f"National MRF TX_CURR: {total_mrf_national:,.0f}")
print(f"Contribution: {prop_mrf:.2f}%")
print("-" * 30)

# Save
output_filename = "Final_Mapped_Facility_List_With_Totals.csv"
df_final.to_csv(output_filename, index=False)
print(f"File saved successfully as: {output_filename}")