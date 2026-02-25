# Q2 Observations Helper for speedtest.keff.org

## 1. Statistical Correlations (vs Goodput)
| Metric | Pearson | Spearman |
|--------|---------|----------|
| snd_cwnd | 0.250 | nan |
| RTT | -0.031 | nan |
| Retransmits | 0.087 | nan |

## 2. Basic Anomaly Flags
- **RTT Spikes (>50% above mean):** Yes (18 occurrences)
- **Loss Events (intervals with retransmits):** 128
- **Congestion Window Drops:** 97 times

## 3. Notes for Report
- *How does CWND influence Goodput?* -> Look at the correlation table above. A strong positive correlation typically suggests the network is utilizing available bandwidth efficiently, until queues build.
- *What happens during an RTT spike?* -> Check if CWND dropped shortly after. Usually, RTT spikes mean buffer bloat, followed by dropped packets.
- *Anomalous behavior?* -> Ensure the fallback variables recorded NaN where kernel support lacked. Discuss the presence of these events.
