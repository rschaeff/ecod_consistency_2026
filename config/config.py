"""Configuration for ECOD F-group consistency analysis."""

import os

# Database connection - reads from environment variables
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "dione"),
    "port": int(os.environ.get("DB_PORT", 45000)),
    "user": os.environ.get("DB_USER", "ecod"),
    "password": os.environ.get("DB_PASSWORD"),  # Required - no default
    "dbname": os.environ.get("DB_NAME", "ecod_protein")
}

# Validate password is set
if DB_CONFIG["password"] is None:
    raise ValueError(
        "DB_PASSWORD environment variable not set. "
        "Either set it directly or source the .env file: source .env"
    )

# ECOD version
ECOD_VERSION_ID = 2  # v293

# Clustering parameters
CLUSTER_PARAM_SET = "F70"  # Use 70% identity cluster representatives

# CLANS parameters
CLANS_CONFIG = {
    "rounds": 500,
    "cores": 4,
    "pval": 1e-4,  # E-value threshold for connections
    "att_val": 10.0,
    "rep_val": 5.0,
}

# Job size limits
MAX_DOMAINS_PER_JOB = 2000  # Jobs larger than this will be subsampled
MIN_DOMAINS_PER_FGROUP = 2  # Minimum domains per F-group to include

# SLURM configuration
SLURM_CONFIG = {
    "partition": "192GB",
    "time": "2:00:00",
    "mem": "8G",
    "cpus_per_task": 4,
    "mail_type": "FAIL",
}

# Paths
CLANS_PATH = "/home/rschaeff/dev/claude_clans/CLANS"
PROJECT_ROOT = "/home/rschaeff/work/ecod_consistency_2026"
