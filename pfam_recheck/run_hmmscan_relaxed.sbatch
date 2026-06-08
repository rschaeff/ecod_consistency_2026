#!/bin/bash
#SBATCH --job-name=pfam_relaxed
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:40:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/relaxed_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/relaxed_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
# NO --cut_ga: capture sub-gathering-threshold hits (default E=10) so we can see
# whether the composite's "extra" Pfam is genuinely absent or just below GA.
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 -E 10 --domE 10 \
  --domtblout "$WD/mover_pfam_relaxed.domtbl" \
  /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/mover_proteins.fasta" > "$WD/relaxed_hmmscan.stdout"
echo "done: $(grep -vc '^#' "$WD/mover_pfam_relaxed.domtbl") rows"
