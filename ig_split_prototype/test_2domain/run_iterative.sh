#!/bin/bash
export OMP_PROC_BIND=false

FOLDSEEK=/sw/apps/Anaconda3-2023.09-0/bin/foldseek
TEMPLATE=/home/rschaeff/data/dpam_reference/ecod_data/ECOD70/002081025.pdb
DOMAIN=P61260_nD1_91-290.pdb
WORKDIR=foldseek_p61260

rm -rf $WORKDIR
mkdir -p $WORKDIR
cp $DOMAIN $WORKDIR/query.pdb

echo "Testing iterative FoldSeek on P61260_nD1 (200aa)"
echo "Template: fn3 (002081025)"
echo "=============================================="

for iter in 1 2 3 4 5; do
    echo ""
    echo "Iteration $iter"
    
    # Count residues
    nres=$(grep "^ATOM" $WORKDIR/query.pdb | awk '{print $6}' | sort -u | wc -l)
    echo "  Residues: $nres"
    
    if [ $nres -lt 50 ]; then
        echo "  Stopping: too few residues"
        break
    fi
    
    # Run FoldSeek
    $FOLDSEEK easy-search \
        $WORKDIR/query.pdb \
        $TEMPLATE \
        $WORKDIR/result_$iter.m8 \
        /tmp/fs_iter_$iter \
        --format-output "query,target,fident,alnlen,qstart,qend,evalue,bits,alntmscore" \
        -e 100 -v 0 2>/dev/null
    
    if [ ! -s $WORKDIR/result_$iter.m8 ]; then
        echo "  No hit found"
        break
    fi
    
    # Parse result
    result=$(cat $WORKDIR/result_$iter.m8)
    alnlen=$(echo "$result" | cut -f4)
    qstart=$(echo "$result" | cut -f5)
    qend=$(echo "$result" | cut -f6)
    tmscore=$(echo "$result" | cut -f9)
    
    echo "  HIT: TM=$tmscore, alnlen=$alnlen, qrange=$qstart-$qend"
    
    # Check TM score threshold
    if (( $(echo "$tmscore < 0.3" | bc -l) )); then
        echo "  TM score too low"
        break
    fi
    
    # Get actual residue range from PDB
    residues=$(grep "^ATOM" $WORKDIR/query.pdb | awk '{print $6}' | sort -u)
    start_res=$(echo "$residues" | sed -n "${qstart}p")
    end_res=$(echo "$residues" | sed -n "${qend}p")
    echo "  Actual range: $start_res-$end_res"
    
    # Remove aligned residues and save new PDB
    python3 - << PYTHON
pdb_in = "$WORKDIR/query.pdb"
pdb_out = "$WORKDIR/query_new.pdb"
remove_start = $start_res
remove_end = $end_res

with open(pdb_in, 'r') as fin, open(pdb_out, 'w') as fout:
    for line in fin:
        if line.startswith('ATOM'):
            resid = int(line[22:26])
            if resid < remove_start or resid > remove_end:
                fout.write(line)
        elif line.startswith(('CRYST', 'END')):
            fout.write(line)
PYTHON
    
    mv $WORKDIR/query_new.pdb $WORKDIR/query.pdb
done

echo ""
echo "=============================================="
echo "Results:"
ls -la $WORKDIR/result_*.m8 2>/dev/null
for f in $WORKDIR/result_*.m8; do
    if [ -f "$f" ]; then
        echo "$(basename $f): $(cat $f)"
    fi
done
