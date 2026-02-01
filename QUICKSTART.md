# ECOD F-group Consistency Analysis

## Overview

This project evaluates the internal consistency of ECOD F-group classifications using CLANS (CLuster ANalysis of Sequences). The premise is that domains within an F-group should cluster closer to their own F-group centroid than to centroids of related F-groups within the same H-group.

### Why This Approach

- **No gold standard**: We cannot easily evaluate if a classification is "correct"
- **Consistency is testable**: Domains should be closer to their own F-group centroid than to other related F-group centroids
- **Partitioned by H-group**: Each H-group (homologous superfamily) contains F-groups with detectable sequence similarity, making it the natural unit for comparison

### Scale

- ~920K active domains in ECOD v293
- ~13,200 F-groups across ~3,200 H-groups
- **1,471 H-groups** have ≥2 F-groups (requiring consistency tests)
- Uses F70 cluster representatives (~858K) to reduce redundancy

## Prerequisites

- Python 3.8+ with psycopg2
- Access to ECOD database (dione:45000)
- CLANS Python implementation (`~/dev/claude_clans/CLANS`)
- SLURM cluster access

## Directory Structure

```
ecod_consistency_2026/
├── config/
│   └── config.py              # Database, CLANS, and SLURM configuration
├── scripts/
│   ├── generate_jobs.py       # Generate FASTA files and job manifest
│   ├── submit_jobs.py         # Submit array jobs to SLURM
│   ├── run_clans_job.sh       # SLURM job template
│   ├── check_status.py        # Monitor job progress
│   ├── parse_clans.py         # Parse CLANS output files
│   ├── evaluate_consistency.py # Evaluate single H-group
│   └── evaluate_all.py        # Batch evaluation and reporting
├── fasta/                     # Generated FASTA files (one per H-group)
├── jobs/                      # Job manifest and submission records
├── results/                   # CLANS output (.clans files)
├── evaluation/                # Evaluation reports and summaries
└── logs/                      # SLURM stdout/stderr logs
```

## Quick Start

### 1. Generate Jobs

Generate FASTA files for all H-groups with ≥2 F-groups:

```bash
cd /home/rschaeff/work/ecod_consistency_2026
source ~/.bashrc

# Preview what will be generated
python scripts/generate_jobs.py --dry-run

# Generate all jobs (~1,471)
python scripts/generate_jobs.py

# Or generate a subset for testing
python scripts/generate_jobs.py --limit 10
python scripts/generate_jobs.py --h-group "1.1"
```

This creates:
- One FASTA file per H-group in `fasta/`
- Job manifest in `jobs/job_manifest.json`

**FASTA header format:**
```
>domain_name|ecod_uid|f_group_id|t_group_id
```

### 2. Submit to SLURM

```bash
# Preview submission command
python scripts/submit_jobs.py --dry-run

# Submit all jobs
python scripts/submit_jobs.py

# Submit specific range
python scripts/submit_jobs.py --job-range 1-100

# Submit specific H-groups
python scripts/submit_jobs.py --h-groups 1.1 2.1 10.1
```

Jobs are submitted as SLURM array jobs. Each job:
1. Reads its H-group info from the manifest
2. Runs CLANS on the corresponding FASTA file
3. Saves output to `results/<h_group_id>/`

### 3. Monitor Progress

```bash
# Check overall status
python scripts/check_status.py

# SLURM queue
squeue -u $USER

# View specific job logs
tail -f logs/clans_<jobid>_<arrayid>.out
```

### 4. Resume After Interruption

If jobs fail or the cluster is interrupted:

```bash
# Skip already-completed jobs
python scripts/submit_jobs.py --resume
```

## Configuration

Edit `config/config.py` to adjust settings:

```python
# Clustering - which representatives to use
CLUSTER_PARAM_SET = "F70"  # Options: F40, F70, F99

# Job size limits
MAX_DOMAINS_PER_JOB = 2000  # Larger H-groups are subsampled

# CLANS parameters
CLANS_CONFIG = {
    "rounds": 500,      # Force-directed layout iterations
    "cores": 4,         # CPUs per job
    "pval": 1e-4,       # E-value threshold for connections
}

# SLURM settings
SLURM_CONFIG = {
    "partition": "batch",
    "time": "2:00:00",
    "mem": "8G",
    "cpus_per_task": 4,
}
```

## Output

Each completed job produces:

```
results/<h_group_id>/
├── <h_group_id>.clans    # CLANS output file with coordinates
└── job_complete.json     # Completion metadata
```

The `.clans` file contains:
- 3D coordinates for each domain after force-directed layout
- Connection strengths (E-values) between domains
- Algorithm parameters used

## Job Statistics

