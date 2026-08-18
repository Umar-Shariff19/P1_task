# Ensemble Comparison

| Dataset | Component | Accuracy | Precision | Recall | F1 | Macro F1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|---|
| **CICIDS2017** | RF | 0.5784 | 0.7406 | 0.6464 | 0.5366 | 0.5559 | 0.4780 | 0.7503 |
| **CICIDS2017** | MLP | 0.5510 | 0.6551 | 0.6100 | 0.5185 | 0.5352 | 0.8646 | 0.8914 |
| **CICIDS2017** | AE | 0.6769 | 0.6649 | 0.6661 | 0.6775 | 0.6655 | 0.7048 | 0.7450 |
| **CICIDS2017** | RF+MLP | 0.5605 | 0.6806 | 0.6224 | 0.5251 | 0.5427 | 0.8495 | 0.8816 |
| **CICIDS2017** | RF+MLP+AE | 0.5700 | 0.6752 | 0.6278 | 0.5411 | 0.5562 | 0.7930 | 0.8574 |
| **Edge-IIoTset** | RF | 0.9996 | 0.9992 | 0.9994 | 0.9996 | 0.9993 | 0.9999 | 1.0000 |
| **Edge-IIoTset** | MLP | 0.7988 | 0.6494 | 0.5003 | 0.7097 | 0.4449 | 0.3461 | 0.7345 |
| **Edge-IIoTset** | AE | 0.8044 | 0.6930 | 0.5445 | 0.7471 | 0.5365 | 0.5013 | 0.8293 |
| **Edge-IIoTset** | RF+MLP | 0.9998 | 0.9999 | 0.9995 | 0.9998 | 0.9997 | 0.9999 | 1.0000 |
| **Edge-IIoTset** | RF+MLP+AE | 0.9998 | 0.9999 | 0.9995 | 0.9998 | 0.9997 | 0.9999 | 1.0000 |
| **BoT-IoT** | RF | 1.0000 | 0.9143 | 1.0000 | 1.0000 | 0.9531 | 1.0000 | 1.0000 |
| **BoT-IoT** | MLP | 0.9999 | 0.6381 | 1.0000 | 0.9999 | 0.7164 | 1.0000 | 1.0000 |
| **BoT-IoT** | AE | 0.9517 | 0.5000 | 0.4759 | 0.9752 | 0.4876 | 0.1064 | 0.9999 |
| **BoT-IoT** | RF+MLP | 1.0000 | 0.9143 | 1.0000 | 1.0000 | 0.9531 | 1.0000 | 1.0000 |
| **BoT-IoT** | RF+MLP+AE | 1.0000 | 0.9219 | 0.9655 | 1.0000 | 0.9426 | 1.0000 | 1.0000 |
| **N-BaIoT** | RF | 0.9991 | 0.9924 | 0.9995 | 0.9991 | 0.9959 | 0.9999 | 1.0000 |
| **N-BaIoT** | MLP | 0.1102 | 0.5307 | 0.5273 | 0.1049 | 0.1101 | 0.6185 | 0.9705 |
| **N-BaIoT** | AE | 0.9511 | 0.9716 | 0.5822 | 0.9342 | 0.6284 | 0.7160 | 0.9795 |
| **N-BaIoT** | RF+MLP | 0.9991 | 0.9928 | 0.9995 | 0.9992 | 0.9962 | 0.9999 | 1.0000 |
| **N-BaIoT** | RF+MLP+AE | 0.9991 | 0.9928 | 0.9995 | 0.9992 | 0.9962 | 0.9999 | 1.0000 |

## Ensemble Advantage Conclusion

- **CICIDS2017**: WORSE THAN BEST COMPONENT (Ensemble: 0.5411 vs Best AE: 0.6775)
- **Edge-IIoTset**: MATCHES BEST COMPONENT (Ensemble: 0.9998 vs Best RF: 0.9996)
- **BoT-IoT**: MATCHES BEST COMPONENT (Ensemble: 1.0000 vs Best RF: 1.0000)
- **N-BaIoT**: MATCHES BEST COMPONENT (Ensemble: 0.9992 vs Best RF: 0.9991)

**Conclusion**: The hybrid ensemble's value is in robustness and fail-safe bounds (e.g., bypassing zero-variance AEs in BoT-IoT). It does not universally improve detection accuracy, and sometimes suppresses strong standalone anomaly signals.