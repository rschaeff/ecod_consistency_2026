#!/bin/bash
#SBATCH --job-name=pfam_rs2
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/rs2_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/rs2_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 --cut_ga \
  --domtblout "$WD/repsel_pilot_dom.domtbl" /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/repsel_pilot_domseqs.fasta" > "$WD/repsel_pilot_dom.stdout"
echo "done: $(grep -vc '^#' "$WD/repsel_pilot_dom.domtbl") rows"
