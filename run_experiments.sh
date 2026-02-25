#!/bin/bash
# -----------------------------------------------------------------------------
# CS 536 - Assignment 2 Automated Pipeline execution script
# Note: Ensure Docker Desktop or the Docker Engine is running before executing.
# -----------------------------------------------------------------------------
set -e

echo "=================================================="
echo " Cleaning previous run data..."
echo "=================================================="
rm -rf results
rm -rf plots
mkdir -p results
mkdir -p plots

echo "=================================================="
echo " Building Docker Image (cs536-a2)..."
echo "=================================================="
docker build -t cs536-a2 .

echo "=================================================="
echo " Executing Pipeline inside Docker Container..."
echo "=================================================="
docker run -t --rm --net=host -v "$(pwd)/results:/app/results" -v "$(pwd)/plots:/app/plots" cs536-a2 "$@"