| Category | Count | Description |
|----------|-------|-------------|
| Total H-groups tested | ~1,471 | H-groups with ≥2 F-groups |
| 2 F-groups | 664 | Simple pairwise comparisons |
| 3-5 F-groups | 501 | Small multi-family tests |
| 6-10 F-groups | 154 | Medium complexity |
| >10 F-groups | 152 | Large, may be subsampled |

## Troubleshooting

### Job fails with "No representatives found"
The H-group may have F-groups without F70 cluster representatives. Check the database:
```sql
SELECT f_group_id, COUNT(*)
FROM ecod_commons.cluster_representatives
WHERE f_group_id LIKE '<h_group>%' AND parameter_set_name = 'F70'
GROUP BY f_group_id;
```

### CLANS runs out of memory
Reduce `MAX_DOMAINS_PER_JOB` in config or increase SLURM memory allocation.

### Jobs stuck in pending
Check cluster availability: `sinfo -p batch`

## Evaluation Pipeline

After CLANS jobs complete, evaluate F-group consistency:

### 5. Evaluate All Completed Jobs

```bash
# Run batch evaluation on all completed jobs
python scripts/evaluate_all.py

# Evaluate specific H-groups only
python scripts/evaluate_all.py --h-groups 1.1 2.1

# Limit for testing
python scripts/evaluate_all.py --limit 10

# Custom output directory
python scripts/evaluate_all.py --output-dir ./my_evaluation
```

This generates:
- `evaluation/summary.csv` - One row per H-group with metrics
- `evaluation/inconsistent_domains.csv` - All domains failing consistency
- `evaluation/TRIAGE_REPORT.md` - Markdown report for manual review
- `evaluation/all_results.json` - Complete results in JSON
- `results/<h_group>/evaluation.json` - Per-job detailed results

### 6. Evaluate Single H-group

```bash
# Summary view
python scripts/evaluate_consistency.py results/1_1/1_1.clans --summary

# Full JSON output
python scripts/evaluate_consistency.py results/1_1/1_1.clans -o result.json
```

### 7. Parse CLANS Files

```bash
# Inspect a CLANS file
python scripts/parse_clans.py results/1_1/1_1.clans
```

## Evaluation Metrics

### Per-Domain Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| `distance_ratio` | own_centroid_dist / nearest_other_dist | <1.0 = consistent, >1.0 = inconsistent |
| `silhouette` | Clustering quality score | -1 to +1, higher = better separated |
| `is_consistent` | Boolean flag | True if distance_ratio < 1.0 |

### Per-H-group Metrics

| Metric | Description | Flag for Review |
|--------|-------------|-----------------|
| `consistency_rate` | Fraction of consistent domains | <90% |
| `mean_silhouette` | Average silhouette score | <0.1 |
| `inconsistent_count` | Number of inconsistent domains | - |

### Triage Criteria

H-groups are flagged for manual review if:
- **Consistency rate < 90%**: Many domains closer to wrong centroid
- **Mean silhouette < 0.1**: Poor cluster separation overall

## Interpreting Results

### Critical Caveat: Pfam Distance ≠ BLAST Distance

**Important:** Analysis revealed that only ~22% of H-groups have F-groups that form distinct BLAST-detectable clusters. For the remaining ~78%, F-groups are defined by Pfam HMM matches that capture relationships pairwise BLAST cannot detect.

Before interpreting consistency scores, check the **separation ratio** in `evaluation/separation_analysis.csv`:

| Separation Ratio | % of H-groups | Consistency Interpretation |
|------------------|---------------|---------------------------|
| < 1.0 | 21.7% | Meaningful - low scores suggest issues |
| ≥ 1.0 | 78.3% | Expected to be low - not a quality problem |

See `analysis/METHODOLOGY_FINDINGS.md` for full details.

### Consistency Rate (for H-groups with separation ratio < 1.0)

| Rate | Interpretation |
|------|----------------|
| ≥95% | Excellent - F-groups are well-separated |
| 90-95% | Good - Minor boundary cases |
| 80-90% | Review needed - Some misclassifications likely |
| <80% | Significant issues - F-group definitions may need revision |

### Distance Ratio

| Ratio | Meaning |
|-------|---------|
| <0.5 | Strongly consistent - clearly belongs to assigned F-group |
| 0.5-1.0 | Consistent - closer to own centroid |
| 1.0-1.5 | Borderline - nearly equidistant |
| 1.5-2.0 | Inconsistent - notably closer to another F-group |
| >2.0 | Strongly inconsistent - likely misclassified |

### Common Patterns

1. **Single outlier domain**: One domain with high ratio
   - May be misclassified or represent a transitional form

2. **Cluster of inconsistent domains**: Multiple domains from same F-group
   - F-group may need to be split or merged

3. **Bidirectional inconsistency**: Domains from F-groups A and B both closer to each other
   - F-groups may need to be merged

4. **Low silhouette, high consistency**:
   - F-groups overlap but centroids are distinct
   - May be acceptable if biological rationale exists
