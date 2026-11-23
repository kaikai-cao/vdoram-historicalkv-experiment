// SOURCE: BDS-SDU/vdoram-artifacts @ 10c90d35464620a35ddb1e2c29d2e8725acedd52
// PATH: CompatCircuit/Experiments/scripts/prove-scripts/prove-r1cs-multiparty.sh
// BLOB SHA: be1069bf5a35e0751baf426b96f86647293aee4d

#!/usr/bin/env bash
set -euo pipefail

source -- ./config.sh

current_dir="$(pwd)"

bash generate-local-host-file.sh

(
    cd -- "$R1CS_PATH"

    # Warning: do not contain space or special characters in the filename
    for file in $(ls -lS *.party0.r1cs.json | awk '{print $9}'); do
        # Extracting the circuit name (removing path and extension)
        circuit_name=$(basename "$file" ".party0.r1cs.json")

        files_exist=1
        for ((i = 0; i < PARTY_COUNT; i++)); do
            test_file="$circuit_name.party$i.r1cs.json"

            if [ ! -f "$test_file" ]; then
                echo "Warning: File $test_file does not exist."
                files_exist=0
            fi
        done

        if ((files_exist == 0)); then
            continue
        fi

        (
            cd -- "$current_dir"
            python3 prove-r1cs-multiparty-inner.py "$PARTY_COUNT" "$circuit_name" "$R1CS_PATH" "$BIN_CLIENT" || true
        )

        sleep 10
    done
)
