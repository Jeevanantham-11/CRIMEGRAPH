"""
CrimeGraph — Synthetic Data Configuration
==========================================
All reference values here are chosen to mirror REAL Karnataka administrative
and NCRB crime-classification structures, so that this generator can later be
swapped for a real KSP data feed without changing the schema or downstream code.

Scale note: real Karnataka records ~2 lakh+ IPC cases/year statewide. For a
demo-able dataset we scale down proportionally (SCALE_FACTOR) while preserving
relative district/crime-type distributions. Bump SCALE_FACTOR up for a
"production realism" run if your machine/Catalyst plan can handle it.
"""

import random

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

YEARS = [2023, 2024, 2025]          # 3 years of FIR history
SCALE_FACTOR = 0.06                  # fraction of real-world case volume to simulate
BASE_ANNUAL_CASES_STATEWIDE = 220_000  # approx real NCRB order-of-magnitude for Karnataka IPC crimes/yr

# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------
STATE = {"StateID": 1, "StateName": "Karnataka", "NationalityID": 1, "Active": 1}

# ---------------------------------------------------------------------------
# DISTRICTS — all 31 real Karnataka districts with approximate relative
# population weight (used to proportionally allocate stations & case volume).
# Weights are illustrative order-of-magnitude, not census-exact.
# ---------------------------------------------------------------------------
DISTRICTS = [
    ("Bengaluru Urban", 24.0), ("Bengaluru Rural", 2.5), ("Mysuru", 7.5),
    ("Belagavi", 12.0), ("Kalaburagi", 6.2), ("Tumakuru", 6.8),
    ("Ballari", 5.5), ("Vijayapura", 4.8), ("Dharwad", 4.5),
    ("Dakshina Kannada", 5.3), ("Shivamogga", 4.5), ("Mandya", 4.6),
    ("Hassan", 4.5), ("Raichur", 4.2), ("Bidar", 3.9),
    ("Bagalkote", 4.4), ("Chitradurga", 4.2), ("Kolar", 3.9),
    ("Udupi", 3.6), ("Davanagere", 5.0), ("Chikkamagaluru", 3.2),
    ("Koppal", 3.5), ("Haveri", 4.1), ("Chamarajanagara", 3.0),
    ("Gadag", 2.5), ("Uttara Kannada", 3.8), ("Yadgir", 3.0),
    ("Kodagu", 1.4), ("Chikkaballapura", 3.4), ("Ramanagara", 2.6),
    ("Vijayanagara", 3.5),
]
assert len(DISTRICTS) == 31

# ---------------------------------------------------------------------------
# UNIT TYPES (hierarchy: lower Hierarchy int = higher authority)
# ---------------------------------------------------------------------------
UNIT_TYPES = [
    (1, "State Police Headquarters", "State", 1),
    (2, "Range/Zone Office", "State", 2),
    (3, "District SP Office", "District", 3),
    (4, "Sub-Division / Circle Office", "District", 4),
    (5, "Police Station", "City", 5),
    (6, "Outpost", "City", 6),
]

# ---------------------------------------------------------------------------
# RANKS (real KSP hierarchy, lower Hierarchy = senior)
# ---------------------------------------------------------------------------
RANKS = [
    (1, "Director General of Police", 1),
    (2, "Inspector General of Police", 2),
    (3, "Deputy Inspector General of Police", 3),
    (4, "Superintendent of Police", 4),
    (5, "Deputy Superintendent of Police", 5),
    (6, "Inspector of Police", 6),
    (7, "Sub-Inspector of Police", 7),
    (8, "Assistant Sub-Inspector", 8),
    (9, "Head Constable", 9),
    (10, "Police Constable", 10),
]

DESIGNATIONS = [
    (1, "Station House Officer", 1),
    (2, "Investigating Officer", 2),
    (3, "Circle Inspector", 3),
    (4, "Beat Constable", 4),
    (5, "Women & Child Desk Officer", 5),
    (6, "Cyber Crime Desk Officer", 6),
]

# ---------------------------------------------------------------------------
# CASE CATEGORY (matches CrimeNo 1-digit category code exactly)
# ---------------------------------------------------------------------------
CASE_CATEGORY = [
    (1, "FIR"),
    (3, "UDR"),
    (8, "Zero FIR"),
    (4, "PAR"),
]

GRAVITY_OFFENCE = [
    (1, "Heinous"),
    (2, "Non-Heinous"),
]

CASE_STATUS = [
    (1, "Under Investigation"),
    (2, "Charge Sheeted"),
    (3, "Closed - Undetected"),
    (4, "Closed - False Case"),
    (5, "Pending Trial"),
    (6, "Convicted"),
    (7, "Acquitted"),
]

OCCUPATIONS = [
    "Farmer", "Government Employee", "Private Employee", "Daily Wage Labourer",
    "Business/Self-Employed", "Student", "Homemaker", "Unemployed", "Driver",
    "Retired", "Not Disclosed",
]

