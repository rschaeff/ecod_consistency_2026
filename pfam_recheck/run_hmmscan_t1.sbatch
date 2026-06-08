#!/bin/bash
#SBATCH --job-name=pfam_t1
#SBATCH --cpus-per-task=16
#SBATCH --mem=12G
#SBATCH --time=01:00:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t1_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t1_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 16 --cut_ga \
  --domtblout "$WD/repsel_t1.domtbl" /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/repsel_t1_domseqs.fasta" > "$WD/repsel_t1.stdout"
echo "done: $(grep -vc '^#' "$WD/repsel_t1.domtbl") rows"
