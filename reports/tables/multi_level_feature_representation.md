# Multi-Level Feature Representation

This table delineates the exact canonical schema count vs the transformed model input dimension. The scientific claim is a 'multi-level representation with dataset-specific feature availability', not that every dataset inherently contains all three semantic levels.

| Dataset | Profile | Raw Canonical Features | Instant Count | Temporal Count | Behavioral Count | Categorical Count | Post-Preprocessing Neural Dimension |
|---|---|---|---|---|---|---|---|
| **CICIDS2017** | `IN_DOMAIN_CICIDS2017` | 18 | 17 | 1 | 0 | 0 | 18 |
| **Edge-IIoTset** | `IN_DOMAIN_EDGE_IIOT` | 7 | 6 | 1 | 0 | 1 | 7 |
| **BoT-IoT** | `IN_DOMAIN_BOT_IOT` | 18 | 17 | 1 | 0 | 2 | 35 |
| **N-BaIoT** | `NBAIOT_SOURCE_AGGREGATE` | 115 | 0 | 0 | 115 | 0 | 115 |

> [!IMPORTANT]
> **Never confuse canonical schema features with encoded neural-network dimensions.** For example, BoT-IoT uses 18 semantic features, but the fitted One-Hot Encoder transforms the two categorical fields (`protocol_family`, `connection_state`) into additional binary vectors, resulting in a strictly defined 35-dimensional input tensor for the MLP and AE.