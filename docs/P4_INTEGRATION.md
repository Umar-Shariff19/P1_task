# P4 Integration Contract

P1 will export a versioned `HybridIDS` artifact loadable by downstream components:

```python
from iot_ids.inference.hybrid import HybridIDS

detector = HybridIDS.load("artifacts/p1/<version>")
result = detector.predict(features)
batch = detector.predict_batch(frame)
```

Each result must expose:

- final prediction, probabilities, and confidence
- Random Forest prediction, probabilities, confidence
- Neural Network prediction, probabilities, confidence, logits
- Autoencoder reconstruction error, anomaly score, threshold, anomaly flag
- model, schema, preprocessor, and feature-profile metadata

P4 may compute confidence drift, prediction instability, component disagreement, and adversarial behavior statistics from these outputs. P1 does not implement the downstream BCL/adversarial calculations.

