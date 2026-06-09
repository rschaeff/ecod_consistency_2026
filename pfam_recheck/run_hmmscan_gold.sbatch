#!/bin/bash
#SBATCH --job-name=pf_arch
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/arch_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/arch_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 --cut_ga \
  --domtblout "$WD/repsel_gold.domtbl" /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/repsel_gold.fasta" > "$WD/repsel_gold.stdout"
echo "done: $(grep -vc '^#' "$WD/repsel_gold.domtbl") rows"
