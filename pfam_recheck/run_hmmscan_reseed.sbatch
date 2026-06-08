#!/bin/bash
#SBATCH --job-name=pfam_reseed
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/reseed_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/reseed_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 --cut_ga \
  --domtblout "$WD/reseed_pfam.domtbl" \
  /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/reseed_proteins.fasta" > "$WD/reseed_hmmscan.stdout"
echo "done: $(grep -vc '^#' "$WD/reseed_pfam.domtbl") rows"
