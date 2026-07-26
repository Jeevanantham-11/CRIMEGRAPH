"""
Approximate lat/long centroids for Karnataka's 31 districts (district HQ town,
rounded). These are order-of-magnitude accurate — good enough for demo-level
hotspot mapping. For production use, replace with surveyed police-station
coordinates; the rest of the pipeline (hotspot/anomaly modules) is agnostic
to where the coordinates come from.
"""

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
