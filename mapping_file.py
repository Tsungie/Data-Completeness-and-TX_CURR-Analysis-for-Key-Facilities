import pandas as pd
import re
from difflib import SequenceMatcher

# ---------------------------------------------------------
# 1. SETUP: Load Data
# ---------------------------------------------------------
file_facility_list = "uploads/Facility List and Reporting Sources.csv"
file_mapping = "uploads/MRF_DATIM_MAPPING_FILE.xlsx"
file_concordance = "uploads/Q4_MRF and DATIM Concordance Analysis.xlsx"

print("Loading files...")

df_list = pd.read_csv(file_facility_list)
df_map = pd.read_excel(file_mapping, sheet_name=0) 

try:
    df_datim = pd.read_excel(file_concordance, sheet_name='DATIM TXCURR')
    df_mrf_raw = pd.read_excel(file_concordance, sheet_name='MRF Q4 Aggregated')
except ValueError:
    print("Error loading specific sheets. Check file structure.")
    raise

# Clean headers
df_list.columns = df_list.columns.str.strip()
df_map.columns = df_map.columns.str.strip()
df_datim.columns = df_datim.columns.str.strip()
df_mrf_raw.columns = df_mrf_raw.columns.str.strip()

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------
def simplify_name(name):
    if not isinstance(name, str): return ""
    name = name.lower()
    # Remove common words to improve fuzzy match
    tokens = ["clinic", "hospital", "mission", "centre", "poly", "rural", "health", 
              "council", "satellite", "rehabilitation", "infectious", "disease", 
              "provincial", "district", "general", "central", "primary", "care", 
              "family", "services", "unit", "post", "base"]
    for token in tokens: name = name.replace(token, "")
    # Remove non-alphanumeric (except spaces)
    name = re.sub(r'[^a-z\s]', '', name)
    name = " ".join(name.split())
    if "ubh" in name: return "ubh"
    return name

def get_id(name):
    # Extracts 6-digit ID (e.g. - 101278 -)
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

# Normalization & ID Extraction
df_list['Simple_Name'] = df_list['Facility Name'].apply(simplify_name)
df_list['ID'] = df_list['Facility Name'].apply(get_id)

df_map['Simple_Name'] = df_map['Facility'].apply(simplify_name)
# Try to get ID from map facility name just in case
df_map['ID'] = df_map['Facility'].apply(get_id)

df_datim['Simple_Name'] = df_datim['Facility'].apply(simplify_name)
df_datim['ID'] = df_datim['Facility'].apply(get_id)

# ---------------------------------------------------------
# 3. CORE LOGIC: Matching
# ---------------------------------------------------------
print("Starting facility matching...")

mrf_tx_list = []
datim_tx_list = []
matched_map_name = []
matched_datim_name = []
potential_matches_list = [] # For verification

