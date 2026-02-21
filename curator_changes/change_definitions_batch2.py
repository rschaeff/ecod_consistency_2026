"""
Central configuration for batch 2 curator classification changes.

Reference: docs/CURATOR_CHANGES_BATCH2.md
"""

from change_definitions import REQUESTED_BY

# --- Change 1: TLC/ELO/TMEM120 unification ---

TLC_ELO_TMEM120_UNIFICATION = {
    "id": "B2_1",
    "description": "Unification of membrane protein families TLC, ELO, TMEM120",
    "new_xgroup_name": "TMEM120/ELO/TLC",
    "a_group": "a.7",  # alpha bundles
    "families": [
        {
            "name": "TRAM_LAG1_CLN8",
            "pfam_acc": "PF03798",
            "prov_manual_rep": "Q20297_F1_nD1",
            "source_fgroups": [
                "150.1.1.89", "192.29.1.139", "310.2.1.18",
                "3567.1.1.76", "5050.1.1.47", "5054.1.1.17",
                "7015.1.1.8",
            ],
        },
        {
            "name": "ELO",
            "pfam_acc": "PF01151",
            "prov_manual_rep": "Q6P978_F1_nD1",
            "source_fgroups": [
                "192.29.1.45", "5054.1.1.26",
            ],
        },
        {
            "name": "TMPIT",
            "pfam_acc": "PF07851",
            "prov_manual_rep": "B6TPF5_F1_nD2",
            "source_fgroups": [
                "150.1.1.25", "3755.3.1.407",
            ],
        },
    ],
}

# Source X-groups that may need deprecation if emptied
TLC_ELO_TMEM120_SOURCE_XGROUPS = [
    # (x_id, h_id, t_id) — only deprecate if all F-groups under T are deprecated
    # We check dynamically rather than listing every possible T/H/X
]

# --- Change 2: VSG + HpHbR X-group merge ---

VSG_HPBHR_MERGE = {
    "id": "B2_2",
    "description": "Merge Trypanosoma surface glycoprotein X-groups",
    "source_x": "3633",
    "source_h": "3633.1",
    "source_t": "3633.1.1",
    "target_t": "1189.1.1",
    "target_x": "1189",
    "new_name": "VSG (variant surface glycoprotein) N-terminal domain and haptoglobin-hemoglobin receptor",
    "new_a_group": "a.7",  # alpha bundles, per curator
    "fgroup_mapping": [
        {
            "source_f": "3633.1.1.1",
            "pfam": "GARP",
            "pfam_acc": "PF16731",
            "target_f": None,  # create new under 1189.1.1
        },
        {
            "source_f": "3633.1.1.2",
            "pfam": "HpHbR",
            "pfam_acc": "PF20933",
            "target_f": None,
        },
        {
            "source_f": "3633.1.1.3",
            "pfam": "ESAG1",
            "pfam_acc": "PF03238",
            "target_f": None,
        },
    ],
}

# --- Change 3a: Cyanophycin_syn new X-group ---

CYANOPHYCIN_SYN_EXTRACTION = {
    "id": "B2_3a",
    "description": "Extract Cyanophycin_syn to new X-group",
    "source_f": "2007.3.1.5",
    "new_xgroup_name": "Cyanophycin_syn",
    "a_group": "a.17",
    "pfam_acc": "PF18921",
    "split_pfams": {
        "cyanophycin": "PF18921",  # N-terminal portion stays
        "atp_grasp": "PF18419",    # C-terminal portion -> Change 3b
    },
    "reference_domain": "e7lg5A4",
    "reference_split": {"cyanophycin": "A:1-162", "atp_grasp": "A:163-208"},
}

# --- Change 3b: ATP-grasp_6 new X-group ---

ATP_GRASP_6_EXTRACTION = {
    "id": "B2_3b",
    "description": "Extract ATP-grasp_6 to new X-group",
    "source_f": "2003.1.10.18",
    "new_xgroup_name": "ATP-grasp_6",
    "a_group": "a.17",
    "pfam_acc": "PF18419",
}

# --- Change 4: KH_domain-like boundary fix ---

KH_DOMAIN_BOUNDARY_FIX = {
    "id": "B2_4",
    "description": "Fix MMR_HSR1/KH_dom-like boundary in Der GTPase structures",
    "mmr_f_group": "2004.1.1.73",     # MMR_HSR1 (extends C-term)
    "kh_f_group": "327.9.1.1",        # KH_dom-like (trims N-term)
    "reference": {
        "domain": "Q83C83_nD2",       # UniProt domain with correct boundary
        "mmr_range": "171-350",
        "kh_range": "351-443",
    },
    # 17 PDB domain pairs to fix (KH domain_id, paired MMR domain_id)
    "pairs": [
        ("e2hjgA2", "e2hjgA1"),
        ("e3j8gX2", "e3j8gX3"),
        ("e4dcsA2", "e4dcsA1"),
        ("e4dctA1", "e4dctA2"),
        ("e4dcvA2", "e4dcvA1"),
        ("e5dn8A3", "e5dn8A2"),
        ("e5m7hA1", "e5m7hA2"),
        ("e5mbsA3", "e5mbsA2"),
        ("e6xrsA3", "e6xrsA2"),
        ("e6xrsB3", "e6xrsB1"),
        ("e6xrsC1", "e6xrsC3"),
        ("e6xrsD3", "e6xrsD2"),
        ("e6yxxEA3", "e6yxxEA1"),
        ("e6yxyEA3", "e6yxyEA1"),
        ("e7am2BU2", "e7am2BU1"),
        ("e7aoiXL3", "e7aoiXL1"),
        ("e9bs0W03", "e9bs0W02"),
    ],
}

# --- Change 5: Helicase_C,RIG-I_C split ---

HELICASE_RIGI_SPLIT = {
    "id": "B2_5",
    "description": "Split Helicase_C,RIG-I_C into RIG-I_C and Helicase_C",
    "source_f": "3930.1.1.1",
    "targets": {
        "rigi_c": {
            "f_group": "3930.1.1.2",
            "pfam_acc": "PF18119",
        },
        "helicase_c": {
            "f_group": "2004.1.1.30",
            "pfam_acc": "PF00271",
        },
    },
    "dead_f_group": "2004.1.1.29",  # neighboring DEAD domain to fix
    # PDBs with already-correct splits (exclude from processing)
    "exclude_pdbs": ["7tnx", "8dvr", "8g7t"],
}
