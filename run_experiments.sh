#!/bin/bash
# -----------------------------------------------------------------------------
# CS 536 - Assignment 2 Automated Pipeline execution script
# Note: Ensure Docker Desktop or the Docker Engine is running before executing.
# -----------------------------------------------------------------------------
set -e

if [[ "$*" != *"--ml_only"* ]]; then
    echo "=================================================="
    echo " WARNING: THIS WILL DELETE PREVIOUS RUN DATA!"
    echo " (Note: To skip data collection and keep your existing"
    echo "  traces for ML training, run with: --ml_only)"
    echo "=================================================="
    read -p "Are you sure you want to clear the 'results/' and 'plots/' folders? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo " Cleaning previous run data..."
        rm -rf results
        rm -rf plots
    else
        echo " Preserving existing trace data..."
    fi
    mkdir -p results
    mkdir -p plots
else
    echo "=================================================="
    echo " ML-Only Mode: Preserving existing trace data..."
    echo "=================================================="
    mkdir -p results
    mkdir -p plots
fi

echo "=================================================="
echo " Building Docker Image (cs536-a2)..."
echo "=================================================="
docker build -t cs536-a2 .

echo "=================================================="
echo " Executing Pipeline inside Docker Container..."
echo "=================================================="
docker run -t --rm --net=host -v "$(pwd)/results:/app/results" -v "$(pwd)/plots:/app/plots" cs536-a2 "$@"
