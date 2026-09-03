#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXE="${1:-$ROOT/build/fracval}"

if [[ "$EXE" != /* ]]; then
    EXE="$ROOT/$EXE"
fi

if [[ ! -x "$EXE" ]]; then
    echo "ERROR: FracVAL executable not found: $EXE" >&2
    echo "Run 'make' first." >&2
    exit 1
fi

cd "$ROOT"

run_case() {
    local name="$1"
    local input="$2"
    local result_dir="$3"
    local expected_n="$4"
    local kind="$5"

    echo "==> $name"
    mkdir -p "$result_dir"
    rm -f "$result_dir"/*.dat "$result_dir"/*.contacts.csv

    "$EXE" "$input"

    # Bash 3.2 compatible file collection (stock macOS ships Bash 3.2).
    local files=()
    local file
    for file in "$result_dir"/*.dat; do
        [[ -f "$file" ]] || continue
        files[${#files[@]}]="$file"
    done

    if [[ ${#files[@]} -ne 1 ]]; then
        echo "FAIL: expected 1 aggregate file, found ${#files[@]}" >&2
        exit 1
    fi

    local rows
    rows="$(awk 'NF {n++} END {print n+0}' "${files[0]}")"
    if [[ "$rows" -ne "$expected_n" ]]; then
        echo "FAIL: expected $expected_n particles, found $rows" >&2
        exit 1
    fi

    if ! awk 'NF != 4 {bad=1} END {exit bad}' "${files[0]}"; then
        echo "FAIL: output must contain exactly four columns (x y z radius)" >&2
        exit 1
    fi

    if [[ "$kind" == "mono" ]]; then
        if ! awk 'NR==1 {r=$4} {if (($4-r)>1e-5 || (r-$4)>1e-5) bad=1} END {exit bad}' "${files[0]}"; then
            echo "FAIL: monodisperse case contains varying radii" >&2
            exit 1
        fi
    else
        if ! awk 'NR==1 {min=$4; max=$4} {if ($4<min) min=$4; if ($4>max) max=$4} END {exit !((max-min)>1e-5)}' "${files[0]}"; then
            echo "FAIL: polydisperse case did not produce varying radii" >&2
            exit 1
        fi
    fi

    local contacts="${files[0]%.dat}.contacts.csv"
    if [[ ! -f "$contacts" ]]; then
        echo "FAIL: contact-overlap sidecar not found: $contacts" >&2
        exit 1
    fi
    local contact_rows
    contact_rows="$(awk -F, 'NR>1 {n++} END {print n+0}' "$contacts")"
    if [[ "$contact_rows" -ne $((expected_n - 1)) ]]; then
        echo "FAIL: expected $((expected_n - 1)) intended contacts, found $contact_rows" >&2
        exit 1
    fi

    echo "PASS: ${files[0]} ($rows particles, $contact_rows intended contacts)"
}

run_overlap_case() {
    local name="$1"
    local input="$2"
    local result_dir="$3"
    local mode="$4"

    echo "==> $name"
    mkdir -p "$result_dir"
    rm -f "$result_dir"/*.dat "$result_dir"/*.contacts.csv
    "$EXE" "$input"

    local dat=""
    local file
    for file in "$result_dir"/*.dat; do
        [[ -f "$file" ]] || continue
        dat="$file"
        break
    done
    if [[ -z "$dat" ]]; then
        echo "FAIL: overlap case produced no aggregate" >&2
        exit 1
    fi

    local contacts="${dat%.dat}.contacts.csv"
    if [[ ! -f "$contacts" ]]; then
        echo "FAIL: overlap contact sidecar missing" >&2
        exit 1
    fi

    if [[ "$mode" == "fixed" ]]; then
        if ! awk -F, 'NR>1 {v=$2+0; n++; if (v<0.04999 || v>0.05001) bad=1} END {exit !(n==29 && !bad)}' "$contacts"; then
            echo "FAIL: fixed-overlap contacts are not all 5%" >&2
            exit 1
        fi
        echo "PASS: fixed 5% overlap (29 intended contacts)"
    else
        if ! awk -F, 'NR>1 {v=$2+0; n++; if (n==1 || v<min) min=v; if (n==1 || v>max) max=v; if (v<0 || v>0.120001) bad=1} END {exit !(n==29 && !bad && (max-min)>0.001)}' "$contacts"; then
            echo "FAIL: statistical overlap is out of bounds or has no variation" >&2
            exit 1
        fi
        echo "PASS: bounded statistical overlap (29 intended contacts)"
    fi
}

run_case "monodisperse" "tests/monodisperse/fracval.in" "tests/monodisperse/results" 100 mono
run_case "polydisperse" "tests/polydisperse/fracval.in" "tests/polydisperse/results" 100 poly
run_overlap_case "fixed overlap" "tests/overlap_fixed/fracval.in" "tests/overlap_fixed/results" fixed
run_overlap_case "statistical overlap" "tests/overlap_statistical/fracval.in" "tests/overlap_statistical/results" statistical

echo "All FracVAL smoke tests passed."
