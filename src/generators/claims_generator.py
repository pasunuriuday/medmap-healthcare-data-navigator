from pathlib import Path
from datetime import date, timedelta
import random

import numpy as np
import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42
NUM_CLAIMS = 1000

fake = Faker()
Faker.seed(SEED)
random.seed(SEED)
np.random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CLIENT_A_DIR = PROJECT_ROOT / "data" / "client_a"
CLIENT_B_DIR = PROJECT_ROOT / "data" / "client_b"
CLIENT_C_DIR = PROJECT_ROOT / "data" / "client_c"

for directory in [
    CLIENT_A_DIR,
    CLIENT_B_DIR,
    CLIENT_C_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# HEALTHCARE REFERENCE VALUES
# ============================================================

PROCEDURE_CODES = [
    "99213",
    "99214",
    "99215",
    "80053",
    "85025",
    "93000",
    "71046",
    "36415",
    "97110",
    "90834",
]

DIAGNOSIS_CODES = [
    "I10",
    "E11.9",
    "J06.9",
    "M54.50",
    "E78.5",
    "R07.9",
    "F41.1",
    "K21.9",
    "J45.909",
    "N39.0",
]

PLACE_OF_SERVICE = [
    "OFFICE",
    "HOSPITAL",
    "OUTPATIENT",
    "URGENT_CARE",
    "TELEHEALTH",
]

CLAIM_STATUSES = [
    "PAID",
    "DENIED",
    "PENDING",
]

PAYER_IDS = [
    "PAY001",
    "PAY002",
    "PAY003",
    "PAY004",
]


# ============================================================
# BASE CLAIM GENERATION
# ============================================================

def random_service_date():
    """
    Generate a service date within the previous 365 days.
    """

    days_ago = random.randint(0, 365)

    return date.today() - timedelta(days=days_ago)


def generate_base_claims(num_claims=NUM_CLAIMS):
    """
    Generate the canonical healthcare claims dataset.

    Client-specific datasets will be derived from this
    canonical representation.
    """

    records = []

    for index in range(1, num_claims + 1):

        billed_amount = round(
            random.uniform(50.0, 10000.0),
            2,
        )

        allowed_amount = round(
            billed_amount * random.uniform(0.55, 0.95),
            2,
        )

        paid_amount = round(
            allowed_amount * random.uniform(0.70, 1.0),
            2,
        )

        status = random.choices(
            CLAIM_STATUSES,
            weights=[80, 12, 8],
            k=1,
        )[0]

        if status == "DENIED":
            paid_amount = 0.0

        if status == "PENDING":
            paid_amount = 0.0

        record = {
            "claim_id": f"CLM-{index:07d}",
            "member_id": f"MEM-{random.randint(1, 500):06d}",
            "provider_id": f"NPI-{random.randint(100000, 999999)}",
            "procedure_code": random.choice(PROCEDURE_CODES),
            "diagnosis_code": random.choice(DIAGNOSIS_CODES),
            "service_date": random_service_date(),
            "billed_amount": billed_amount,
            "allowed_amount": allowed_amount,
            "paid_amount": paid_amount,
            "place_of_service": random.choice(PLACE_OF_SERVICE),
            "claim_status": status,
            "payer_id": random.choice(PAYER_IDS),
        }

        records.append(record)

    return pd.DataFrame(records)


# ============================================================
# CLIENT A LAYOUT
# ============================================================

def create_client_a(base_df):
    """
    Client A uses abbreviated uppercase healthcare field names.
    """

    df = base_df.copy()

    df = df.rename(
        columns={
            "claim_id": "CLM_ID",
            "member_id": "MEM_ID",
            "provider_id": "PROV_NPI",
            "procedure_code": "PROC_CD",
            "diagnosis_code": "DX_CD",
            "service_date": "DOS",
            "billed_amount": "BILLED_AMT",
            "allowed_amount": "ALLOW_AMT",
            "paid_amount": "PAID_AMT",
            "place_of_service": "POS",
            "claim_status": "CLM_STATUS",
            "payer_id": "PAYER_CD",
        }
    )

    df["DOS"] = pd.to_datetime(
        df["DOS"]
    ).dt.strftime("%Y%m%d")

    return df


# ============================================================
# CLIENT B LAYOUT
# ============================================================

def create_client_b(base_df):
    """
    Client B uses descriptive business-friendly field names.
    """

    df = base_df.copy()

    df = df.rename(
        columns={
            "claim_id": "CLAIM_NUMBER",
            "member_id": "PATIENT_NUMBER",
            "provider_id": "DOCTOR_ID",
            "procedure_code": "CPT_CODE",
            "diagnosis_code": "DIAGNOSIS",
            "service_date": "SERVICE_DATE",
            "billed_amount": "CHARGE_AMOUNT",
            "allowed_amount": "APPROVED_AMOUNT",
            "paid_amount": "PAYMENT_AMOUNT",
            "place_of_service": "SERVICE_LOCATION",
            "claim_status": "STATUS",
            "payer_id": "INSURANCE_ID",
        }
    )

    df["SERVICE_DATE"] = pd.to_datetime(
        df["SERVICE_DATE"]
    ).dt.strftime("%m/%d/%Y")

    return df


# ============================================================
# CLIENT C LAYOUT
# ============================================================

def create_client_c(base_df):
    """
    Client C uses lowercase application-style field names.
    """

    df = base_df.copy()

    df = df.rename(
        columns={
            "claim_id": "claim_number",
            "member_id": "subscriber_id",
            "provider_id": "provider_number",
            "procedure_code": "procedure",
            "diagnosis_code": "icd10",
            "service_date": "date_of_service",
            "billed_amount": "claim_amount",
            "allowed_amount": "eligible_amount",
            "paid_amount": "reimbursement",
            "place_of_service": "facility_type",
            "claim_status": "processing_status",
            "payer_id": "health_plan",
        }
    )

    df["date_of_service"] = pd.to_datetime(
        df["date_of_service"]
    ).dt.strftime("%Y-%m-%d")

    return df


# ============================================================
# DATA QUALITY VALIDATION
# ============================================================

def validate_generated_data(base_df):
    """
    Run basic validation before writing client datasets.
    """

    expected_columns = {
        "claim_id",
        "member_id",
        "provider_id",
        "procedure_code",
        "diagnosis_code",
        "service_date",
        "billed_amount",
        "allowed_amount",
        "paid_amount",
        "place_of_service",
        "claim_status",
        "payer_id",
    }

    missing_columns = expected_columns - set(base_df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing canonical columns: {sorted(missing_columns)}"
        )

    if base_df["claim_id"].duplicated().any():
        raise ValueError(
            "Duplicate claim IDs detected."
        )

    if base_df["claim_id"].isna().any():
        raise ValueError(
            "Missing claim IDs detected."
        )

    if base_df["member_id"].isna().any():
        raise ValueError(
            "Missing member IDs detected."
        )

    if base_df["provider_id"].isna().any():
        raise ValueError(
            "Missing provider IDs detected."
        )

    if (base_df["billed_amount"] < 0).any():
        raise ValueError(
            "Negative billed amounts detected."
        )

    if (
        base_df["allowed_amount"]
        > base_df["billed_amount"]
    ).any():
        raise ValueError(
            "Allowed amount exceeds billed amount."
        )

    if (
        base_df["paid_amount"]
        > base_df["allowed_amount"]
    ).any():
        raise ValueError(
            "Paid amount exceeds allowed amount."
        )

    return True


# ============================================================
# WRITE CLIENT FILES
# ============================================================

def write_client_files(
    client_a,
    client_b,
    client_c,
):
    """
    Write each client's unique source layout.
    """

    client_a_path = (
        CLIENT_A_DIR
        / "client_a_claims.csv"
    )

    client_b_path = (
        CLIENT_B_DIR
        / "client_b_claims.csv"
    )

    client_c_path = (
        CLIENT_C_DIR
        / "client_c_claims.csv"
    )

    client_a.to_csv(
        client_a_path,
        index=False,
    )

    client_b.to_csv(
        client_b_path,
        index=False,
    )

    client_c.to_csv(
        client_c_path,
        index=False,
    )

    return (
        client_a_path,
        client_b_path,
        client_c_path,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MEDMAP HEALTHCARE CLAIMS GENERATOR")
    print("=" * 70)

    base_df = generate_base_claims()

    validate_generated_data(base_df)

    client_a = create_client_a(base_df)
    client_b = create_client_b(base_df)
    client_c = create_client_c(base_df)

    paths = write_client_files(
        client_a,
        client_b,
        client_c,
    )

    print()
    print(f"Canonical claims generated : {len(base_df):,}")
    print(f"Client A records           : {len(client_a):,}")
    print(f"Client B records           : {len(client_b):,}")
    print(f"Client C records           : {len(client_c):,}")

    print()
    print("Files created:")

    for path in paths:
        print(f"  {path.relative_to(PROJECT_ROOT)}")

    print()
    print("CLIENT SCHEMA COMPARISON")
    print("-" * 70)

    print(
        f"Client A member field : {client_a.columns[1]}"
    )

    print(
        f"Client B member field : {client_b.columns[1]}"
    )

    print(
        f"Client C member field : {client_c.columns[1]}"
    )

    print()
    print("Data validation       : PASSED")

    print("=" * 70)


if __name__ == "__main__":
    main()
