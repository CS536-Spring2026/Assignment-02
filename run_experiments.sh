#!/bin/bash
# run_experiments.sh

# 1. Set default value for n
N=10

# Parse command-line arguments to allow overriding n
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -n|--num) N="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

TARGET_FILE="server_list.csv"
if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: $TARGET_FILE not found."
    exit 1
fi

echo "Starting iPerf3 TCP experiments. Target successful connections: $N"

SUCCESS_COUNT=0

# Loop through the CSV file using a comma as the delimiter
# We read each column into a variable, even if we don't use the later ones
while IFS=',' read -r ip port gbs continent country site provider; do

    # Clean up any potential carriage returns (important if CSV was saved on Windows)
    ip=$(echo "$ip" | tr -d '\r')
    port=$(echo "$port" | tr -d '\r')

    # Skip empty lines or the header row
    if [ -z "$ip" ] || [ "$ip" == "IP/HOST" ]; then
        continue
    fi

    # Stop if we have reached our target number of successful tests
    if [ "$SUCCESS_COUNT" -ge "$N" ]; then
        break
    fi

    # Default to port 5201 if the CSV column happens to be empty
    if [ -z "$port" ]; then
        port=5201
    fi

    echo "Attempting destination: $ip on port $port"

    # Invoke the Python client with both the server and the specific port
    python3 iperf_client.py --server "$ip" --port "$port" --time 60

    # Check the exit status of the python script
    if [ $? -eq 0 ]; then
        echo "Successfully tested $ip."
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo "Progress: $SUCCESS_COUNT / $N"
    else
        echo "Failed to connect to $ip. Skipping to replacement..."
    fi
    echo "--------------------------------------------------"

done < "$TARGET_FILE"
# Check if we ran out of IPs before hitting n
if [ "$SUCCESS_COUNT" -lt "$N" ]; then
    echo "Warning: Reached the end of the list. Only completed $SUCCESS_COUNT out of $N tests."
else
    echo "Successfully completed $N tests."
fi

echo "Experiments complete. Extracting statistics..."

# 2. Trigger the visualization for Q2
echo "Generating TCP statistics plots..."
python3 generate_plots.py --data_dir ./results

# 3. Trigger the ML pipeline for Q3
echo "Training ML model and predicting Congestion Windows..."
python3 train_model.py --data_dir ./results

echo "Pipeline finished successfully!"
