"""
Generates CaseMaster + all child transactional tables:
  ComplainantDetails, ActSectionAssociation, Victim, Accused,
  ArrestSurrender, ChargesheetDetails

Also produces `entity_resolution_ground_truth.csv` — NOT part of the official
ER schema, but the labeled truth of which Accused rows belong to the same
real person. This is what lets us report real precision/recall numbers for
the entity-resolution module instead of just describing the method.

Case outcome (ChargesheetDetails.cstype) is driven by a REAL, injected,
learnable relationship (crime-type base solvability + reporting delay +
whether an arrest was made + noise) rather than an arbitrary status
lookup — this is what gives the predictive risk-scoring model genuine
signal to learn instead of noise. See SUBHEAD_BASE_SOLVE_PROB below.
"""

import random
from datetime import datetime, timedelta
from faker import Faker

import config as cfg
from geo_centroids import DISTRICT_CENTROIDS
from name_variants import generate_name_variant, maybe_age_drift
from crimeno_utils import encode_crime_no, encode_case_no

fake = Faker("en_IN")

HEINOUS_SUBHEADS = {
    "Murder", "Attempt to Murder", "Rape", "Dacoity", "Dowry Death",
    "Kidnapping & Abduction", "POCSO Offence",
}

# Relative frequency weights per sub-head (property/economic crime dominate
# real crime statistics; heinous crimes are comparatively rare) — mirrors
# real NCRB proportions at an order-of-magnitude level.
SUBHEAD_WEIGHTS = {
    "Murder": 1, "Attempt to Murder": 2, "Culpable Homicide Not Amounting to Murder": 1,
    "Grievous Hurt": 6, "Simple Hurt": 12, "Kidnapping & Abduction": 3,
    "Rape": 2, "Assault on Women (Outrage Modesty)": 5, "Cruelty by Husband/Relatives": 6,
    "Dowry Death": 1, "Insult to Modesty of Women": 3,
    "Theft": 20, "Auto Theft": 8, "Burglary": 10, "Robbery": 5, "Dacoity": 1,
    "Criminal Breach of Trust": 4,
    "Cheating": 10, "Counterfeiting": 1, "Cyber Fraud": 9, "Criminal Breach of Trust (Financial)": 2,
    "Riots": 3, "Arson": 2, "Unlawful Assembly": 3,
    "NDPS Offence": 3, "Arms Act Offence": 2, "POCSO Offence": 2, "Excise Act Offence": 2,
}

# MO signature phrases, grouped by crime category so narratives stay coherent
# (a burglary MO should never show up describing a rape case). Reused
# verbatim in BriefFacts whenever a matching person/category appears, so the
# text-mining MO-extraction module has a genuine, consistent pattern to find.
MO_PHRASE_CATEGORIES = {
    "property": [
        "The accused gained entry through a rear window left unlatched.",
        "The accused targeted unattended shops during the late-night hours.",
        "The accused used a duplicate key/lock-picking method to gain entry.",
        "The accused used a rented vehicle with tampered number plates to transport stolen goods.",
        "The accused worked in a group of two, one keeping watch while the other broke in.",
    ],
    "violent_person": [
        "The accused used a two-wheeler to approach and flee the scene rapidly.",
        "The accused wore a helmet throughout to avoid CCTV identification.",
        "The accused was known to the victim through a prior personal dispute.",
        "The accused waylaid the victim along a known secluded route.",
    ],
    "women_children": [
        "The accused approached the victim through a fake social media profile.",
        "The accused was a person known to the victim's family.",
        "The accused lured the victim on the pretext of a job offer.",
    ],
    "cyber_economic": [
        "The accused posed as a bank/delivery representative to gain the victim's trust.",
        "The accused used a spoofed phone number to contact the victim.",
        "The accused operated using a fraudulent online payment link.",
    ],
    "public_order": [
        "The accused operated in daylight hours near crowded public spaces.",
        "The accused acted as part of an organized group during the incident.",
    ],
    "narcotics_arms": [
        "The accused was found in possession of the contraband during a routine check.",
        "The accused used a concealed compartment in the vehicle to transport the contraband.",
    ],
}

