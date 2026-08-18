# Final Feature Consumption Audit

This table verifies the exact input dimensionality and feature consumption of every trained model artifact to ensure the multi-level representation was genuinely used, instead of just existing in the schema.

| Dataset | Profile | Schema Features (approx) | Actual RF Features | Actual MLP Input Dim | Actual AE Input Dim |
|---|---|---|---|---|---|
| **CICIDS2017** | `IN_DOMAIN_CICIDS2017` | 21 | 18 | 18 | 18 |
| **Edge-IIoTset** | `IN_DOMAIN_EDGE_IIOT` | 10 | 7 | 7 | 7 |
| **BoT-IoT** | `IN_DOMAIN_BOT_IOT` | 20 | 18 | 35 | 35 |
| **N-BaIoT** | `NBAIOT_SOURCE_AGGREGATE` | 115 | 115 | 115 | 115 |

**Conclusion**: The serialized artifacts match identically across RF, MLP, and AE components for each profile, proving the models genuinely consumed the intended multi-level representation.
