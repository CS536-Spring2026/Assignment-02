# Q2 Observations Helper for 96.45.39.38

## 1. Statistical Correlations (vs Goodput)
| Metric | Pearson | Spearman |
|--------|---------|----------|
| snd_cwnd | 0.420 | 0.382 |
| RTT | -0.494 | -0.249 |
| Retransmits | -0.121 | -0.167 |

## 2. Basic Anomaly Flags
- **RTT Spikes (>50% above mean):** Yes (10 occurrences)
- **Loss Events (intervals with retransmits):** 4
- **Congestion Window Drops:** 3 times

## 3. Notes for Report
- *How does CWND influence Goodput?* -> Look at the correlation table above. A strong positive correlation typically suggests the network is utilizing available bandwidth efficiently, until queues build.
- *What happens during an RTT spike?* -> Check if CWND dropped shortly after. Usually, RTT spikes mean buffer bloat, followed by dropped packets.
- *Anomalous behavior?* -> Ensure the fallback variables recorded NaN where kernel support lacked. Discuss the presence of these events.
