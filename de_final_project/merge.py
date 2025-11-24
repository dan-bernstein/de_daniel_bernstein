import pandas as pd

df1 = pd.read_csv("Police_Data__Crime_Reports_20251109.csv")
df2 = pd.read_csv("somerville_crime_log.csv")

if "Incident Number" in df1.columns:
    df1.rename(columns={"Incident Number": "incident_number"}, inplace=True)
if "Case Number" in df2.columns:
    df2.rename(columns={"Case Number": "incident_number"}, inplace=True)

df1 = df1.drop_duplicates(subset=["incident_number"])
df2 = df2.drop_duplicates(subset=["incident_number"])

merged = pd.merge(df1, df2, on="incident_number", how="inner")

merged.to_csv("merged_incidents.csv", index=False)
merged.to_json("merged_incidents.json", orient="records", indent=2)

print(f"Merged {len(merged)} incidents successfully.")
print("Output files: merged_incidents.csv, merged_incidents.json")