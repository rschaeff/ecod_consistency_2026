#!/bin/bash
#SBATCH --job-name=pfam_t2
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:40:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t2_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t2_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 --cut_ga \
  --domtblout "$WD/t2_674.domtbl" /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/t2_674_proteins.fasta" > "$WD/t2_674.stdout"
echo "done: $(grep -vc '^#' "$WD/t2_674.domtbl") rows"
