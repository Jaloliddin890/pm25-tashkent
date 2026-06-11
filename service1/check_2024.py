import pandas as pd
import numpy as np

df = pd.read_csv('data/tashkent_pm25_weather.csv', parse_dates=['datetime'])

# Timezone normalize
if df['datetime'].dt.tz is None:
    df['datetime'] = df['datetime'].dt.tz_localize('UTC')
df = df.sort_values('datetime').reset_index(drop=True)

# source ustunini saqlash
source_col = df.set_index('datetime')['source']
df2 = df.drop(columns=['source'])

# Resample
df2 = df2.set_index('datetime')
df2 = df2.resample('h').mean()

# source qaytarish
source_col = source_col[~source_col.index.duplicated(keep='first')]
source_col = source_col.reindex(df2.index, fill_value='cams')
df2['source'] = source_col.values

# ffill
df2 = df2.ffill(limit=3)
df2 = df2.dropna(subset=['pm25'])
df2 = df2.reset_index()

# 2024 tekshiruv
mask = (df2['datetime'] >= '2024-01-01') & (df2['datetime'] <= '2024-08-01')
sub = df2[mask].copy()
sub['month'] = sub['datetime'].dt.month
months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug']

print("=== CLEAN dan keyin (feature engineering DAN OLDIN) ===")
for m, g in sub.groupby('month'):
    null_cols = g.isnull().sum()
    null_cols = null_cols[null_cols > 0]
    print(f"  {months[m]}: {len(g)} qator, pm25_null={g['pm25'].isna().sum()}")
    if len(null_cols) > 0:
        print(f"    Null ustunlar: {null_cols.to_dict()}")
