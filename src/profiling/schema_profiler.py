from pathlib import Path
import json
import warnings

import pandas as pd


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROFILE_OUTPUT_DIR = PROJECT_ROOT / "data" / "profiles"

PROFILE_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_sample_values(series, limit=5):
    """
    Return a small list of non-null sample values.
    """

    values = (
        series
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return values[:limit]


def calculate_null_percentage(series):
    """
    Calculate percentage of missing values.
    """

    if len(series) == 0:
        return 0.0

    return round(
        float(series.isna().mean() * 100),
        2,
    )


def calculate_unique_percentage(series):
    """
    Calculate percentage of unique non-null values.
    """

    non_null = series.dropna()

    if len(non_null) == 0:
        return 0.0

    return round(
        float(
            non_null.nunique()
            / len(non_null)
            * 100
        ),
        2,
    )


# ============================================================
# TYPE INFERENCE
# ============================================================

def looks_like_date(series):
    """
    Determine whether a column likely contains dates.
    """

    non_null = (
        series
        .dropna()
        .astype(str)
    )

    if non_null.empty:
        return False

    sample = non_null.head(100)

    # Some non-date columns may contain values that cause
    # pandas to emit date parsing warnings. Suppress those
    # warnings because failed parsing is expected here.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        parsed = pd.to_datetime(
            sample,
            errors="coerce",
        )

    success_rate = parsed.notna().mean()

    return success_rate >= 0.90


def infer_semantic_type(
    column_name,
    series,
):
    """
    Infer a high-level semantic category using both
    the column name and observed values.
    """

    name = column_name.lower()

    identifier_keywords = [
        "id",
        "number",
        "npi",
        "subscriber",
        "member",
        "patient",
        "provider",
        "claim",
        "payer",
        "insurance",
        "plan",
    ]

    amount_keywords = [
        "amount",
        "amt",
        "charge",
        "payment",
        "paid",
        "allow",
        "approved",
        "eligible",
        "reimbursement",
    ]

    date_keywords = [
        "date",
        "dos",
        "service_date",
    ]

    procedure_keywords = [
        "procedure",
        "proc",
        "cpt",
    ]

    diagnosis_keywords = [
        "diagnosis",
        "dx",
        "icd",
    ]

    status_keywords = [
        "status",
    ]

    location_keywords = [
        "location",
        "facility",
        "pos",
    ]

    # --------------------------------------------------------
    # IMPORTANT:
    # STATUS must be checked before PROCEDURE_CODE.
    #
    # "processing_status" contains "proc", so checking
    # procedure first would incorrectly classify it.
    # --------------------------------------------------------

    if any(
        keyword in name
        for keyword in date_keywords
    ):
        return "DATE"

    if any(
        keyword in name
        for keyword in amount_keywords
    ):
        return "AMOUNT"

    if any(
        keyword in name
        for keyword in status_keywords
    ):
        return "STATUS"

    if any(
        keyword in name
        for keyword in procedure_keywords
    ):
        return "PROCEDURE_CODE"

    if any(
        keyword in name
        for keyword in diagnosis_keywords
    ):
        return "DIAGNOSIS_CODE"

    if any(
        keyword in name
        for keyword in location_keywords
    ):
        return "LOCATION"

    if any(
        keyword in name
        for keyword in identifier_keywords
    ):
        return "IDENTIFIER"

    if looks_like_date(series):
        return "DATE"

    if pd.api.types.is_numeric_dtype(series):
        return "NUMERIC"

    return "TEXT"


# ============================================================
# COLUMN PROFILING
# ============================================================

def profile_column(
    column_name,
    series,
):
    """
    Generate profiling metadata for one column.
    """

    profile = {
        "column_name": column_name,
        "pandas_dtype": str(series.dtype),

        "semantic_type": infer_semantic_type(
            column_name,
            series,
        ),

        "row_count": int(len(series)),

        "null_count": int(
            series.isna().sum()
        ),

        "null_percentage":
            calculate_null_percentage(
                series
            ),

        "unique_count": int(
            series.nunique(
                dropna=True
            )
        ),

        "unique_percentage":
            calculate_unique_percentage(
                series
            ),

        "sample_values":
            safe_sample_values(
                series
            ),
    }

    numeric_series = pd.to_numeric(
        series,
        errors="coerce",
    )

    if numeric_series.notna().mean() >= 0.90:

        profile["numeric_min"] = float(
            numeric_series.min()
        )

        profile["numeric_max"] = float(
            numeric_series.max()
        )

        profile["numeric_mean"] = round(
            float(
                numeric_series.mean()
            ),
            2,
        )

    else:

        profile["numeric_min"] = None
        profile["numeric_max"] = None
        profile["numeric_mean"] = None

    return profile


