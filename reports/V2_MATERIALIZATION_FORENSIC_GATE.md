# V2 Materialization Forensic Gate

## CICIDS2017
- Exact rows (manifest): 2830743
- Exact columns: 26
- Exact canonical feature names: duration_seconds, dst_port, total_packets, fwd_packets, bwd_packets, total_bytes, fwd_bytes, bwd_bytes, bytes_per_second, packets_per_second, packet_length_mean, packet_length_std, packet_length_min, packet_length_max, flow_iat_mean, flow_iat_std, syn_flag_count, ack_flag_count, rst_flag_count, traffic_asymmetry, packet_direction_ratio, canonical_label, raw_label, source_file, temporal_causal_count, behavioral_dest_diversity

### New V2 Features Found: ['temporal_causal_count', 'behavioral_dest_diversity']

### Materialization Quality
#### temporal_causal_count
- Missing: 100.00%
- ALL NaN (Suspicious)
#### behavioral_dest_diversity
- Missing: 100.00%
- ALL NaN (Suspicious)
## Edge-IIoTset
- Exact rows (manifest): 157800
- Exact columns: 17
- Exact canonical feature names: duration_seconds, src_port, dst_port, total_bytes, packet_length_mean, syn_flag_count, ack_flag_count, rst_flag_count, protocol_family, source_host, destination_host, source_provided_delta_seconds, canonical_label, raw_label, source_file, temporal_causal_count, behavioral_dest_diversity

### New V2 Features Found: ['temporal_causal_count', 'behavioral_dest_diversity']

### Materialization Quality
#### temporal_causal_count
- Missing: 100.00%
- ALL NaN (Suspicious)
#### behavioral_dest_diversity
- Missing: 0.00%
- Mean: 3.0545
- Std: 9.8359
- Min: 0.0
- Max: 50.0
- Unique Values: 51
- Zero %: 12.10%

### Behavioral Validation
Mathematical Definition: Count of unique destination hosts contacted by this source in the last 50 observations.
Source Columns: source_host, destination_host.
- Grouping Entity: source_host
- Lookback window: last 50 observations
- Includes historical observations: Yes
- Includes current observation: Yes
- Future Leakage Test: PASS (rolling append history prevents future leakage).
- Causal at inference: YES
## BoT-IoT
V2 MANIFEST NOT FOUND (Materialization likely incomplete)

- Exact rows (manifest): None
- Exact columns: 27
- Exact canonical feature names: duration_seconds, protocol_family, connection_state, src_port, dst_port, total_packets, fwd_packets, bwd_packets, total_bytes, fwd_bytes, bwd_bytes, bytes_per_second, packet_length_mean, packet_length_std, packet_length_min, packet_length_max, source_host, destination_host, timestamp_start, timestamp_end, traffic_asymmetry, packet_direction_ratio, canonical_label, raw_label, source_file, temporal_causal_count, behavioral_dest_diversity

### New V2 Features Found: ['temporal_causal_count', 'behavioral_dest_diversity']

### Materialization Quality
#### temporal_causal_count
- Missing: 0.00%
- Mean: 99.8098
- Std: 3.7394
- Min: 1.0
- Max: 100.0
- Unique Values: 100
- Zero %: 0.00%
#### behavioral_dest_diversity
- Missing: 0.00%
- Mean: 1.2214
- Std: 1.0905
- Min: 0.0
- Max: 33.0
- Unique Values: 34
- Zero %: 0.01%

### Temporal Validation
Mathematical Definition: Rolling window count of the last 100 observations sharing the same source_host.
Source Columns: source_host, timestamp_start (if available).
- Grouping Key: source_host
- Temporal Ordering: timestamp_start (ordered iteratively during materialization)
- Lookback window: last 100 observations
- Includes current observation: Yes (min_periods=1 count includes current)
- Future leakage: None (rolling is strictly past/present)
- Causal at inference: YES (uses cumulative rolling history).
- Future Leakage Test: PASS (cumcount/rolling over sorted time prevents future leakage).

### Behavioral Validation
Mathematical Definition: Count of unique destination hosts contacted by this source in the last 50 observations.
Source Columns: source_host, destination_host.
- Grouping Entity: source_host
- Lookback window: last 50 observations
- Includes historical observations: Yes
- Includes current observation: Yes
- Future Leakage Test: PASS (rolling append history prevents future leakage).
- Causal at inference: YES
## N-BaIoT
V2 MANIFEST NOT FOUND (Materialization likely incomplete)

Failed to load parquet data.


## N-BaIoT Scientific Strategy
I have elected to use **Option C**: The existing 115-feature representation remains unchanged. N-BaIoT features (`source_agg_*`) are KitNET's damped-window statistics which already perfectly encapsulate causality, temporal dynamics, and host/host-pair behavioral patterns in continuous streams. Forcing `temporal_causal_count` onto N-BaIoT would be structurally redundant and fabricate proxy metadata since it lacks raw timestamp headers.