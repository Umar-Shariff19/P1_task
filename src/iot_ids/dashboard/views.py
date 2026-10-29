"""Dashboard HTML Views and Interactive Frontend Template.

Self-contained, responsive single-page application with dark theme, live WebSocket telemetry,
threat scenario switcher, adversarial attack lab, and explainability visualizations.
"""
from __future__ import annotations


def render_dashboard_html() -> str:
    """Renders the self-contained single page dashboard HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Level IoT IDS & Adversarial Robustness Platform</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #182234;
            --bg-card-hover: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #334155;
            --accent-cyan: #06b6d4;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #8b5cf6;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--font-family);
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Top Header */
        header {
            background-color: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-title h1 {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--text-primary);
        }

        .badge {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .badge-live {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .badge-threat {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .badge-model {
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
            display: inline-block;
            box-shadow: 0 0 8px currentColor;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .btn {
            font-size: 0.85rem;
            font-weight: 600;
            padding: 7px 14px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn:hover {
            background: var(--bg-card-hover);
            border-color: var(--text-muted);
        }

        .btn-primary {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: #fff;
        }

        .btn-primary:hover {
            background: #2563eb;
        }

        .btn-danger {
            background: rgba(239, 68, 68, 0.2);
            border-color: var(--accent-red);
            color: var(--accent-red);
        }

        .btn-danger:hover {
            background: var(--accent-red);
            color: #fff;
        }

        .btn-success {
            background: rgba(16, 185, 129, 0.2);
            border-color: var(--accent-green);
            color: var(--accent-green);
        }

        .btn-success:hover {
            background: var(--accent-green);
            color: #fff;
        }

        select.form-select {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 7px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            outline: none;
            cursor: pointer;
        }

        /* Navigation Bar */
        nav.nav-tabs {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 0 24px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
        }

        .tab-btn {
            padding: 12px 16px;
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
        }

        .tab-btn:hover {
            color: var(--text-primary);
        }

        .tab-btn.active {
            color: var(--accent-cyan);
            border-bottom-color: var(--accent-cyan);
        }

        /* Main Container */
        main {
            padding: 24px;
            flex: 1;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.2s ease-in-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* KPI Cards Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 18px;
            transition: border-color 0.2s ease;
        }

        .card:hover {
            border-color: var(--accent-cyan);
        }

        .card-header {
            font-size: 0.8rem;
            text-transform: uppercase;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .card-subtext {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 6px;
        }

        /* Grids and Panels */
        .panel-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }

        @media (max-width: 900px) {
            .panel-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Data Tables */
        .table-responsive {
            width: 100%;
            overflow-x: auto;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }

        table.data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            text-align: left;
        }

        table.data-table th {
            background: var(--bg-secondary);
            color: var(--text-secondary);
            padding: 12px 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            white-space: nowrap;
        }

        table.data-table td {
            padding: 10px 14px;
            border-bottom: 1px solid rgba(51, 65, 85, 0.4);
            white-space: nowrap;
            color: var(--text-primary);
        }

        table.data-table tr:hover td {
            background: rgba(30, 41, 59, 0.7);
        }

        .pill-critical { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
        .pill-high { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }
        .pill-medium { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #3b82f6; }
        .pill-low { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }

        /* Devices Grid */
        .devices-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }

        .device-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .device-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .device-name {
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--text-primary);
        }

        .device-detail {
            font-size: 0.8rem;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }

        /* Scenarios Selector */
        .scenarios-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 14px;
            margin-top: 16px;
        }

        .scenario-box {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .scenario-box:hover {
            border-color: var(--accent-cyan);
            transform: translateY(-2px);
        }

        .scenario-box.active {
            border-color: var(--accent-cyan);
            background: rgba(6, 182, 212, 0.08);
            box-shadow: 0 0 12px rgba(6, 182, 212, 0.2);
        }

        .scenario-title {
            font-weight: 700;
            font-size: 0.9rem;
            margin-bottom: 6px;
            color: var(--text-primary);
        }

        .scenario-desc {
            font-size: 0.75rem;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        /* Adversarial Lab Controls */
        .lab-form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            align-items: end;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .form-group label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        .form-control {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            outline: none;
        }

        /* Results Matrix */
        .results-matrix {
            margin-top: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }

        .matrix-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
        }

        .matrix-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--accent-cyan);
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 6px;
        }

        .metric-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            padding: 6px 0;
            border-bottom: 1px solid rgba(51, 65, 85, 0.2);
        }

        .metric-label {
            color: var(--text-secondary);
        }

        .metric-val {
            font-weight: 600;
            color: var(--text-primary);
        }

        /* Explainability Waterfall */
        .waterfall-bar {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
            font-size: 0.8rem;
            gap: 12px;
        }

        .waterfall-label {
            width: 180px;
            color: var(--text-secondary);
            font-family: monospace;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .waterfall-track {
            flex: 1;
            height: 20px;
            background: var(--bg-secondary);
            border-radius: 4px;
            position: relative;
            overflow: hidden;
        }

        .waterfall-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .waterfall-fill.positive {
            background: var(--accent-red);
        }

        .waterfall-fill.negative {
            background: var(--accent-green);
        }

        .waterfall-score {
            width: 70px;
            text-align: right;
            font-family: monospace;
            font-weight: 600;
        }

        /* Footer */
        footer {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            padding: 12px 24px;
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="header-title">
            <h1>IoT IDS & Adversarial Platform</h1>
            <span id="wsBadge" class="badge badge-live">
                <span class="pulse-dot"></span> Live WS
            </span>
            <span id="activeScenarioBadge" class="badge badge-threat">BENIGN_NORMAL</span>
            <span id="activeModelBadge" class="badge badge-model">Option C Ensemble</span>
        </div>

        <div class="header-controls">
            <button id="btnStart" class="btn btn-success" onclick="controlSim('start')">▶ Start</button>
            <button id="btnPause" class="btn" onclick="controlSim('pause')">⏸ Pause</button>
            <button id="btnStep" class="btn btn-primary" onclick="controlSim('step')">⚡ Step 10</button>
            <button id="btnStop" class="btn btn-danger" onclick="controlSim('stop')">⏹ Stop</button>
            <button id="btnReset" class="btn" onclick="controlSim('reset')">↺ Reset</button>

            <select id="modelSelect" class="form-select" onchange="changeModel(this.value)">
                <option value="option_c" selected>Option C Ensemble (0.7 RF + 0.3 Robust MLP)</option>
                <option value="robust_mlp">Robust MLP (PGD-Trained)</option>
                <option value="standard_mlp">Standard MLP</option>
                <option value="rf">Random Forest Classifier</option>
            </select>
        </div>
    </header>

    <!-- Nav Tabs -->
    <nav class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('overview')">Overview</button>
        <button class="tab-btn" onclick="switchTab('telemetry')">Live Telemetry</button>
        <button class="tab-btn" onclick="switchTab('environment')">IoT Environment</button>
        <button class="tab-btn" onclick="switchTab('adversarial')">Adversarial Lab</button>
        <button class="tab-btn" onclick="switchTab('explainability')">Explainability (XAI)</button>
        <button class="tab-btn" onclick="switchTab('alerts')">Alert Investigation</button>
        <button class="tab-btn" onclick="switchTab('experiments')">Provenance & Ledger</button>
    </nav>

    <!-- Main Content -->
    <main>

        <!-- TAB 1: OVERVIEW -->
        <section id="tab-overview" class="tab-content active">
            <div class="kpi-grid">
                <div class="card">
                    <div class="card-header">Total Packets Processed</div>
                    <div id="kpiPackets" class="card-value">0</div>
                    <div class="card-subtext">Aggregated Scapy / Dict frames</div>
                </div>
                <div class="card">
                    <div class="card-header">Active Canonical Flows</div>
                    <div id="kpiFlows" class="card-value">0</div>
                    <div class="card-subtext">21-Feature multi-level flows</div>
                </div>
                <div class="card">
                    <div class="card-header">Anomaly Alerts Triggered</div>
                    <div id="kpiAlerts" class="card-value" style="color: var(--accent-yellow);">0</div>
                    <div class="card-subtext">Exceeded calibrated threshold</div>
                </div>
                <div class="card">
                    <div class="card-header">Attacks Mitigated</div>
                    <div id="kpiAttacks" class="card-value" style="color: var(--accent-red);">0</div>
                    <div class="card-subtext">Verified ground-truth malicious</div>
                </div>
                <div class="card">
                    <div class="card-header">Throughput</div>
                    <div id="kpiThroughput" class="card-value" style="color: var(--accent-cyan);">0.0</div>
                    <div class="card-subtext">Packets / second</div>
                </div>
                <div class="card">
                    <div class="card-header">Pipeline Health</div>
                    <div id="kpiHealth" class="card-value" style="color: var(--accent-green); font-size: 1.4rem;">READY</div>
                    <div class="card-subtext">Schema & Inference valid</div>
                </div>
            </div>

            <div class="panel-grid">
                <!-- Recent Live Flows Preview -->
                <div class="card">
                    <div class="card-header">
                        <span>Recent Flow Ingestion Stream</span>
                        <a href="javascript:void(0)" onclick="switchTab('telemetry')" style="color: var(--accent-cyan); text-decoration: none; font-size: 0.75rem;">View All →</a>
                    </div>
                    <div class="table-responsive">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Flow ID</th>
                                    <th>Protocol</th>
                                    <th>Ground Truth</th>
                                    <th>Probability</th>
                                    <th>Risk Level</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody id="overviewFlowsTable">
                                <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Waiting for network flows... Click '⚡ Step 10' or '▶ Start'.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Threat Scenarios Quick Launch -->
                <div class="card">
                    <div class="card-header">Active Threat Scenario</div>
                    <div id="overviewScenarioDesc" style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 16px;">
                        Baseline benign telemetry is currently active across all 8 simulated IoT devices.
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px;">
                        <button class="btn btn-primary" onclick="setScenario('MIRAI_BOTNET_FLOOD')">⚡ Launch Mirai SYN Flood</button>
                        <button class="btn" onclick="setScenario('SLOWLORIS_DOS')">⏳ Launch Slowloris DoS</button>
                        <button class="btn" onclick="setScenario('DATA_EXFILTRATION_MITM')">📡 Launch Exfiltration MITM</button>
                        <button class="btn" onclick="setScenario('COMMAND_INJECTION')">⚙️ Launch Modbus Injection</button>
                        <button class="btn btn-success" onclick="setScenario('BENIGN_NORMAL')">✓ Restore Benign Baseline</button>
                    </div>
                </div>
            </div>
        </section>

        <!-- TAB 2: LIVE TELEMETRY -->
        <section id="tab-telemetry" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <h2>Live Network Telemetry Stream</h2>
                <div style="display: flex; gap: 10px;">
                    <label style="font-size: 0.85rem; display: flex; align-items: center; gap: 6px;">
                        <input type="checkbox" id="chkOnlyAnomalies" onchange="filterFlows()"> Only Show Alerts
                    </label>
                    <button class="btn" onclick="fetchRecentFlows()">Refresh Table</button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Flow ID (Source → Destination)</th>
                            <th>Ground Truth</th>
                            <th>Attack Prob</th>
                            <th>Risk Score</th>
                            <th>Severity</th>
                            <th>Active Scenario</th>
                            <th>Explain</th>
                        </tr>
                    </thead>
                    <tbody id="liveFlowsTable">
                        <tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No flows recorded yet.</td></tr>
                    </tbody>
                </table>
            </div>
        </section>

        <!-- TAB 3: IOT ENVIRONMENT -->
        <section id="tab-environment" class="tab-content">
            <h2>Simulated IoT Environment & Topology</h2>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">
                Heterogeneous multi-device IoT network with realistic industrial, surveillance, and smart sensor profiles.
            </p>

            <div class="devices-grid" id="devicesGrid">
                <!-- Device Cards rendered via JS -->
            </div>

            <h3 style="margin-top: 28px; font-size: 1.05rem;">Available Threat & Attack Scenarios</h3>
            <div class="scenarios-grid">
                <div class="scenario-box active" onclick="setScenario('BENIGN_NORMAL')">
                    <div class="scenario-title">1. Benign Normal Baseline</div>
                    <div class="scenario-desc">Standard telemetry across temperature sensors, RTSP video streams, and Modbus polling.</div>
                </div>
                <div class="scenario-box" onclick="setScenario('MIRAI_BOTNET_FLOOD')">
                    <div class="scenario-title">2. Mirai Botnet SYN Flood</div>
                    <div class="scenario-desc">Compromised camera launches high-volume TCP SYN flood with spoofed source IPs and high fanout.</div>
                </div>
                <div class="scenario-box" onclick="setScenario('SLOWLORIS_DOS')">
                    <div class="scenario-title">3. Slowloris HTTP DoS</div>
                    <div class="scenario-desc">Low-and-slow HTTP starvation attack maintaining open sockets via partial periodic header transmissions.</div>
                </div>
                <div class="scenario-box" onclick="setScenario('DATA_EXFILTRATION_MITM')">
                    <div class="scenario-title">4. Data Exfiltration (MITM)</div>
                    <div class="scenario-desc">Tunneling sensitive telemetry data outside the private network over rogue DNS / HTTP POST requests.</div>
                </div>
                <div class="scenario-box" onclick="setScenario('COMMAND_INJECTION')">
                    <div class="scenario-title">5. Modbus Command Injection</div>
                    <div class="scenario-desc">Unauthorized PLC coil overrides and malicious Function Code 5/6 writes sent to industrial controllers.</div>
                </div>
            </div>
        </section>

        <!-- TAB 4: ADVERSARIAL ATTACK LAB -->
        <section id="tab-adversarial" class="tab-content">
            <h2>Adversarial Attack & Robustness Evaluation Laboratory</h2>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; margin-bottom: 16px;">
                Generate mathematically constrained PGD / FGSM perturbations with continuous feature masks and domain clamping,
                evaluating cross-model transferability and evasion rates.
            </p>

            <div class="lab-form">
                <div class="form-group">
                    <label>Attack Algorithm</label>
                    <select id="advMethod" class="form-control">
                        <option value="pgd" selected>Projected Gradient Descent (PGD - L∞)</option>
                        <option value="fgsm">Fast Gradient Sign Method (FGSM)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Perturbation Magnitude (ε): <span id="advEpsVal">0.50</span></label>
                    <input type="range" id="advEpsilon" min="0.05" max="1.50" step="0.05" value="0.50" class="form-control" oninput="document.getElementById('advEpsVal').innerText = this.value">
                </div>
                <div class="form-group">
                    <label>PGD Iterations (Steps): <span id="advStepsVal">7</span></label>
                    <input type="range" id="advSteps" min="1" max="20" step="1" value="7" class="form-control" oninput="document.getElementById('advStepsVal').innerText = this.value">
                </div>
                <div class="form-group">
                    <label>Attack Samples Count</label>
                    <input type="number" id="advSamples" value="25" min="5" max="100" class="form-control">
                </div>
                <div>
                    <button id="btnRunAttack" class="btn btn-primary" onclick="runAdversarialAttack()" style="width: 100%; height: 38px;">
                        ⚔️ Launch Attack Evaluation
                    </button>
                </div>
            </div>

            <div id="advResultsContainer" style="display: none;">
                <div class="card" style="margin-bottom: 16px; border-color: var(--accent-cyan);">
                    <div class="card-header">
                        <span>Laboratory Attack Summary</span>
                        <span id="advExpId" style="font-family: monospace; color: var(--accent-cyan);"></span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 8px;">
                        <div><strong style="color: var(--text-secondary); font-size: 0.8rem;">Method:</strong> <span id="resMethod" style="font-weight: 600;"></span></div>
                        <div><strong style="color: var(--text-secondary); font-size: 0.8rem;">Budget (ε):</strong> <span id="resEps" style="font-weight: 600;"></span></div>
                        <div><strong style="color: var(--text-secondary); font-size: 0.8rem;">Mean L2 Norm:</strong> <span id="resL2" style="font-weight: 600;"></span></div>
                        <div><strong style="color: var(--text-secondary); font-size: 0.8rem;">Mean L∞ Norm:</strong> <span id="resLinf" style="font-weight: 600;"></span></div>
                        <div><strong style="color: var(--text-secondary); font-size: 0.8rem;">AE Catch Rate:</strong> <span id="resAECatch" style="font-weight: 600; color: var(--accent-green);"></span></div>
                    </div>
                </div>

                <h3>Cross-Model Robustness & Detection Evasion Matrix</h3>
                <div class="results-matrix" id="advMatrixGrid">
                    <!-- Populated via JS -->
                </div>
            </div>
        </section>

        <!-- TAB 5: EXPLAINABILITY (XAI) -->
        <section id="tab-explainability" class="tab-content">
            <h2>Explainable AI: Feature Attribution Waterfall</h2>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; margin-bottom: 16px;">
                Local per-flow decision attribution combining TreeExplainer (Random Forest) and Gradient Attribution (Robust MLP).
            </p>

            <div class="panel-grid">
                <div class="card">
                    <div class="card-header">Top Influential Features Driving Prediction</div>
                    <div id="xaiWaterfallContainer" style="margin-top: 14px;">
                        <p style="color: var(--text-muted); font-size: 0.85rem;">Click 'Explain' on any flow in the Telemetry tab, or click the button below to inspect the latest flow.</p>
                    </div>
                    <button class="btn btn-primary" onclick="requestLatestExplanation()" style="margin-top: 14px;">Explain Latest Network Flow</button>
                </div>

                <div class="card">
                    <div class="card-header">Model Decision Breakdown</div>
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px;">
                        <div>
                            <div class="metric-label">Ensemble Decision:</div>
                            <div id="xaiDecision" style="font-size: 1.4rem; font-weight: 700; color: var(--accent-green);">UNKNOWN</div>
                        </div>
                        <div>
                            <div class="metric-label">Option C Combined Probability:</div>
                            <div id="xaiOptCProb" style="font-size: 1.1rem; font-weight: 600;">-</div>
                        </div>
                        <div>
                            <div class="metric-label">Random Forest Stream Prob:</div>
                            <div id="xaiRFProb" style="font-size: 0.95rem; color: var(--text-secondary);">-</div>
                        </div>
                        <div>
                            <div class="metric-label">Robust MLP Stream Prob:</div>
                            <div id="xaiMLPProb" style="font-size: 0.95rem; color: var(--text-secondary);">-</div>
                        </div>
                        <div style="border-top: 1px solid var(--border-color); padding-top: 10px; margin-top: 6px;">
                            <div class="metric-label">Automated Security Analysis:</div>
                            <div id="xaiNarrative" style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; margin-top: 4px;">
                                -
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- TAB 6: ALERTS INVESTIGATION -->
        <section id="tab-alerts" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <h2>Security Alert Triage Log</h2>
                <button class="btn btn-primary" onclick="exportAlertsJSON()">📥 Export Alerts JSON</button>
            </div>
            <div class="table-responsive">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Alert Timestamp</th>
                            <th>Target Endpoint</th>
                            <th>Anomaly Confidence</th>
                            <th>Risk Score</th>
                            <th>Severity</th>
                            <th>Active Scenario</th>
                            <th>Inspect Canonical Features</th>
                        </tr>
                    </thead>
                    <tbody id="alertsTable">
                        <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No security alerts recorded. Baseline network is operating normally.</td></tr>
                    </tbody>
                </table>
            </div>
        </section>

        <!-- TAB 7: EXPERIMENTS PROVENANCE -->
        <section id="tab-experiments" class="tab-content">
            <h2>Reproducibility & Laboratory Experiment Ledger</h2>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; margin-bottom: 16px;">
                Cryptographic provenance ledger tracking all adversarial robustness runs, parameters, and evaluations.
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 20px;">
                <div class="card" style="border-left: 3px solid var(--accent-blue);">
                    <div class="card-header">Model Suite Provenance</div>
                    <div id="provenanceSuiteType" style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin-top: 4px;">Synthetic-Reference Suite (Seed: 42)</div>
                    <div id="provenanceSuiteDesc" class="card-subtext" style="margin-top: 4px;">21-Feature Calibrated RF, MLP, Robust MLP, Autoencoder &amp; Option C Ensemble</div>
                </div>
                <div class="card" style="border-left: 3px solid var(--accent-yellow);">
                    <div class="card-header">Research Checkpoint Authorization</div>
                    <div id="provenanceAuthStatus" style="font-size: 0.95rem; font-weight: 600; color: var(--accent-yellow); margin-top: 4px;">Blocked (Fail-Closed)</div>
                    <div id="provenanceAuthDesc" class="card-subtext" style="margin-top: 4px;">require_real_data_authorization() requires root identity &amp; owner approval</div>
                </div>
                <div class="card" style="border-left: 3px solid var(--accent-green);">
                    <div class="card-header">Traffic Ingress Provenance</div>
                    <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin-top: 4px;">Simulated 8-Node IoT Network</div>
                    <div class="card-subtext" style="margin-top: 4px;">Real-time Scapy-formatted packets; Physical NIC capture disabled</div>
                </div>
            </div>
            <div class="table-responsive">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Experiment ID</th>
                            <th>Timestamp</th>
                            <th>Attack Method</th>
                            <th>Perturbation (ε)</th>
                            <th>Steps</th>
                            <th>Samples</th>
                            <th>Std MLP Evasion (ASR)</th>
                            <th>Robust MLP Degradation</th>
                        </tr>
                    </thead>
                    <tbody id="experimentsTable">
                        <tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No adversarial experiments executed yet in this session.</td></tr>
                    </tbody>
                </table>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer>
        <div>Multi-Level IoT Intrusion Detection System • Verified Deterministic Engine</div>
        <div id="footerUptime">Uptime: 0s</div>
    </footer>

    <!-- Client-Side JavaScript -->
    <script>
        // State
        let currentTab = 'overview';
        let ws = null;
        let recentFlowsList = [];
        let recentAlertsList = [];

        // Tab Switching
        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
            if (targetBtn) targetBtn.classList.add('active');

            const targetSection = document.getElementById('tab-' + tabId);
            if (targetSection) targetSection.classList.add('active');

            if (tabId === 'environment') fetchDevices();
            if (tabId === 'telemetry') fetchRecentFlows();
            if (tabId === 'alerts') fetchRecentAlerts();
            if (tabId === 'experiments') fetchExperiments();
        }

        // WebSocket Connection
        function connectWebSocket() {
            const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${proto}//${window.location.host}/ws/live`;
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                const b = document.getElementById('wsBadge');
                b.className = 'badge badge-live';
                b.innerHTML = '<span class="pulse-dot"></span> Live WS';
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'FLOW_EVENT') {
                        handleIncomingFlow(msg.data);
                    } else if (msg.type === 'INITIAL_STATE') {
                        updateKPIs(msg.status);
                    }
                } catch (e) {
                    console.error('WS parse error:', e);
                }
            };

            ws.onclose = () => {
                const b = document.getElementById('wsBadge');
                b.className = 'badge';
                b.style.borderColor = 'var(--accent-red)';
                b.style.color = 'var(--accent-red)';
                b.innerHTML = '<span class="pulse-dot"></span> Disconnected';
                setTimeout(connectWebSocket, 2000);
            };
        }

        // Handle Incoming Telemetry
        function handleIncomingFlow(flow) {
            recentFlowsList.unshift(flow);
            if (recentFlowsList.length > 200) recentFlowsList.pop();

            if (flow.is_anomaly || flow.risk_score >= 0.5) {
                recentAlertsList.unshift(flow);
                if (recentAlertsList.length > 100) recentAlertsList.pop();
            }

            renderOverviewFlows();
            if (currentTab === 'telemetry') renderTelemetryTable();
            if (currentTab === 'alerts') renderAlertsTable();
        }

        function renderOverviewFlows() {
            const tbody = document.getElementById('overviewFlowsTable');
            if (!recentFlowsList.length) return;
            const top = recentFlowsList.slice(0, 7);
            tbody.innerHTML = top.map(f => `
                <tr>
                    <td><strong>${f.flow_id}</strong></td>
                    <td style="text-transform: uppercase;">${f.raw_features?.proto_tcp ? 'TCP' : (f.raw_features?.proto_udp ? 'UDP' : 'OTHER')}</td>
                    <td><span class="badge ${f.ground_truth === 1 ? 'badge-threat' : 'badge-live'}">${f.ground_truth === 1 ? 'ATTACK' : 'BENIGN'}</span></td>
                    <td>${(f.prediction_prob * 100).toFixed(1)}%</td>
                    <td><span class="badge pill-${f.risk_level.toLowerCase()}">${f.risk_level}</span></td>
                    <td><button class="btn" style="padding: 2px 8px; font-size: 0.75rem;" onclick="explainFlowObj('${f.flow_id}')">Explain</button></td>
                </tr>
            `).join('');
        }

        function renderTelemetryTable() {
            const tbody = document.getElementById('liveFlowsTable');
            const onlyAnomalies = document.getElementById('chkOnlyAnomalies').checked;
            let list = onlyAnomalies ? recentFlowsList.filter(f => f.is_anomaly) : recentFlowsList;

            if (!list.length) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No matching flows found.</td></tr>`;
                return;
            }

            tbody.innerHTML = list.slice(0, 40).map(f => `
                <tr>
                    <td style="color: var(--text-muted); font-family: monospace;">${new Date(f.timestamp * 1000).toLocaleTimeString()}</td>
                    <td><strong>${f.flow_id}</strong></td>
                    <td><span class="badge ${f.ground_truth === 1 ? 'badge-threat' : 'badge-live'}">${f.ground_truth === 1 ? 'ATTACK' : 'BENIGN'}</span></td>
                    <td>${(f.prediction_prob * 100).toFixed(1)}%</td>
                    <td>${f.risk_score.toFixed(2)}</td>
                    <td><span class="badge pill-${f.risk_level.toLowerCase()}">${f.risk_level}</span></td>
                    <td style="font-size: 0.75rem; color: var(--text-secondary);">${f.scenario || 'BENIGN'}</td>
                    <td><button class="btn" style="padding: 2px 8px; font-size: 0.75rem;" onclick="explainFlowObj('${f.flow_id}')">Explain</button></td>
                </tr>
            `).join('');
        }

        function renderAlertsTable() {
            const tbody = document.getElementById('alertsTable');
            if (!recentAlertsList.length) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No security alerts recorded. Baseline network is operating normally.</td></tr>`;
                return;
            }

            tbody.innerHTML = recentAlertsList.slice(0, 30).map(a => `
                <tr>
                    <td style="color: var(--text-muted); font-family: monospace;">${new Date(a.timestamp * 1000).toLocaleTimeString()}</td>
                    <td><strong>${a.dst_ip}</strong> (${a.flow_id})</td>
                    <td style="color: var(--accent-red); font-weight: 600;">${(a.prediction_prob * 100).toFixed(1)}%</td>
                    <td>${a.risk_score.toFixed(2)}</td>
                    <td><span class="badge pill-${a.risk_level.toLowerCase()}">${a.risk_level}</span></td>
                    <td><span class="badge badge-threat">${a.scenario}</span></td>
                    <td><button class="btn" style="padding: 2px 8px; font-size: 0.75rem;" onclick="explainFlowObj('${a.flow_id}')">Inspect Features</button></td>
                </tr>
            `).join('');
        }

        // Simulation Controls
        async function controlSim(action) {
            try {
                const res = await fetch(`/api/simulation/${action}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ count: 10, interval: 0.25 })
                });
                const data = await res.json();
                pollStatus();
            } catch (e) {
                console.error('Control error:', e);
            }
        }

        async function setScenario(scenario) {
            try {
                const res = await fetch('/api/simulation/scenario', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scenario })
                });
                const data = await res.json();
                document.getElementById('activeScenarioBadge').innerText = data.scenario_type;
                document.getElementById('overviewScenarioDesc').innerText = data.description;

                document.querySelectorAll('.scenario-box').forEach(box => {
                    if (box.getAttribute('onclick').includes(scenario)) {
                        box.classList.add('active');
                    } else {
                        box.classList.remove('active');
                    }
                });
            } catch (e) {
                console.error('Scenario error:', e);
            }
        }

        async function changeModel(model) {
            try {
                const res = await fetch('/api/models/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model })
                });
                const data = await res.json();
                document.getElementById('activeModelBadge').innerText = model.toUpperCase();
                pollStatus();
            } catch (e) {
                console.error('Model change error:', e);
            }
        }

        // Fetch Devices
        async function fetchDevices() {
            try {
                const res = await fetch('/api/devices');
                const data = await res.json();
                const grid = document.getElementById('devicesGrid');
                grid.innerHTML = data.devices.map(d => `
                    <div class="device-card">
                        <div class="device-card-header">
                            <span class="device-name">${d.name}</span>
                            <span class="badge ${d.status === 'ONLINE' ? 'badge-live' : 'badge-threat'}">${d.status}</span>
                        </div>
                        <div class="device-detail"><span>IP Address:</span> <strong>${d.ip_address}</strong></div>
                        <div class="device-detail"><span>Type:</span> <span>${d.device_type}</span></div>
                        <div class="device-detail"><span>Ports:</span> <span>${d.typical_ports.join(', ')}</span></div>
                        <div class="device-detail"><span>Nominal Rate:</span> <span>${d.nominal_rate_pps} pkt/s</span></div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${d.description}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Device fetch error:', e);
            }
        }

        // Adversarial Attack Lab Execution
        async function runAdversarialAttack() {
            const btn = document.getElementById('btnRunAttack');
            btn.disabled = true;
            btn.innerText = '⏳ Perturbing & Evaluating...';

            const payload = {
                attack_method: document.getElementById('advMethod').value,
                epsilon: parseFloat(document.getElementById('advEpsilon').value),
                steps: parseInt(document.getElementById('advSteps').value),
                sample_count: parseInt(document.getElementById('advSamples').value),
            };

            try {
                const res = await fetch('/api/adversarial/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                displayAdversarialResults(data);
            } catch (e) {
                alert('Adversarial experiment failed: ' + e);
            } finally {
                btn.disabled = false;
                btn.innerText = '⚔️ Launch Attack Evaluation';
            }
        }

        function displayAdversarialResults(exp) {
            document.getElementById('advResultsContainer').style.display = 'block';
            document.getElementById('advExpId').innerText = exp.experiment_id;
            document.getElementById('resMethod').innerText = exp.attack_method;
            document.getElementById('resEps').innerText = exp.epsilon;
            document.getElementById('resL2').innerText = exp.perturbation_l2.toFixed(3);
            document.getElementById('resLinf').innerText = exp.perturbation_linf.toFixed(3);

            const aeRate = (exp.risk_layer?.ae_catch_rate || 0.0) * 100;
            document.getElementById('resAECatch').innerText = `${aeRate.toFixed(1)}% (${exp.risk_layer?.suspicious_evaded_count || 0} zero-days flagged)`;

            const models = exp.models;
            const grid = document.getElementById('advMatrixGrid');
            grid.innerHTML = Object.entries(models).map(([name, m]) => {
                const cleanRate = (m.clean_detection_rate * 100).toFixed(1);
                const advRate = (m.adv_detection_rate * 100).toFixed(1);
                const deg = ((m.degradation || 0) * 100).toFixed(1);
                const isRobust = name.includes('robust') || name.includes('option_c');

                return `
                    <div class="matrix-card" style="${isRobust ? 'border-color: var(--accent-green);' : ''}">
                        <div class="matrix-title" style="${isRobust ? 'color: var(--accent-green);' : ''}">${name.toUpperCase().replace('_', ' ')}</div>
                        <div class="metric-row"><span class="metric-label">Clean Detection Rate:</span> <span class="metric-val">${cleanRate}%</span></div>
                        <div class="metric-row"><span class="metric-label">Adversarial Detection Rate:</span> <span class="metric-val" style="color: ${parseFloat(advRate) > 75 ? 'var(--accent-green)' : 'var(--accent-red)'}; font-weight: 700;">${advRate}%</span></div>
                        <div class="metric-row"><span class="metric-label">Degradation:</span> <span class="metric-val">${deg}%</span></div>
                        <div class="metric-row"><span class="metric-label">Mean Adv Probability:</span> <span class="metric-val">${(m.mean_adv_prob * 100).toFixed(1)}%</span></div>
                    </div>
                `;
            }).join('');
        }

        // Explainability (XAI)
        async function explainFlowObj(flowId) {
            switchTab('explainability');
            try {
                const res = await fetch('/api/explain', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flow_id: flowId })
                });
                const xai = await res.json();
                renderXAIWaterfall(xai);
            } catch (e) {
                console.error('XAI error:', e);
            }
        }

        async function requestLatestExplanation() {
            try {
                const res = await fetch('/api/explain', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const xai = await res.json();
                renderXAIWaterfall(xai);
            } catch (e) {
                console.error('XAI error:', e);
            }
        }

        function renderXAIWaterfall(xai) {
            const decEl = document.getElementById('xaiDecision');
            decEl.innerText = xai.final_decision;
            decEl.style.color = xai.final_decision === 'ATTACK' ? 'var(--accent-red)' : 'var(--accent-green)';

            document.getElementById('xaiOptCProb').innerText = `${((xai.option_c_probability || 0.5) * 100).toFixed(1)}%`;
            document.getElementById('xaiRFProb').innerText = `${((xai.rf_probability || 0.5) * 100).toFixed(1)}%`;
            document.getElementById('xaiMLPProb').innerText = `${((xai.mlp_probability || 0.5) * 100).toFixed(1)}%`;

            const feats = xai.top_k_features || [];
            const container = document.getElementById('xaiWaterfallContainer');

            if (!feats.length) {
                container.innerHTML = '<p>No feature attributions returned.</p>';
                return;
            }

            const maxAbs = Math.max(...feats.map(f => Math.abs(f.attribution)), 0.001);

            container.innerHTML = feats.map(f => {
                const widthPct = Math.min((Math.abs(f.attribution) / maxAbs) * 100, 100);
                const isPos = f.attribution >= 0;
                return `
                    <div class="waterfall-bar">
                        <div class="waterfall-label" title="${f.feature}">${f.feature}</div>
                        <div class="waterfall-track">
                            <div class="waterfall-fill ${isPos ? 'positive' : 'negative'}" style="width: ${widthPct}%;"></div>
                        </div>
                        <div class="waterfall-score" style="color: ${isPos ? 'var(--accent-red)' : 'var(--accent-green)'}">
                            ${isPos ? '+' : ''}${f.attribution.toFixed(3)}
                        </div>
                    </div>
                `;
            }).join('');

            const topF = feats[0];
            document.getElementById('xaiNarrative').innerText =
                `Decision was most heavily influenced by feature '${topF.feature}' (${topF.direction > 0 ? 'pushing towards ATTACK' : 'supporting BENIGN'}). ` +
                `Combined dual-stream confidence is ${((xai.option_c_probability || 0.5) * 100).toFixed(1)}%.`;
        }

        // Export JSON
        function exportAlertsJSON() {
            const blob = new Blob([JSON.stringify(recentAlertsList, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ids_alerts_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }

        // Status Polling
        async function pollStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                updateKPIs(data);
            } catch (e) {
                console.error('Status poll error:', e);
            }
        }

        function updateKPIs(status) {
            const p = status.pipeline;
            if (!p) return;
            document.getElementById('kpiPackets').innerText = p.total_packets.toLocaleString();
            document.getElementById('kpiFlows').innerText = p.total_flows.toLocaleString();
            document.getElementById('kpiAlerts').innerText = p.total_alerts.toLocaleString();
            document.getElementById('kpiAttacks').innerText = p.total_attacks_detected.toLocaleString();
            document.getElementById('kpiThroughput').innerText = p.packets_per_second.toFixed(1);
            document.getElementById('kpiHealth').innerText = p.health;

            document.getElementById('footerUptime').innerText = `Uptime: ${Math.floor(status.uptime_seconds)}s`;

            if (status.provenance) {
                const prov = status.provenance;
                const suiteEl = document.getElementById('provenanceSuiteType');
                const suiteDesc = document.getElementById('provenanceSuiteDesc');
                const authEl = document.getElementById('provenanceAuthStatus');
                const authDesc = document.getElementById('provenanceAuthDesc');
                if (suiteEl) {
                    suiteEl.innerText = prov.model_suite_type === 'VERIFIED_RESEARCH_BASELINE'
                        ? `Verified Research Baseline (${prov.dataset_name})`
                        : 'Synthetic-Reference Suite (Seed: 42)';
                }
                if (suiteDesc && prov.model_suite_type === 'VERIFIED_RESEARCH_BASELINE') {
                    suiteDesc.innerText = `Authoritative 21-Feature Checkpoints at ${prov.artifact_path}`;
                }
                if (authEl) {
                    const isAuth = prov.model_authorization_status === 'AUTHORIZED_CRYPTOGRAPHIC_POLICY';
                    authEl.innerText = isAuth
                        ? 'Authorized (Cryptographic Policy HMAC-SHA256)'
                        : 'Blocked (Fail-Closed)';
                    authEl.style.color = isAuth ? 'var(--accent-green)' : 'var(--accent-yellow)';
                }
                if (authDesc && prov.model_authorization_status === 'AUTHORIZED_CRYPTOGRAPHIC_POLICY') {
                    authDesc.innerText = 'Cryptographic policy verified: signature valid, non-overlapping roots';
                }
            }
        }

        async function fetchRecentFlows() {
            try {
                const res = await fetch('/api/flows?limit=50');
                const data = await res.json();
                recentFlowsList = data.flows;
                renderTelemetryTable();
            } catch (e) {
                console.error('Fetch flows error:', e);
            }
        }

        async function fetchRecentAlerts() {
            try {
                const res = await fetch('/api/alerts?limit=50');
                const data = await res.json();
                recentAlertsList = data.alerts;
                renderAlertsTable();
            } catch (e) {
                console.error('Fetch alerts error:', e);
            }
        }

        async function fetchExperiments() {
            try {
                const res = await fetch('/api/experiments');
                const data = await res.json();
                const tbody = document.getElementById('experimentsTable');
                if (!data.experiments.length) {
                    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No adversarial experiments executed yet in this session.</td></tr>`;
                    return;
                }
                tbody.innerHTML = data.experiments.map(e => `
                    <tr>
                        <td style="font-family: monospace; font-weight: 600;">${e.experiment_id}</td>
                        <td style="font-size: 0.75rem; color: var(--text-secondary);">${new Date(e.timestamp * 1000).toLocaleTimeString()}</td>
                        <td>${e.attack_method}</td>
                        <td>${e.epsilon}</td>
                        <td>${e.steps}</td>
                        <td>${e.samples_attacked}</td>
                        <td style="color: var(--accent-red); font-weight: 600;">${((e.models.standard_mlp.degradation || 0) * 100).toFixed(1)}% drop</td>
                        <td style="color: var(--accent-green); font-weight: 600;">${((e.models.robust_mlp.degradation || 0) * 100).toFixed(1)}% drop</td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error('Fetch experiments error:', e);
            }
        }

        // Init
        window.addEventListener('DOMContentLoaded', () => {
            connectWebSocket();
            pollStatus();
            setInterval(pollStatus, 3000);
        });
    </script>
</body>
</html>
"""
