"""
plotting.py

Purpose:
Responsible for sweeping the 'results/' directory and generating visualizations for Questions 1 & 2.
- `generate_q1()` aggregates Application Goodput traces across all destinations into a single PDF 
  and calculates aggregate statistics (Median, Mean, p95).
- `generate_q2()` targets a single representative trace to generate TCP metrics graphs (CWND, RTT, Loss)
  over time, alongside scatter plots, and calculates analytical correlation coefficients.
"""
import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_q1(data_dir, plot_dir):
    # Find all trace.csv files
    trace_files = glob.glob(os.path.join(data_dir, "*", "trace.csv"))
    if not trace_files:
        print("No trace files found for Q1. Skipping.")
        return

    plt.figure(figsize=(10, 6))
    summary_data = []

    for file in trace_files:
        dest_ip = os.path.basename(os.path.dirname(file))
        df = pd.read_csv(file)
        if df.empty:
            continue
            
        # Plot time series
        plt.plot(df['timestamp'], df['goodput_bps'] / 1e6, label=dest_ip, alpha=0.7)

        # Compute summary stats
        goodput_mbps = df['goodput_bps'] / 1e6
        summary_data.append({
            'Destination': dest_ip,
            'Min (Mbps)': round(goodput_mbps.min(), 2),
            'Median (Mbps)': round(goodput_mbps.median(), 2),
            'Mean (Mbps)': round(goodput_mbps.mean(), 2),
            'p95 (Mbps)': round(goodput_mbps.quantile(0.95), 2),
        })

    plt.title("Q1c: Application Goodput Over Time (All Destinations)")
    plt.xlabel("Time (seconds)")
    plt.ylabel("Goodput (Mbps)")
    
    # Put legend outside
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, "Q1_goodput_all.pdf"))
    plt.close()

    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_csv_path = os.path.join(plot_dir, "Q1_summary.csv")
        summary_df.to_csv(summary_csv_path, index=False)
        print(f"[{len(trace_files)} traces] Saved Q1 goodput plot and summary.")
        print("\n--- Console Summary ---")
        print(summary_df.to_string(index=False))
        print("-----------------------\n")

def generate_q2(data_dir, plot_dir, representative_dest=None):
    trace_files = glob.glob(os.path.join(data_dir, "*", "trace.csv"))
    if not trace_files:
        return

    # Choose representative
    if representative_dest is None:
        # Find one with median average throughput
        averages = []
        for file in trace_files:
            dest_ip = os.path.basename(os.path.dirname(file))
            df = pd.read_csv(file)
            if not df.empty:
                averages.append((dest_ip, file, df['goodput_bps'].mean()))
        
        if not averages:
            return
            
        averages.sort(key=lambda x: x[2])
        median_idx = len(averages) // 2
        rep_ip, rep_file, _ = averages[median_idx]
    else:
        rep_ip = representative_dest
        rep_file = os.path.join(data_dir, rep_ip, "trace.csv")
        if not os.path.exists(rep_file):
            print(f"Could not find trace for explicit representative {rep_ip}")
            return

    df = pd.read_csv(rep_file)
    if df.empty:
        return

    # Prepare data
    goodput_mbps = df['goodput_bps'] / 1e6
    time_series = df['timestamp']

    # 1. Time Series
    fig, axs = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
    
    axs[0].plot(time_series, df['snd_cwnd'], color='blue')
    axs[0].set_ylabel('snd_cwnd (segments)')
    axs[0].set_title(f"Q2b: TCP Stats Time Series for {rep_ip}")
    axs[0].grid(True)

    axs[1].plot(time_series, df['rtt_ms'], color='orange')
    axs[1].set_ylabel('RTT (ms)')
    axs[1].grid(True)

    # Calculate retransmits delta if available
    loss_proxy = df['retransmits'].diff().fillna(0)
    axs[2].plot(time_series, loss_proxy, color='red')
    axs[2].set_ylabel('Retransmits (Delta)')
    axs[2].grid(True)

    axs[3].plot(time_series, goodput_mbps, color='green')
    axs[3].set_ylabel('Goodput (Mbps)')
    axs[3].set_xlabel('Time (seconds)')
    axs[3].grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, f"Q2_timeseries_{rep_ip}.pdf"))
    plt.close()

    # 2. Scatter Plots
    fig_scatter, axs_scatter = plt.subplots(1, 3, figsize=(18, 5))

    axs_scatter[0].scatter(goodput_mbps, df['snd_cwnd'], alpha=0.5, color='blue')
    axs_scatter[0].set_xlabel('Goodput (Mbps)')
    axs_scatter[0].set_ylabel('snd_cwnd')
    axs_scatter[0].set_title('snd_cwnd vs Goodput')
    axs_scatter[0].grid(True)

    axs_scatter[1].scatter(goodput_mbps, df['rtt_ms'], alpha=0.5, color='orange')
    axs_scatter[1].set_xlabel('Goodput (Mbps)')
    axs_scatter[1].set_ylabel('RTT (ms)')
    axs_scatter[1].set_title('RTT vs Goodput')
    axs_scatter[1].grid(True)

    axs_scatter[2].scatter(goodput_mbps, loss_proxy, alpha=0.5, color='red')
    axs_scatter[2].set_xlabel('Goodput (Mbps)')
    axs_scatter[2].set_ylabel('Retransmits (Delta)')
    axs_scatter[2].set_title('Retransmits vs Goodput')
    axs_scatter[2].grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(plot_dir, f"Q2_scatter_{rep_ip}.pdf"))
    plt.close()

    print(f"Saved Q2 timeseries and scatter plots for {rep_ip}")

    # 3. Generating Markdown Observations
    md_path = os.path.join(plot_dir, f"Q2_observations_notes_{rep_ip}.md")
    generate_markdown_observations(md_path, rep_ip, df, goodput_mbps, loss_proxy)


