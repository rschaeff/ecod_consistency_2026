#!/bin/bash
#SBATCH --job-name=pfam37_disambig
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/pfam37_%j.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/pfam37_%j.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
HS=/data/ecod/hmmer-3.1b2/binaries/hmmscan
P37=/home/rschaeff/data/pfam/v37.4/Pfam-A.hmm
# cut_ga: does Q pass the 37.4 gathering threshold?  relaxed: Q raw score under 37.4
"$HS" --cpu 8 --cut_ga --domtblout "$WD/disambig19_37_cutga.domtbl" "$P37" "$WD/disambig19.fasta" > "$WD/d19_37_cutga.out"
"$HS" --cpu 8 -E 10 --domE 10 --domtblout "$WD/disambig19_37_relaxed.domtbl" "$P37" "$WD/disambig19.fasta" > "$WD/d19_37_relaxed.out"
echo "cutga rows: $(grep -vc '^#' "$WD/disambig19_37_cutga.domtbl"); relaxed rows: $(grep -vc '^#' "$WD/disambig19_37_relaxed.domtbl")"
