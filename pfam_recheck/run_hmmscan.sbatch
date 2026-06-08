#!/bin/bash
#SBATCH --job-name=pfam_recheck
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/slurm_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/slurm_%j.err

set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
HMMSCAN=/data/ecod/hmmer-3.1b2/binaries/hmmscan
PFAM=/home/rschaeff/data/pfam/v38.2/Pfam-A.hmm

# Current policy: full protein sequence, gathering threshold (--cut_ga).
# --domtblout gives per-domain envelope coords; overlap resolution ("top hit
# per region") is done downstream in Python.
"$HMMSCAN" --cpu 8 --cut_ga \
  --domtblout "$WD/mover_pfam.domtbl" \
  "$PFAM" "$WD/mover_proteins.fasta" > "$WD/hmmscan.stdout"

echo "hmmscan done: $(grep -vc '^#' "$WD/mover_pfam.domtbl") domtbl rows"
