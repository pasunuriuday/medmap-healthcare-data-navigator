from pathlib import Path
from difflib import SequenceMatcher
import json
import re


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROFILE_DIR = PROJECT_ROOT / "data" / "profiles"
MAPPING_OUTPUT_DIR = PROJECT_ROOT / "mappings"

MAPPING_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# MEDMAP COMMON DATA MODEL
# ============================================================

TARGET_SCHEMA = {
    "claim_id": {
        "semantic_type": "IDENTIFIER",
        "synonyms": [
            "claim_id",
            "claim_number",
            "clm_id",
            "claim",
        ],
    },

    "member_id": {
        "semantic_type": "IDENTIFIER",
        "synonyms": [
            "member_id",
            "mem_id",
            "patient_number",
            "patient_id",
            "subscriber_id",
            "subscriber",
            "member",
        ],
    },

    "provider_id": {
        "semantic_type": "IDENTIFIER",
        "synonyms": [
            "provider_id",
            "provider_number",
            "prov_npi",
            "doctor_id",
            "npi",
            "provider",
        ],
    },

    "procedure_code": {
        "semantic_type": "PROCEDURE_CODE",
        "synonyms": [
            "procedure_code",
            "procedure",
            "proc_cd",
            "cpt_code",
            "cpt",
        ],
    },

    "diagnosis_code": {
        "semantic_type": "DIAGNOSIS_CODE",
        "synonyms": [
            "diagnosis_code",
            "diagnosis",
            "dx_cd",
            "icd10",
            "icd",
        ],
    },

    "service_date": {
        "semantic_type": "DATE",
        "synonyms": [
            "service_date",
            "date_of_service",
            "dos",
        ],
    },

    "billed_amount": {
        "semantic_type": "AMOUNT",
        "synonyms": [
            "billed_amount",
            "billed_amt",
            "charge_amount",
            "claim_amount",
            "charge",
        ],
    },

    "allowed_amount": {
        "semantic_type": "AMOUNT",
        "synonyms": [
            "allowed_amount",
            "allow_amt",
            "approved_amount",
            "eligible_amount",
        ],
    },

    "paid_amount": {
        "semantic_type": "AMOUNT",
        "synonyms": [
            "paid_amount",
            "paid_amt",
            "payment_amount",
            "reimbursement",
        ],
    },

    "place_of_service": {
        "semantic_type": "LOCATION",
        "synonyms": [
            "place_of_service",
            "pos",
            "service_location",
            "facility_type",
        ],
    },

    "claim_status": {
        "semantic_type": "STATUS",
        "synonyms": [
            "claim_status",
            "clm_status",
            "status",
            "processing_status",
        ],
    },

    "payer_id": {
        "semantic_type": "IDENTIFIER",
        "synonyms": [
            "payer_id",
            "payer_cd",
            "insurance_id",
            "health_plan",
            "plan_id",
        ],
    },
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_name(name):
    """
    Normalize source/target field names before comparison.
    """

    name = str(name).lower().strip()

    name = re.sub(
        r"[^a-z0-9]+",
        "_",
        name,
    )

    return name.strip("_")


# ============================================================
# STRING SIMILARITY
# ============================================================

def similarity_score(
    source_name,
    candidate_name,
):
    """
    Calculate string similarity from 0 to 1.
    """

    source = normalize_name(source_name)
    candidate = normalize_name(candidate_name)

    if source == candidate:
        return 1.0

    return SequenceMatcher(
        None,
        source,
        candidate,
    ).ratio()


# ============================================================
# NAME SCORE
# ============================================================

def calculate_name_score(
    source_name,
    target_name,
    synonyms,
):
    """
    Find the best similarity between the source field
    and the target field/synonyms.
    """

    candidates = [
        target_name,
        *synonyms,
    ]

    scores = [
        similarity_score(
            source_name,
            candidate,
        )
        for candidate in candidates
    ]

    return max(scores)


# ============================================================
# SEMANTIC TYPE SCORE
# ============================================================

def calculate_semantic_score(
    source_type,
    target_type,
):
    """
    Score semantic compatibility.
    """

    if source_type == target_type:
        return 1.0

    return 0.0


# ============================================================
# VALUE PATTERN SCORE
# ============================================================

def calculate_value_score(
    source_column,
    target_name,
):
    """
    Use observed sample values to provide additional
    evidence for common healthcare identifiers.
    """

    samples = [
        str(value).upper()
        for value in source_column.get(
            "sample_values",
            []
        )
    ]

    if not samples:
        return 0.0

    matches = 0

    for value in samples:

        if (
            target_name == "claim_id"
            and value.startswith("CLM-")
        ):
            matches += 1

        elif (
            target_name == "member_id"
            and value.startswith("MEM-")
        ):
            matches += 1

        elif (
            target_name == "provider_id"
            and value.startswith("NPI-")
        ):
            matches += 1

        elif (
            target_name == "payer_id"
            and value.startswith("PAY")
        ):
            matches += 1

    return matches / len(samples)


# ============================================================
# TOTAL CANDIDATE SCORE
# ============================================================

def calculate_candidate_score(
    source_column,
    target_name,
    target_definition,
):
    """
    Calculate mapping confidence using:

        60% field-name similarity
        25% semantic compatibility
        15% observed value patterns
    """

    name_score = calculate_name_score(
        source_column["column_name"],
        target_name,
        target_definition[
            "synonyms"
        ],
    )

    semantic_score = (
        calculate_semantic_score(
            source_column[
                "semantic_type"
            ],
            target_definition[
                "semantic_type"
            ],
        )
    )

    value_score = (
        calculate_value_score(
            source_column,
            target_name,
        )
    )

    final_score = (
        name_score * 0.60
        + semantic_score * 0.25
        + value_score * 0.15
    )

    return {
        "name_score": round(
            name_score * 100,
            2,
        ),

        "semantic_score": round(
            semantic_score * 100,
            2,
        ),

        "value_score": round(
            value_score * 100,
            2,
        ),

        "confidence": round(
            final_score * 100,
            2,
        ),
    }


# ============================================================
# REVIEW DECISION
# ============================================================

def get_mapping_decision(confidence):
    """
    Determine whether a mapping can be automatically
    accepted or requires human review.
    """

    if confidence >= 90:
        return "AUTO_MAP"

    if confidence >= 70:
        return "REVIEW"

    return "MANUAL"


# ============================================================
# FIND BEST TARGET
# ============================================================

def find_best_mapping(source_column):
    """
    Evaluate one source field against the complete
    MedMap target schema.
    """

    candidates = []

    for (
        target_name,
        target_definition,
    ) in TARGET_SCHEMA.items():

        scores = calculate_candidate_score(
            source_column,
            target_name,
            target_definition,
        )

        candidates.append(
            {
                "target_field":
                    target_name,

                **scores,
            }
        )

    candidates.sort(
        key=lambda item:
            item["confidence"],
        reverse=True,
    )

    best = candidates[0]

    return {
        "source_field":
            source_column[
                "column_name"
            ],

        "source_semantic_type":
            source_column[
                "semantic_type"
            ],

        "target_field":
            best[
                "target_field"
            ],

        "confidence":
            best[
                "confidence"
            ],

        "decision":
            get_mapping_decision(
                best[
                    "confidence"
                ]
            ),

        "score_details": {
            "name_score":
                best[
                    "name_score"
                ],

            "semantic_score":
                best[
                    "semantic_score"
                ],

            "value_score":
                best[
                    "value_score"
                ],
        },

        "alternative_targets":
            [
                {
                    "target_field":
                        candidate[
                            "target_field"
                        ],

                    "confidence":
                        candidate[
                            "confidence"
                        ],
                }

                for candidate
                in candidates[1:4]
            ],
    }


# ============================================================
# LOAD PROFILE
# ============================================================

def load_profile(profile_path):

    profile_path = Path(
        profile_path
    )

    with open(
        profile_path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# MAP CLIENT
# ============================================================

def map_client_profile(
    client_name,
    profile,
):
    """
    Generate source-to-target mappings for one client.
    """

    mappings = []

    for source_column in profile[
        "columns"
    ]:

        mapping = find_best_mapping(
            source_column
        )

        mappings.append(
            mapping
        )

    return {
        "client_name":
            client_name,

        "source_file":
            profile[
                "file_name"
            ],

        "target_model":
            "MEDMAP_COMMON_CLAIMS_MODEL",

        "mapping_count":
            len(mappings),

        "mappings":
            mappings,
    }


# ============================================================
# SAVE MAPPING
# ============================================================

def save_mapping(
    client_name,
    mapping_result,
):

    output_path = (
        MAPPING_OUTPUT_DIR
        / f"{client_name}_mapping.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            mapping_result,
            file,
            indent=2,
        )

    return output_path


# ============================================================
# DISPLAY RESULTS
# ============================================================

def print_mapping_result(
    mapping_result,
):

    print()
    print("=" * 100)

    print(
        f"CLIENT: "
        f"{mapping_result['client_name'].upper()}"
    )

    print("=" * 100)

    print(
        f"{'SOURCE FIELD':<24}"
        f"{'TARGET FIELD':<24}"
        f"{'CONFIDENCE':<14}"
        f"DECISION"
    )

    print("-" * 100)

    for mapping in mapping_result[
        "mappings"
    ]:

        print(
            f"{mapping['source_field']:<24}"
            f"{mapping['target_field']:<24}"
            f"{mapping['confidence']:>6.2f}%"
            f"{'':<7}"
            f"{mapping['decision']}"
        )


# ============================================================
# PROCESS ALL CLIENTS
# ============================================================

def process_all_clients():

    profile_files = {
        "client_a":
            PROFILE_DIR
            / "client_a_profile.json",

        "client_b":
            PROFILE_DIR
            / "client_b_profile.json",

        "client_c":
            PROFILE_DIR
            / "client_c_profile.json",
    }

    results = {}

    for (
        client_name,
        profile_path,
    ) in profile_files.items():

        if not profile_path.exists():

            raise FileNotFoundError(
                f"Profile not found: "
                f"{profile_path}"
            )

        profile = load_profile(
            profile_path
        )

        mapping_result = (
            map_client_profile(
                client_name,
                profile,
            )
        )

        save_mapping(
            client_name,
            mapping_result,
        )

        print_mapping_result(
            mapping_result
        )

        results[
            client_name
        ] = mapping_result

    return results


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results):

    mappings = [
        mapping

        for result
        in results.values()

        for mapping
        in result[
            "mappings"
        ]
    ]

    auto_count = sum(
        mapping["decision"]
        == "AUTO_MAP"
        for mapping in mappings
    )

    review_count = sum(
        mapping["decision"]
        == "REVIEW"
        for mapping in mappings
    )

    manual_count = sum(
        mapping["decision"]
        == "MANUAL"
        for mapping in mappings
    )

    average_confidence = (
        sum(
            mapping[
                "confidence"
            ]
            for mapping in mappings
        )
        / len(mappings)
    )

    print()
    print("=" * 100)

    print(
        "MEDMAP SOURCE-TO-TARGET "
        "MAPPING SUMMARY"
    )

    print("=" * 100)

    print(
        f"Clients processed     : "
        f"{len(results)}"
    )

    print(
        f"Mappings generated    : "
        f"{len(mappings)}"
    )

    print(
        f"Auto mappings         : "
        f"{auto_count}"
    )

    print(
        f"Review required       : "
        f"{review_count}"
    )

    print(
        f"Manual mappings       : "
        f"{manual_count}"
    )

    print(
        f"Average confidence    : "
        f"{average_confidence:.2f}%"
    )

    print("=" * 100)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 100)

    print(
        "MEDMAP NAVIGATOR - "
        "SOURCE-TO-TARGET MAPPING ENGINE"
    )

    print("=" * 100)

    results = process_all_clients()

    print_summary(
        results
    )


if __name__ == "__main__":
    main()