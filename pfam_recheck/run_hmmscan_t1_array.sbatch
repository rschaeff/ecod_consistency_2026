#!/bin/bash
#SBATCH --job-name=pfam_t1a
#SBATCH --array=0-19
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --output=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t1a_%A_%a.out
#SBATCH --error=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck/t1a_%A_%a.err
set -euo pipefail
WD=/home/rschaeff/work/ecod_consistency_2026/pfam_recheck
i=$SLURM_ARRAY_TASK_ID
/data/ecod/hmmer-3.1b2/binaries/hmmscan --cpu 8 --cut_ga \
  --domtblout "$WD/repsel_t1_chunk_${i}.domtbl" /home/rschaeff/data/pfam/v38.2/Pfam-A.hmm "$WD/repsel_t1_chunk_${i}.fasta" > "$WD/repsel_t1_chunk_${i}.stdout"
