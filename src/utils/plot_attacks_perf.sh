# Perform multiple attacks and store the results in a CSV file.

# * Configuration

# Output CSV file for Python.
outfile="attack_results.csv"
# Dataset path.
dataset="/home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg"
# Profile path.
profile="$dataset"/profile_pois_1

# * CSV building

# Write header.
echo "trace_nb;log2(key_rank);correct_bytes;pge_median" > "$outfile"

# Iteration over number of traces.
for num_traces in $(seq 100 10 200); do
    # Write number of traces.
    echo -n "$num_traces;" | tee -a "$outfile"

    # Attack and extract:
    # 1) The key rank
    # 2) The correct number of bytes.
    # 3) The median of the PGE
    ./attack.py --no-log --no-plot --norm --dataset-path "$dataset" \
                --start-point 740 --end-point 1140 --num-traces $num_traces attack \
                --attack-algo pcc --profile "$profile" \
                --num-pois 1 --poi-spacing 2 --variable p_xor_k --align 2>/dev/null \
        | grep -E 'actual rounded|CORRECT|MEDIAN' \
        | cut -f 2 -d ':' \
        | tr -d ' ' \
        | tr '[\n]' '[;]' \
        | sed 's/2^//' \
        | sed 's/;$//' \
        | tee -a "$outfile"

    echo "" | tee -a "$outfile"
done
