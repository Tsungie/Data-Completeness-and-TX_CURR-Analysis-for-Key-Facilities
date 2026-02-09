import pandas as pd

# 1. Load the data files
# These paths match the CSV versions of the files you provided
df_master = pd.read_csv('uploads/Facility List and Reporting Sources.csv')
df_mrf = pd.read_csv('uploads/MRF-ONLY.xlsx')
df_datim = pd.read_csv('uploads/DATIM-ONLY.xlsx')

# 2. Define a standardization function
# This removes codes (e.g., 100429) and suffixes (e.g., Clinic) to help find matches
def standardize_name(name):
    if pd.isna(name): return ""
    name = str(name).lower()
    # Remove common suffixes that cause mismatches
    suffixes = ['clinic', 'rhc', 'rural health centre', 'hospital', 'mission', 'rural', 'centre', 'poly', 'health']
    for word in suffixes:
        name = name.replace(word, '')
    # Remove numerical facility codes and punctuation
    name = ''.join([i for i in name if not i.isdigit()])
    return " ".join(name.replace('-', ' ').replace('.', ' ').split())

# 3. Create cleaned matching keys
df_master['match_key'] = df_master['Facility Name'].apply(standardize_name)
df_master['match_prov'] = df_master['Province'].str.lower().str.replace(' metropolitan', '').str.strip()

df_mrf['match_key'] = df_mrf['Facility'].apply(standardize_name)
df_mrf['match_prov'] = df_mrf['Province'].str.lower().str.replace(' metropolitan', '').str.strip()

df_datim['match_key'] = df_datim['Facility'].apply(standardize_name)

# 4. Merge MRF TX_CURR
# We match on both Province and Name for the MRF data
df_mrf_clean = df_mrf[['match_prov', 'match_key', 'TX_CURR ']].drop_duplicates(subset=['match_prov', 'match_key'])
df_populated = pd.merge(
    df_master, 
    df_mrf_clean.rename(columns={'TX_CURR ': 'MRF_RESULT'}), 
    on=['match_prov', 'match_key'], 
    how='left'
)

# 5. Merge DATIM TX_CURR
# We match on Name for the DATIM data
df_datim_clean = df_datim[['match_key', 'TX_CURR ']].drop_duplicates(subset=['match_key'])
df_populated = pd.merge(
    df_populated,
    df_datim_clean.rename(columns={'TX_CURR ': 'DATIM_RESULT'}),
    on='match_key',
    how='left'
)

# 6. Map the results back to your specific columns
df_populated['MRF TX_CURR'] = df_populated['MRF_RESULT']
df_populated['DATIM TX_CURR'] = df_populated['DATIM_RESULT']

# 7. Final Clean up: Remove temporary match columns and export
df_final = df_populated.drop(columns=['match_key', 'match_prov', 'MRF_RESULT', 'DATIM_RESULT'])
df_final.to_csv('Populated_Facility_List.csv', index=False)

print(f"Successfully processed {len(df_final)} sites.")