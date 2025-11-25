import pandas as pd
import geopandas as gpd
from pathlib import Path

INCIDENTS_CSV = "/Users/danielbernstein/de_daniel_bernstein/de_final_project/merged_incidents.csv"
SHAPEFILE_PATH = "tl_2024_25_tabblock20/tl_2024_25_tabblock20.shp"
OUTPUT_CSV = "incidents_with_latlon.csv"
BLOCK_COLUMN = "Block Code"

def detect_geoid_field(gdf):
    """Return the column name in the block shapefile dataframe that looks like GEOID (case-insensitive)."""
    for col in gdf.columns:
        if "geoid" in col.lower():
            return col
    raise KeyError("No GEOID field found in shapefile. Columns: " + ", ".join(gdf.columns))

def normalize_geoid(s):
    """Normalize various representations to a clean string GEOID (no decimals, no spaces)."""
    if pd.isna(s):
        return ""
    s = str(s).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = s.replace(" ", "")
    return s

def main():
    shp = Path(SHAPEFILE_PATH)
    csvf = Path(INCIDENTS_CSV)
    assert csvf.exists(), f"Input CSV not found: {INCIDENTS_CSV}"
    assert shp.exists(), f"Shapefile not found: {SHAPEFILE_PATH}"

    print("Loading incidents CSV:", INCIDENTS_CSV)
    df = pd.read_csv(INCIDENTS_CSV, dtype=str)

    if BLOCK_COLUMN not in df.columns:
        print(f"Warning: '{BLOCK_COLUMN}' not found in CSV columns. Available columns: {df.columns.tolist()}")
        candidates = [c for c in df.columns if "block" in c.lower() or "geoid" in c.lower() or "tract" in c.lower()]
        if candidates:
            print("Auto-detected block-like column:", candidates[0])
            df.rename(columns={candidates[0]: BLOCK_COLUMN}, inplace=True)
        else:
            raise KeyError(f"Could not find block code column. Please set BLOCK_COLUMN to the correct column name in the script.")

    df[BLOCK_COLUMN] = df[BLOCK_COLUMN].apply(normalize_geoid)
    print("Unique block codes in CSV:", df[BLOCK_COLUMN].nunique())

    print("Loading block shapefile:", SHAPEFILE_PATH)
    gdf = gpd.read_file(SHAPEFILE_PATH)

    geoid_field = detect_geoid_field(gdf)  # e.g. 'GEOID20'
    print("Detected GEOID field in shapefile:", geoid_field)

    gdf[geoid_field] = gdf[geoid_field].astype(str).apply(normalize_geoid)

    print("Computing centroids and reprojecting to EPSG:4326 (lat/lon)...")
    try:
        gdf_cent = gdf[[geoid_field, "geometry"]].copy()
    except KeyError:
        gdf_cent = gdf.copy()[["geometry"]]
        gdf_cent[geoid_field] = gdf[geoid_field]

    gdf_cent["centroid"] = gdf_cent.geometry.centroid
    gdf_cent = gdf_cent.set_geometry("centroid")
    gdf_cent = gdf_cent.to_crs(epsg=4326)
    gdf_cent["latitude"] = gdf_cent.geometry.y
    gdf_cent["longitude"] = gdf_cent.geometry.x

    lookup = gdf_cent[[geoid_field, "latitude", "longitude"]].drop_duplicates(subset=[geoid_field])
    lookup = lookup.set_index(geoid_field)

    print("Merging lat/lon into incidents table...")
    df["latitude"] = df[BLOCK_COLUMN].map(lambda x: lookup.at[x, "latitude"] if x in lookup.index else None)
    df["longitude"] = df[BLOCK_COLUMN].map(lambda x: lookup.at[x, "longitude"] if x in lookup.index else None)

    missing = df[df["latitude"].isnull() | df["longitude"].isnull()]
    print(f"Total records: {len(df)}. Matched: {len(df) - len(missing)}. Unmatched: {len(missing)}")
    if len(missing) > 0:
        print("Examples of unmatched block codes (up to 10):")
        print(missing[BLOCK_COLUMN].unique()[:10])

    print("Saving to:", OUTPUT_CSV)
    df.to_csv(OUTPUT_CSV, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
