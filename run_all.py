"""
run_all.py

Purpose:
The master entrypoint for the CS536 Assignment 2 iPerf3 Pipeline.
Parses command line arguments (like duration, server_list, and interval) and acts as the 
central coordinator. It sequentially invokes the test runner over the server list, then 
commands the plotting module to generate the requested PDFs after the data is collected.
"""
import argparse
import os
from runner import run_experiments
import plotting
import ml_model

def main():
    parser = argparse.ArgumentParser(description="CS536 A2 iPerf3 Master Pipeline")
    parser.add_argument("--server_list", type=str, default="server_list.csv")
    parser.add_argument("-n", "--n", type=int, default=10, help="Number of successful destinations")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--interval", type=float, default=0.2, help="Sampling interval")
    parser.add_argument("--timeout", type=float, default=10.0, help="Socket timeout")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for server picking")
    parser.add_argument("--outdir", type=str, default="results", help="Dir to store traces")
    parser.add_argument("--plotsdir", type=str, default="plots", help="Dir to store plots")
    parser.add_argument("--representative", type=str, default=None, help="Explicitly select representive server ip")
    parser.add_argument("--ml_only", action="store_true", help="Skip data collection and only run the ML pipeline")
    
    args = parser.parse_args()
    
    if not args.ml_only:
        print("="*50)
        print(f"Running iperf3 tests: {args.n} destinations, {args.duration}s duration")
        print("="*50)
        run_experiments(
            args.server_list, 
            args.n, 
            args.duration, 
            args.interval, 
            args.timeout, 
            args.seed, 
            args.outdir
        )
        
        print("="*50)
        print("Generating Plots and Summaries")
        print("="*50)
        os.makedirs(args.plotsdir, exist_ok=True)
        plotting.generate_q1(args.outdir, args.plotsdir)
        plotting.generate_q2(args.outdir, args.plotsdir, args.representative)
    else:
        print("="*50)
        print("Skipping Q1/Q2 data collection. Fast-forwarding to ML Pipeline.")
        print("="*50)
        
    # Execute the Question 3 Machine Learning Pipeline
    ml_model.run_ml_pipeline(args.outdir, args.plotsdir)
    print("Pipeline Complete.")

if __name__ == "__main__":
    main()
