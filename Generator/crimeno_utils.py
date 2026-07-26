"""
CrimeNo / CaseNo encoding utilities.

Per the ER document:
  CrimeNo  = 1-digit CaseCategoryCode + 4-digit DistrictID + 4-digit PoliceStationID(UnitID)
             + 4-digit Year + 5-digit running serial   (18 chars total)
  CaseNo   = last 9 digits of CrimeNo = 4-digit Year + 5-digit running serial

A separate running serial is maintained per (PoliceStationID, CaseCategory, Year).
This module is the SAME encoder used for synthetic generation and would be the
SAME decoder used to validate/ingest real FIRs — one source of truth for the format.
"""


def encode_crime_no(category_code: int, district_id: int, station_id: int,
                     year: int, serial: int) -> str:
    return (
        f"{category_code:01d}"
        f"{district_id:04d}"
        f"{station_id:04d}"
        f"{year:04d}"
        f"{serial:05d}"
    )


def encode_case_no(year: int, serial: int) -> str:
    return f"{year:04d}{serial:05d}"


def decode_crime_no(crime_no: str) -> dict:
    """Decode and validate a CrimeNo string. Raises ValueError on malformed input."""
    if not crime_no.isdigit() or len(crime_no) != 18:
        raise ValueError(f"CrimeNo must be 18 digits, got {len(crime_no)}: {crime_no!r}")
    return {
        "category_code": int(crime_no[0:1]),
        "district_id": int(crime_no[1:5]),
        "station_id": int(crime_no[5:9]),
        "year": int(crime_no[9:13]),
        "serial": int(crime_no[13:18]),
    }


def validate_crime_no_consistency(crime_no: str, case_master_row: dict) -> list:
    """
    Cross-checks a decoded CrimeNo against the CaseMaster row it's supposedly
    attached to. Returns a list of human-readable discrepancy strings (empty
    list = consistent). This is the core of the "CrimeNo structural audit"
    anomaly-detection module — works identically on synthetic or real data.
    """
    issues = []
    try:
        decoded = decode_crime_no(crime_no)
    except ValueError as e:
        return [str(e)]

    if decoded["district_id"] != case_master_row.get("district_id"):
        issues.append(
            f"CrimeNo district ({decoded['district_id']}) != linked PoliceStation's "
            f"district ({case_master_row.get('district_id')})"
        )
    if decoded["station_id"] != case_master_row.get("PoliceStationID"):
        issues.append(
            f"CrimeNo station ({decoded['station_id']}) != CaseMaster.PoliceStationID "
            f"({case_master_row.get('PoliceStationID')})"
        )
    reg_year = case_master_row.get("CrimeRegisteredDate_year")
    if reg_year is not None and decoded["year"] != reg_year:
        issues.append(
            f"CrimeNo year ({decoded['year']}) != CrimeRegisteredDate year ({reg_year})"
        )
    return issues