# ============================================================
# FILE PROFILING
# ============================================================

def profile_csv(file_path):
    """
    Profile an entire client CSV file.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    df = pd.read_csv(
        file_path
    )

    profile = {
        "file_name": file_path.name,

        "file_path": str(
            file_path.relative_to(
                PROJECT_ROOT
            )
        ),

        "row_count": int(len(df)),

        "column_count": int(
            len(df.columns)
        ),

        "duplicate_rows": int(
            df.duplicated().sum()
        ),

        "columns": [],
    }

    for column in df.columns:

        column_profile = profile_column(
            column,
            df[column],
        )

        profile["columns"].append(
            column_profile
        )

    return profile


# ============================================================
# SAVE PROFILE
# ============================================================

def save_profile(
    profile,
    output_name,
):
    """
    Save profiling results as JSON.
    """

    output_path = (
        PROFILE_OUTPUT_DIR
        / output_name
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            profile,
            file,
            indent=2,
        )

    return output_path


# ============================================================
# DISPLAY PROFILE
# ============================================================

def print_profile(profile):

    print()
    print("=" * 90)

    print(
        f"SCHEMA PROFILE: "
        f"{profile['file_name']}"
    )

    print("=" * 90)

    print(
        f"Rows       : "
        f"{profile['row_count']:,}"
    )

    print(
        f"Columns    : "
        f"{profile['column_count']}"
    )

    print(
        f"Duplicates : "
        f"{profile['duplicate_rows']}"
    )

    print()

    print(
        f"{'COLUMN':<22}"
        f"{'TYPE':<18}"
        f"{'NULL %':<12}"
        f"{'UNIQUE %':<12}"
        f"SAMPLES"
    )

    print("-" * 90)

    for column in profile["columns"]:

        samples = ", ".join(
            column[
                "sample_values"
            ][:3]
        )

        print(
            f"{column['column_name']:<22}"
            f"{column['semantic_type']:<18}"
            f"{column['null_percentage']:<12.2f}"
            f"{column['unique_percentage']:<12.2f}"
            f"{samples}"
        )


# ============================================================
# PROFILE ALL CLIENTS
# ============================================================

def profile_all_clients():

    clients = {
        "client_a": (
            PROJECT_ROOT
            / "data"
            / "client_a"
            / "client_a_claims.csv"
        ),

        "client_b": (
            PROJECT_ROOT
            / "data"
            / "client_b"
            / "client_b_claims.csv"
        ),

        "client_c": (
            PROJECT_ROOT
            / "data"
            / "client_c"
            / "client_c_claims.csv"
        ),
    }

    profiles = {}

    for client_name, path in clients.items():

        profile = profile_csv(
            path
        )

        output_path = save_profile(
            profile,
            f"{client_name}_profile.json",
        )

        profiles[
            client_name
        ] = profile

        print_profile(
            profile
        )

        print()

        print(
            f"Profile saved: "
            f"{output_path.relative_to(PROJECT_ROOT)}"
        )

    return profiles


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print("=" * 90)

    print(
        "MEDMAP NAVIGATOR - "
        "HEALTHCARE SCHEMA PROFILER"
    )

    print("=" * 90)

    profiles = profile_all_clients()

    print()

    print("=" * 90)

    print(
        f"CLIENTS PROFILED : "
        f"{len(profiles)}"
    )

    total_columns = sum(
        profile["column_count"]
        for profile in profiles.values()
    )

    print(
        f"COLUMNS ANALYZED : "
        f"{total_columns}"
    )

    print(
        "SCHEMA PROFILING : PASSED"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()