#!/bin/bash
#SBATCH --job-name=clans_consistency
#SBATCH --output=logs/clans_%A_%a.out
#SBATCH --error=logs/clans_%A_%a.err
#SBATCH --partition=96GB
#SBATCH --time=2:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4

# ECOD F-group Consistency Analysis - CLANS Job (with offset support)
# This script runs CLANS on a single H-group FASTA file
# Use JOB_OFFSET environment variable to shift array task IDs

set -e

# Configuration
PROJECT_ROOT="/home/rschaeff/work/ecod_consistency_2026"
CLANS_PATH="/home/rschaeff/dev/claude_clans/CLANS"
RESULTS_DIR="${PROJECT_ROOT}/results"

# CLANS parameters
ROUNDS=500
PVAL="1e-4"
CORES=${SLURM_CPUS_PER_TASK:-4}

# Apply offset to get actual job ID
# Usage: JOB_OFFSET=1000 sbatch --array=1-471 run_clans_job_offset.sh
JOB_OFFSET=${JOB_OFFSET:-0}

# Create unique temporary working directory for this job
JOB_TMPDIR="/tmp/clans_job_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
mkdir -p "$JOB_TMPDIR"

# Cleanup function
cleanup() {
    if [ -d "$JOB_TMPDIR" ]; then
        rm -rf "$JOB_TMPDIR"
    fi
}
trap cleanup EXIT

# Get job info from manifest
MANIFEST="${PROJECT_ROOT}/jobs/job_manifest.json"

if [ -z "$SLURM_ARRAY_TASK_ID" ]; then
    echo "Error: This script must be run as a SLURM array job"
    exit 1
fi

# Calculate actual job ID with offset
JOB_ID=$((SLURM_ARRAY_TASK_ID + JOB_OFFSET))

# Extract job info
JOB_INFO=$(python3 << EOF
import json
with open("${MANIFEST}") as f:
    manifest = json.load(f)

job = None
for j in manifest["jobs"]:
    if j["job_id"] == ${JOB_ID}:
        job = j
        break

if job:
    print(f"{job['h_group_id']}|{job['fasta_file']}|{job['domain_count']}|{job['f_group_count']}")
else:
    print("NOT_FOUND")
EOF
)

if [ "$JOB_INFO" = "NOT_FOUND" ]; then
    echo "Error: Job ID ${JOB_ID} not found in manifest"
    exit 1
fi

# Parse job info
IFS='|' read -r H_GROUP_ID FASTA_FILE DOMAIN_COUNT F_GROUP_COUNT <<< "$JOB_INFO"

echo "=========================================="
echo "CLANS Consistency Analysis Job"
echo "=========================================="
echo "Job ID: ${JOB_ID} (array task ${SLURM_ARRAY_TASK_ID} + offset ${JOB_OFFSET})"
echo "SLURM Job: ${SLURM_JOB_ID}"
echo "H-group: ${H_GROUP_ID}"
echo "Domains: ${DOMAIN_COUNT}"
echo "F-groups: ${F_GROUP_COUNT}"
echo "FASTA: ${FASTA_FILE}"
echo "Started: $(date)"
echo "=========================================="

# Check FASTA exists
if [ ! -f "$FASTA_FILE" ]; then
    echo "Error: FASTA file not found: ${FASTA_FILE}"
    exit 1
fi

# Create output directory
SAFE_HGROUP=$(echo "$H_GROUP_ID" | tr '.' '_')
OUTPUT_DIR="${RESULTS_DIR}/${SAFE_HGROUP}"
mkdir -p "$OUTPUT_DIR"

OUTPUT_FILE="${OUTPUT_DIR}/${SAFE_HGROUP}.clans"

# Activate conda environment
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

if conda env list | grep -q "clans_test\|clans_2_2"; then
    conda activate clans_test 2>/dev/null || conda activate clans_2_2 2>/dev/null || true
fi

# Run CLANS from unique temp directory
echo ""
echo "Running CLANS..."
echo "Working directory: ${JOB_TMPDIR}"
echo "Command: python ${CLANS_PATH}/run_clans_cmd.py -nogui \\"
echo "    -infile ${FASTA_FILE} \\"
echo "    -saveto ${OUTPUT_FILE} \\"
echo "    -dorounds ${ROUNDS} \\"
echo "    -pval ${PVAL} \\"
echo "    -cores ${CORES}"
echo ""

cd "$JOB_TMPDIR"

python "${CLANS_PATH}/run_clans_cmd.py" -nogui \
    -infile "$FASTA_FILE" \
    -saveto "$OUTPUT_FILE" \
    -dorounds "$ROUNDS" \
    -pval "$PVAL" \
    -cores "$CORES"

CLANS_EXIT=$?

if [ $CLANS_EXIT -ne 0 ]; then
    echo "Error: CLANS failed with exit code ${CLANS_EXIT}"
    exit $CLANS_EXIT
fi

echo ""
echo "CLANS completed successfully"
echo "Output: ${OUTPUT_FILE}"

# Create job completion marker
echo "{
    \"job_id\": ${JOB_ID},
    \"h_group_id\": \"${H_GROUP_ID}\",
    \"domain_count\": ${DOMAIN_COUNT},
    \"f_group_count\": ${F_GROUP_COUNT},
    \"output_file\": \"${OUTPUT_FILE}\",
    \"completed_at\": \"$(date -Iseconds)\",
    \"slurm_job_id\": \"${SLURM_JOB_ID}\"
}" > "${OUTPUT_DIR}/job_complete.json"

echo "Finished: $(date)"
echo "=========================================="
