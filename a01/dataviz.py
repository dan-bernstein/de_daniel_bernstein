import pandas as pd

df = pd.read_json("zillow_june.json", lines=True)

print("Schema:")
print(df.dtypes)

df["date_period"] = pd.to_datetime(df["date_period"])

df_2002 = df[df["date_period"].dt.year == 2002]

most_expensive = df_2002.loc[df_2002["home_value"].idxmax()]

print("\nMost expensive in 2002:")
print(most_expensive)