SUBHEAD_TO_MO_CATEGORY = {
    "Theft": "property", "Auto Theft": "property", "Burglary": "property",
    "Robbery": "property", "Dacoity": "property", "Criminal Breach of Trust": "property",
    "Murder": "violent_person", "Attempt to Murder": "violent_person",
    "Culpable Homicide Not Amounting to Murder": "violent_person",
    "Grievous Hurt": "violent_person", "Simple Hurt": "violent_person",
    "Kidnapping & Abduction": "violent_person",
    "Rape": "women_children", "Assault on Women (Outrage Modesty)": "women_children",
    "Cruelty by Husband/Relatives": "women_children", "Dowry Death": "women_children",
    "Insult to Modesty of Women": "women_children", "POCSO Offence": "women_children",
    "Cheating": "cyber_economic", "Counterfeiting": "cyber_economic",
    "Cyber Fraud": "cyber_economic", "Criminal Breach of Trust (Financial)": "cyber_economic",
    "Riots": "public_order", "Arson": "public_order", "Unlawful Assembly": "public_order",
    "NDPS Offence": "narcotics_arms", "Arms Act Offence": "narcotics_arms",
    "Excise Act Offence": "narcotics_arms",
}


def mo_category_for_subhead(subhead_name: str) -> str:
    return SUBHEAD_TO_MO_CATEGORY.get(subhead_name, "property")


# Base "solved" (chargesheet) probability per crime sub-head, reflecting real
# investigative reality: crimes with a known/identifiable offender (domestic,
# personal-dispute violence) or caught-in-the-act patterns (NDPS, arms) solve
# far more often than anonymous property/cyber crime. Combined at generation
# time with reporting delay and arrest status (see build_transactional_data),
# this is what gives the predictive risk-scoring model genuine, honest signal
# to learn instead of noise.
SUBHEAD_BASE_SOLVE_PROB = {
    "Murder": 0.72, "Attempt to Murder": 0.62, "Culpable Homicide Not Amounting to Murder": 0.68,
    "Grievous Hurt": 0.65, "Simple Hurt": 0.72, "Kidnapping & Abduction": 0.55,
    "Rape": 0.68, "Assault on Women (Outrage Modesty)": 0.60, "Cruelty by Husband/Relatives": 0.80,
    "Dowry Death": 0.70, "Insult to Modesty of Women": 0.58,
    "Theft": 0.28, "Auto Theft": 0.25, "Burglary": 0.32, "Robbery": 0.42, "Dacoity": 0.48,
    "Criminal Breach of Trust": 0.45,
    "Cheating": 0.32, "Counterfeiting": 0.38, "Cyber Fraud": 0.18, "Criminal Breach of Trust (Financial)": 0.40,
    "Riots": 0.55, "Arson": 0.42, "Unlawful Assembly": 0.58,
    "NDPS Offence": 0.78, "Arms Act Offence": 0.75, "POCSO Offence": 0.62, "Excise Act Offence": 0.72,
}

CASE_FINALIZATION_DAYS = 90  # cases younger than this (relative to dataset snapshot)
                              # are still "Under Investigation" with no chargesheet yet —
                              # mirrors real investigation timelines, not a label shortcut


class SerialCounter:
    def __init__(self):
        self._counters = {}

    def next(self, station_id, category_id, year):
        key = (station_id, category_id, year)
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]


def weighted_choice(weight_dict):
    items = list(weight_dict.items())
    return random.choices([k for k, _ in items], weights=[w for _, w in items])[0]


def jitter_coord(lat, lon, km=8):
    # ~0.01 deg ~ 1.1km; jitter within station's district roughly
    deg = km / 111.0
    return round(lat + random.uniform(-deg, deg), 6), round(lon + random.uniform(-deg, deg), 6)


def build_repeat_offender_pool(n_persons: int, district_ids: list):
    """Ground-truth pool of real 'people' who will be re-used across multiple
    Accused rows with name-variant/age-drift noise applied at insertion time.
    Each person has a 'home' district; reuse is biased toward it (see
    HOME_DISTRICT_BIAS below) so cross-jurisdiction offending is a realistic
    minority pattern worth discovering, not near-universal noise."""
    pool = []
    for i in range(n_persons):
        gender = random.choices(["M", "F"], weights=[85, 15])[0]
        name = fake.name_male() if gender == "M" else fake.name_female()
        specialty = random.choice(list(MO_PHRASE_CATEGORIES.keys()))
        pool.append({
            "person_master_id": i + 1,
            "canonical_name": name,
            "gender": gender,
            "birth_year": random.randint(1965, 2006),
            "home_district_id": random.choice(district_ids),
            "mo_category": specialty,
            "mo_phrase": random.choice(MO_PHRASE_CATEGORIES[specialty]),
        })
    return pool


