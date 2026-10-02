from pathlib import Path
from datetime import datetime, timezone
import json


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MAPPING_DIR = PROJECT_ROOT / "mappings"
APPROVED_DIR = MAPPING_DIR / "approved"

APPROVED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# REVIEW STATUS CONSTANTS
# ============================================================

VALID_REVIEW_STATUSES = {
    "APPROVED",
    "MODIFIED",
    "REJECTED",
}

VALID_SOURCE_DECISIONS = {
    "AUTO_MAP",
    "REVIEW",
    "MANUAL",
}


# ============================================================
# LOAD MAPPING FILE
# ============================================================

def load_mapping_file(client_name):
    """
    Load generated mapping suggestions for one client.
    """

    mapping_path = (
        MAPPING_DIR
        / f"{client_name}_mapping.json"
    )

    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Mapping file not found: {mapping_path}"
        )

    with open(
        mapping_path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# BUILD REVIEW RECORD
# ============================================================

def build_review_record(
    mapping,
    reviewed_by,
    review_status,
    approved_target=None,
    review_notes=None,
):
    """
    Create one analyst review record.
    """

    review_status = review_status.upper()

    if review_status not in VALID_REVIEW_STATUSES:
        raise ValueError(
            f"Invalid review status: {review_status}"
        )

    source_decision = mapping.get(
        "decision",
        "REVIEW",
    )

    if source_decision not in VALID_SOURCE_DECISIONS:
        raise ValueError(
            f"Invalid source mapping decision: {source_decision}"
        )

    suggested_target = mapping[
        "target_field"
    ]

    if review_status == "APPROVED":
        final_target = suggested_target

    elif review_status == "MODIFIED":

        if not approved_target:
            raise ValueError(
                "approved_target is required "
                "when review_status is MODIFIED."
            )

        final_target = approved_target

    else:
        final_target = None

    return {
        "source_field":
            mapping["source_field"],

        "source_semantic_type":
            mapping["source_semantic_type"],

        "suggested_target":
            suggested_target,

        "mapping_confidence":
            mapping["confidence"],

        "source_decision":
            source_decision,

        "review_status":
            review_status,

        "final_target":
            final_target,

        "reviewed_by":
            reviewed_by,

        "review_notes":
            review_notes,

        "reviewed_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


# ============================================================
# AUTO APPROVE HIGH-CONFIDENCE MAPPINGS
# ============================================================

def auto_approve_mappings(
    client_name,
    reviewed_by="SYSTEM",
):
    """
    Automatically approve mappings already classified
    as AUTO_MAP.

    REVIEW and MANUAL mappings remain pending.
    """

    mapping_data = load_mapping_file(
        client_name
    )

    reviews = []

    for mapping in mapping_data[
        "mappings"
    ]:

        if mapping["decision"] == "AUTO_MAP":

            review = build_review_record(
                mapping=mapping,
                reviewed_by=reviewed_by,
                review_status="APPROVED",
                review_notes=(
                    "Automatically approved based on "
                    "high mapping confidence."
                ),
            )

        else:

            review = {
                "source_field":
                    mapping[
                        "source_field"
                    ],

                "source_semantic_type":
                    mapping[
                        "source_semantic_type"
                    ],

                "suggested_target":
                    mapping[
                        "target_field"
                    ],

                "mapping_confidence":
                    mapping[
                        "confidence"
                    ],

                "source_decision":
                    mapping[
                        "decision"
                    ],

                "review_status":
                    "PENDING_REVIEW",

                "final_target":
                    None,

                "reviewed_by":
                    None,

                "review_notes":
                    None,

                "reviewed_at":
                    None,
            }

        reviews.append(
            review
        )

    review_package = {
        "client_name":
            client_name,

        "source_file":
            mapping_data[
                "source_file"
            ],

        "target_model":
            mapping_data[
                "target_model"
            ],

        "review_count":
            len(reviews),

        "reviews":
            reviews,
    }

    return review_package


# ============================================================
# SAVE REVIEW PACKAGE
# ============================================================

def save_review_package(
    client_name,
    review_package,
):
    """
    Save review state for one client.
    """

    output_path = (
        APPROVED_DIR
        / f"{client_name}_review.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            review_package,
            file,
            indent=2,
        )

    return output_path


# ============================================================
# LOAD REVIEW PACKAGE
# ============================================================

def load_review_package(
    client_name,
):
    """
    Load existing review state.
    """

    path = (
        APPROVED_DIR
        / f"{client_name}_review.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Review package not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# REVIEW ONE MAPPING
# ============================================================

def review_mapping(
    client_name,
    source_field,
    reviewed_by,
    review_status,
    approved_target=None,
    review_notes=None,
):
    """
    Update one source-field mapping after analyst review.
    """

    review_package = load_review_package(
        client_name
    )

    mapping_data = load_mapping_file(
        client_name
    )

    original_mapping = None

    for mapping in mapping_data[
        "mappings"
    ]:

        if mapping[
            "source_field"
        ] == source_field:

            original_mapping = mapping
            break

    if original_mapping is None:
        raise ValueError(
            f"Source field not found: {source_field}"
        )

    updated_review = build_review_record(
        mapping=original_mapping,
        reviewed_by=reviewed_by,
        review_status=review_status,
        approved_target=approved_target,
        review_notes=review_notes,
    )

    updated = False

    for index, review in enumerate(
        review_package[
            "reviews"
        ]
    ):

        if review[
            "source_field"
        ] == source_field:

            review_package[
                "reviews"
            ][index] = updated_review

            updated = True
            break

    if not updated:
        raise ValueError(
            f"Review record not found for: {source_field}"
        )

    save_review_package(
        client_name,
        review_package,
    )

    return updated_review


# ============================================================
# REVIEW SUMMARY
# ============================================================

def get_review_summary(
    review_package,
):
    """
    Return review-status statistics.
    """

    reviews = review_package[
        "reviews"
    ]

    return {
        "total":
            len(reviews),

        "approved":
            sum(
                review[
                    "review_status"
                ] == "APPROVED"

                for review in reviews
            ),

        "modified":
            sum(
                review[
                    "review_status"
                ] == "MODIFIED"

                for review in reviews
            ),

        "rejected":
            sum(
                review[
                    "review_status"
                ] == "REJECTED"

                for review in reviews
            ),

        "pending":
            sum(
                review[
                    "review_status"
                ] == "PENDING_REVIEW"

                for review in reviews
            ),
    }


# ============================================================
# PRINT REVIEW PACKAGE
# ============================================================

def print_review_package(
    review_package,
):

    summary = get_review_summary(
        review_package
    )

    print()
    print("=" * 100)

    print(
        f"CLIENT REVIEW: "
        f"{review_package['client_name'].upper()}"
    )

    print("=" * 100)

    print(
        f"{'SOURCE FIELD':<24}"
        f"{'SUGGESTED TARGET':<24}"
        f"{'CONFIDENCE':<14}"
        f"{'STATUS':<18}"
        f"FINAL TARGET"
    )

    print("-" * 100)

    for review in review_package[
        "reviews"
    ]:

        final_target = (
            review[
                "final_target"
            ]
            or "-"
        )

        print(
            f"{review['source_field']:<24}"
            f"{review['suggested_target']:<24}"
            f"{review['mapping_confidence']:>6.2f}%"
            f"{'':<7}"
            f"{review['review_status']:<18}"
            f"{final_target}"
        )

    print()
    print(
        f"Total     : "
        f"{summary['total']}"
    )

    print(
        f"Approved  : "
        f"{summary['approved']}"
    )

    print(
        f"Modified  : "
        f"{summary['modified']}"
    )

    print(
        f"Rejected  : "
        f"{summary['rejected']}"
    )

    print(
        f"Pending   : "
        f"{summary['pending']}"
    )


# ============================================================
# INITIALIZE ALL CLIENT REVIEWS
# ============================================================

def initialize_all_reviews():

    clients = [
        "client_a",
        "client_b",
        "client_c",
    ]

    results = {}

    for client_name in clients:

        review_package = (
            auto_approve_mappings(
                client_name
            )
        )

        save_review_package(
            client_name,
            review_package,
        )

        print_review_package(
            review_package
        )

        results[
            client_name
        ] = review_package

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 100)

    print(
        "MEDMAP NAVIGATOR - "
        "MAPPING REVIEW MANAGER"
    )

    print("=" * 100)

    results = initialize_all_reviews()

    total_pending = sum(
        get_review_summary(
            review_package
        )[
            "pending"
        ]

        for review_package
        in results.values()
    )

    total_approved = sum(
        get_review_summary(
            review_package
        )[
            "approved"
        ]

        for review_package
        in results.values()
    )

    print()
    print("=" * 100)

    print(
        "GLOBAL REVIEW SUMMARY"
    )

    print("=" * 100)

    print(
        f"Clients initialized : "
        f"{len(results)}"
    )

    print(
        f"Auto approved       : "
        f"{total_approved}"
    )

    print(
        f"Pending review      : "
        f"{total_pending}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()