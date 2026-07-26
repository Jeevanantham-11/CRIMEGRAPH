"""
One-time patch: fixes CaseMaster.csv latitude/longitude to use proper
circular jitter (not the buggy square jitter from the original generator)
and a more realistic radius matching real Karnataka district extents.

Safe to run standalone -- no other table references lat/long, so this
does NOT require re-running entity resolution, network graph, MO
extraction, risk scoring, or anomaly detection afterward.
"""

import math
import random
import pandas as pd

DATA_DIR = "../synthetic_data"
random.seed(11)

DISTRICT_CENTROIDS = {
    "Bengaluru Urban": (12.97, 77.59), "Bengaluru Rural": (13.25, 77.55),
    "Mysuru": (12.30, 76.64), "Belagavi": (15.85, 74.50),
    "Kalaburagi": (17.33, 76.84), "Tumakuru": (13.34, 77.10),
    "Ballari": (15.14, 76.92), "Vijayapura": (16.83, 75.71),
    "Dharwad": (15.36, 75.12), "Dakshina Kannada": (12.87, 74.88),
    "Shivamogga": (13.93, 75.57), "Mandya": (12.52, 76.90),
    "Hassan": (13.00, 76.10), "Raichur": (16.20, 77.35),
    "Bidar": (17.91, 77.52), "Bagalkote": (16.18, 75.70),
    "Chitradurga": (14.23, 76.40), "Kolar": (13.14, 78.13),
    "Udupi": (13.34, 74.75), "Davanagere": (14.46, 75.92),
    "Chikkamagaluru": (13.32, 75.77), "Koppal": (15.35, 76.15),
    "Haveri": (14.79, 75.40), "Chamarajanagara": (11.92, 76.94),
    "Gadag": (15.43, 75.63), "Uttara Kannada": (14.80, 74.13),
    "Yadgir": (16.77, 77.14), "Kodagu": (12.42, 75.74),
    "Chikkaballapura": (13.43, 77.73), "Ramanagara": (12.72, 77.28),
    "Vijayanagara": (15.27, 76.39),
}


def circular_jitter(lat, lon, max_km=45):
    """Proper circular (not square) jitter: uniform angle + sqrt-scaled
    radius for uniform density across the disc area, not concentrated
    at the center or boxy at the edges."""
    angle = random.uniform(0, 2 * math.pi)
    radius_km = max_km * math.sqrt(random.random())
    deg_lat = (radius_km / 111.0) * math.cos(angle)
    deg_lon = (radius_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(angle)
    return round(lat + deg_lat, 6), round(lon + deg_lon, 6)


def main():
    cm = pd.read_csv(f"{DATA_DIR}/CaseMaster.csv")
    unit = pd.read_csv(f"{DATA_DIR}/Unit.csv")
    district = pd.read_csv(f"{DATA_DIR}/District.csv")

    station_to_district = dict(zip(unit["UnitID"], unit["DistrictID"]))
    district_id_to_name = dict(zip(district["DistrictID"], district["DistrictName"]))

    cm["DistrictID"] = cm["PoliceStationID"].map(station_to_district)
    cm["DistrictName"] = cm["DistrictID"].map(district_id_to_name)

    had_gps_before = cm["latitude"].notna()
    new_lat, new_lon = [], []
    for _, row in cm.iterrows():
        if not pd.notna(row["latitude"]):
            new_lat.append(None)
            new_lon.append(None)
            continue
        centroid = DISTRICT_CENTROIDS.get(row["DistrictName"], (14.5, 76.0))
        lat, lon = circular_jitter(*centroid, max_km=45)
        new_lat.append(lat)
        new_lon.append(lon)

    cm["latitude"] = new_lat
    cm["longitude"] = new_lon
    cm = cm.drop(columns=["DistrictID", "DistrictName"])

    cm.to_csv(f"{DATA_DIR}/CaseMaster.csv", index=False)
    print(f"Patched {had_gps_before.sum():,} case coordinates with proper circular jitter "
          f"(45km radius). {(~had_gps_before).sum():,} rows kept as missing GPS, unchanged.")
    print(f"Saved -> {DATA_DIR}/CaseMaster.csv")


if __name__ == "__main__":
    main()