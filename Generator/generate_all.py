import os
import pandas as pd

from reference_data import build_reference_data
from transactional_data import build_transactional_data
import config as cfg

OUT_DIR = "../synthetic_data"


def strip_helper_cols(rows):
    """Remove any leading-underscore helper keys before export (they're not
    part of the real ER schema, only used internally during generation)."""
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Building reference/master data...")
    ref = build_reference_data()

    print("Building transactional data (this generates the full 3-year FIR history)...")
    txn = build_transactional_data(ref)

    all_tables = {**ref, **txn}

    # ---------------- Referential integrity checks ----------------
    print("\nRunning referential integrity checks...")
    case_ids = {c["CaseMasterID"] for c in txn["CaseMaster"]}
    accused_ids = {a["AccusedMasterID"] for a in txn["Accused"]}
    unit_ids = {u["UnitID"] for u in ref["Unit"]}
    district_ids = {d["DistrictID"] for d in ref["District"]}
    employee_ids = {e["EmployeeID"] for e in ref["Employee"]}

    errors = []
    for c in txn["ComplainantDetails"]:
        if c["CaseMasterID"] not in case_ids:
            errors.append(f"ComplainantDetails {c['ComplainantID']} -> missing CaseMasterID")
    for a in txn["ArrestSurrender"]:
        if a["AccusedMasterID"] not in accused_ids:
            errors.append(f"ArrestSurrender {a['ArrestSurrenderID']} -> missing AccusedMasterID")
        if a["PoliceStationID"] not in unit_ids:
            errors.append(f"ArrestSurrender {a['ArrestSurrenderID']} -> missing PoliceStationID")
    for c in txn["CaseMaster"]:
        if c["PoliceStationID"] not in unit_ids:
            errors.append(f"CaseMaster {c['CaseMasterID']} -> missing PoliceStationID")

    if errors:
        print(f"FOUND {len(errors)} integrity errors (showing first 10):")
        for e in errors[:10]:
            print("  -", e)
    else:
        print("  All FK checks passed.")

    # ---------------- Write CSVs (real ER-schema tables only) ----------------
    schema_tables = [
        "State", "District", "UnitType", "Unit", "Rank", "Designation", "Employee",
        "CaseCategory", "GravityOffence", "CaseStatusMaster", "OccupationMaster",
        "ReligionMaster", "CasteMaster", "CrimeHead", "CrimeSubHead", "Act", "Section",
        "CrimeHeadActSection", "Court", "CaseMaster", "ComplainantDetails",
        "ActSectionAssociation", "Victim", "Accused", "ArrestSurrender", "ChargesheetDetails",
    ]

    print(f"\nWriting {len(schema_tables)} schema-exact tables to {OUT_DIR}/ ...")
    for name in schema_tables:
        rows = strip_helper_cols(all_tables[name])
        df = pd.DataFrame(rows)
        df.to_csv(f"{OUT_DIR}/{name}.csv", index=False)
        print(f"  {name}.csv  -> {len(df):,} rows")

    # ---------------- Ground truth for entity-resolution evaluation ----------------
    gt_df = pd.DataFrame(txn["_entity_resolution_ground_truth"])
    gt_df.to_csv(f"{OUT_DIR}/entity_resolution_ground_truth.csv", index=False)
    print(f"\n  entity_resolution_ground_truth.csv -> {len(gt_df):,} rows "
          f"({gt_df['person_master_id'].nunique():,} unique real persons across cases)")

    total_cases = len(txn["CaseMaster"])
    total_accused = len(txn["Accused"])
    print(f"\nDone. {total_cases:,} FIRs, {total_accused:,} accused entries, "
          f"{gt_df['person_master_id'].nunique():,} of them are repeat offenders "
          f"appearing under {len(gt_df):,} name-variant records.")


if __name__ == "__main__":
    main()
