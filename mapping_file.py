import pandas as pd
import re
from difflib import SequenceMatcher

# ---------------------------------------------------------
# 1. SETUP: Load Data
# ---------------------------------------------------------
file_source_list = "uploads/corrected _Mapped_facility_verify_here_column.csv"
file_mapping = "uploads/MRF_DATIM_MAPPING_FILE.xlsx"
file_concordance = "uploads/Q4_MRF and DATIM Concordance Analysis.xlsx"

print("Loading files...")

# Load List
df_list = pd.read_csv(file_source_list)

# Load Reference Files
try:
    df_map_bank = pd.read_excel(file_mapping, sheet_name=0) 
    df_datim_bank = pd.read_excel(file_concordance, sheet_name='DATIM TXCURR')
    df_mrf_bank_agg = pd.read_excel(file_concordance, sheet_name='MRF Q4 Aggregated')
except ValueError:
    print("Error loading Excel sheets. Check file structure.")
    raise

# Clean headers
df_list.columns = df_list.columns.str.strip()
df_map_bank.columns = df_map_bank.columns.str.strip()
df_datim_bank.columns = df_datim_bank.columns.str.strip()
df_mrf_bank_agg.columns = df_mrf_bank_agg.columns.str.strip()

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------
def simplify_name(name):
    if not isinstance(name, str): return ""
    name = name.lower()
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

def extract_verified_name(candidate_str):
    if not isinstance(candidate_str, str): return None
    clean = candidate_str.split('|')[0]
    clean = clean.replace("[ID MATCH]", "")
    clean = re.sub(r'\(\d+%?\)', '', clean) 
    return clean.strip()

# Standardize Provinces
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
if 'Province' in df_list.columns:
    df_list['Std_Province'] = df_list['Province'].map(province_map).fillna(df_list['Province'])

# Pre-processing
df_datim_bank['Simple_Name'] = df_datim_bank['Facility'].apply(simplify_name)
df_datim_bank['ID'] = df_datim_bank['Facility'].apply(get_id)

# ---------------------------------------------------------
# 3. CORE LOGIC: Lookup
# ---------------------------------------------------------
print("Starting verified lookup...")

mrf_values = []
datim_values = []

# Filter out summary rows
df_list = df_list[~df_list['Facility Name'].astype(str).str.contains("SUMMARY|TOTAL|PROPORTION", case=False, na=False)]

for index, row in df_list.iterrows():
    # --- A. GET MRF VALUE ---
    verified_str = row.get('MRF_Candidates (Verify Here)', '')
    target_name = extract_verified_name(verified_str)
    
    mrf_val = 0
    
    if target_name:
        prov_subset = df_map_bank[df_map_bank['Province'] == row['Std_Province']]
        if prov_subset.empty: prov_subset = df_map_bank
        
        # Exact Match on Verified Name
        match = prov_subset[prov_subset['Facility'].str.strip().str.lower() == target_name.lower()]
        
        if not match.empty:
            mrf_val = match.iloc[0]['MRF TX_CURR']
        else:
            # Fuzzy Fallback
            best_score = 0
            for idx, m_row in prov_subset.iterrows():
                score = SequenceMatcher(None, simplify_name(target_name), simplify_name(str(m_row['Facility']))).ratio()
                if score > best_score:
                    best_score = score
                    if score > 0.90: 
                        mrf_val = m_row['MRF TX_CURR']
    
    mrf_values.append(mrf_val)

    # --- B. GET DATIM VALUE ---
    list_name = str(row['Facility Name'])
    list_id = get_id(list_name)
    list_simple = simplify_name(list_name)
    
    datim_val = 0
    
    if list_id:
        id_match = df_datim_bank[df_datim_bank['ID'] == list_id]
        if not id_match.empty:
            datim_val = id_match.iloc[0]['TX_CURR']
            
    if datim_val == 0:
        best_d = 0
        for idx, d_row in df_datim_bank.iterrows():
            score = SequenceMatcher(None, list_simple, d_row['Simple_Name']).ratio()
            if "united bulawayo" in list_name.lower() or "ubh" in list_name.lower():
                if "ubh" in d_row['Simple_Name'] or "united bulawayo" in d_row['Simple_Name']:
                    score = 1.0
            if score > best_d:
                best_d = score
                if score > 0.65:
                    datim_val = d_row['TX_CURR']

    datim_values.append(datim_val)

# ---------------------------------------------------------
# 4. EXPORT
# ---------------------------------------------------------
# FIX: Convert lists to Series first to allow fillna
df_list['MRF TX_CURR'] = pd.to_numeric(pd.Series(mrf_values), errors='coerce').fillna(0).astype(int)
df_list['DATIM TX_CURR'] = pd.to_numeric(pd.Series(datim_values), errors='coerce').fillna(0).astype(int)

# Cleanup
cols_to_drop = ['Std_Province', 'Lookup_Status']
df_list.drop(columns=[c for c in cols_to_drop if c in df_list.columns], inplace=True)

# Summaries
sum_mrf = df_list['MRF TX_CURR'].sum()
sum_datim = df_list['DATIM TX_CURR'].sum()
nat_mrf = int(df_mrf_bank_agg['TX_CURR'].sum())
nat_datim = int(df_datim_bank['TX_CURR'].sum())

summary_rows = pd.DataFrame([
    {"Facility Name": ""},
    {"Facility Name": "--- SUMMARY ---"},
    {"Facility Name": "TOTAL (Verified Sites)", "MRF TX_CURR": sum_mrf, "DATIM TX_CURR": sum_datim},
    {"Facility Name": "NATIONAL TOTAL", "MRF TX_CURR": nat_mrf, "DATIM TX_CURR": nat_datim},
    {"Facility Name": "PROPORTION (%)", "MRF TX_CURR": round(sum_mrf/nat_mrf*100, 2) if nat_mrf else 0, "DATIM TX_CURR": round(sum_datim/nat_datim*100, 2) if nat_datim else 0}
])

df_final = pd.concat([df_list, summary_rows], ignore_index=True)
output_filename = "Final_Verified_Facility_List.csv"
df_final.to_csv(output_filename, index=False)

print("-" * 30)
print(f"File saved as: {output_filename}")
print(f"Total MRF (Verified): {sum_mrf:,.0f}")
print(f"Proportion: {sum_mrf/nat_mrf*100:.2f}%")
print("-" * 30)