def generate_markdown_observations(md_path, ip, df, goodput_mbps, loss_proxy):
    import warnings
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        # Calculate correlations
        pearson_cwnd = df['snd_cwnd'].corr(goodput_mbps, method='pearson')
        pearson_rtt = df['rtt_ms'].corr(goodput_mbps, method='pearson')
        pearson_loss = loss_proxy.corr(goodput_mbps, method='pearson')
        
        spearman_cwnd, spearman_rtt, spearman_loss = float('nan'), float('nan'), float('nan')
        try:
            spearman_cwnd = df['snd_cwnd'].corr(goodput_mbps, method='spearman')
            spearman_rtt = df['rtt_ms'].corr(goodput_mbps, method='spearman')
            spearman_loss = loss_proxy.corr(goodput_mbps, method='spearman')
        except ImportError:
            pass

    # Anomalies
    rtt_mean = df['rtt_ms'].mean()
    rtt_spikes = df[df['rtt_ms'] > rtt_mean * 1.5]
    has_rtt_spikes = len(rtt_spikes) > 0
    
    loss_events = sum(loss_proxy > 0)
    cwnd_drops = sum(df['snd_cwnd'].diff() < 0)

    content = f"# Q2 Observations Helper for {ip}\n\n"
    content += "## 1. Statistical Correlations (vs Goodput)\n"
    content += "| Metric | Pearson | Spearman |\n"
    content += "|--------|---------|----------|\n"
    content += f"| snd_cwnd | {pearson_cwnd:.3f} | {spearman_cwnd:.3f} |\n"
    content += f"| RTT | {pearson_rtt:.3f} | {spearman_rtt:.3f} |\n"
    content += f"| Retransmits | {pearson_loss:.3f} | {spearman_loss:.3f} |\n\n"

    content += "## 2. Basic Anomaly Flags\n"
    content += f"- **RTT Spikes (>50% above mean):** {'Yes' if has_rtt_spikes else 'No'} ({len(rtt_spikes)} occurrences)\n"
    content += f"- **Loss Events (intervals with retransmits):** {loss_events}\n"
    content += f"- **Congestion Window Drops:** {cwnd_drops} times\n\n"
    
    content += "## 3. Notes for Report\n"
    content += "- *How does CWND influence Goodput?* -> Look at the correlation table above. A strong positive correlation typically suggests the network is utilizing available bandwidth efficiently, until queues build.\n"
    content += "- *What happens during an RTT spike?* -> Check if CWND dropped shortly after. Usually, RTT spikes mean buffer bloat, followed by dropped packets.\n"
    content += "- *Anomalous behavior?* -> Ensure the fallback variables recorded NaN where kernel support lacked. Discuss the presence of these events.\n"

    with open(md_path, "w") as f:
        f.write(content)
        
    print(f"Generated Q2 Markdown notes: {md_path}")
