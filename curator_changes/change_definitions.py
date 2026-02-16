"""
Central configuration for all curator classification changes.

All change parameters are defined here to keep implementation scripts clean.
Reference: docs/CURATOR_CHANGE_PLAN.md
"""

# --- Change 1: X-group Merges ---

XGROUP_MERGES = [
    {
        "id": "1C",
        "source_x": "3488",
        "source_h": "3488.1",
        "source_t": "3488.1.1",
        "target_t": "223.1.1",
        "description": "Putative sensor histidine kinase -> sensor domains (Profilin-like)",
        "fgroup_mapping": [
            {
                "source_f": "3488.1.1.1",
                "pfam": "dCache_2",
                "pfam_acc": "PF08269",
                "target_f": None,  # no match in 223.1.1 -> create new
            },
            {
                "source_f": "3488.1.1.2",
                "pfam": "sCache_2",
                "pfam_acc": "PF17200",
                "target_f": None,  # no match in 223.1.1 -> create new
            },
        ],
    },
    {
        "id": "1B",
        "source_x": "1139",
        "source_h": "1139.1",
        "source_t": "1139.1.1",
        "target_t": "327.6.1",
        "description": "Secretin domain -> Fe-S cluster assembly (FSCA) domain-like",
        "fgroup_mapping": [
            {
                "source_f": "1139.1.1.1",
                "pfam": "Secretin",
                "pfam_acc": "PF00263",
                "target_f": None,  # no match in 327.6.1 -> create new
            },
        ],
    },
    {
        "id": "1A",
        "source_x": "7584",
        "source_h": "7584.1",
        "source_t": "7584.1.1",
        "target_t": "323.1.1",
        "description": "Rossmann-like domain in Acetyl-CoA synthetase-like -> CoA-dependent acyltransferases",
        "fgroup_mapping": [
            {
                "source_f": "7584.1.1.1",
                "pfam": "AMP-binding",
                "pfam_acc": "PF00501",
                "target_f": "323.1.1.3",  # MERGE: same pfam_acc PF00501
            },
            {
                "source_f": "7584.1.1.2",
                "pfam": "AMP-binding,ACAS_N",
                "pfam_acc": "PF00501,PF16177",
                "target_f": None,  # no exact pfam match -> create new
            },
            {
                "source_f": "7584.1.1.3",
                "pfam": "GH3",
                "pfam_acc": "PF03321",
                "target_f": None,  # no match -> create new
            },
            {
                "source_f": "7584.1.1.4",
                "pfam": "ACAS_N",
                "pfam_acc": "PF16177",
                "target_f": None,  # no match -> create new
            },
            {
                "source_f": "7584.1.1.5",
                "pfam": "LuxE",
                "pfam_acc": "PF04443",
                "target_f": None,  # no match -> create new
            },
        ],
    },
]


# --- Change 2: Family-Level Reclassifications ---

FAMILY_RECLASSIFICATIONS = [
    {
        "id": "2A",
        "source_f": "274.1.1.3",
        "target_f": "301.3.1.1",
        "description": "OmpA domains: Pili subunits -> OmpA-like",
        "pfam_filter": "OmpA",  # PF00691
        "move_entire_fgroup": True,  # move all domains in 274.1.1.3
    },
    {
        "id": "2B_part1",
        "source_f": "310.1.1.1",
        "target_f": "140.1.1.3",
        "description": "tRNA-synt_1d,DALR_1: ArgRS N-terminal -> Anticodon-binding domain",
        "pfam_filter": "tRNA-synt_1d,DALR_1",
        "move_entire_fgroup": True,
    },
    {
        "id": "2B_part2",
        "source_f": "310.1.1.3",
        "target_f": "140.1.1.3",
        "description": "DALR_1: ArgRS N-terminal -> Anticodon-binding domain",
        "pfam_filter": "DALR_1",
        "move_entire_fgroup": True,
    },
]


# --- Change 2C: Domain Split ---

DOMAIN_SPLITS = [
    {
        "id": "2C",
        "source_f": "380.1.1.3",
        "source_f_name": "Kringle,WSC",
        "reference_domain": "e5fwwB1",
        "reference_ecod_uid": None,  # will be looked up
        "splits": [
            {
                "name": "Kringle",
                "ref_range_start": 30,
                "ref_range_end": 115,
                "target_f": "380.1.1.2",
                "pfam_acc": "PF00051",
            },
            {
                "name": "WSC",
                "ref_range_start": 116,
                "ref_range_end": 213,
                "target_f": "390.1.1.2",
                "pfam_acc": "PF01822",
            },
        ],
    },
]


# --- Change 3: Boundary Corrections ---

BOUNDARY_CORRECTIONS = [
    {
        "id": "3A",
        "domain_id": "e6bmsD1",
        "current_range": "D:79-240",
        "new_range": "D:79-156",
        "f_group": "4106.1.1.1",
        "description": "Trim non-zinc-hairpin C-terminal extension",
        "ecod_commons_only": True,  # domain is AUTO_NONREP, not in ecod_rep
    },
    {
        "id": "3B",
        "f_group": "563.1.1",
        "description": "Fix over-extended OSCP N-terminal domain boundaries",
        "reference_domain": "e1abvA1",
        "reference_length": 105,
        "max_expected_length": 150,  # domains longer than this are candidates for trimming
        "curator_specified_domains": ["e6rdqP1"],
    },
]


# --- Shared constants ---

REQUESTED_BY = 'curator_change_pipeline'
BATCH_PREFIX = 'curator_change_2026'
