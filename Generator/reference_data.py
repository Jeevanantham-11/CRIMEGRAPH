"""
Builds every master/lookup table in the ER schema as a list of dicts.
Returns a dict-of-lists keyed by table name, ready to be written to CSV
or pushed directly into Catalyst Data Store via ZCQL insert later.
"""

import random
from faker import Faker
import config as cfg

fake = Faker("en_IN")


def build_reference_data():
    tables = {}

    # ---------------- State / District ----------------
    tables["State"] = [cfg.STATE]

    districts = []
    for i, (name, weight) in enumerate(cfg.DISTRICTS, start=1):
        districts.append({
            "DistrictID": i, "DistrictName": name, "StateID": 1,
            "Active": 1, "_weight": weight,
        })
    tables["District"] = districts

    # ---------------- UnitType ----------------
    tables["UnitType"] = [
        {"UnitTypeID": tid, "UnitTypeName": name, "CityDistState": level, "Hierarchy": h, "Active": 1}
        for tid, name, level, h in cfg.UNIT_TYPES
    ]

    # ---------------- Unit (police stations + hierarchy) ----------------
    # Real KSP has 1100+ stations; allocate proportionally to district weight.
    total_stations = 1100
    total_weight = sum(w for _, w in cfg.DISTRICTS)
    units = []
    unit_id = 1

    # One SP Office per district (parent of that district's stations)
    district_sp_office_id = {}
    for d in districts:
        units.append({
            "UnitID": unit_id, "UnitName": f"SP Office, {d['DistrictName']}",
            "TypeID": 3, "ParentUnit": None, "NationalityID": 1,
            "StateID": 1, "DistrictID": d["DistrictID"], "Active": 1,
        })
        district_sp_office_id[d["DistrictID"]] = unit_id
        unit_id += 1

    stations_by_district = {}
    for d in districts:
        n_stations = max(3, round(total_stations * (d["_weight"] / total_weight)))
        station_ids = []
        for s in range(n_stations):
            units.append({
                "UnitID": unit_id,
                "UnitName": f"{d['DistrictName']} PS-{s + 1}",
                "TypeID": 5,
                "ParentUnit": district_sp_office_id[d["DistrictID"]],
                "NationalityID": 1,
                "StateID": 1,
                "DistrictID": d["DistrictID"],
                "Active": 1,
            })
            station_ids.append(unit_id)
            unit_id += 1
        stations_by_district[d["DistrictID"]] = station_ids

    tables["Unit"] = units
    tables["_stations_by_district"] = stations_by_district  # internal helper, not a real table

    # ---------------- Rank / Designation ----------------
    tables["Rank"] = [
        {"RankID": rid, "RankName": name, "Hierarchy": h, "Active": 1}
        for rid, name, h in cfg.RANKS
    ]
    tables["Designation"] = [
        {"DesignationID": did, "DesignationName": name, "Active": 1, "SortOrder": so}
        for did, name, so in cfg.DESIGNATIONS
    ]

    # ---------------- Employee ----------------
    employees = []
    emp_id = 1
    for d in districts:
        station_ids = stations_by_district[d["DistrictID"]]
        for st_id in station_ids:
            n_emp = random.randint(8, 20)  # officers posted per station
            for _ in range(n_emp):
                gender = random.choices(["M", "F"], weights=[80, 20])[0]
                dob = fake.date_of_birth(minimum_age=23, maximum_age=58)
                employees.append({
                    "EmployeeID": emp_id,
                    "DistrictID": d["DistrictID"],
                    "UnitID": st_id,
                    "RankID": random.choices(
                        [10, 9, 7, 6, 5], weights=[45, 20, 15, 15, 5])[0],
                    "DesignationID": random.choice([1, 2, 3, 4, 5, 6]),
                    "KGID": f"KGID{100000 + emp_id}",
                    "FirstName": fake.first_name_male() if gender == "M" else fake.first_name_female(),
                    "EmployeeDOB": dob.isoformat(),
                    "GenderID": gender,
                    "BloodGroupID": random.choice(["A+", "B+", "O+", "AB+", "A-", "B-", "O-"]),
                    "PhysicallyChallenged": random.choices([0, 1], weights=[98, 2])[0],
                    "AppointmentDate": fake.date_between(start_date="-30y", end_date="-1y").isoformat(),
                })
                emp_id += 1
    tables["Employee"] = employees

    # ---------------- Case-related lookups ----------------
    tables["CaseCategory"] = [
        {"CaseCategoryID": cid, "LookupValue": name} for cid, name in cfg.CASE_CATEGORY
    ]
    tables["GravityOffence"] = [
        {"GravityOffenceID": gid, "LookupValue": name} for gid, name in cfg.GRAVITY_OFFENCE
    ]
    tables["CaseStatusMaster"] = [
        {"CaseStatusID": sid, "CaseStatusName": name} for sid, name in cfg.CASE_STATUS
    ]
    tables["OccupationMaster"] = [
        {"OccupationID": i + 1, "OccupationName": name} for i, name in enumerate(cfg.OCCUPATIONS)
    ]
    tables["ReligionMaster"] = [
        {"ReligionID": i + 1, "ReligionName": name} for i, name in enumerate(cfg.RELIGIONS)
    ]
    tables["CasteMaster"] = [
        {"caste_master_id": i + 1, "caste_master_name": name} for i, name in enumerate(cfg.CASTE_CATEGORIES)
    ]

    # ---------------- Crime taxonomy ----------------
    crime_heads = []
    crime_subheads = []
    subhead_name_to_id = {}
    head_id = 1
    subhead_id = 1
    for head_name, subheads in cfg.CRIME_TAXONOMY.items():
        crime_heads.append({"CrimeHeadID": head_id, "CrimeGroupName": head_name, "Active": 1})
        for seq, sub in enumerate(subheads, start=1):
            crime_subheads.append({
                "CrimeSubHeadID": subhead_id, "CrimeHeadID": head_id,
                "CrimeHeadName": sub, "SeqID": seq,
            })
            subhead_name_to_id[sub] = subhead_id
            subhead_id += 1
        head_id += 1
    tables["CrimeHead"] = crime_heads
    tables["CrimeSubHead"] = crime_subheads
    tables["_subhead_name_to_id"] = subhead_name_to_id

    # ---------------- Act / Section ----------------
    tables["Act"] = [
        {"ActCode": code, "ActDescription": desc, "ShortName": short, "Active": 1}
        for code, desc, short in cfg.ACTS
    ]
    sections = []
    crimehead_actsection = []
    for act_code, sec_code, desc, subhead_name in cfg.SECTIONS:
        sections.append({
            "ActCode": act_code, "SectionCode": sec_code,
            "SectionDescription": desc, "Active": 1,
        })
        sub_id = subhead_name_to_id.get(subhead_name)
        if sub_id:
            # Need the parent CrimeHeadID for this sub-head
            head = next(h for h in crime_subheads if h["CrimeSubHeadID"] == sub_id)
            crimehead_actsection.append({
                "CrimeHeadID": head["CrimeHeadID"], "ActCode": act_code, "SectionCode": sec_code,
            })
    tables["Section"] = sections
    tables["CrimeHeadActSection"] = crimehead_actsection
    tables["_section_to_subhead"] = {
        (a, s): subhead_name_to_id[sub] for a, s, d, sub in cfg.SECTIONS if sub in subhead_name_to_id
    }

    # ---------------- Court ----------------
    courts = []
    court_id = 1
    for d in districts:
        for cname in cfg.COURTS_PER_DISTRICT:
            courts.append({
                "CourtID": court_id, "CourtName": f"{cname}, {d['DistrictName']}",
                "DistrictID": d["DistrictID"], "StateID": 1, "Active": 1,
            })
            court_id += 1
    tables["Court"] = courts

    return tables


if __name__ == "__main__":
    data = build_reference_data()
    for k, v in data.items():
        if not k.startswith("_"):
            print(f"{k}: {len(v)} rows")
