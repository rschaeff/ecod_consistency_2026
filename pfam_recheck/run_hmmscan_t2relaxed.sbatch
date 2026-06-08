#!/bin/bash
#SBATCH --job-name=pfam_t2rx
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t2rx_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t2rx_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 -E 10 --domE 10 \
  --domtblout "$WD/t2_674_relaxed.domtbl" /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/t2_674_proteins.fasta" > "$WD/t2_674_relaxed.stdout"
echo "done: $(grep -vc '^#' "$WD/t2_674_relaxed.domtbl") rows"