RELIGIONS = ["Hindu", "Muslim", "Christian", "Jain", "Sikh", "Buddhist", "Not Disclosed"]

# Official Indian administrative social-category classifications (used for
# statutory reporting, not for model features — see fairness notes in README).
CASTE_CATEGORIES = ["General", "OBC", "SC", "ST", "Not Disclosed"]

# ---------------------------------------------------------------------------
# CRIME HEAD / SUB-HEAD taxonomy — mirrors real NCRB IPC/BNS grouping
# ---------------------------------------------------------------------------
CRIME_TAXONOMY = {
    "Crimes Against Body": [
        "Murder", "Attempt to Murder", "Culpable Homicide Not Amounting to Murder",
        "Grievous Hurt", "Simple Hurt", "Kidnapping & Abduction",
    ],
    "Crimes Against Women": [
        "Rape", "Assault on Women (Outrage Modesty)", "Cruelty by Husband/Relatives",
        "Dowry Death", "Insult to Modesty of Women",
    ],
    "Crimes Against Property": [
        "Theft", "Auto Theft", "Burglary", "Robbery", "Dacoity", "Criminal Breach of Trust",
    ],
    "Economic Offences": [
        "Cheating", "Counterfeiting", "Cyber Fraud", "Criminal Breach of Trust (Financial)",
    ],
    "Crimes Against Public Order": [
        "Riots", "Arson", "Unlawful Assembly",
    ],
    "Special & Local Laws": [
        "NDPS Offence", "Arms Act Offence", "POCSO Offence", "Excise Act Offence",
    ],
}

# ---------------------------------------------------------------------------
# ACTS & SECTIONS — real acts; BNS 2023 included alongside legacy IPC since
# India is mid-transition and any real feed will contain a mix of both.
# ---------------------------------------------------------------------------
ACTS = [
    ("IPC", "Indian Penal Code, 1860", "IPC"),
    ("BNS", "Bharatiya Nyaya Sanhita, 2023", "BNS"),
    ("NDPS", "Narcotic Drugs and Psychotropic Substances Act, 1985", "NDPS"),
    ("ARMS", "Arms Act, 1959", "Arms Act"),
    ("POCSO", "Protection of Children from Sexual Offences Act, 2012", "POCSO"),
]

# (ActCode, SectionCode, Description, mapped CrimeSubHead name)
SECTIONS = [
    ("IPC", "302", "Murder", "Murder"),
    ("BNS", "103", "Murder", "Murder"),
    ("IPC", "307", "Attempt to Murder", "Attempt to Murder"),
    ("BNS", "109", "Attempt to Murder", "Attempt to Murder"),
    ("IPC", "304", "Culpable Homicide Not Amounting to Murder", "Culpable Homicide Not Amounting to Murder"),
    ("IPC", "323", "Simple Hurt", "Simple Hurt"),
    ("IPC", "326", "Grievous Hurt (Dangerous Weapon)", "Grievous Hurt"),
    ("IPC", "363", "Kidnapping", "Kidnapping & Abduction"),
    ("IPC", "376", "Rape", "Rape"),
    ("BNS", "64", "Rape", "Rape"),
    ("IPC", "354", "Assault on Woman - Outrage Modesty", "Assault on Women (Outrage Modesty)"),
    ("IPC", "498A", "Cruelty by Husband or Relatives", "Cruelty by Husband/Relatives"),
    ("IPC", "304B", "Dowry Death", "Dowry Death"),
    ("IPC", "379", "Theft", "Theft"),
    ("IPC", "379A", "Auto Theft", "Auto Theft"),
    ("IPC", "380", "Burglary", "Burglary"),
    ("IPC", "392", "Robbery", "Robbery"),
    ("IPC", "395", "Dacoity", "Dacoity"),
    ("IPC", "406", "Criminal Breach of Trust", "Criminal Breach of Trust"),
    ("IPC", "420", "Cheating", "Cheating"),
    ("IPC", "489A", "Counterfeiting Currency", "Counterfeiting"),
    ("IPC", "66D-ITACT", "Cyber Fraud (IT Act r/w IPC 420)", "Cyber Fraud"),
    ("IPC", "147", "Riot", "Riots"),
    ("IPC", "436", "Arson", "Arson"),
    ("IPC", "144", "Unlawful Assembly", "Unlawful Assembly"),
    ("NDPS", "20", "Possession/Sale of Narcotics", "NDPS Offence"),
    ("ARMS", "25", "Illegal Possession of Arms", "Arms Act Offence"),
    ("POCSO", "4", "Penetrative Sexual Assault on Child", "POCSO Offence"),
    ("ARMS", "27", "Use of Arms in Commission of Offence", "Arms Act Offence"),
]

COURTS_PER_DISTRICT = ["District & Sessions Court", "JMFC Court", "Fast Track Special Court"]
