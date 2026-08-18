# V2 vs P1 Performance Comparison

| Dataset | Model | P1 F1 | V2 F1 | Delta | Interpretation |
|---|---|---|---|---|---|
| CICIDS2017 | RF | 0.4562 | 0.4612 | +0.0050 | Comparable |
| CICIDS2017 | MLP | 0.4493 | 0.5964 | +0.1471 | Significant Improvement |
| CICIDS2017 | AE | 0.7273 | 0.7152 | -0.0121 | Degradation |
| CICIDS2017 | RF+MLP | 0.4523 | 0.6066 | +0.1543 | Significant Improvement |
| CICIDS2017 | RF+MLP+AE | 0.4782 | 0.6066 | +0.1284 | Significant Improvement |
| Edge-IIoTset | RF | 0.9997 | 0.9998 | +0.0001 | Comparable |
| Edge-IIoTset | MLP | 0.8881 | 0.9442 | +0.0561 | Significant Improvement |
| Edge-IIoTset | AE | 0.8889 | 0.9439 | +0.0550 | Significant Improvement |
| Edge-IIoTset | RF+MLP | 0.9999 | 0.9998 | -0.0001 | Comparable |
| Edge-IIoTset | RF+MLP+AE | 0.9999 | 0.9998 | -0.0001 | Comparable |
| BoT-IoT | RF | 1.0000 | 1.0000 | -0.0000 | Comparable |
| BoT-IoT | MLP | 1.0000 | 0.9997 | -0.0003 | Comparable |
| BoT-IoT | AE | 0.9753 | 0.0000 | -0.9753 | Degradation |
| BoT-IoT | RF+MLP | 1.0000 | 1.0000 | -0.0000 | Comparable |
| BoT-IoT | RF+MLP+AE | 1.0000 | 1.0000 | -0.0000 | Comparable |
| N-BaIoT | RF | 0.9995 | 0.9998 | +0.0003 | Comparable |
| N-BaIoT | MLP | 0.1042 | 0.9997 | +0.8955 | Significant Improvement |
| N-BaIoT | AE | 0.9747 | 0.9815 | +0.0068 | Comparable |
| N-BaIoT | RF+MLP | 0.9995 | 0.9999 | +0.0004 | Comparable |
| N-BaIoT | RF+MLP+AE | 0.9995 | 0.9999 | +0.0004 | Comparable |