HOME_DISTRICT_BIAS = 0.82  # probability a repeat offender's reuse happens in their home district


def build_transactional_data(ref: dict, years=cfg.YEARS, scale_factor=cfg.SCALE_FACTOR):
    districts = ref["District"]
    stations_by_district = ref["_stations_by_district"]
    employees = ref["Employee"]
    courts = ref["Court"]
    section_to_subhead = ref["_section_to_subhead"]
    subhead_name_to_id = ref["_subhead_name_to_id"]
    subhead_id_to_head = {s["CrimeSubHeadID"]: s["CrimeHeadID"] for s in ref["CrimeSubHead"]}

    emp_by_station = {}
    for e in employees:
        emp_by_station.setdefault(e["UnitID"], []).append(e["EmployeeID"])

    courts_by_district = {}
    for c in courts:
        courts_by_district.setdefault(c["DistrictID"], []).append(c["CourtID"])

    # sections available per act, grouped by (act, section) -> subhead name
    act_section_list = list(section_to_subhead.keys())  # [(ActCode, SectionCode), ...]

    total_weight = sum(w for _, w in cfg.DISTRICTS)
    annual_total = cfg.BASE_ANNUAL_CASES_STATEWIDE * scale_factor

    # Ground truth repeat-offender pool sized ~ a few thousand recurring persons
    all_district_ids = [d["DistrictID"] for d in districts]
    repeat_pool = build_repeat_offender_pool(n_persons=1800, district_ids=all_district_ids)
    repeat_pool_by_district = {}
    for p in repeat_pool:
        repeat_pool_by_district.setdefault(p["home_district_id"], []).append(p)
    # Track which cases/accused-rows each repeat person has been used in (for ground truth export)
    person_usage_log = []  # rows: person_master_id, AccusedMasterID, CaseMasterID

    case_master, complainants, act_section_assoc = [], [], []
    victims, accused_rows, arrest_surrender, chargesheets = [], [], [], []

    case_id = 1
    complainant_id = 1
    victim_id = 1
    accused_id = 1
    arrest_id = 1
    cs_id = 1
    serial = SerialCounter()
    snapshot_date = datetime(years[-1], 12, 31)  # dataset "as-of" date

    for d in districts:
        d_id = d["DistrictID"]
        stations = stations_by_district[d_id]
        centroid = DISTRICT_CENTROIDS.get(d["DistrictName"], (14.5, 76.0))
        district_case_share = annual_total * (d["_weight"] / total_weight)

        for year in years:
            n_cases_this_year = max(20, round(district_case_share))
            for _ in range(n_cases_this_year):
                station_id = random.choice(stations)
                category_id = random.choices([1, 3, 8, 4], weights=[85, 5, 7, 3])[0]  # mostly FIR
                sn = serial.next(station_id, category_id, year)
                crime_no = encode_crime_no(category_id, d_id, station_id, year, sn)
                case_no = encode_case_no(year, sn)

                subhead_name = weighted_choice(SUBHEAD_WEIGHTS)
                subhead_id = subhead_name_to_id[subhead_name]
                head_id = subhead_id_to_head[subhead_id]
                gravity_id = 1 if subhead_name in HEINOUS_SUBHEADS else 2

                # Realistic time-of-day skew: property crime -> late night/early morning;
                # crimes-against-women -> evening; violent crime -> variable.
                if subhead_name in {"Theft", "Auto Theft", "Burglary", "Dacoity"}:
                    hour = random.choices(range(24), weights=[6 if 0 <= h <= 4 or h >= 22 else 1 for h in range(24)])[0]
                elif subhead_name in {"Assault on Women (Outrage Modesty)", "Rape"}:
                    hour = random.choices(range(24), weights=[4 if 18 <= h <= 22 else 1 for h in range(24)])[0]
                else:
                    hour = random.randint(0, 23)

                month = random.randint(1, 12)
                day = random.randint(1, 28)
                incident_dt = datetime(year, month, day, hour, random.randint(0, 59))
                registered_dt = incident_dt + timedelta(hours=random.choice([0, 1, 2, 6, 24]))
                info_received_dt = incident_dt + timedelta(minutes=random.randint(5, 300))
                report_delay_hours = (info_received_dt - incident_dt).total_seconds() / 3600.0

                lat, lon = jitter_coord(*centroid)
                # ~4% of cases missing GPS — realistic data-entry gap
                if random.random() < 0.04:
                    lat, lon = None, None

                emp_pool = emp_by_station.get(station_id, [None])
                police_person_id = random.choice(emp_pool)

                court_id = random.choice(courts_by_district.get(d_id, [None]))

                case_master.append({
                    "CaseMasterID": case_id, "CrimeNo": crime_no, "CaseNo": case_no,
                    "CrimeRegisteredDate": registered_dt.date().isoformat(),
                    "PolicePersonID": police_person_id, "PoliceStationID": station_id,
                    "CaseCategoryID": category_id, "GravityOffenceID": gravity_id,
                    "CrimeMajorHeadID": head_id, "CrimeMinorHeadID": subhead_id,
                    "CaseStatusID": None,  # finalized below, after accused/arrest are known
                    "CourtID": court_id,
                    "IncidentFromDate": incident_dt.isoformat(sep=" "),
                    "IncidentToDate": incident_dt.isoformat(sep=" "),
                    "InfoReceivedPSDate": info_received_dt.isoformat(sep=" "),
                    "latitude": lat, "longitude": lon,
                    "BriefFacts": None,  # filled after accused generated below
                    "_district_id": d_id, "_subhead_name": subhead_name,  # helper cols, stripped at export
                })

                # ---------------- ComplainantDetails ----------------
                n_complainants = random.choices([1, 2], weights=[92, 8])[0]
                for _ in range(n_complainants):
                    gender = random.choices(["M", "F", "T"], weights=[55, 43, 2])[0]
                    complainants.append({
                        "ComplainantID": complainant_id, "CaseMasterID": case_id,
                        "ComplainantName": fake.name_male() if gender == "M" else fake.name_female(),
                        "AgeYear": random.randint(18, 75) if random.random() > 0.03 else None,
                        "OccupationID": random.randint(1, len(cfg.OCCUPATIONS)) if random.random() > 0.1 else None,
                        "ReligionID": random.randint(1, len(cfg.RELIGIONS)),
                        "CasteID": random.randint(1, len(cfg.CASTE_CATEGORIES)),
                        "GenderID": gender,
                    })
                    complainant_id += 1

                # ---------------- ActSectionAssociation ----------------
                matching_sections = [(a, s) for (a, s), sub in section_to_subhead.items() if sub == subhead_id]
                if not matching_sections:
                    matching_sections = random.sample(act_section_list, k=1)
                n_sections = random.choices([1, 2, 3], weights=[70, 22, 8])[0]
                chosen = random.sample(matching_sections, k=min(n_sections, len(matching_sections)))
                for order, (act_code, sec_code) in enumerate(chosen, start=1):
                    act_section_assoc.append({
                        "CaseMasterID": case_id, "ActID": act_code, "SectionID": sec_code,
                        "ActOrderID": order, "SectionOrderID": order,
                    })

                # ---------------- Victim ----------------
                n_victims = random.choices([0, 1, 2, 3], weights=[15, 65, 15, 5])[0]
                for _ in range(n_victims):
                    v_gender = random.choices(["M", "F", "T"], weights=[48, 50, 2])[0]
                    victims.append({
                        "VictimMasterID": victim_id, "CaseMasterID": case_id,
                        "VictimName": fake.name_male() if v_gender == "M" else fake.name_female(),
                        "AgeYear": random.randint(1, 85),
                        "GenderID": v_gender,
                        "VictimPolice": random.choices([0, 1], weights=[99, 1])[0],
                    })
                    victim_id += 1

                # ---------------- Accused (with identity-collision injection) ----------------
                case_mo_category = mo_category_for_subhead(subhead_name)
                case_mo_pool = MO_PHRASE_CATEGORIES[case_mo_category]
                n_accused = random.choices([1, 2, 3, 4], weights=[55, 25, 13, 7])[0]
                case_mo_phrases = []
                case_n_arrests = 0
                for person_idx in range(n_accused):
                    use_repeat = random.random() < 0.35  # 35% of accused slots drawn from repeat pool
                    if use_repeat:
                        if random.random() < HOME_DISTRICT_BIAS and repeat_pool_by_district.get(d_id):
                            gt_person = random.choice(repeat_pool_by_district[d_id])
                        else:
                            gt_person = random.choice(repeat_pool)  # cross-jurisdiction appearance
                        true_age = year - gt_person["birth_year"]
                        recorded_age = maybe_age_drift(true_age)
                        recorded_name = generate_name_variant(gt_person["canonical_name"])
                        gender = gt_person["gender"]
                        # Use the person's own signature phrase only when it matches this
                        # case's category (genuine repeat-MO signal); otherwise fall back
                        # to a category-appropriate phrase so the narrative stays coherent.
                        mo_phrase = (
                            gt_person["mo_phrase"] if gt_person["mo_category"] == case_mo_category
                            else random.choice(case_mo_pool)
                        )
                        person_usage_log.append({
                            "person_master_id": gt_person["person_master_id"],
                            "AccusedMasterID": accused_id, "CaseMasterID": case_id,
                            "recorded_name": recorded_name, "true_name": gt_person["canonical_name"],
                        })
                    else:
                        gender = random.choices(["M", "F", "T"], weights=[90, 9, 1])[0]
                        recorded_name = fake.name_male() if gender == "M" else fake.name_female()
                        recorded_age = random.randint(16, 65)
                        mo_phrase = random.choice(case_mo_pool)

                    accused_rows.append({
                        "AccusedMasterID": accused_id, "CaseMasterID": case_id,
                        "AccusedName": recorded_name, "AgeYear": recorded_age,
                        "GenderID": gender, "PersonID": f"A{person_idx + 1}",
                    })
                    case_mo_phrases.append(mo_phrase)

                    # ---------------- ArrestSurrender (subset of accused) ----------------
                    if random.random() < 0.6:
                        arr_type = random.choices([1, 2], weights=[85, 15])[0]  # 1=Arrest, 2=Surrender
                        arrest_dt = registered_dt + timedelta(days=random.randint(0, 60))
                        arrest_surrender.append({
                            "ArrestSurrenderID": arrest_id, "CaseMasterID": case_id,
                            "ArrestSurrenderTypeID": arr_type, "ArrestSurrenderDate": arrest_dt.date().isoformat(),
                            "ArrestSurrenderStateId": 1, "ArrestSurrenderDistrictId": d_id,
                            "PoliceStationID": station_id, "IOID": police_person_id, "CourtID": court_id,
                            "AccusedMasterID": accused_id,
                            "IsAccused": 1, "IsComplainantAccused": random.choices([0, 1], weights=[97, 3])[0],
                        })
                        arrest_id += 1
                        case_n_arrests += 1
                    accused_id += 1

                case_master[-1]["BriefFacts"] = (
                    f"On {incident_dt.strftime('%d %b %Y around %H:%M')}, a case of {subhead_name} "
                    f"was registered at the police station. {' '.join(set(case_mo_phrases))} "
                    f"Investigation is being carried out as per standard procedure."
                )

                # ---------------- Case outcome: REAL injected signal ----------------
                # Combines crime-type base solvability + reporting delay + whether an
                # arrest was made + noise. This is what the risk-scoring model learns
                # from — not an arbitrary status lookup.
                age_of_case_days = (snapshot_date - registered_dt).days
                if age_of_case_days < CASE_FINALIZATION_DAYS:
                    status_id = 1  # Under Investigation — no chargesheet yet
                else:
                    base_solve = SUBHEAD_BASE_SOLVE_PROB.get(subhead_name, 0.5)
                    delay_penalty = min(report_delay_hours / 720.0, 1.0) * 0.25  # up to -0.25 for 30+ day delay
                    arrest_bonus = 0.25 if case_n_arrests > 0 else -0.05
                    noise = random.gauss(0, 0.08)
                    resolve_prob = max(0.03, min(0.95, base_solve - delay_penalty + arrest_bonus + noise))

                    r = random.random()
                    if r < resolve_prob:
                        status_id = random.choices([2, 6], weights=[80, 20])[0]  # Chargesheeted / Convicted
                        cstype = "A"
                    elif r < resolve_prob + 0.05:
                        status_id = 4  # False case
                        cstype = "B"
                    else:
                        status_id = 3  # Closed - Undetected
                        cstype = "C"

                    cs_date = registered_dt + timedelta(days=random.randint(30, 300))
                    chargesheets.append({
                        "CSID": cs_id, "CaseMasterID": case_id, "csdate": cs_date.isoformat(sep=" "),
                        "cstype": cstype, "PolicePersonID": police_person_id,
                    })
                    cs_id += 1

                case_master[-1]["CaseStatusID"] = status_id
                case_id += 1

    return {
        "CaseMaster": case_master,
        "ComplainantDetails": complainants,
        "ActSectionAssociation": act_section_assoc,
        "Victim": victims,
        "Accused": accused_rows,
        "ArrestSurrender": arrest_surrender,
        "ChargesheetDetails": chargesheets,
        "_entity_resolution_ground_truth": person_usage_log,
    }
