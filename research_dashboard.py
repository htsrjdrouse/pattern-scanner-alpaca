"""
Research dashboard routes for signal monitoring and analysis.
"""
from flask import render_template_string, request
import pandas as pd
from datetime import datetime, timedelta


RESEARCH_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Alpha Research Platform</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #4fc3f7;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #9e9e9e;
            margin-bottom: 30px;
        }
        .nav {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
        }
        .nav a, .nav button {
            padding: 10px 20px;
            background: #3a3a52;
            color: #4fc3f7;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
            border: none;
            cursor: pointer;
            font-size: 1em;
        }
        .nav a:hover, .nav button:hover {
            background: #4a4a62;
        }
        .nav a.active, .nav button.active {
            background: #4fc3f7;
            color: #1e1e2e;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
            background: #4a4a62;
        }
        .section {
            background: #2a2a3e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .section h2 {
            color: #4fc3f7;
            margin-top: 0;
            border-bottom: 2px solid #4fc3f7;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            table-layout: fixed;
        }
        th, td {
            padding: 12px 8px;
            text-align: center;
            border-bottom: 1px solid #3a3a52;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        th:first-child, td:first-child {
            text-align: left;
            font-weight: 600;
        }
        th {
            background: #3a3a52;
            color: #4fc3f7;
            font-weight: 600;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background: #3a3a52;
        }
        .metric {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            margin: 0;
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
            min-width: 60px;
            text-align: center;
        }
        .metric.positive {
            background: #1b5e20;
            color: #4caf50;
        }
        .metric.negative {
            background: #b71c1c;
            color: #ef5350;
        }
        .metric.neutral {
            background: #424242;
            color: #9e9e9e;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #b0b0b0;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            background: #3a3a52;
            border: 1px solid #4a4a62;
            border-radius: 5px;
            color: #e0e0e0;
            box-sizing: border-box;
        }
        button {
            padding: 12px 30px;
            background: #4fc3f7;
            color: #1e1e2e;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
        }
        button:hover {
            background: #29b6f6;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
    </style>
</head>
<body>
    <!-- Version: 2026-03-12-06:50 - Robinhood text import + bulk delete -->
    <div class="container">
        <h1>🔬 Alpha Research Platform</h1>
        <p class="subtitle">Systematic signal analysis and backtesting</p>
        
        <div class="nav">
            <a href="/">Pattern Scanner</a>
            <button onclick="showTab('morning-brief')" id="tab-morning-brief">🌅 Morning Brief</button>
            <button onclick="showTab('signals')" id="tab-signals" class="active">Signal Analysis</button>
            <button onclick="showTab('sector-scan')" id="tab-sector-scan">Sector Scan</button>
            <button onclick="showTab('regime')" id="tab-regime">Regime Classifier</button>
            <button onclick="showTab('macro')" id="tab-macro">Macro Regime</button>
            <button onclick="showTab('risk')" id="tab-risk">Risk Manager</button>
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <span id="tastytrade-badge" style="padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; background: #4caf50; color: #fff;">
                TT LIVE
            </span>
            <script>
                // Define showTab early so onclick handlers work
                function showTab(tabName) {
                    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
                    document.getElementById(tabName + '-tab').classList.add('active');
                    document.getElementById('tab-' + tabName).classList.add('active');
                }
                
                // Update badge immediately
                fetch('/signals/tastytrade/status')
                    .then(r => r.json())
                    .then(d => {
                        const b = document.getElementById('tastytrade-badge');
                        if (!d.connected) {
                            b.textContent = 'TT OFFLINE';
                            b.style.background = '#f44336';
                        } else if (d.env !== 'production') {
                            b.textContent = 'TT SANDBOX';
                            b.style.background = '#ff9800';
                            b.style.color = '#000';
                        }
                    })
                    .catch(() => {
                        const b = document.getElementById('tastytrade-badge');
                        b.textContent = 'TT ERROR';
                        b.style.background = '#9e9e9e';
                    });
            </script>
        </div>

        <div id="signals-tab" class="tab-content active">

        <div class="section">
            <h2>ℹ️ What This Tool Does</h2>
            <p style="color: #b0b0b0; line-height: 1.6;">
                This platform tests whether technical signals can predict future stock returns. It answers: 
                <strong>"If I buy stocks with high signal values, will they outperform?"</strong>
            </p>
            <details style="margin-top: 15px;">
                <summary style="cursor: pointer; color: #4fc3f7; font-weight: 600;">📖 Metric Explanations</summary>
                <div style="margin-top: 10px; padding: 15px; background: #1e1e2e; border-radius: 5px; line-height: 1.8;">
                    <p><strong style="color: #4fc3f7;">IC (Information Coefficient)</strong><br>
                    Correlation between the signal and actual future returns. Ranges from -1 to +1. For sector trend detection:<br>
                    • Below 0.02 → signal has no real edge, ignore it<br>
                    • 0.02–0.05 → weak but potentially useful, especially combined with others<br>
                    • 0.05–0.10 → solid edge, this signal is worth using<br>
                    • Above 0.10 → strong edge, rare to see, trust it</p>
                    
                    <p><strong style="color: #4fc3f7;">Hit Rate</strong><br>
                    Percentage of times the signal correctly predicted the direction of price movement. For sector work:<br>
                    • Below 50% → worse than a coin flip, not useful<br>
                    • 50–55% → marginal, only useful if the wins are bigger than the losses<br>
                    • 55–60% → good, this signal has real directional accuracy<br>
                    • Above 60% → excellent for a trend-detection signal</p>
                    
                    <p><strong style="color: #4fc3f7;">Long Ret (Long Return)</strong><br>
                    Average return when you follow the signal's buy recommendation. You want this to be meaningfully positive — at least 1-2% over your backtest horizon. If it's near zero the signal isn't generating real returns even when it's "right."</p>
                    
                    <p><strong style="color: #4fc3f7;">L/S Ret (Long/Short Return)</strong><br>
                    Return of buying the top signal stocks and shorting the bottom signal stocks. For sector work where you're not shorting, focus less on this. But a high L/S return confirms the signal discriminates well between strong and weak sectors.</p>
                    
                    <p><strong style="color: #4fc3f7;">L/S Sharpe (Long/Short Sharpe Ratio)</strong><br>
                    Risk-adjusted return of the long/short portfolio. Arguably the most important single number:<br>
                    • Below 0.5 → weak, not worth using as a standalone signal<br>
                    • 0.5–1.0 → acceptable, consider combining with other signals<br>
                    • 1.0–1.5 → good, this is a real signal with consistent edge<br>
                    • Above 1.5 → excellent, this signal works reliably</p>
                    
                    <p style="margin-bottom: 0;"><strong style="color: #4fc3f7;">Obs (Observations)</strong><br>
                    Number of data points in the backtest. Your statistical confidence check. Under 100 observations means the results could easily be noise — you can't trust them. For sector baskets of 20-25 stocks over 2 years of daily data you'll typically get plenty of observations, but watch for signals that trigger rarely (like cup & handle) where obs might be low.</p>
                </div>
            </details>
        </div>

        <div class="section">
            <h2>🧪 Quick Backtest</h2>
            <form id="backtestForm">
                <div class="grid">
                    <div class="form-group">
                        <label>Signals (Ctrl+Click for multiple)</label>
                        <select name="signal_names" multiple size="8" required>
                            {% for name in signals.keys() %}
                            <option value="{{ name }}">{{ name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Sector <button type="button" onclick="showSectorManager()" style="padding: 4px 8px; font-size: 0.85em; margin-left: 10px;">Manage</button></label>
                        <select id="sectorSelect" name="sector">
                            <option value="">Custom Symbols</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Symbols (comma-separated)</label>
                        <input type="text" id="symbolsInput" name="symbols" value="AAPL,MSFT,GOOGL,AMZN,NVDA" required>
                    </div>
                    <div class="form-group">
                        <label>Timeframe</label>
                        <select name="timeframe" required>
                            <option value="3m">3 Months</option>
                            <option value="6m" selected>6 Months</option>
                            <option value="1y">1 Year</option>
                            <option value="2y">2 Years</option>
                            <option value="3y">3 Years</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Horizon (days)</label>
                        <input type="number" name="horizon_days" value="10" required>
                    </div>
                </div>
                <button type="submit">Run Backtest</button>
            </form>
            <div id="results" style="margin-top: 20px;"></div>
        </div>

        <div id="sectorModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; overflow-y: auto;">
            <div style="max-width: 900px; margin: 50px auto; background: #2a2a3e; padding: 30px; border-radius: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #4fc3f7;">Sector Manager</h2>
                    <button onclick="hideSectorManager()" style="background: #ef5350;">Close</button>
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h3 style="color: #4fc3f7;">Create New Sector</h3>
                    <form id="createSectorForm">
                        <div class="form-group">
                            <label>Sector ID (lowercase, underscores)</label>
                            <input type="text" id="newSectorId" placeholder="e.g., tech_giants" required>
                        </div>
                        <div class="form-group">
                            <label>Sector Name</label>
                            <input type="text" id="newSectorName" placeholder="e.g., Tech Giants" required>
                        </div>
                        <div class="form-group">
                            <label>Tickers (comma-separated)</label>
                            <textarea id="newSectorTickers" rows="3" placeholder="AAPL,MSFT,GOOGL,AMZN,META" required></textarea>
                        </div>
                        <button type="submit">Create Sector</button>
                    </form>
                </div>

                <div>
                    <h3 style="color: #4fc3f7;">Existing Sectors</h3>
                    <div id="sectorList"></div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📈 Signal Correlation Analysis</h2>
            <p style="color: #9e9e9e;">Compare multiple signals to identify redundancy and diversification opportunities.</p>
            <form id="correlationForm">
                <div class="grid">
                    <div class="form-group">
                        <label>Select Signals (Ctrl+Click for multiple)</label>
                        <select name="signal_names" multiple size="8" required>
                            {% for name in signals.keys() %}
                            <option value="{{ name }}">{{ name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Sector <button type="button" onclick="showSectorManager()" style="padding: 4px 8px; font-size: 0.85em; margin-left: 10px;">Manage</button></label>
                        <select id="corrSectorSelect" name="sector">
                            <option value="">Custom Symbols</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Symbols (comma-separated)</label>
                        <input type="text" id="corrSymbolsInput" name="symbols" value="AAPL,MSFT,GOOGL,AMZN,NVDA" required>
                    </div>
                </div>
                <button type="submit">Compute Correlation</button>
            </form>
            <div id="corrResults" style="margin-top: 20px;"></div>
        </div>
        </div>

        <!-- Sector Scan Tab -->
        <div id="sector-scan-tab" class="tab-content">
            <div class="section">
                <h2>🎯 Sector Scan Control Panel</h2>
                <p style="color: #9e9e9e;">Automated sector analysis with configurable signals and scheduling</p>
                
                <div class="grid" style="grid-template-columns: 1fr 1fr;">
                    <div>
                        <h3 style="color: #4fc3f7;">Scan Configuration</h3>
                        <div class="form-group">
                            <label>Signals to Run</label>
                            <div style="max-height: 200px; overflow-y: auto; padding: 10px; background: #1e1e2e; border-radius: 5px; margin-top: 5px;">
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="momentum_20" checked> momentum_20 (20-day momentum)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="ma_cross_50_200" checked> ma_cross_50_200 (Golden/Death cross)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="adx_14" checked> adx_14 (Trend strength)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="cto_larsson" checked> cto_larsson (CTO lines)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="rsi_14"> rsi_14 (Oversold/overbought)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="macd"> macd (MACD crossover)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check" value="volume_surge_20"> volume_surge_20 (Volume spike)</label>
                                <hr style="border-color: #3a3a52; margin: 8px 0;">
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check pattern-signal" value="cup_handle"> cup_handle (Pattern)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check pattern-signal" value="bull_flag"> bull_flag (Pattern)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check pattern-signal" value="asc_triangle"> asc_triangle (Pattern)</label>
                                <label style="display: block; margin: 3px 0; cursor: pointer;"><input type="checkbox" class="signal-check pattern-signal" value="double_bottom"> double_bottom (Pattern)</label>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Timeframe</label>
                            <select id="scanTimeframe">
                                <option value="365">1 Year (recommended for daily)</option>
                                <option value="730">2 Years (recommended for weekly)</option>
                                <option value="1095">3 Years</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Minimum Stocks per Sector</label>
                            <input type="number" id="minStocks" value="15" min="5" max="25">
                        </div>
                        <button onclick="runScanNow()" id="runScanBtn">Run Scan Now</button>
                        <p style="color: #9e9e9e; font-size: 0.9em; margin-top: 10px;">💡 Tip: Pattern signals work best with 2+ year timeframes</p>
                    </div>
                    
                    <div>
                        <h3 style="color: #4fc3f7;">Automated Scheduling</h3>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="schedulerEnabled" onchange="toggleScheduler()">
                                Enable Automated Scanning
                            </label>
                        </div>
                        <div class="form-group">
                            <label>Daily Scan Time (Weekdays)</label>
                            <input type="time" id="dailyTime" value="16:30">
                        </div>
                        <div class="form-group">
                            <label>Weekly Scan (Sunday)</label>
                            <input type="time" id="weeklyTime" value="18:00">
                        </div>
                        <div id="schedulerStatus" style="margin-top: 15px; padding: 10px; background: #1e1e2e; border-radius: 5px;">
                            <p style="margin: 5px 0;"><strong>Status:</strong> <span id="schedStatus">Stopped</span></p>
                            <p style="margin: 5px 0;"><strong>Next Daily:</strong> <span id="nextDaily">-</span></p>
                            <p style="margin: 5px 0;"><strong>Next Weekly:</strong> <span id="nextWeekly">-</span></p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>📊 Latest Sector Scorecard</h2>
                <p style="color: #9e9e9e; margin-bottom: 10px;">
                    Scanning 19 sectors from your sector baskets. 
                    <button onclick="showSectorManager()" style="padding: 4px 12px; font-size: 0.9em; background: #4fc3f7; color: #1e1e2e; border: none; border-radius: 3px; cursor: pointer;">Manage Sectors & Tickers</button>
                </p>
                <div id="scanProgress" style="display: none; padding: 15px; background: #1e1e2e; border-radius: 5px; margin-bottom: 15px;">
                    <p style="margin: 0;"><strong>Scan in progress...</strong></p>
                    <p id="progressText" style="margin: 5px 0 0 0; color: #9e9e9e;">Starting scan...</p>
                </div>
                <div id="scorecardResults">
                    <p style="color: #9e9e9e;">No results yet. Run a scan to see the scorecard.</p>
                </div>
            </div>
        </div>

        <!-- REGIME CLASSIFIER TAB -->
        <div id="regime-tab" class="tab-content">
            <div class="section">
                <h2>🎯 Market Regime Classifier</h2>
                <p style="color: #9e9e9e;">Pre-market intelligence for options premium selling strategies</p>
                
                <!-- Verdict Banner -->
                <div id="verdictBanner" style="margin: 20px 0; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                        <div id="verdictBadge" style="font-size: 1.8em; font-weight: bold;">LOADING...</div>
                        <div style="display: flex; gap: 30px; align-items: center;">
                            <span>SPX: <strong id="spxPrice">-</strong></span>
                            <span>VIX: <strong id="vixLevel">-</strong></span>
                            <span>Score: <strong id="compositeScore">-</strong>/100</span>
                            <span style="color: #9e9e9e; font-size: 0.9em;" id="regimeTimestamp">-</span>
                            <button onclick="refreshRegime()" style="padding: 8px 16px; background: #4fc3f7; color: #1e1e2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">🔄 Refresh</button>
                        </div>
                    </div>
                </div>
                
                <!-- Hard Override Warning -->
                <div id="overrideWarning" style="display: none; padding: 15px; background: #7f1d1d; color: white; border-radius: 5px; margin: 10px 0; font-weight: bold;">
                    ⚠️ HARD OVERRIDE: <span id="overrideReason"></span>
                </div>

                <!-- 7-Dimension Scorecard Grid -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">7-Dimension Analysis</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 15px; margin-top: 15px;" id="dimensionsGrid">
                    <!-- Populated by JavaScript -->
                </div>

                <!-- Strategy Recommendation Panel -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">📋 Strategy Recommendation</h3>
                <div id="strategyPanel" style="margin-top: 15px; padding: 20px; background: #1e1e2e; border-radius: 8px; border-left: 4px solid #4fc3f7;">
                    <p style="font-size: 1.3em; font-weight: bold; margin: 10px 0;" id="recommendedStrategy">-</p>
                    <p style="margin: 10px 0;"><strong>💰 Position Sizing:</strong> <span id="positionSizing">-</span></p>
                    <p style="margin: 10px 0;"><strong>⏰ Entry Timing:</strong> <span id="entryTiming">-</span></p>
                </div>

                <!-- Regime History Chart + Table -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">30-Day Regime History</h3>
                <div style="display: grid; grid-template-columns: 60% 40%; gap: 20px; margin-top: 15px;">
                    <div>
                        <canvas id="regimeChart" style="max-height: 300px;"></canvas>
                    </div>
                    <div style="max-height: 300px; overflow-y: auto;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
                            <thead style="position: sticky; top: 0; background: #2a2a3e;">
                                <tr>
                                    <th style="padding: 8px; text-align: left;">Date</th>
                                    <th style="padding: 8px; text-align: right;">VIX</th>
                                    <th style="padding: 8px; text-align: right;">Score</th>
                                    <th style="padding: 8px; text-align: center;">Verdict</th>
                                </tr>
                            </thead>
                            <tbody id="historyTable">
                                <!-- Populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Data Source Status Bar -->
                <div style="margin-top: 30px; padding: 15px; background: #1e1e2e; border-radius: 8px; font-size: 0.9em; color: #9e9e9e;">
                    <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
                        <span>Term Structure: <strong id="termSource">-</strong></span>
                        <span>Last Updated: <strong id="lastUpdated">-</strong></span>
                        <span>Cache: <strong id="cacheStatus">-</strong></span>
                        <span style="cursor: pointer;" onclick="toggleErrors()">Errors: <strong id="errorCount">-</strong></span>
                    </div>
                    <div id="errorList" style="display: none; margin-top: 10px; padding: 10px; background: #0f0f23; border-radius: 4px; max-height: 100px; overflow-y: auto;">
                        <!-- Populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>

        <!-- MACRO REGIME TAB -->
        <div id="macro-tab" class="tab-content">
            <div class="section">
                <h2>🌍 Macro Regime Overlay</h2>
                <p style="color: #9e9e9e;">Geopolitical and macro context for pattern scanner</p>
                
                <div style="display: flex; gap: 20px; margin-top: 20px;">
                    <button onclick="loadMacroRegime()" style="padding: 10px 20px; background: #4fc3f7; color: #1e1e2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Load Regime</button>
                    <button onclick="loadMacroRegime(true)" style="padding: 10px 20px; background: #ff9800; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Force Refresh</button>
                </div>
                
                <div id="macroRegimeContent" style="margin-top: 30px;"></div>
            </div>
        </div>

        <!-- RISK MANAGER TAB -->
        <div id="risk-tab" class="tab-content">
            <div class="section">
                <h2>🛡️ Wolverine Risk Management System</h2>
                <p style="color: #9e9e9e;">Cross-account portfolio risk monitor with live Alpaca integration</p>
                
                <!-- Alert Banner -->
                <div id="riskAlertBanner" style="margin: 20px 0; padding: 15px; border-radius: 8px; display: none;">
                    <div id="riskAlertContent"></div>
                    <button onclick="resetBaseline()" style="margin-top: 10px; padding: 8px 16px; background: #4fc3f7; color: #1e1e2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Reset Baseline (Fix False Alert)</button>
                </div>
                
                <!-- Risk Status Dashboard -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div class="card" style="text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: #9e9e9e;">Daily P&L</h4>
                        <div id="dailyPnl" style="font-size: 1.5em; font-weight: bold;">$0</div>
                        <div style="margin-top: 10px; background: #0f0f23; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div id="dailyPnlBar" style="height: 100%; width: 0%; background: #22c55e;"></div>
                        </div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: #9e9e9e;">Weekly P&L</h4>
                        <div id="weeklyPnl" style="font-size: 1.5em; font-weight: bold;">$0</div>
                        <div style="margin-top: 10px; background: #0f0f23; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div id="weeklyPnlBar" style="height: 100%; width: 0%; background: #22c55e;"></div>
                        </div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: #9e9e9e;">Monthly P&L</h4>
                        <div id="monthlyPnl" style="font-size: 1.5em; font-weight: bold;">$0</div>
                        <div style="margin-top: 10px; background: #0f0f23; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div id="monthlyPnlBar" style="height: 100%; width: 0%; background: #22c55e;"></div>
                        </div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: #9e9e9e;">Buying Power</h4>
                        <div id="buyingPower" style="font-size: 1.5em; font-weight: bold;">0%</div>
                        <div style="margin-top: 10px; background: #0f0f23; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div id="buyingPowerBar" style="height: 100%; width: 0%; background: #22c55e;"></div>
                        </div>
                    </div>
                    <div class="card" style="text-align: center;">
                        <h4 style="margin: 0 0 10px 0; color: #9e9e9e;">VIX</h4>
                        <div id="vixLevel" style="font-size: 1.5em; font-weight: bold;">-</div>
                        <div id="vixChange" style="margin-top: 5px; font-size: 0.9em; color: #9e9e9e;">-</div>
                    </div>
                </div>

                <!-- Account Breakdown -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">Account Breakdown</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;" id="accountsGrid">
                    <!-- Populated by JavaScript -->
                </div>

                <!-- Portfolio Exposure -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">Portfolio Exposure</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div class="card">
                        <h4 style="margin: 0 0 10px 0;">Directional Bias</h4>
                        <div id="directionalBias" style="font-size: 1.2em; font-weight: bold; margin: 10px 0;">NEUTRAL</div>
                        <div style="background: #0f0f23; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div id="deltaBar" style="height: 100%; width: 50%; background: #6b7280;"></div>
                        </div>
                    </div>
                    <div class="card">
                        <h4 style="margin: 0 0 10px 0;">PDT Tracker</h4>
                        <div id="pdtInfo" style="margin: 10px 0;">
                            <p style="margin: 5px 0;"><strong>Day Trades:</strong> <span id="pdtCount">0 / 3</span></p>
                            <p style="margin: 5px 0;"><strong>Remaining:</strong> <span id="pdtRemaining">3</span></p>
                            <p style="margin: 5px 0;"><strong>Account Equity:</strong> <span id="pdtEquity">$0</span></p>
                        </div>
                    </div>
                </div>

                <!-- Positions Table -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">Open Positions</h3>
                <div style="margin-top: 15px; max-height: 400px; overflow-y: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead style="position: sticky; top: 0; background: #16213e;">
                            <tr>
                                <th style="padding: 10px; text-align: left;">Symbol</th>
                                <th style="padding: 10px; text-align: left;">Account</th>
                                <th style="padding: 10px; text-align: left;">Type</th>
                                <th style="padding: 10px; text-align: left;">Side</th>
                                <th style="padding: 10px; text-align: right;">Qty</th>
                                <th style="padding: 10px; text-align: right;">Market Value</th>
                                <th style="padding: 10px; text-align: right;">Unrealized P&L</th>
                                <th style="padding: 10px; text-align: right;">P&L %</th>
                                <th style="padding: 10px; text-align: center;">Action</th>
                            </tr>
                        </thead>
                        <tbody id="positionsTable">
                            <!-- Populated by JavaScript -->
                        </tbody>
                    </table>
                </div>

                <!-- Add Manual Position Form -->
                <details style="margin-top: 30px;">
                    <summary style="cursor: pointer; color: #4fc3f7; font-weight: 600; padding: 10px; background: #1e1e2e; border-radius: 5px;">➕ Add Manual Position</summary>
                    <div style="margin-top: 15px; padding: 20px; background: #1e1e2e; border-radius: 8px;">
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Symbol</label>
                                <input type="text" id="manualSymbol" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Account</label>
                                <select id="manualAccount" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                                    <option value="thinkorswim">ThinkorSwim</option>
                                    <option value="sofi">SoFi</option>
                                    <option value="robinhood">Robinhood</option>
                                </select>
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Position Type</label>
                                <select id="manualType" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                                    <option value="equity">Equity</option>
                                    <option value="call_option">Call Option</option>
                                    <option value="put_option">Put Option</option>
                                    <option value="call_spread">Call Spread</option>
                                    <option value="put_spread">Put Spread</option>
                                    <option value="iron_condor">Iron Condor</option>
                                </select>
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Side</label>
                                <select id="manualSide" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                                    <option value="long">Long</option>
                                    <option value="short">Short</option>
                                </select>
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Quantity</label>
                                <input type="number" id="manualQty" step="0.01" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Cost Basis</label>
                                <input type="number" id="manualCost" step="0.01" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                            </div>
                            <div>
                                <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Current Price</label>
                                <input type="number" id="manualPrice" step="0.01" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;">
                            </div>
                        </div>
                        <div style="margin-top: 15px;">
                            <label style="display: block; margin-bottom: 5px; color: #9e9e9e;">Notes</label>
                            <textarea id="manualNotes" rows="2" style="width: 100%; padding: 8px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px;"></textarea>
                        </div>
                        <button onclick="addManualPosition()" style="margin-top: 15px; padding: 10px 20px; background: #4fc3f7; color: #1e1e2e; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Add Position</button>
                    </div>
                </details>

                <!-- Bulk Import: Robinhood Text -->
                <details style="margin-top: 20px;">
                    <summary style="cursor: pointer; color: #22c55e; font-weight: 600; padding: 10px; background: #1e1e2e; border-radius: 5px;">📋 Bulk Import: Robinhood (Paste Text)</summary>
                    <div style="margin-top: 15px; padding: 20px; background: #1e1e2e; border-radius: 8px;">
                        <p style="color: #9e9e9e; margin-bottom: 10px; font-size: 0.9em;">Copy your portfolio from Robinhood app and paste here (Name, Symbol, Shares, Price, etc.)</p>
                        <textarea id="robinhoodText" rows="10" placeholder="Tesla&#10;TSLA&#10;19.352&#10;$417.44&#10;$386.79&#10;$593.13&#10;$8,078.13&#10;..." style="width: 100%; padding: 10px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px; font-family: monospace; font-size: 0.85em;"></textarea>
                        <button id="importRobinhoodBtn" style="margin-top: 10px; padding: 10px 20px; background: #22c55e; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Import Robinhood Positions</button>
                        <button onclick="deleteByAccount('robinhood')" style="margin-top: 10px; margin-left: 10px; padding: 10px 20px; background: #ef4444; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Delete All Robinhood</button>
                    </div>
                </details>

                <!-- Bulk Import: ThinkorSwim CSV -->
                <details style="margin-top: 20px;">
                    <summary style="cursor: pointer; color: #f59e0b; font-weight: 600; padding: 10px; background: #1e1e2e; border-radius: 5px;">📁 Bulk Import: ThinkorSwim CSV</summary>
                    <div style="margin-top: 15px; padding: 20px; background: #1e1e2e; border-radius: 8px;">
                        <p style="color: #9e9e9e; margin-bottom: 10px; font-size: 0.9em;">Upload your ThinkorSwim Position Statement CSV file</p>
                        <input type="file" id="tosFile" accept=".csv" style="margin-bottom: 10px; color: #fff;">
                        <button id="importTosBtn" style="padding: 10px 20px; background: #f59e0b; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Import ThinkorSwim Positions</button>
                        <button onclick="deleteByAccount('thinkorswim')" style="margin-left: 10px; padding: 10px 20px; background: #ef4444; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Delete All ThinkorSwim</button>
                    </div>
                </details>

                <!-- Bulk Import: Schwab Positions -->
                <details style="margin-top: 20px;">
                    <summary style="cursor: pointer; color: #8b5cf6; font-weight: 600; padding: 10px; background: #1e1e2e; border-radius: 5px;">📊 Bulk Import: Schwab (Paste Text)</summary>
                    <div style="margin-top: 15px; padding: 20px; background: #1e1e2e; border-radius: 8px;">
                        <p style="color: #9e9e9e; margin-bottom: 10px; font-size: 0.9em;">Copy ALL your positions from Schwab and paste here</p>
                        <textarea id="schwabText" rows="10" style="width: 100%; padding: 10px; background: #0f0f23; color: #fff; border: 1px solid #333; border-radius: 4px; font-family: monospace; font-size: 0.85em;"></textarea>
                        <button id="importSchwabBtn" style="margin-top: 10px; padding: 10px 20px; background: #8b5cf6; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Import Schwab Positions</button>
                        <button onclick="deleteByAccount('schwab')" style="margin-top: 10px; margin-left: 10px; padding: 10px 20px; background: #ef4444; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Delete All Schwab</button>
                    </div>
                </details>

                <!-- 30-Day P&L History -->
                <h3 style="color: #4fc3f7; margin-top: 30px;">30-Day P&L History</h3>
                <div style="margin-top: 15px;">
                    <canvas id="riskHistoryChart" style="max-height: 200px;"></canvas>
                </div>
            </div>
        </div>

    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        let sectorsData = {};
        let currentJobId = null;
        let regimeChart = null;

        // Override showTab with full version that handles tab-specific logic
        function showTab(tabName) {
            // Deactivate previous tab
            const previousTab = document.querySelector('.tab-content.active');
            if (previousTab) {
                const prevTabName = previousTab.id.replace('-tab', '');
                if (prevTabName === 'regime' && typeof onRegimeTabDeactivated === 'function') {
                    onRegimeTabDeactivated();
                }
            }
            
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            
            document.getElementById(tabName + '-tab').classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
            
            // Activate new tab - use setTimeout to ensure functions are defined
            setTimeout(() => {
                if (tabName === 'sector-scan' && typeof loadSchedulerStatus === 'function') {
                    loadSchedulerStatus();
                    loadLatestResults();
                } else if (tabName === 'regime' && typeof onRegimeTabActivated === 'function') {
                    onRegimeTabActivated();
                } else if (tabName === 'risk' && typeof loadRiskSnapshot === 'function') {
                    loadRiskSnapshot();
                }
            }, 0);
        }

        async function loadSchedulerStatus() {
            try {
                const response = await fetch('/signals/sector/schedule');
                const data = await response.json();
                
                document.getElementById('schedulerEnabled').checked = data.config.enabled;
                document.getElementById('dailyTime').value = data.config.daily_time;
                document.getElementById('weeklyTime').value = data.config.weekly_time;
                document.getElementById('minStocks').value = data.config.min_stocks;
                
                document.getElementById('schedStatus').textContent = data.running ? 'Running' : 'Stopped';
                document.getElementById('schedStatus').style.color = data.running ? '#4caf50' : '#ef5350';
                document.getElementById('nextDaily').textContent = data.next_daily ? new Date(data.next_daily).toLocaleString() : '-';
                document.getElementById('nextWeekly').textContent = data.next_weekly ? new Date(data.next_weekly).toLocaleString() : '-';
            } catch (error) {
                console.error('Failed to load scheduler status:', error);
            }
        }

        async function toggleScheduler() {
            const enabled = document.getElementById('schedulerEnabled').checked;
            const dailyTime = document.getElementById('dailyTime').value;
            const weeklyTime = document.getElementById('weeklyTime').value;
            const minStocks = parseInt(document.getElementById('minStocks').value);
            
            try {
                await fetch('/signals/sector/schedule', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        enabled: enabled,
                        daily_time: dailyTime,
                        weekly_time: weeklyTime,
                        weekly_day: 'sunday',
                        min_stocks: minStocks
                    })
                });
                
                setTimeout(loadSchedulerStatus, 1000);
            } catch (error) {
                alert('Failed to update scheduler: ' + error.message);
            }
        }

        async function runScanNow() {
            const selectedSignals = Array.from(document.querySelectorAll('.signal-check:checked')).map(cb => cb.value);
            const timeframe = parseInt(document.getElementById('scanTimeframe').value);
            const minStocks = parseInt(document.getElementById('minStocks').value);
            const btn = document.getElementById('runScanBtn');
            
            if (selectedSignals.length === 0) {
                alert('Please select at least one signal');
                return;
            }
            
            btn.disabled = true;
            btn.textContent = 'Scanning...';
            document.getElementById('scanProgress').style.display = 'block';
            
            try {
                const response = await fetch('/signals/sector/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        mode: 'custom',
                        min_stocks: minStocks,
                        signals: selectedSignals
                    })
                });
                const data = await response.json();
                
                if (data.success) {
                    currentJobId = data.job_id;
                    document.getElementById('progressText').textContent = `Running ${selectedSignals.length} signals on 19 sectors...`;
                    checkScanStatus();
                } else {
                    alert('Failed to start scan: ' + (data.error || 'Unknown error'));
                    btn.disabled = false;
                    btn.textContent = 'Run Scan Now';
                    document.getElementById('scanProgress').style.display = 'none';
                }
            } catch (error) {
                alert('Failed to start scan: ' + error.message);
                btn.disabled = false;
                btn.textContent = 'Run Scan Now';
                document.getElementById('scanProgress').style.display = 'none';
            }
        }

        async function checkScanStatus() {
            if (!currentJobId) return;
            
            try {
                const response = await fetch(`/signals/sector/status/${currentJobId}`);
                const data = await response.json();
                
                if (data.status === 'running') {
                    document.getElementById('progressText').textContent = 'Processing sectors...';
                    setTimeout(checkScanStatus, 3000);
                } else {
                    document.getElementById('scanProgress').style.display = 'none';
                    document.getElementById('runScanBtn').disabled = false;
                    document.getElementById('runScanBtn').textContent = 'Run Scan Now';
                    currentJobId = null;
                    loadLatestResults();
                }
            } catch (error) {
                console.error('Failed to check scan status:', error);
            }
        }

        async function loadLatestResults() {
            try {
                const response = await fetch('/signals/sector/results');
                const data = await response.json();
                
                if (data.results && data.results.length > 0) {
                    displayScorecard(data.results, data.timestamp);
                }
            } catch (error) {
                console.error('No results available:', error);
            }
        }

        function displayScorecard(results, timestamp) {
            const date = new Date(timestamp * 1000).toLocaleString();
            
            let html = `<p style="color: #9e9e9e; margin-bottom: 15px;">Generated: ${date}</p>`;
            html += '<div style="overflow-x: auto;"><table><thead><tr>';
            html += '<th>Rank</th><th>Sector</th><th>Score</th><th>Hit Rate</th><th>Sharpe</th><th>Obs</th><th>Signal</th>';
            html += '</tr></thead><tbody>';
            
            results.forEach(row => {
                const signalColor = row.trend_signal === 'GREEN' ? '#4caf50' : 
                                   row.trend_signal === 'YELLOW' ? '#ffc107' : '#ef5350';
                const sectorLink = `<a href="#" onclick="openSectorManager('${row.sector_id}'); return false;" style="color: #4fc3f7; text-decoration: none;">${row.sector}</a>`;
                html += `<tr>
                    <td>${row.rank}</td>
                    <td style="text-align: left;">${sectorLink}</td>
                    <td>${row.composite_score.toFixed(3)}</td>
                    <td>${(row.avg_hit_rate * 100).toFixed(1)}%</td>
                    <td>${row.avg_sharpe.toFixed(2)}</td>
                    <td>${row.observations}</td>
                    <td><span style="color: ${signalColor}; font-weight: bold;">${row.trend_signal}</span></td>
                </tr>`;
            });
            
            html += '</tbody></table></div>';
            document.getElementById('scorecardResults').innerHTML = html;
        }

        function openSectorManager(sectorId) {
            showTab('signals');
            showSectorManager();
            // Scroll to sector if possible
            setTimeout(() => {
                const sectorElements = document.querySelectorAll('#sectorList h4');
                sectorElements.forEach(el => {
                    if (el.textContent.includes(sectorId)) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        el.style.backgroundColor = '#4fc3f7';
                        el.style.color = '#1e1e2e';
                        setTimeout(() => {
                            el.style.backgroundColor = '';
                            el.style.color = '';
                        }, 2000);
                    }
                });
            }, 500);
        }

        async function loadSectors() {
            try {
                const response = await fetch('/signals/sectors');
                sectorsData = await response.json();
                populateSectorDropdown();
            } catch (error) {
                console.error('Failed to load sectors:', error);
            }
        }

        function populateSectorDropdown() {
            const select = document.getElementById('sectorSelect');
            const corrSelect = document.getElementById('corrSectorSelect');
            
            select.innerHTML = '<option value="">Custom Symbols</option>';
            corrSelect.innerHTML = '<option value="">Custom Symbols</option>';
            
            const sectors = sectorsData.sectors || {};
            Object.keys(sectors).sort().forEach(id => {
                const sector = sectors[id];
                const option1 = document.createElement('option');
                option1.value = id;
                option1.textContent = sector.name;
                select.appendChild(option1);
                
                const option2 = document.createElement('option');
                option2.value = id;
                option2.textContent = sector.name;
                corrSelect.appendChild(option2);
            });
        }

        function showSectorManager() {
            document.getElementById('sectorModal').style.display = 'block';
            renderSectorList();
        }

        function hideSectorManager() {
            document.getElementById('sectorModal').style.display = 'none';
        }

        function renderSectorList() {
            const container = document.getElementById('sectorList');
            const sectors = sectorsData.sectors || {};
            
            if (Object.keys(sectors).length === 0) {
                container.innerHTML = '<p style="color: #9e9e9e;">No sectors yet. Create one above.</p>';
                return;
            }

            let html = '';
            Object.keys(sectors).sort().forEach(id => {
                const sector = sectors[id];
                html += `
                    <div style="background: #3a3a52; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h4 style="margin: 0 0 10px 0; color: #4fc3f7;">${sector.name}</h4>
                                <p style="margin: 0; color: #9e9e9e; font-size: 0.9em;">ID: ${id}</p>
                                <p style="margin: 5px 0 0 0; color: #b0b0b0; font-size: 0.9em;">${sector.tickers.length} tickers: ${sector.tickers.join(', ')}</p>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <button onclick="editSector('${id}')" style="padding: 8px 15px; background: #4fc3f7;">Edit</button>
                                <button onclick="deleteSector('${id}')" style="padding: 8px 15px; background: #ef5350;">Delete</button>
                            </div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        async function deleteSector(sectorId) {
            if (!confirm(`Delete sector "${sectorsData.sectors[sectorId].name}"?`)) return;
            
            try {
                const response = await fetch(`/signals/sectors/${sectorId}`, { method: 'DELETE' });
                const result = await response.json();
                
                if (result.success) {
                    await loadSectors();
                    renderSectorList();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Failed to delete sector: ' + error.message);
            }
        }

        function editSector(sectorId) {
            const sector = sectorsData.sectors[sectorId];
            const newName = prompt('Sector Name:', sector.name);
            if (!newName) return;
            
            const newTickers = prompt('Tickers (comma-separated):', sector.tickers.join(','));
            if (!newTickers) return;
            
            updateSector(sectorId, newName, newTickers.split(',').map(t => t.trim()));
        }

        async function updateSector(sectorId, name, tickers) {
            try {
                const response = await fetch(`/signals/sectors/${sectorId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name, tickers })
                });
                const result = await response.json();
                
                if (result.success) {
                    await loadSectors();
                    renderSectorList();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Failed to update sector: ' + error.message);
            }
        }

        document.getElementById('createSectorForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = document.getElementById('newSectorId').value.trim();
            const name = document.getElementById('newSectorName').value.trim();
            const tickers = document.getElementById('newSectorTickers').value.split(',').map(t => t.trim()).filter(t => t);
            
            try {
                const response = await fetch('/signals/sectors', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id, name, tickers })
                });
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('createSectorForm').reset();
                    await loadSectors();
                    renderSectorList();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Failed to create sector: ' + error.message);
            }
        });

        document.getElementById('sectorSelect').addEventListener('change', (e) => {
            const sectorId = e.target.value;
            if (sectorId && sectorsData.sectors && sectorsData.sectors[sectorId]) {
                const tickers = sectorsData.sectors[sectorId].tickers;
                document.getElementById('symbolsInput').value = tickers.join(',');
            }
        });

        document.getElementById('corrSectorSelect').addEventListener('change', (e) => {
            const sectorId = e.target.value;
            if (sectorId && sectorsData.sectors && sectorsData.sectors[sectorId]) {
                const tickers = sectorsData.sectors[sectorId].tickers;
                document.getElementById('corrSymbolsInput').value = tickers.join(',');
            }
        });

        // Load sectors on page load
        loadSectors();

        document.getElementById('backtestForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            // Calculate dates based on timeframe
            const endDate = new Date();
            const startDate = new Date();
            const timeframe = formData.get('timeframe');
            
            switch(timeframe) {
                case '3m': startDate.setMonth(startDate.getMonth() - 3); break;
                case '6m': startDate.setMonth(startDate.getMonth() - 6); break;
                case '1y': startDate.setFullYear(startDate.getFullYear() - 1); break;
                case '2y': startDate.setFullYear(startDate.getFullYear() - 2); break;
                case '3y': startDate.setFullYear(startDate.getFullYear() - 3); break;
            }
            
            const signalNames = Array.from(formData.getAll('signal_names'));
            const symbols = formData.get('symbols').split(',').map(s => s.trim());
            const horizonDays = parseInt(formData.get('horizon_days'));
            const startDateStr = startDate.toISOString().split('T')[0];
            const endDateStr = endDate.toISOString().split('T')[0];
            
            document.getElementById('results').innerHTML = `<p>Running backtest for ${signalNames.length} signal(s)...</p>`;
            
            try {
                // Run all backtests in parallel
                const promises = signalNames.map(signalName => 
                    fetch('/signals/backtest', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            signal_name: signalName,
                            symbols: symbols,
                            horizon_days: horizonDays,
                            start_date: startDateStr,
                            end_date: endDateStr
                        })
                    }).then(r => r.json())
                );
                
                const results = await Promise.all(promises);
                
                // Check for errors
                const errors = results.filter(r => r.error);
                if (errors.length > 0) {
                    document.getElementById('results').innerHTML = `<p style="color: #ef5350;">Errors: ${errors.map(e => e.error).join(', ')}</p>`;
                    return;
                }
                
                const formatPct = (val) => val === null || val === undefined ? 'N/A' : (val * 100).toFixed(2) + '%';
                const formatNum = (val) => val === null || val === undefined ? 'N/A' : val.toFixed(2);
                
                // Build comparison table
                let html = '<h3>Backtest Results Comparison</h3>';
                html += '<div style="overflow-x: auto;">';
                html += '<table><thead><tr>';
                html += '<th style="min-width: 120px;">Signal</th>';
                html += '<th style="min-width: 80px;">IC</th>';
                html += '<th style="min-width: 80px;">Hit Rate</th>';
                html += '<th style="min-width: 90px;">Long Ret</th>';
                html += '<th style="min-width: 90px;">L/S Ret</th>';
                html += '<th style="min-width: 90px;">L/S Sharpe</th>';
                html += '<th style="min-width: 70px;">Obs</th>';
                html += '</tr></thead><tbody>';
                
                results.forEach(result => {
                    html += `<tr>
                        <td style="text-align: left;"><strong>${result.signal_name}</strong></td>
                        <td><span class="metric ${result.ic_pearson_mean > 0 ? 'positive' : 'negative'}">${formatPct(result.ic_pearson_mean)}</span></td>
                        <td><span class="metric ${result.hit_rate > 0.5 ? 'positive' : 'negative'}">${formatPct(result.hit_rate)}</span></td>
                        <td><span class="metric ${result.long_only_return > 0 ? 'positive' : 'negative'}">${formatPct(result.long_only_return)}</span></td>
                        <td><span class="metric ${result.long_short_return > 0 ? 'positive' : 'negative'}">${formatPct(result.long_short_return)}</span></td>
                        <td><span class="metric ${result.long_short_sharpe > 0 ? 'positive' : 'negative'}">${formatNum(result.long_short_sharpe)}</span></td>
                        <td>${result.n_observations}</td>
                    </tr>`;
                });
                
                html += '</tbody></table></div>';
                html += '<p style="margin-top: 15px; color: #9e9e9e; font-size: 0.9em;">💡 Tip: Higher IC and Sharpe ratios indicate better signals. Hit rate > 50% means the signal works more often than not.</p>';
                
                document.getElementById('results').innerHTML = html;
            } catch (error) {
                document.getElementById('results').innerHTML = `<p style="color: #ef5350;">Error: ${error.message}</p>`;
            }
        });

        document.getElementById('correlationForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = {
                signal_names: Array.from(formData.getAll('signal_names')),
                symbols: document.getElementById('corrSymbolsInput').value.split(',').map(s => s.trim()),
                start_date: '2024-01-01',
                end_date: '2025-12-31'
            };
            
            document.getElementById('corrResults').innerHTML = '<p>Computing correlations...</p>';
            
            try {
                const response = await fetch('/signals/correlation', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                if (result.error) {
                    document.getElementById('corrResults').innerHTML = `<p style="color: #ef5350;">Error: ${result.error}</p>`;
                } else {
                    const signals = Object.keys(result);
                    let html = '<h3>Signal Correlation Matrix</h3>';
                    html += '<div style="overflow-x: auto;">';
                    html += '<table style="table-layout: auto;"><thead><tr>';
                    html += '<th style="min-width: 120px; text-align: left;">Signal</th>';
                    signals.forEach(s => html += `<th style="min-width: 80px;">${s}</th>`);
                    html += '</tr></thead><tbody>';
                    
                    signals.forEach(s1 => {
                        html += `<tr><td style="text-align: left;"><strong>${s1}</strong></td>`;
                        signals.forEach(s2 => {
                            const corr = result[s1][s2];
                            const color = Math.abs(corr) > 0.7 ? (corr > 0 ? 'positive' : 'negative') : 'neutral';
                            html += `<td><span class="metric ${color}">${corr.toFixed(2)}</span></td>`;
                        });
                        html += '</tr>';
                    });
                    html += '</tbody></table></div>';
                    
                    document.getElementById('corrResults').innerHTML = html;
                }
            } catch (error) {
                document.getElementById('corrResults').innerHTML = `<p style="color: #ef5350;">Error: ${error.message}</p>`;
            }
        });

        // ============================================================================
        // REGIME CLASSIFIER FUNCTIONS
        // ============================================================================
        
        let regimeRefreshInterval = null;
        
        async function loadRegimeData(forceRefresh = false) {
            console.log('loadRegimeData called, forceRefresh:', forceRefresh);
            try {
                // Show loading state
                const badge = document.getElementById('verdictBadge');
                console.log('verdictBadge element:', badge);
                if (badge) {
                    badge.textContent = 'LOADING...';
                    badge.style.background = '#6b7280';
                }
                
                const url = forceRefresh ? '/signals/regime/refresh' : '/signals/regime/analysis';
                const method = forceRefresh ? 'POST' : 'GET';
                
                const response = await fetch(url, {method});
                const data = await response.json();
                
                if (data.error) {
                    console.error('Regime analysis error:', data.error);
                    if (badge) {
                        badge.textContent = 'ERROR';
                        badge.style.background = '#ef4444';
                    }
                    return;
                }
                
                updateAllSections(data);
                
            } catch (error) {
                console.error('Failed to load regime data:', error);
                const badge = document.getElementById('verdictBadge');
                if (badge) {
                    badge.textContent = 'ERROR';
                    badge.style.background = '#ef4444';
                }
            }
        }
        
        function updateAllSections(data) {
            try {
                // Update verdict banner
                const verdictColors = {GREEN: '#22c55e', YELLOW: '#f59e0b', RED: '#ef4444'};
                const verdictText = {
                    GREEN: '● GREEN — SELL PREMIUM',
                    YELLOW: '● YELLOW — SELL CONSERVATIVELY',
                    RED: '● RED — SIT IN CASH'
                };
                
                const banner = document.getElementById('verdictBanner');
                if (banner) {
                    banner.style.background = verdictColors[data.verdict];
                    banner.style.color = 'white';
                }
                
                const badge = document.getElementById('verdictBadge');
                if (badge) badge.textContent = verdictText[data.verdict];
                
                const spx = document.getElementById('spxPrice');
                if (spx) spx.textContent = data.spx_price ? `$${data.spx_price.toFixed(2)}` : '-';
                
                const vix = document.getElementById('vixLevel');
                if (vix) vix.textContent = data.vix_level || '-';
                
                const displayScore = Math.round((data.composite_score + 1) / 2 * 100);
                const score = document.getElementById('compositeScore');
                if (score) score.textContent = displayScore;
                
                const timestamp = document.getElementById('regimeTimestamp');
                if (timestamp) timestamp.textContent = new Date(data.timestamp).toLocaleString();
                
                // Update hard override warning
                const warning = document.getElementById('overrideWarning');
                if (warning) {
                    if (data.hard_override_triggered) {
                        warning.style.display = 'block';
                        const reason = document.getElementById('overrideReason');
                        if (reason) reason.textContent = data.override_reason;
                    } else {
                        warning.style.display = 'none';
                    }
                }
                
                // Update 7-dimension cards
                const dimensionsGrid = document.getElementById('dimensionsGrid');
                if (!dimensionsGrid) return;
                dimensionsGrid.innerHTML = '';
            
            const dimensionNames = {
                vix_regime: 'VIX Regime',
                term_structure: 'Term Structure',
                trend_assessment: 'Trend Assessment',
                vol_spread: 'Vol Spread Edge',
                breadth: 'Market Breadth',
                pcr_sentiment: 'Put/Call Sentiment',
                correlation_regime: 'Correlation Regime'
            };
            
            Object.entries(data.dimensions).forEach(([key, dim]) => {
                const card = document.createElement('div');
                card.style.cssText = 'padding: 15px; background: #1e1e2e; border-radius: 8px;';
                
                const scoreColor = getScoreColor(dim.score);
                const badgeColor = dim.score > 0.3 ? '#22c55e33' : (dim.score < -0.3 ? '#ef444433' : '#6b728033');
                
                // Build raw metrics line
                let metricsLine = '';
                if (key === 'vix_regime') {
                    metricsLine = `VIX: ${data.vix_level}`;
                } else if (key === 'term_structure') {
                    const spread = data.vix_3m && data.vix_level ? (data.vix_3m - data.vix_level).toFixed(2) : '-';
                    metricsLine = `Spread: ${spread} pts | Source: ${data.term_structure_source || 'unknown'}`;
                } else if (key === 'trend_assessment') {
                    metricsLine = `ADX: ${dim.adx || '-'}`;
                } else if (key === 'vol_spread') {
                    metricsLine = `IV: ${(dim.implied_vol * 100).toFixed(1)}% | RV: ${(dim.realized_vol * 100).toFixed(1)}% | Edge: ${(dim.spread * 100).toFixed(1)}%`;
                } else if (key === 'breadth') {
                    metricsLine = `A/D: ${(dim.ad_ratio * 100).toFixed(0)}% | NH/NL: ${(dim.nh_nl_ratio * 100).toFixed(0)}%`;
                } else if (key === 'pcr_sentiment') {
                    metricsLine = `PCR: ${dim.pcr} | Source: ${data.pcr_source || 'unknown'}`;
                } else if (key === 'correlation_regime') {
                    metricsLine = `Avg Corr: ${dim.avg_correlation ? dim.avg_correlation.toFixed(2) : '-'}`;
                }
                
                // Score bar with center line
                const scorePercent = ((dim.score + 1) / 2) * 100;
                const barFillColor = dim.score < 0 ? '#ef4444' : '#22c55e';
                const barWidth = Math.abs(dim.score) * 50; // 0 to 50% from center
                const barLeft = dim.score < 0 ? (50 - barWidth) : 50;
                
                card.innerHTML = `
                    <h4 style="margin: 0 0 10px 0; color: #4fc3f7;">${dimensionNames[key]}</h4>
                    <div style="text-align: center; padding: 10px; background: ${badgeColor}; border-radius: 4px; margin: 10px 0;">
                        <span style="font-size: 1.2em; font-weight: bold;">${dim.value}</span>
                    </div>
                    <div style="position: relative; background: #0f0f23; height: 20px; border-radius: 4px; margin: 10px 0;">
                        <div style="position: absolute; left: 50%; top: 0; width: 2px; height: 100%; background: #6b7280;"></div>
                        <div style="position: absolute; left: ${barLeft}%; width: ${barWidth}%; height: 100%; background: ${barFillColor}; border-radius: 4px;"></div>
                        <span style="position: absolute; right: 5px; top: 2px; font-size: 0.85em; color: #9e9e9e;">${dim.score.toFixed(2)}</span>
                    </div>
                    <p style="margin: 5px 0; font-size: 0.85em; color: #6b7280;">${metricsLine}</p>
                    <p style="margin: 5px 0; font-size: 0.9em; color: #9e9e9e; font-style: italic;">${dim.description}</p>
                `;
                
                dimensionsGrid.appendChild(card);
            });
            
            // Update strategy panel
            const strategyPanel = document.getElementById('strategyPanel');
            strategyPanel.style.borderLeftColor = verdictColors[data.verdict];
            document.getElementById('recommendedStrategy').textContent = data.recommended_strategy;
            document.getElementById('positionSizing').textContent = data.position_sizing;
            document.getElementById('entryTiming').textContent = data.entry_timing;
            
            // Update data source status bar
            const termSourceMap = {
                'tastytrade': '<span style="color: #22c55e;">Tastytrade LIVE ✅</span>',
                'yfinance_fallback': '<span style="color: #f59e0b;">yfinance proxy ⚠️</span>',
                'unavailable': '<span style="color: #ef4444;">Unavailable ❌</span>'
            };
            document.getElementById('termSource').innerHTML = termSourceMap[data.term_structure_source] || '-';
            document.getElementById('lastUpdated').textContent = new Date(data.timestamp).toLocaleTimeString();
            
            const cacheStatus = data.cache_age_minutes < 1 ? 'Fresh' : `${data.cache_age_minutes.toFixed(0)} min old`;
            document.getElementById('cacheStatus').textContent = cacheStatus;
            
            const errorCount = data.errors.length;
            const errorCountEl = document.getElementById('errorCount');
            if (errorCount === 0) {
                errorCountEl.innerHTML = '<span style="color: #22c55e;">None ✅</span>';
            } else {
                errorCountEl.innerHTML = `<span style="color: #f59e0b;">${errorCount} warnings ⚠️</span>`;
            }
            
            const errorList = document.getElementById('errorList');
            errorList.innerHTML = data.errors.map(e => `<div>• ${e}</div>`).join('');
            
            // Load history
            loadRegimeHistory();
            } catch (error) {
                console.error('Error updating regime sections:', error);
            }
        }
        
        function getScoreColor(score) {
            if (score > 0.3) return '#22c55e';
            if (score < -0.3) return '#ef4444';
            return '#6b7280';
        }
        
        async function refreshRegime() {
            await loadRegimeData(true);
        }
        
        function toggleErrors() {
            const errorList = document.getElementById('errorList');
            errorList.style.display = errorList.style.display === 'none' ? 'block' : 'none';
        }
        
        async function loadRegimeHistory() {
            try {
                const response = await fetch('/signals/regime/history');
                const data = await response.json();
                
                if (!data.history || data.history.length === 0) return;
                
                // Update table (most recent first, max 10 rows)
                const tbody = document.getElementById('historyTable');
                tbody.innerHTML = '';
                
                const verdictColors = {GREEN: '#22c55e', YELLOW: '#f59e0b', RED: '#ef4444'};
                
                data.history.slice(0, 10).forEach(entry => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td style="padding: 8px;">${new Date(entry.timestamp).toLocaleDateString()}</td>
                        <td style="padding: 8px; text-align: right;">${entry.vix_level}</td>
                        <td style="padding: 8px; text-align: right;">${Math.round((entry.composite_score + 1) / 2 * 100)}</td>
                        <td style="padding: 8px; text-align: center;">
                            <span style="padding: 3px 8px; border-radius: 4px; background: ${verdictColors[entry.verdict]}; color: white; font-weight: bold; font-size: 0.85em;">
                                ${entry.verdict.charAt(0)}
                            </span>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
                
                // Update chart with colored points
                const ctx = document.getElementById('regimeChart').getContext('2d');
                
                if (regimeChart) {
                    regimeChart.destroy();
                }
                
                const pointColors = data.history.map(e => verdictColors[e.verdict]);
                
                regimeChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.history.map(e => new Date(e.timestamp).toLocaleDateString()),
                        datasets: [{
                            label: 'Composite Score',
                            data: data.history.map(e => (e.composite_score + 1) / 2 * 100),
                            borderColor: '#4fc3f7',
                            backgroundColor: 'rgba(79, 195, 247, 0.1)',
                            pointBackgroundColor: pointColors,
                            pointBorderColor: pointColors,
                            pointRadius: 5,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {display: false},
                            annotation: {
                                annotations: {
                                    greenLine: {
                                        type: 'line',
                                        yMin: 75,
                                        yMax: 75,
                                        borderColor: '#22c55e',
                                        borderWidth: 1,
                                        borderDash: [5, 5]
                                    },
                                    yellowLine: {
                                        type: 'line',
                                        yMin: 57.5,
                                        yMax: 57.5,
                                        borderColor: '#f59e0b',
                                        borderWidth: 1,
                                        borderDash: [5, 5]
                                    },
                                    redLine: {
                                        type: 'line',
                                        yMin: 50,
                                        yMax: 50,
                                        borderColor: '#ef4444',
                                        borderWidth: 1,
                                        borderDash: [5, 5]
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                min: 0,
                                max: 100,
                                grid: {color: '#2e2e3e'},
                                ticks: {color: '#9e9e9e'}
                            },
                            x: {
                                grid: {color: '#2e2e3e'},
                                ticks: {color: '#9e9e9e', maxRotation: 45}
                            }
                        }
                    }
                });
                
            } catch (error) {
                console.error('Failed to load regime history:', error);
            }
        }
        
        function onRegimeTabActivated() {
            console.log('onRegimeTabActivated called');
            loadRegimeData();
            if (regimeRefreshInterval) clearInterval(regimeRefreshInterval);
            regimeRefreshInterval = setInterval(() => loadRegimeData(), 5 * 60 * 1000);
        }
        
        function onRegimeTabDeactivated() {
            if (regimeRefreshInterval) {
                clearInterval(regimeRefreshInterval);
                regimeRefreshInterval = null;
            }
        }

        // ============================================================================
        // RISK MANAGER FUNCTIONS
        // ============================================================================
        // Version: 2026-03-11-16:30 - Null safety for positions
        
        let riskHistoryChart = null;
        let riskRefreshInterval = null;
        
        async function loadMacroRegime(force = false) {
            try {
                const url = force ? '/signals/api/macro-regime?force=true' : '/signals/api/macro-regime';
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('macroRegimeContent').innerHTML = `<p style="color: #ef4444;">Error: ${data.error}</p>`;
                    return;
                }
                
                const quadrantColors = {
                    'GOLDILOCKS': '#4caf50',
                    'REFLATION': '#ff9800',
                    'STAGFLATION': '#ff5722',
                    'DEFLATION': '#f44336'
                };
                
                const geoColors = {
                    'LOW': '#4caf50',
                    'ELEVATED': '#ff9800',
                    'HIGH': '#f44336',
                    'UNKNOWN': '#9e9e9e'
                };
                
                let html = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                        <div style="background: #1e1e2e; padding: 20px; border-radius: 8px;">
                            <h3 style="margin-top: 0;">Macro Quadrant</h3>
                            <div style="font-size: 24px; font-weight: bold; padding: 15px; background: ${quadrantColors[data.quadrant] || '#9e9e9e'}; color: #fff; border-radius: 8px; text-align: center;">
                                ${data.quadrant}
                            </div>
                            <p style="margin-top: 10px; color: #9e9e9e; font-size: 0.9em;">
                                Growth: ${data.growth_regime}<br>
                                Inflation: ${data.inflation_regime}
                            </p>
                        </div>
                        
                        <div style="background: #1e1e2e; padding: 20px; border-radius: 8px;">
                            <h3 style="margin-top: 0;">Geopolitical Risk</h3>
                            <div style="font-size: 24px; font-weight: bold; padding: 15px; background: ${geoColors[data.geopolitical_risk]}; color: #fff; border-radius: 8px; text-align: center;">
                                ${data.geopolitical_risk}
                            </div>
                            <p style="margin-top: 10px; color: #9e9e9e; font-size: 0.9em;">
                                Confidence: ${(data.regime_confidence * 100).toFixed(0)}%
                            </p>
                        </div>
                    </div>
                    
                    ${Object.keys(data.commodity_disruption).length > 0 ? `
                    <div style="background: #1e1e2e; padding: 20px; border-radius: 8px; margin-top: 20px;">
                        <h3 style="margin-top: 0;">🛢️ Commodity Disruptions</h3>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            ${Object.entries(data.commodity_disruption).map(([commodity, severity]) => {
                                const severityColor = severity === 'HIGH' ? '#f44336' : '#ff9800';
                                return `<span style="padding: 8px 16px; background: ${severityColor}; color: #fff; border-radius: 4px; font-weight: bold;">${commodity.toUpperCase()}: ${severity}</span>`;
                            }).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                        <div style="background: #1e1e2e; padding: 20px; border-radius: 8px;">
                            <h3 style="margin-top: 0; color: #4caf50;">✅ Favored Sectors</h3>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                ${data.favored_sectors.map(s => `<span style="padding: 6px 12px; background: #4caf50; color: #fff; border-radius: 4px; font-size: 0.9em;">${s}</span>`).join('')}
                            </div>
                        </div>
                        
                        <div style="background: #1e1e2e; padding: 20px; border-radius: 8px;">
                            <h3 style="margin-top: 0; color: #f44336;">❌ Suppressed Sectors</h3>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                                ${data.suppressed_sectors.map(s => `<span style="padding: 6px 12px; background: #f44336; color: #fff; border-radius: 4px; font-size: 0.9em;">${s}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: #1e1e2e; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 0.85em; color: #9e9e9e;">
                        <strong>Last Updated:</strong> ${new Date(data.last_updated).toLocaleString()}<br>
                        <strong>Cache Age:</strong> ${data.cache_age_minutes} minutes (refreshes every 4 hours)<br>
                        <strong>Sources:</strong> ${data.sources.join(', ')}
                    </div>
                `;
                
                document.getElementById('macroRegimeContent').innerHTML = html;
                
            } catch (error) {
                console.error('Error loading macro regime:', error);
                document.getElementById('macroRegimeContent').innerHTML = `<p style="color: #ef4444;">Error: ${error.message}</p>`;
            }
        }
        
        async function loadRiskSnapshot() {
            try {
                const response = await fetch('/signals/risk/snapshot');
                const data = await response.json();
                
                if (data.error) {
                    console.error('Risk snapshot error:', data.error);
                    return;
                }
                
                // Update alert banner
                const banner = document.getElementById('riskAlertBanner');
                const content = document.getElementById('riskAlertContent');
                
                if (data.alert_count_critical > 0) {
                    banner.style.display = 'block';
                    banner.style.background = '#ef4444';
                    banner.style.color = 'white';
                    const criticalAlerts = data.alerts.filter(a => a.level === 'CRITICAL');
                    content.innerHTML = '<strong>⚠️ CRITICAL ALERTS:</strong><br>' + criticalAlerts.map(a => `• ${a.message}`).join('<br>');
                } else if (data.alert_count_warning > 0) {
                    banner.style.display = 'block';
                    banner.style.background = '#f59e0b';
                    banner.style.color = '#1e1e2e';
                    const warningAlerts = data.alerts.filter(a => a.level === 'WARNING');
                    content.innerHTML = '<strong>⚠ WARNING:</strong><br>' + warningAlerts.map(a => `• ${a.message}`).join('<br>');
                } else {
                    banner.style.display = 'block';
                    banner.style.background = '#22c55e';
                    banner.style.color = '#1e1e2e';
                    content.innerHTML = '<strong>✓ All Clear</strong> — No risk alerts at this time';
                }
                
                // Update P&L cards
                const dailyColor = data.pnl.daily >= 0 ? '#22c55e' : '#ef4444';
                document.getElementById('dailyPnl').textContent = `$${data.pnl.daily.toFixed(0)} (${(data.pnl.daily_pct * 100).toFixed(1)}%)`;
                document.getElementById('dailyPnl').style.color = dailyColor;
                document.getElementById('dailyPnlBar').style.width = `${Math.min(Math.abs(data.limits.daily_loss.usage_pct) * 100, 100)}%`;
                document.getElementById('dailyPnlBar').style.background = data.limits.daily_loss.status === 'BREACHED' ? '#ef4444' : (data.limits.daily_loss.status === 'WARNING' ? '#f59e0b' : '#22c55e');
                
                const weeklyColor = data.pnl.weekly >= 0 ? '#22c55e' : '#ef4444';
                document.getElementById('weeklyPnl').textContent = `$${data.pnl.weekly.toFixed(0)} (${(data.pnl.weekly_pct * 100).toFixed(1)}%)`;
                document.getElementById('weeklyPnl').style.color = weeklyColor;
                document.getElementById('weeklyPnlBar').style.width = `${Math.min(Math.abs(data.limits.weekly_loss.usage_pct) * 100, 100)}%`;
                document.getElementById('weeklyPnlBar').style.background = data.limits.weekly_loss.status === 'BREACHED' ? '#ef4444' : (data.limits.weekly_loss.status === 'WARNING' ? '#f59e0b' : '#22c55e');
                
                const monthlyColor = data.pnl.monthly >= 0 ? '#22c55e' : '#ef4444';
                document.getElementById('monthlyPnl').textContent = `$${data.pnl.monthly.toFixed(0)} (${(data.pnl.monthly_pct * 100).toFixed(1)}%)`;
                document.getElementById('monthlyPnl').style.color = monthlyColor;
                document.getElementById('monthlyPnlBar').style.width = `${Math.min(Math.abs(data.limits.monthly_loss.usage_pct) * 100, 100)}%`;
                document.getElementById('monthlyPnlBar').style.background = data.limits.monthly_loss.status === 'BREACHED' ? '#ef4444' : (data.limits.monthly_loss.status === 'WARNING' ? '#f59e0b' : '#22c55e');
                
                document.getElementById('buyingPower').textContent = `${(data.limits.buying_power.current * 100).toFixed(0)}%`;
                document.getElementById('buyingPowerBar').style.width = `${data.limits.buying_power.usage_pct * 100}%`;
                document.getElementById('buyingPowerBar').style.background = data.limits.buying_power.status === 'BREACHED' ? '#ef4444' : (data.limits.buying_power.status === 'WARNING' ? '#f59e0b' : '#22c55e');
                
                document.getElementById('vixLevel').textContent = data.vix.current ? data.vix.current.toFixed(1) : '-';
                document.getElementById('vixChange').textContent = data.vix.current ? `${data.vix.change_pct >= 0 ? '+' : ''}${(data.vix.change_pct * 100).toFixed(1)}% today` : '-';
                document.getElementById('vixChange').style.color = data.vix.spike_detected ? '#ef4444' : '#9e9e9e';
                
                // Update accounts grid
                const accountsGrid = document.getElementById('accountsGrid');
                accountsGrid.innerHTML = '';
                
                Object.entries(data.accounts).forEach(([name, acc]) => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    const badge = acc.source === 'manual' ? '<span style="background: #f59e0b; color: #1e1e2e; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 5px;">MANUAL</span>' : '<span style="background: #22c55e; color: #1e1e2e; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-left: 5px;">LIVE</span>';
                    card.innerHTML = `
                        <h4 style="margin: 0 0 10px 0;">${name.replace('_', ' ').toUpperCase()}${badge}</h4>
                        <p style="margin: 5px 0;"><strong>Portfolio Value:</strong> $${acc.portfolio_value.toFixed(0)}</p>
                        <p style="margin: 5px 0;"><strong>Positions:</strong> ${acc.positions_count}</p>
                        ${acc.buying_power ? `<p style="margin: 5px 0;"><strong>Buying Power:</strong> $${acc.buying_power.toFixed(0)}</p>` : ''}
                    `;
                    accountsGrid.appendChild(card);
                });
                
                // Update directional bias
                document.getElementById('directionalBias').textContent = data.exposure.directional_bias;
                const deltaBarPos = ((data.exposure.net_delta_dollars / data.total_portfolio_value) + 1) / 2 * 100;
                document.getElementById('deltaBar').style.width = `${Math.min(Math.max(deltaBarPos, 0), 100)}%`;
                
                // Update PDT info
                document.getElementById('pdtCount').textContent = `${data.pdt.daytrade_count} / 3`;
                document.getElementById('pdtRemaining').textContent = data.pdt.remaining_day_trades;
                document.getElementById('pdtEquity').textContent = `$${data.pdt.account_equity.toFixed(0)}`;
                
                // Update positions table
                const tbody = document.getElementById('positionsTable');
                tbody.innerHTML = '';
                
                data.positions.forEach(pos => {
                    const row = document.createElement('tr');
                    const plColor = (pos.unrealized_pl || 0) >= 0 ? '#22c55e' : '#ef4444';
                    let actionCell = '-';
                    
                    if (pos.rolling_vs_closing) {
                        const rec = pos.rolling_vs_closing.recommendation;
                        const color = rec === 'CLOSE' ? '#ef4444' : (rec === 'EVALUATE_ROLL' ? '#f59e0b' : '#22c55e');
                        actionCell = `<span style="padding: 4px 8px; border-radius: 4px; background: ${color}; color: ${rec === 'EVALUATE_ROLL' ? '#1e1e2e' : 'white'}; font-size: 0.85em; cursor: help;" title="${pos.rolling_vs_closing.reason}">${rec}</span>`;
                    }
                    
                    const unrealizedPL = pos.unrealized_pl !== null && pos.unrealized_pl !== undefined ? pos.unrealized_pl : 0;
                    const unrealizedPLPC = pos.unrealized_plpc !== null && pos.unrealized_plpc !== undefined ? pos.unrealized_plpc : 0;
                    
                    row.innerHTML = `
                        <td style="padding: 8px;">${pos.symbol}</td>
                        <td style="padding: 8px;">${pos.account}</td>
                        <td style="padding: 8px;">${pos.position_type || pos.asset_class}</td>
                        <td style="padding: 8px;">${pos.side}</td>
                        <td style="padding: 8px; text-align: right;">${pos.qty}</td>
                        <td style="padding: 8px; text-align: right;">$${(pos.market_value || 0).toFixed(0)}</td>
                        <td style="padding: 8px; text-align: right; color: ${plColor};">$${unrealizedPL.toFixed(0)}</td>
                        <td style="padding: 8px; text-align: right; color: ${plColor};">${(unrealizedPLPC * 100).toFixed(1)}%</td>
                        <td style="padding: 8px; text-align: center;" id="action-${pos.id || 'none'}">${actionCell}</td>
                    `;
                    tbody.appendChild(row);
                    
                    // Add delete button for manual positions after row is added
                    if (pos.id && pos.account !== 'alpaca_scanner') {
                        const actionTd = document.getElementById(`action-${pos.id}`);
                        const deleteBtn = document.createElement('button');
                        deleteBtn.textContent = 'Delete';
                        deleteBtn.style.cssText = 'padding: 4px 8px; background: #ef4444; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; margin-left: 5px;';
                        deleteBtn.onclick = () => deleteManualPosition(pos.id);
                        actionTd.appendChild(deleteBtn);
                    }
                });
                
                // Load history chart
                await loadRiskHistory();
                
            } catch (error) {
                console.error('Failed to load risk snapshot:', error);
            }
        }
        
        async function loadRiskHistory() {
            try {
                const response = await fetch('/signals/risk/history');
                const data = await response.json();
                
                if (!data.history || data.history.length === 0) return;
                
                const ctx = document.getElementById('riskHistoryChart').getContext('2d');
                
                if (riskHistoryChart) {
                    riskHistoryChart.destroy();
                }
                
                riskHistoryChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.history.map(e => new Date(e.date).toLocaleDateString()),
                        datasets: [{
                            label: 'Daily P&L',
                            data: data.history.map(e => e.daily_pnl),
                            borderColor: '#4fc3f7',
                            backgroundColor: 'rgba(79, 195, 247, 0.1)',
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {display: false}
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                grid: {color: '#2e2e3e'},
                                ticks: {color: '#9e9e9e'}
                            },
                            x: {
                                grid: {color: '#2e2e3e'},
                                ticks: {color: '#9e9e9e'}
                            }
                        }
                    }
                });
                
            } catch (error) {
                console.error('Failed to load risk history:', error);
            }
        }
        
        async function addManualPosition() {
            const position = {
                symbol: document.getElementById('manualSymbol').value.toUpperCase(),
                account: document.getElementById('manualAccount').value,
                position_type: document.getElementById('manualType').value,
                side: document.getElementById('manualSide').value,
                qty: parseFloat(document.getElementById('manualQty').value),
                cost_basis: parseFloat(document.getElementById('manualCost').value),
                current_price: parseFloat(document.getElementById('manualPrice').value),
                notes: document.getElementById('manualNotes').value,
                date_entered: new Date().toISOString().split('T')[0]
            };
            
            position.market_value = position.qty * position.current_price;
            position.unrealized_pl = (position.current_price - position.cost_basis) * position.qty;
            position.unrealized_plpc = (position.current_price - position.cost_basis) / position.cost_basis;
            
            try {
                const response = await fetch('/signals/risk/positions/manual', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(position)
                });
                
                if (response.ok) {
                    alert('Position added successfully');
                    // Clear form
                    document.getElementById('manualSymbol').value = '';
                    document.getElementById('manualQty').value = '';
                    document.getElementById('manualCost').value = '';
                    document.getElementById('manualPrice').value = '';
                    document.getElementById('manualNotes').value = '';
                    // Reload snapshot
                    await loadRiskSnapshot();
                } else {
                    alert('Failed to add position');
                }
            } catch (error) {
                console.error('Error adding position:', error);
                alert('Error adding position');
            }
        }
        
        async function importRobinhoodJson() {
            const text = document.getElementById('robinhoodText').value.trim();
            if (!text) {
                alert('Please paste Robinhood portfolio text');
                return;
            }
            
            try {
                // Parse Robinhood text format (same as stock_portfolio app)
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                
                // Remove header lines if present
                while (lines.length && ['Name', 'Symbol', 'Shares', 'Price', 'Average cost', 'Total return', 'Equity'].includes(lines[0])) {
                    lines.shift();
                }
                
                const cleanNumber = (s) => {
                    s = s.replace(/[$,]/g, '').trim();
                    if (s.startsWith('(') && s.endsWith(')')) {
                        s = '-' + s.slice(1, -1);
                    }
                    return parseFloat(s);
                };
                
                const holdings = [];
                for (let i = 0; i + 6 < lines.length; i += 7) {
                    try {
                        const shares = cleanNumber(lines[i+2]);
                        const avgCost = cleanNumber(lines[i+4]);
                        const equity = cleanNumber(lines[i+6]);
                        holdings.push({
                            name: lines[i],
                            symbol: lines[i+1],
                            shares: shares,
                            price: cleanNumber(lines[i+3]),
                            average_cost: avgCost,
                            total_return: equity - (shares * avgCost),
                            equity: equity
                        });
                    } catch (e) {
                        console.error('Error parsing position:', e);
                    }
                }
                
                if (holdings.length === 0) {
                    alert('No positions found. Make sure you copied the full portfolio text from Robinhood.');
                    return;
                }
                
                let imported = 0;
                for (const holding of holdings) {
                    const position = {
                        symbol: holding.symbol,
                        account: 'robinhood',
                        position_type: 'equity',
                        side: 'long',
                        qty: holding.shares,
                        cost_basis: holding.average_cost,
                        current_price: holding.price,
                        notes: `Imported from Robinhood - ${holding.name}`,
                        date_entered: new Date().toISOString().split('T')[0],
                        market_value: holding.equity,
                        unrealized_pl: holding.total_return,
                        unrealized_plpc: holding.total_return / (holding.average_cost * holding.shares)
                    };
                    
                    const response = await fetch('/signals/risk/positions/manual', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(position)
                    });
                    
                    if (response.ok) imported++;
                }
                
                alert(`Imported ${imported} of ${holdings.length} positions`);
                document.getElementById('robinhoodText').value = '';
                await loadRiskSnapshot();
            } catch (error) {
                console.error('Error importing:', error);
                alert('Error parsing Robinhood text: ' + error.message);
            }
        }
        
        async function importTosFile() {
            const fileInput = document.getElementById('tosFile');
            if (!fileInput.files || !fileInput.files[0]) {
                alert('Please select a CSV file');
                return;
            }
            
            const file = fileInput.files[0];
            const text = await file.text();
            const lines = text.split('\\n');
            
            // Find the header line (starts with "Symbol,")
            let headerIndex = -1;
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].startsWith('Symbol,')) {
                    headerIndex = i;
                    break;
                }
            }
            
            if (headerIndex === -1) {
                alert('Could not find position data in CSV');
                return;
            }
            
            const headers = lines[headerIndex].split(',');
            let imported = 0;
            
            for (let i = headerIndex + 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line || line.startsWith('Total') || line.startsWith('Cash')) continue;
                
                const values = line.split(',');
                if (values.length < headers.length) continue;
                
                const symbol = values[0].trim();
                if (!symbol) continue;
                
                // Parse P/L Open (remove $ and parentheses for negative)
                const plOpenStr = values[4].replace(/[$,()]/g, '').trim();
                const plOpen = plOpenStr.startsWith('(') ? -parseFloat(plOpenStr) : parseFloat(plOpenStr);
                
                // Parse BP Effect to estimate position value
                const bpStr = values[6].replace(/[$,()]/g, '').trim();
                const bpEffect = parseFloat(bpStr) || 0;
                
                const position = {
                    symbol: symbol,
                    account: 'thinkorswim',
                    position_type: 'equity',
                    side: 'long',
                    qty: parseFloat(values[1]) || 1, // Delta as proxy for shares
                    cost_basis: null,
                    current_price: null,
                    notes: `Imported from TOS - BP Effect: $${bpEffect.toFixed(2)}`,
                    date_entered: new Date().toISOString().split('T')[0],
                    market_value: bpEffect,
                    unrealized_pl: plOpen,
                    unrealized_plpc: null
                };
                
                const response = await fetch('/signals/risk/positions/manual', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(position)
                });
                
                if (response.ok) imported++;
            }
            
            alert(`Imported ${imported} positions from ThinkorSwim`);
            fileInput.value = '';
            await loadRiskSnapshot();
        }
        
        async function importSchwabText() {
            const text = document.getElementById('schwabText').value.trim();
            if (!text) {
                alert('Please paste Schwab positions text');
                return;
            }
            
            try {
                const response = await fetch('/signals/risk/positions/import-schwab', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({text: text})
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(`Imported ${result.imported} of ${result.found} positions`);
                    document.getElementById('schwabText').value = '';
                    await loadRiskSnapshot();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                console.error('Error importing:', error);
                alert('Error importing: ' + error.message);
            }
        }
        
        async function deleteByAccount(account) {
            const accountNames = {
                'robinhood': 'Robinhood',
                'schwab': 'Schwab',
                'thinkorswim': 'ThinkorSwim'
            };
            
            if (!confirm(`⚠️ WARNING: This will delete ALL ${accountNames[account]} positions. This cannot be undone. Continue?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/signals/risk/positions/manual/delete-by-account/${account}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Deleted ${result.deleted_count} ${accountNames[account]} positions`);
                    await loadRiskSnapshot();
                } else {
                    alert('Failed to delete positions');
                }
            } catch (error) {
                console.error('Error deleting:', error);
                alert('Error: ' + error.message);
            }
        }
        
        async function bulkDeleteAllPositions() {
            if (!confirm('⚠️ WARNING: This will delete ALL manual positions from ALL accounts (Robinhood, ThinkorSwim, SoFi). This cannot be undone. Continue?')) {
                return;
            }
            
            try {
                const response = await fetch('/signals/risk/positions/manual/bulk-delete', {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Deleted ${result.deleted_count} positions`);
                    await loadRiskSnapshot();
                } else {
                    alert('Failed to delete positions');
                }
            } catch (error) {
                console.error('Error deleting positions:', error);
                alert('Error deleting positions');
            }
        }
        
        // Attach event listeners after functions are defined
        document.getElementById('importRobinhoodBtn')?.addEventListener('click', importRobinhoodJson);
        document.getElementById('importTosBtn')?.addEventListener('click', importTosFile);
        document.getElementById('importSchwabBtn')?.addEventListener('click', importSchwabText);
        document.getElementById('bulkDeleteBtn')?.addEventListener('click', bulkDeleteAllPositions);
        
        async function deleteManualPosition(positionId) {
            if (!confirm('Are you sure you want to delete this position?')) {
                return;
            }
            
            try {
                const response = await fetch(`/signals/risk/positions/manual/${positionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    alert('Position deleted successfully');
                    await loadRiskSnapshot();
                } else {
                    alert('Failed to delete position');
                }
            } catch (error) {
                console.error('Error deleting position:', error);
                alert('Error deleting position');
            }
        }
        
        async function resetBaseline() {
            if (!confirm('This will reset your start-of-day baseline to your current portfolio value and clear recovery mode. This is useful when you first add manual positions. Continue?')) {
                return;
            }
            
            try {
                const response = await fetch('/signals/risk/reset-baseline', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    alert(`Baseline reset to $${data.start_of_day_value.toFixed(0)}. Recovery mode cleared.`);
                    await loadRiskSnapshot();
                } else {
                    alert('Failed to reset baseline');
                }
            } catch (error) {
                console.error('Error resetting baseline:', error);
                alert('Error resetting baseline');
            }
        }
        
        // Auto-refresh risk data every 5 minutes when tab is active
        function startRiskAutoRefresh() {
            if (riskRefreshInterval) clearInterval(riskRefreshInterval);
            riskRefreshInterval = setInterval(() => {
                const activeTab = document.querySelector('.tab-content.active');
                if (activeTab && activeTab.id === 'risk-tab') {
                    loadRiskSnapshot();
                }
            }, 300000); // 5 minutes
        }
        
        startRiskAutoRefresh();
    </script>

    <!-- MORNING BRIEF TAB -->
    <div id="morning-brief-tab" class="tab-content">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h2 style="color:#4fc3f7; margin:0;">🌅 Morning Brief</h2>
            <div>
                <span id="mb-updated" style="color:#666; font-size:12px;"></span>
                <button onclick="loadMorningBrief()" style="padding:6px 14px; background:#4fc3f7; color:#1e1e2e; border:none; border-radius:4px; cursor:pointer; font-weight:bold; margin-left:10px;">🔄 Refresh</button>
            </div>
        </div>
        <div id="mb-content">
            <p style="color:#9e9e9e;">Click the tab to load the morning brief.</p>
        </div>
    </div>

    <script>
    // Morning Brief
    let mbLoaded = false;
    const origShowTab = showTab;
    showTab = function(name) {
        origShowTab(name);
        if (name === 'morning-brief' && !mbLoaded) {
            mbLoaded = true;
            loadMorningBrief();
        }
    };

    function mbScoreBar(score, min, max) {
        const pct = Math.max(0, Math.min(100, ((score - min) / (max - min)) * 100));
        const color = score > 0.3 ? '#22c55e' : (score > -0.2 ? '#f59e0b' : '#ef4444');
        return `<div style="background:#1a1a2e; border-radius:4px; height:8px; margin:8px 0; overflow:hidden;">
            <div style="width:${pct}%; height:100%; background:${color}; border-radius:4px;"></div>
        </div>`;
    }

    function mbColor(val, map) { return map[val] || '#9e9e9e'; }

    async function loadMorningBrief() {
        const el = document.getElementById('mb-content');
        el.innerHTML = `<div style="color:#666;">Loading morning brief...</div>`;
        try {
            const resp = await fetch('/signals/morning/brief');
            if (!resp.ok) throw new Error('Failed');
            const data = await resp.json();
            if (data.error) throw new Error(data.error);
            renderMorningBrief(data);
            storeBriefDataForTicket(data);
            const t = new Date(data.generated_at);
            document.getElementById('mb-updated').textContent = 'Last updated: ' + t.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
        } catch(e) {
            el.innerHTML = `<div style="background:#3b1c1c; border:1px solid #ef4444; border-radius:8px; padding:20px; text-align:center;">
                <div style="font-size:18px; margin-bottom:10px;">⚠️ Morning Brief unavailable</div>
                <div style="color:#999; margin-bottom:15px;">${e.message || 'Regime data could not be loaded.'}</div>
                <button onclick="loadMorningBrief()" style="padding:8px 20px; background:#4fc3f7; color:#1e1e2e; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">Retry</button>
            </div>`;
        }
    }

    function renderMorningBrief(data) {
        const s = data.sections;
        const el = document.getElementById('mb-content');
        const tsColors = {CONTANGO:'#22c55e', FLAT:'#9e9e9e', BACKWARDATION:'#ef4444'};
        const tsIcon = s.vix_regime.term_structure === 'BACKWARDATION' ? '⚠️ ' : '';

        // Section 1 — VIX
        let html = `<div class="section">
            <h2>① VIX Regime</h2>
            <div style="display:flex; gap:40px; flex-wrap:wrap; font-size:16px; margin-bottom:10px;">
                <div>VIX: <strong>${s.vix_regime.vix ?? '—'}</strong></div>
                <div>VIX3M: <strong>${s.vix_regime.vix_3m ?? '—'}</strong></div>
                <div>Term Structure: <strong style="color:${tsColors[s.vix_regime.term_structure] || '#9e9e9e'};">${tsIcon}${s.vix_regime.term_structure}</strong></div>
            </div>
            ${mbScoreBar(s.vix_regime.score, -1, 1)}
            <div style="color:#bbb;">${s.vix_regime.summary}</div>
        </div>`;

        // Section 2 — Trend
        const adxOk = s.trend_assessment.adx < s.trend_assessment.adx_threshold;
        const adxColor = adxOk ? '#22c55e' : '#ef4444';
        const trendLabel = adxOk ? 'RANGE-BOUND' : 'TRENDING';
        html += `<div class="section">
            <h2>② Trend Assessment</h2>
            <div style="font-size:16px; margin-bottom:10px;">
                ADX: <strong>${s.trend_assessment.adx}</strong> (threshold: &lt; ${s.trend_assessment.adx_threshold})
                &nbsp;&nbsp; Assessment: <strong style="color:${adxColor};">${trendLabel}</strong>
            </div>
            ${mbScoreBar(s.trend_assessment.score, -1, 1)}
            <div style="color:#bbb;">${s.trend_assessment.summary}</div>
            ${!adxOk ? '<div style="background:#3b1c1c; border:1px solid #ef4444; border-radius:6px; padding:10px; margin-top:10px; color:#ef4444;">⛔ Iron condor suspended. Single-side credit spread only (half size).</div>' : ''}
        </div>`;

        // Section 3 — Vol Edge
        const veColors = {STRONG:'#22c55e', PRESENT:'#22c55e', THIN:'#f59e0b', ABSENT:'#ef4444'};
        html += `<div class="section">
            <h2>③ Volatility Edge</h2>
            <div style="font-size:16px; margin-bottom:10px;">
                IV vs RV Spread: <strong>${s.volatility_edge.vol_edge_pct}%</strong>
                &nbsp;&nbsp; Assessment: <strong style="color:${veColors[s.volatility_edge.value] || '#9e9e9e'};">${s.volatility_edge.value}</strong>
            </div>
            ${mbScoreBar(s.volatility_edge.score, -1, 1)}
            <div style="color:#bbb;">${s.volatility_edge.summary}</div>
        </div>`;

        // Section 4 — Gap Risk
        const grColors = {LOW:'#22c55e', ELEVATED:'#f59e0b', HIGH:'#ef4444', UNKNOWN:'#9e9e9e'};
        const grVal = s.gap_risk.value;
        const esPct = s.gap_risk.es_change_pct != null ? `${s.gap_risk.es_direction} ${Math.abs(s.gap_risk.es_change_pct).toFixed(2)}%` : '—';
        html += `<div class="section">
            <h2>④ Gap Risk</h2>
            <div style="font-size:16px; margin-bottom:10px;">
                ES Futures: <strong>${s.gap_risk.es_price ?? '—'}</strong> (${esPct} pre-market)
                &nbsp;&nbsp; Gap Risk: <strong style="color:${grColors[grVal]};">${grVal}</strong>
            </div>
            <div style="color:#bbb;">${s.gap_risk.summary}</div>
            ${s.gap_risk.gap_risk_override ? '<div style="background:#3b1c1c; border:1px solid #ef4444; border-radius:6px; padding:10px; margin-top:10px; color:#ef4444;">⚠️ Gap Risk Override — Overnight move > 1%. Verdict downgraded from GREEN → YELLOW. Widen strike distances. Trade half size.</div>' : ''}
        </div>`;

        // Section 5 — Verdict
        const v = s.verdict;
        const vColors = {GREEN:{bg:'#1b4332',border:'#22c55e',text:'#22c55e',icon:'✅'},
                         YELLOW:{bg:'#4a3728',border:'#f59e0b',text:'#f59e0b',icon:'⚠️'},
                         RED:{bg:'#3b1c1c',border:'#ef4444',text:'#ef4444',icon:'🛑'}};
        const vc = vColors[v.value] || vColors.RED;
        const volEdge = (s.volatility_edge?.vol_edge_pct || 0);
        const adx = s.trend_assessment?.adx || 99;
        const VOL_EDGE_MIN = 5.0, ADX_MAX = 28;
        let verdictText, verdictSubtext;
        if (v.value === 'RED') { verdictText = 'DO NOT TRADE'; verdictSubtext = 'Sit in cash.'; }
        else if (v.value === 'YELLOW') { verdictText = 'TRADE CAUTIOUSLY'; verdictSubtext = 'Single-side spread only, half size.'; }
        else if (v.value === 'GREEN' && volEdge < VOL_EDGE_MIN && adx > ADX_MAX) { verdictText = 'WAIT — Vol Edge Thin + ADX High'; verdictSubtext = `Vol edge ${volEdge.toFixed(1)}% (need 5%) and ADX ${adx.toFixed(1)} (need < 28). No trade today.`; }
        else if (v.value === 'GREEN' && volEdge < VOL_EDGE_MIN) { verdictText = 'WAIT — Vol Edge Too Thin'; verdictSubtext = `Vol edge ${volEdge.toFixed(1)}% below 5% minimum. Premium math doesn't work today.`; }
        else if (v.value === 'GREEN' && adx > ADX_MAX) { verdictText = 'WAIT — ADX Too High'; verdictSubtext = `ADX ${adx.toFixed(1)} above 28 threshold. Iron condor suspended.`; }
        else { verdictText = 'TRADE AGGRESSIVELY'; verdictSubtext = 'All conditions favorable. Run the chain poller.'; }

        let strategyText, sizingText, entryText;
        if (v.value === 'RED') { strategyText = 'No trade — sit in cash'; sizingText = '$0'; entryText = 'N/A'; }
        else if (volEdge < VOL_EDGE_MIN && adx > ADX_MAX) { strategyText = 'No trade today — vol edge absent and ADX too high'; sizingText = '$0 — skip today'; entryText = 'Wait for conditions to improve'; }
        else if (volEdge < VOL_EDGE_MIN) { strategyText = 'No trade today — vol edge too thin for premium selling'; sizingText = '$0 — skip today'; entryText = 'Monitor vol edge — target 5%+'; }
        else if (adx > ADX_MAX) { strategyText = 'Single-side credit spread only — half size'; sizingText = '$125–$187 per spread'; entryText = '9:45–10:30 AM — confirm direction first'; }
        else { strategyText = v.strategy; sizingText = v.sizing; entryText = v.entry_window; }

        const nextLink = v.value === 'RED'
            ? `<a href="#" onclick="showTab('risk'); return false;" style="color:${vc.text}; font-size:15px;">→ Review open positions</a>`
            : (verdictText === 'TRADE AGGRESSIVELY' || verdictText === 'TRADE CAUTIOUSLY')
            ? `<a href="/" style="color:${vc.text}; font-size:15px;">→ Go to Scanner — start the chain poller</a>`
            : '';
        html += `<div style="background:${vc.bg}; border:2px solid ${vc.border}; border-radius:12px; padding:30px; margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <div style="font-size:26px; font-weight:bold; color:${vc.text};">${vc.icon} ${v.value} — ${verdictText}</div>
                <div style="font-size:18px; color:${vc.text};">Score: ${v.composite_score}/100</div>
            </div>
            <div style="color:${vc.text}; font-size:14px; margin-top:8px;">${verdictSubtext}</div>
            <div style="display:grid; grid-template-columns:auto 1fr; gap:6px 20px; margin-top:20px; font-size:15px; color:#ccc;">
                <div style="color:#999;">Strategy:</div><div>${strategyText}</div>
                <div style="color:#999;">Sizing:</div><div>${sizingText}</div>
                <div style="color:#999;">Entry:</div><div>${entryText}</div>
            </div>
            <div style="color:#bbb; margin-top:15px; font-size:14px;">${verdictText === 'TRADE AGGRESSIVELY' ? v.notes : 'Monitor conditions — check back when vol edge crosses 5% and ADX drops below 28.'}</div>
            <div style="margin-top:15px;">${nextLink}</div>
            <div id="mb-position-status" style="margin-top:10px; color:#888; font-size:13px;">○ No active 0DTE position today</div>
        </div>`;

        // Fetch position status
        fetch('/api/poller/spx/proximity').then(r=>r.json()).then(p => {
            const el = document.getElementById('mb-position-status');
            if (p.status === 'NO_ACTIVE_POSITION' || p.status === 'ERROR' || p.status === 'NO_DATA') {
                el.innerHTML = '○ No active 0DTE position today';
                el.style.color = '#888';
            } else {
                const sc = {SAFE:'#22c55e', WARNING:'#f59e0b', CRITICAL:'#ef4444'};
                el.innerHTML = `● Active position — $${p.short_put_strike} / $${p.short_call_strike} — <span style="color:${sc[p.status] || '#888'};">${p.status}</span> (Put: ${p.put_buffer}pts | Call: ${p.call_buffer}pts)`;
                el.style.color = '#ccc';
            }
        }).catch(()=>{});

        // Section 6 — Strike Probability Panel
        const sp = data.strike_probability;
        if (sp) {
            html += `<div class="section" style="margin-top:20px;">
                <h2>⑥ Strike Probability Panel</h2>
                <div style="color:#999; margin-bottom:10px;">SPX: ${sp.spx_price} | VIX: ${sp.vix} | Daily IV: ${sp.daily_iv_pct}%</div>
                <table style="width:100%; border-collapse:collapse; font-size:13px; margin-bottom:20px;">
                    <tr style="color:#9e9e9e; border-bottom:1px solid #3a3a52;"><th style="text-align:left;padding:8px;">Delta</th><th style="text-align:right;padding:8px;">Put Strike</th><th style="text-align:right;padding:8px;">Call Strike</th><th style="text-align:right;padding:8px;">Prob OTM</th><th style="text-align:left;padding:8px;">Status</th></tr>`;
            sp.delta_map.forEach(r => {
                const bg = r.is_current_target ? 'background:#4a3728;' : '';
                const grey = r.pop < 80 ? 'opacity:0.4;' : '';
                const status = r.is_current_target ? '<strong style="color:#f59e0b;">← Current target</strong>'
                    : (r.pop >= 85 ? '✅' : (r.pop >= 80 ? '⚠️ minimum' : '❌ below 80%'));
                html += `<tr style="${bg}${grey} border-bottom:1px solid #2a2a3e;">
                    <td style="padding:6px 8px; color:#ccc;${r.is_current_target ? 'font-weight:bold;' : ''}">${r.delta.toFixed(2)}</td>
                    <td style="padding:6px 8px; text-align:right; color:#ef4444;">$${Number(r.put_strike).toLocaleString()}</td>
                    <td style="padding:6px 8px; text-align:right; color:#22c55e;">$${Number(r.call_strike).toLocaleString()}</td>
                    <td style="padding:6px 8px; text-align:right; color:#ccc; font-weight:bold;">${r.pop}%</td>
                    <td style="padding:6px 8px;">${status}</td>
                </tr>`;
            });
            html += `</table><div style="color:#666; font-size:12px; margin-bottom:20px;">Platform minimum: 80% PoP (delta ≤ 0.20)</div>`;

            // SD Bands
            html += `<h3 style="color:#4fc3f7; margin-bottom:10px;">Standard Deviation Bands</h3>`;
            const bands = sp.sd_bands;
            // Visual bar
            const b2 = bands['2_sigma'], b15 = bands['1_5_sigma'], b1 = bands['1_sigma'];
            html += `<div style="position:relative; height:50px; background:#1a1a2e; border-radius:6px; margin-bottom:15px; overflow:hidden;">
                <div style="position:absolute; left:5%; right:5%; top:5px; bottom:5px; background:#3b1c1c33; border:1px solid #ef444444; border-radius:4px;"></div>
                <div style="position:absolute; left:15%; right:15%; top:8px; bottom:8px; background:#4a372844; border:1px solid #f59e0b44; border-radius:4px;"></div>
                <div style="position:absolute; left:25%; right:25%; top:11px; bottom:11px; background:#1b433244; border:1px solid #22c55e44; border-radius:4px;"></div>
                <div style="position:absolute; left:50%; top:0; bottom:0; width:2px; background:#4fc3f7; transform:translateX(-1px);"></div>
                <div style="position:absolute; left:50%; bottom:2px; transform:translateX(-50%); color:#4fc3f7; font-size:10px;">ATM</div>
            </div>`;
            [{k:'1_sigma',c:'#22c55e',l:'1σ'},{k:'1_5_sigma',c:'#f59e0b',l:'1.5σ'},{k:'2_sigma',c:'#ef4444',l:'2σ'}].forEach(b => {
                const d = bands[b.k];
                html += `<div style="padding:4px 0; color:#ccc; font-size:13px;"><span style="color:${b.c}; font-weight:bold; display:inline-block; width:40px;">${b.l}</span> ±$${d.move.toFixed(2)} → $${d.lower.toFixed(2)} – $${d.upper.toFixed(2)} <span style="color:#888;">${d.pct} of sessions</span></div>`;
            });
            if (sp.straddle_range) {
                const sr = sp.straddle_range;
                html += `<div style="padding:4px 0; color:#4fc3f7; font-size:13px; font-weight:bold;">Straddle ±$${sr.move.toFixed(2)} → $${sr.lower.toFixed(2)} – $${sr.upper.toFixed(2)} <span style="color:#888; font-weight:normal;">Most accurate 0DTE range</span></div>`;
            }

            // Historical win rates
            const hw = sp.historical_win_rates;
            if (hw) {
                html += `<div style="margin-top:20px; background:#1a1a2e; padding:15px; border-radius:8px;">`;
                if (hw.status === 'ready') {
                    const wrColor = hw.win_rate_pct >= 80 ? '#22c55e' : '#f59e0b';
                    const wrIcon = hw.win_rate_pct >= 80 ? '✅ Above 80% threshold' : '⚠️ Below 80% threshold — review strike selection';
                    const winPct = hw.total_traded > 0 ? Math.round(hw.wins / hw.total_traded * 100) : 0;
                    const lossPct = 100 - winPct;
                    html += `<div style="color:${wrColor}; font-weight:bold; margin-bottom:8px;">📊 Historical Win Rate: ${hw.win_rate_pct}% (${hw.total_traded} trades) — ${wrIcon}</div>
                        <div style="margin-bottom:6px;"><span style="color:#22c55e;">Wins</span> <div style="display:inline-block; width:200px; height:10px; background:#2a2a3e; border-radius:5px; vertical-align:middle;"><div style="width:${winPct}%; height:100%; background:#22c55e; border-radius:5px;"></div></div> ${winPct}%</div>
                        <div style="margin-bottom:10px;"><span style="color:#ef4444;">Loss</span> <div style="display:inline-block; width:200px; height:10px; background:#2a2a3e; border-radius:5px; vertical-align:middle;"><div style="width:${lossPct}%; height:100%; background:#ef4444; border-radius:5px;"></div></div> ${lossPct}%</div>`;
                } else {
                    const pct = Math.min(100, ((hw.total_traded || 0) / hw.required) * 100);
                    html += `<div style="color:#4fc3f7; font-weight:bold; margin-bottom:8px;">📊 Historical Win Rates — Accumulating baseline</div>
                        <div style="background:#2a2a3e; height:12px; border-radius:6px; overflow:hidden; margin-bottom:8px;">
                            <div style="width:${pct}%; height:100%; background:#4fc3f7; border-radius:6px;"></div>
                        </div>
                        <div style="color:#888; font-size:13px; margin-bottom:8px;">${hw.message}</div>`;
                }
                if (hw.breakdown) {
                    const bd = hw.breakdown;
                    html += `<div style="color:#888; font-size:12px;">✅ Expired worthless: ${bd.expired_worthless} · ✅ Closed 50%: ${bd.closed_50pct} · ❌ Stopped out: ${bd.stopped_out} · ⬜ Closed manually: ${bd.closed_manually}</div>`;
                }
                html += `</div>`;
            }
            html += `</div>`;
        }

        // Trade Ticket Section
        html += `<div id="trade-ticket-section" style="margin:16px 0;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                <button id="trade-ticket-btn" onclick="generateTradeTicket()" style="background:#1d4ed8; color:white; border:none; border-radius:6px; padding:10px 20px; font-size:14px; font-weight:bold; cursor:pointer;">📋 Generate Trade Ticket</button>
                <span id="trade-ticket-strategy-label" style="color:#888; font-size:13px;"></span>
            </div>
            <div id="trade-ticket-output" style="display:none;"></div>
        </div>`;

        // Section 7 — Trade Plan
        html += `<div class="section" style="margin-top:20px;"><h2>📋 Trade Plan</h2>`;

        // Sub-section A: Key Levels
        const kl = data.key_levels;
        if (kl && kl.status === 'ok' && kl.levels && kl.levels.length > 0) {
            html += `<h3 style="color:#4fc3f7; margin-bottom:10px;">Key SPX Levels</h3>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-bottom:20px;">`;
            const borderColors = {resistance:'#ef4444', support:'#22c55e', pivot:'#4fc3f7', psychological:'#a78bfa'};
            kl.levels.forEach(lv => {
                const bc = borderColors[lv.type] || '#666';
                const arrow = lv.position === 'above' ? '↑' : '↓';
                html += `<div style="background:#1a1a2e; padding:15px; border-radius:8px; border-left:4px solid ${bc};">
                    <div style="color:#999; font-size:12px; margin-bottom:4px;">${lv.label}</div>
                    <div style="font-size:20px; font-weight:bold; color:#fff;">$${Number(lv.price).toLocaleString(undefined,{minimumFractionDigits:2})}</div>
                    <div style="color:${bc}; font-size:13px; margin-top:4px;">${arrow} ${lv.distance_pts}pts ${lv.position} (${lv.distance_pct}%)</div>
                    <div style="color:#888; font-size:12px; margin-top:6px;">${lv.context}</div>
                </div>`;
            });
            html += `</div>`;
        } else {
            html += `<div style="background:#1a1a2e; padding:15px; border-radius:8px; color:#999; margin-bottom:20px;">⚠️ Key levels unavailable — market data could not be loaded</div>`;
        }

        // Sub-section B: Scenario Playbook
        const pb = data.playbook;
        if (pb) {
            html += `<h3 style="color:#4fc3f7; margin-bottom:10px;">Scenario Playbook</h3>`;
            if (pb.adx_note) {
                html += `<div style="background:#4a3728; border:1px solid #f59e0b; border-radius:6px; padding:10px; margin-bottom:12px; color:#f59e0b; font-size:13px;">${pb.adx_note}</div>`;
            }
            const scenColors = {bull:'#22c55e', bear:'#ef4444', neutral:'#666'};
            const activeStratLabel = (volEdge >= VOL_EDGE_MIN && adx < ADX_MAX) ? 'the iron condor' : (adx >= ADX_MAX) ? 'the put spread' : 'the position';
            html += `<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:12px; margin-bottom:15px;">`;
            ['bull','bear','neutral'].forEach(key => {
                const sc = pb.scenarios[key];
                const bc = scenColors[key];
                const actionText = sc.action.replace(/the full IC/g, activeStratLabel);
                html += `<div style="background:#1a1a2e; padding:15px; border-radius:8px; border-left:4px solid ${bc};">
                    <div style="font-size:16px; font-weight:bold; color:${bc}; margin-bottom:8px;">${sc.label}</div>
                    <div style="color:#999; font-size:12px; margin-bottom:4px;">Trigger: ${sc.trigger}</div>
                    <div style="color:#ccc; font-size:12px; margin-bottom:8px;">Risk: ${sc.spread_risk}</div>
                    <div style="color:#bbb; font-size:13px;">${actionText}</div>
                </div>`;
            });
            html += `</div>`;
            const emStr = pb.expected_move ? `±$${Number(pb.expected_move).toFixed(0)}pts` : '—';
            let strikeLine = 'Strikes will appear here after first ENTER recommendation';
            if (pb.put_strike_ref && pb.call_strike_ref) {
                strikeLine = `Short put $${Number(pb.put_strike_ref).toLocaleString()} / Short call $${Number(pb.call_strike_ref).toLocaleString()}`;
            }
            html += `<div style="color:#999; font-size:13px;">Expected move today: ${emStr} · ${strikeLine}</div>`;
        }
        html += `</div>`;

        el.innerHTML = html;
    }

    // ── Trade Ticket Generator ────────────────────────────────────────
    let _briefData = null;

    function storeBriefDataForTicket(data) {
        _briefData = data;
        updateTradeTicketButton(data);
    }

    function updateTradeTicketButton(data) {
        const btn = document.getElementById('trade-ticket-btn');
        const label = document.getElementById('trade-ticket-strategy-label');
        if (!btn || !label) return;

        const volEdgePct = data.sections?.volatility_edge?.vol_edge_pct || 0;
        const adxVal = data.sections?.trend_assessment?.adx || 99;
        const verdict = data.sections?.verdict?.value || 'RED';

        const isWaitDay = (verdict === 'RED' || volEdgePct < 5.0 || adxVal > 35);
        if (isWaitDay) {
            btn.disabled = true;
            btn.style.background = '#374151';
            btn.style.cursor = 'not-allowed';
            label.textContent = volEdgePct < 5.0
                ? `Vol edge ${volEdgePct.toFixed(1)}% — no trade today`
                : 'No trade — conditions not met';
            label.style.color = '#ef4444';
            const output = document.getElementById('trade-ticket-output');
            if (output) output.style.display = 'none';
            return;
        }

        const strategy = _getAutoStrategy(data);
        if (strategy === 'NONE') {
            btn.disabled = true;
            btn.style.background = '#374151';
            btn.style.cursor = 'not-allowed';
            label.textContent = 'No trade — conditions not met';
            label.style.color = '#ef4444';
        } else {
            btn.disabled = false;
            btn.style.background = '#1d4ed8';
            btn.style.cursor = 'pointer';
            label.textContent = strategy === 'IC' ? 'Iron Condor (4 legs)' : 'Put Credit Spread (2 legs)';
            label.style.color = '#22c55e';
        }
        document.getElementById('trade-ticket-output').style.display = 'none';
    }

    function _getAutoStrategy(data) {
        if (!data) return 'NONE';
        const verdict = (data.sections?.verdict?.value) || 'RED';
        const adx = data.sections?.trend_assessment?.adx || 99;
        const volEdge = data.sections?.volatility_edge?.vol_edge_pct || 0;
        const term = data.sections?.vix_regime?.term_structure || 'UNKNOWN';
        if (verdict === 'RED' || term === 'BACKWARDATION' || adx > 35) return 'NONE';
        if (verdict === 'GREEN' && adx < 28 && volEdge >= 5.0) return 'IC';
        if (verdict === 'YELLOW' || (adx >= 28 && adx <= 35)) return 'PS';
        if (verdict === 'GREEN' && volEdge < 5.0) return 'PS';
        return 'NONE';
    }

    function generateTradeTicket() {
        if (!_briefData) return;
        const _ve = _briefData.sections?.volatility_edge?.vol_edge_pct || 0;
        const _verdict = _briefData.sections?.verdict?.value || 'RED';
        if (_ve < 5.0 || _verdict === 'RED') return;
        const strategy = _getAutoStrategy(_briefData);
        if (strategy === 'NONE') return;

        const spx = _briefData.strike_probability?.spx_price || 0;
        const dm = _briefData.strike_probability?.delta_map || [];
        const target = dm.find(r => r.is_current_target) || dm.find(r => Math.abs(r.delta - 0.12) < 0.03);
        const putStrike = target ? target.put_strike : _estStrike(spx, -1);
        const callStrike = target ? target.call_strike : _estStrike(spx, 1);
        const putWing = putStrike - 5;
        const callWing = callStrike + 5;
        const expiry = _getTodayExpiry();

        const tickets = {
            tastytrade: _ticketTT(strategy, putStrike, putWing, callStrike, callWing, expiry),
            thinkorswim: _ticketTOS(strategy, putStrike, putWing, callStrike, callWing, expiry),
            robinhood: _ticketRH(strategy, putStrike, putWing, callStrike, callWing, expiry)
        };
        _renderTicket(strategy, tickets, putStrike, putWing, callStrike, callWing, expiry);
    }

    function _estStrike(spx, dir) { return Math.round((spx + spx * 0.012 * 1.17 * dir) / 5) * 5; }
    function _getTodayExpiry() {
        const d = new Date();
        const mm = String(d.getMonth()+1).padStart(2,'0'), dd = String(d.getDate()).padStart(2,'0'), yy = String(d.getFullYear()).slice(2);
        return `${mm}/${dd}/${yy}`;
    }

    function _ticketTT(s, ps, pw, cs, cw, exp) {
        if (s === 'IC') return {
            title: 'Tastytrade — Iron Condor',
            steps: ['1. Search: SPX', `2. Select expiry: ${exp} (0DTE)`, '3. Click "Iron Condor" under Spreads', `4. Short Put: ${ps} | Long Put: ${pw}`, `5. Short Call: ${cs} | Long Call: ${cw}`, '6. Qty: 1 | Limit (mid)'],
            clipboard: `SPX ${exp} Iron Condor\\nSell Put ${ps} / Buy Put ${pw}\\nSell Call ${cs} / Buy Call ${cw}\\nQty: 1 | Limit (mid)`
        };
        return {
            title: 'Tastytrade — Put Credit Spread',
            steps: ['1. Search: SPX', `2. Select expiry: ${exp} (0DTE)`, '3. Click "Vertical" → Put', `4. Short Put: ${ps} | Long Put: ${pw}`, '5. Qty: 1 | Limit (mid)'],
            clipboard: `SPX ${exp} Put Credit Spread\\nSell Put ${ps} / Buy Put ${pw}\\nQty: 1 | Limit (mid)`
        };
    }

    function _ticketTOS(s, ps, pw, cs, cw, exp) {
        if (s === 'IC') return {
            title: 'Thinkorswim — Iron Condor',
            steps: ['1. Trade tab → search SPX', `2. Expiry: ${exp}`, '3. Right-click → Sell → Iron Condor', `4. Or manually set: Put ${ps}/${pw}, Call ${cs}/${cw}`, '5. Limit order at mid | Qty: 1'],
            clipboard: `SPX ${exp} Iron Condor (TOS)\\n-1 SPX ${exp} ${ps}P\\n+1 SPX ${exp} ${pw}P\\n-1 SPX ${exp} ${cs}C\\n+1 SPX ${exp} ${cw}C`
        };
        return {
            title: 'Thinkorswim — Put Credit Spread',
            steps: ['1. Trade tab → search SPX', `2. Expiry: ${exp}`, `3. Right-click Put ${ps} → Sell`, `4. Right-click Put ${pw} → Buy`, '5. Limit order at mid | Qty: 1'],
            clipboard: `SPX ${exp} Put Credit Spread (TOS)\\n-1 SPX ${exp} ${ps}P\\n+1 SPX ${exp} ${pw}P`
        };
    }

    function _ticketRH(s, ps, pw, cs, cw, exp) {
        const sps=Math.round(ps/10), spw=sps-1, scs=Math.round(cs/10), scw=scs+1;
        const warn = '⚠️ Robinhood does not support SPX. Using SPY equivalent (SPX ÷ 10). Width: 1 point (SPY equivalent of 5-point SPX spread).';
        if (s === 'IC') return {
            title: 'Robinhood — SPY Iron Condor', warning: warn,
            steps: ['1. Search: SPY', `2. Expiry: ${exp} (0DTE)`, '3. Trade → Trade Options → Iron Condor', `4. Short Put: ${sps} | Long Put: ${spw}`, `5. Short Call: ${scs} | Long Call: ${scw}`, '6. Qty: 1 | Width: 1pt | Review credit'],
            clipboard: `SPY ${exp} Iron Condor (RH)\\nSell Put ${sps} / Buy Put ${spw}\\nSell Call ${scs} / Buy Call ${scw}\\nQty: 1 | Width: 1pt\\n⚠️ SPX equivalent`
        };
        return {
            title: 'Robinhood — SPY Put Credit Spread', warning: warn,
            steps: ['1. Search: SPY', `2. Expiry: ${exp}`, '3. Trade → Trade Options → Put Credit Spread', `4. Short Put: ${sps} | Long Put: ${spw}`, '5. Qty: 1 | Width: 1pt | Review credit'],
            clipboard: `SPY ${exp} Put Credit Spread (RH)\\nSell Put ${sps} / Buy Put ${spw}\\nQty: 1 | Width: 1pt\\n⚠️ SPX equivalent`
        };
    }

    function _renderTicket(strategy, tickets, ps, pw, cs, cw, exp) {
        const out = document.getElementById('trade-ticket-output');
        out.style.display = 'block';
        const label = strategy === 'IC' ? 'Iron Condor' : 'Put Credit Spread';
        const legs = strategy === 'IC' ? `Sell Put ${ps} / Buy Put ${pw} | Sell Call ${cs} / Buy Call ${cw}` : `Sell Put ${ps} / Buy Put ${pw}`;
        const platforms = ['tastytrade','thinkorswim','robinhood'];
        const pNames = {tastytrade:'Tastytrade', thinkorswim:'Thinkorswim', robinhood:'Robinhood'};

        out.innerHTML = `<div style="background:#1a1a2e; border:1px solid #334155; border-radius:8px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div>
                    <div style="font-size:16px; font-weight:bold; color:#e2e8f0;">📋 ${label} — SPX ${exp}</div>
                    <div style="font-size:13px; color:#94a3b8; margin-top:4px;">${legs}</div>
                    <div style="font-size:11px; color:#64748b; margin-top:4px;">For manual entry only — not an automated order</div>
                </div>
                <button onclick="document.getElementById('trade-ticket-output').style.display='none'" style="background:none; border:none; color:#64748b; cursor:pointer; font-size:18px;">✕</button>
            </div>
            <div style="display:flex; gap:8px; margin-bottom:16px;">
                ${platforms.map(p => `<button onclick="showTicketPlatform('${p}')" id="ticket-tab-${p}" style="padding:6px 14px; border-radius:6px; border:1px solid #334155; background:#0f172a; color:#94a3b8; cursor:pointer; font-size:13px;">${pNames[p]}</button>`).join('')}
            </div>
            ${platforms.map(p => {
                const t = tickets[p]; if (!t) return '';
                return `<div id="ticket-panel-${p}" style="display:none;">
                    <div style="font-size:14px; font-weight:bold; color:#e2e8f0; margin-bottom:8px;">${t.title}</div>
                    ${t.warning ? `<div style="background:#451a03; border:1px solid #f59e0b; border-radius:6px; padding:8px; margin-bottom:10px; color:#fbbf24; font-size:12px;">${t.warning}</div>` : ''}
                    <ol style="color:#cbd5e1; font-size:13px; line-height:1.8; margin:0 0 12px 16px; padding:0;">${t.steps.map(s => `<li>${s}</li>`).join('')}</ol>
                    <button onclick="copyTicket('${p}')" style="background:#1d4ed8; color:white; border:none; border-radius:6px; padding:8px 16px; font-size:13px; cursor:pointer; width:100%;">📋 Copy to Clipboard</button>
                    <div id="ticket-copied-${p}" style="display:none; color:#22c55e; font-size:12px; margin-top:6px; text-align:center;">✅ Copied to clipboard</div>
                </div>`;
            }).join('')}
        </div>`;
        window._tickets = tickets;
        showTicketPlatform('tastytrade');
    }

    function showTicketPlatform(p) {
        ['tastytrade','thinkorswim','robinhood'].forEach(x => {
            const panel = document.getElementById('ticket-panel-'+x);
            const tab = document.getElementById('ticket-tab-'+x);
            if (panel) panel.style.display = x===p ? 'block' : 'none';
            if (tab) { tab.style.background = x===p ? '#1d4ed8' : '#0f172a'; tab.style.color = x===p ? 'white' : '#94a3b8'; }
        });
    }

    async function copyTicket(p) {
        const text = (window._tickets?.[p]?.clipboard || '').replace(/\\n/g, '\\n');
        try { await navigator.clipboard.writeText(text); } catch(e) {
            const el = document.createElement('textarea'); el.value = text; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
        }
        const c = document.getElementById('ticket-copied-'+p);
        if (c) { c.style.display = 'block'; setTimeout(() => c.style.display = 'none', 3000); }
    }
    </script>
</body>
</html>
"""


def add_research_routes(app):
    """Add research dashboard routes to Flask app."""
    
    @app.route('/research')
    def research_dashboard():
        import signals
        from flask import make_response
        signal_list = signals.list_signals()
        response = make_response(render_template_string(RESEARCH_DASHBOARD_HTML, signals=signal_list))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
