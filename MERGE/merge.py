import pandas as pd

# 1. Load your data
df = pd.read_excel('DATIM_Report_COP2025_Q1.xlsx')

# 2. Select columns and remove duplicates based on SiteName
# This keeps the first occurrence of each unique Site Name
unique_sites = df[['SiteProvince', 'SiteDistrict', 'SiteName']].drop_duplicates(subset=['SiteName'])

# 3. Sort them for a clean look (optional)
unique_sites = unique_sites.sort_values(by=['SiteProvince', 'SiteDistrict', 'SiteName'])

# 4. Save to a new Excel sheet
unique_sites.to_excel('Unique_Site_List.xlsx', index=False)