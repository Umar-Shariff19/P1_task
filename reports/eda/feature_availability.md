| canonical_name | level | valid_for | leakage_role | CICIDS2017 | Edge-IIoTset | BoT-IoT | N-BaIoT |
| --- | --- | --- | --- | --- | --- | --- | --- |
| duration_seconds | instant | both | SAFE_FEATURE | Flow Duration | udp.time_delta | dur |  |
| protocol_family | instant | in_domain | CONDITIONAL_FEATURE |  | tcp.len; udp.port; icmp.checksum | proto |  |
| connection_state | instant | in_domain | SAFE_FEATURE |  |  | state |  |
| src_port | instant | in_domain | CONDITIONAL_FEATURE |  | tcp.srcport | sport |  |
| dst_port | instant | both | CONDITIONAL_FEATURE | Destination Port | tcp.dstport; udp.port | dport |  |
| total_packets | instant | in_domain | SAFE_FEATURE | Total Fwd Packets; Total Backward Packets |  | pkts |  |
| fwd_packets | instant | in_domain | SAFE_FEATURE | Total Fwd Packets |  | spkts |  |
| bwd_packets | instant | in_domain | SAFE_FEATURE | Total Backward Packets |  | dpkts |  |
| total_bytes | instant | both | SAFE_FEATURE | Total Length of Fwd Packets; Total Length of Bwd Packets | tcp.len; mqtt.len; http.content_length | bytes |  |
| fwd_bytes | instant | in_domain | SAFE_FEATURE | Total Length of Fwd Packets |  | sbytes |  |
| bwd_bytes | instant | in_domain | SAFE_FEATURE | Total Length of Bwd Packets |  | dbytes |  |
| bytes_per_second | instant | in_domain | SAFE_FEATURE | Flow Bytes/s |  | rate |  |
| packets_per_second | instant | in_domain | SAFE_FEATURE | Flow Packets/s |  |  |  |
| packet_length_mean | instant | both | CONDITIONAL_FEATURE | Packet Length Mean | tcp.len; mqtt.len; http.content_length | mean |  |
| packet_length_std | instant | in_domain | SAFE_FEATURE | Packet Length Std |  | stddev |  |
| packet_length_min | instant | in_domain | SAFE_FEATURE | Min Packet Length |  | min |  |
| packet_length_max | instant | in_domain | SAFE_FEATURE | Max Packet Length |  | max |  |
| flow_iat_mean | temporal | in_domain | SAFE_FEATURE | Flow IAT Mean |  |  |  |
| flow_iat_std | temporal | in_domain | SAFE_FEATURE | Flow IAT Std |  |  |  |
| source_provided_delta_seconds | temporal | in_domain | SAFE_FEATURE |  | udp.time_delta |  |  |
| timestamp_start | temporal | in_domain | USED_FOR_GROUPING_FEATURE_GENERATION |  |  | stime |  |
| source_host | behavioral | in_domain | USED_FOR_GROUPING_FEATURE_GENERATION |  | ip.src_host | saddr |  |
| destination_host | behavioral | in_domain | USED_FOR_GROUPING_FEATURE_GENERATION |  | ip.dst_host | daddr |  |
| traffic_asymmetry | behavioral | in_domain | SAFE_FEATURE | Total Length of Fwd Packets; Total Length of Bwd Packets |  | sbytes; dbytes |  |
| packet_direction_ratio | behavioral | in_domain | SAFE_FEATURE | Total Fwd Packets; Total Backward Packets |  | spkts; dpkts |  |
| source_agg_* | behavioral | in_domain | SAFE_FEATURE |  |  |  | MI_dir_*; H_*; HH_*; HH_jit_*; HpHp_* |