for index, row in df_list.iterrows():
    target_id = row['ID']
    target_name = row['Simple_Name']
    
    # --- A. MRF MATCHING ---
    # 1. Filter by Province first (Strict)
    prov_subset = df_map[df_map['Province'] == row['Std_Province']]
    if prov_subset.empty: prov_subset = df_map 
    
    match_found = False
    best_match_tuple = (0, "No Match", 0) # (Score, Name, TX_CURR)
    candidates = []
    
    # 2. Try ID Match (Priority 1)
    if target_id:
        id_match = prov_subset[prov_subset['ID'] == target_id]
        if not id_match.empty:
            best_match_tuple = (1.0, id_match.iloc[0]['Facility'], id_match.iloc[0]['MRF TX_CURR'])
            match_found = True
            candidates.append((1.0, f"ID MATCH: {best_match_tuple[1]}", best_match_tuple[2]))

    # 3. If no ID match, try Name Match
    if not match_found:
        # Calculate scores for ALL in province to populate candidates list
        for idx, m_row in prov_subset.iterrows():
            score = SequenceMatcher(None, target_name, m_row['Simple_Name']).ratio()
            
            # Special Override for UBH
            if "united bulawayo" in row['Facility Name'].lower() or "ubh" in row['Facility Name'].lower():
                 if "united bulawayo" in m_row['Facility'].lower() or "ubh" == m_row['Facility'].lower():
                     score = 1.0

            candidates.append((score, m_row['Facility'], m_row['MRF TX_CURR']))
        
        # Sort candidates
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_3 = candidates[:3]
        
        # Pick best if score is good enough
        if top_3 and top_3[0][0] > 0.65:
             best_match_tuple = top_3[0]
    
    # Store MRF Result
    mrf_tx_list.append(best_match_tuple[2])
    matched_map_name.append(best_match_tuple[1])
    # Create verification string
    verify_str = " | ".join([f"{c[1]} ({c[0]*100:.0f}%)" for c in candidates[:3]])
    potential_matches_list.append(verify_str)

    # --- B. DATIM MATCHING ---
    d_tx = 0
    d_name = "No Match"
    
    # 1. ID Match (Priority 1)
    if target_id:
        id_match = df_datim[df_datim['ID'] == target_id]
        if not id_match.empty:
            d_tx = id_match.iloc[0]['TX_CURR']
            d_name = id_match.iloc[0]['Facility']
    
    # 2. Fuzzy Match (Only if ID failed)
    if d_name == "No Match":
        best_d_score = 0
        for idx, d_row in df_datim.iterrows():
            score = SequenceMatcher(None, target_name, d_row['Simple_Name']).ratio()
            if score > best_d_score:
                best_d_score = score
                pot_tx = d_row['TX_CURR']
                pot_name = d_row['Facility']
        
        if best_d_score > 0.65:
            d_tx = pot_tx
            d_name = pot_name

    datim_tx_list.append(d_tx)
    matched_datim_name.append(d_name)

# ---------------------------------------------------------
# 4. OUTPUT
# ---------------------------------------------------------
df_list['Matched_MRF_Name'] = matched_map_name
df_list['MRF_Candidates (Verify Here)'] = potential_matches_list
df_list['MRF TX_CURR'] = mrf_tx_list
df_list['Matched_DATIM_Name'] = matched_datim_name
df_list['DATIM TX_CURR'] = datim_tx_list

# Clean up
df_list.drop(columns=['Simple_Name', 'ID', 'Std_Province'], inplace=True)

# Summary Calculation
sum_mrf_204 = df_list['MRF TX_CURR'].sum()
sum_datim_204 = df_list['DATIM TX_CURR'].sum()
total_mrf_national = df_mrf_raw['TX_CURR'].sum()
total_datim_national = df_datim['TX_CURR'].sum()
prop_mrf = (sum_mrf_204 / total_mrf_national * 100) if total_mrf_national else 0
prop_datim = (sum_datim_204 / total_datim_national * 100) if total_datim_national else 0

# Append Summary
summary_rows = pd.DataFrame([
    {"Facility Name": ""}, 
    {"Facility Name": "--- SUMMARY ---"},
    {"Facility Name": "TOTAL (204 Sites)", "MRF TX_CURR": sum_mrf_204, "DATIM TX_CURR": sum_datim_204},
    {"Facility Name": "NATIONAL TOTAL", "MRF TX_CURR": total_mrf_national, "DATIM TX_CURR": total_datim_national},
    {"Facility Name": "PROPORTION (%)", "MRF TX_CURR": prop_mrf, "DATIM TX_CURR": prop_datim}
])
df_final = pd.concat([df_list, summary_rows], ignore_index=True)

# Save
output_filename = "Final_Mapped_List_With_Candidates.csv"
df_final.to_csv(output_filename, index=False)
print(f"File saved as: {output_filename}")
print("Please check the 'MRF_Candidates (Verify Here)' column to ensure correct mapping.")