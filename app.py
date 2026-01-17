#!/usr/bin/env python3
"""Gradle Status Dashboard - Simple process monitor for Gradle and Kotlin daemons."""

import subprocess
import re
import os
import sys
import json
import psutil
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from pathlib import Path

APP_START_TIME = datetime.now()
APP_PID = os.getpid()

# Config file location
CONFIG_DIR = Path.home() / '.gradik'
CONFIG_FILE = CONFIG_DIR / 'config.json'
DEFAULT_PORT = 5050

def load_config():
    """Load config from file or return defaults."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return {'port': DEFAULT_PORT}

def save_config(config):
    """Save config to file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False

def get_port():
    """Get port from config or command line."""
    # Command line arg takes precedence
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            pass
    return load_config().get('port', DEFAULT_PORT)

CURRENT_PORT = get_port()

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gradik</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0b;
            --bg-secondary: #111113;
            --bg-tertiary: #1a1a1d;
            --border: #27272a;
            --text-primary: #fafafa;
            --text-secondary: #a1a1aa;
            --text-muted: #52525b;
            --accent-green: #22c55e;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
            --accent-purple: #a855f7;
            --accent-cyan: #06b6d4;
            --kotlin-purple: #7c3aed;
            --studio-green: #10b981;
            --warning-bg: rgba(245, 158, 11, 0.1);
            --danger-bg: rgba(239, 68, 68, 0.1);
        }

        [data-theme="light"] {
            --bg-primary: #fafafa;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f4f4f5;
            --border: #e4e4e7;
            --text-primary: #18181b;
            --text-secondary: #52525b;
            --text-muted: #a1a1aa;
            --warning-bg: rgba(245, 158, 11, 0.15);
            --danger-bg: rgba(239, 68, 68, 0.15);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            font-size: 12px;
            line-height: 1.5;
        }

        .container { max-width: 1100px; margin: 0 auto; padding: 1rem; }

        /* Header */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 0;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
            font-size: 14px;
        }

        .logo-icon {
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, var(--accent-green), var(--kotlin-purple));
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            color: white;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 0.375rem;
            color: var(--text-muted);
            font-size: 11px;
        }

        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse { 50% { opacity: 0.5; } }

        .theme-toggle {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 0.375rem 0.5rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.15s;
        }

        .theme-toggle:hover { background: var(--border); color: var(--text-primary); }

        /* Port button */
        .port-btn {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--accent-cyan);
            padding: 6px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.15s;
        }
        .port-btn:hover { background: var(--border); color: var(--text-primary); }
        
        /* Port dialog */
        .port-dialog-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(4px);
        }
        .port-dialog {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 320px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }
        .port-dialog-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }
        .port-dialog-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }
        .port-dialog-close:hover { color: var(--text-primary); }
        .port-dialog-body {
            padding: 16px;
        }
        .port-dialog-body label {
            display: block;
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .port-dialog-body input {
            width: 100%;
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            box-sizing: border-box;
        }
        .port-dialog-body input:focus {
            outline: none;
            border-color: var(--accent-cyan);
        }
        .port-dialog-info {
            display: flex;
            justify-content: space-between;
            margin-top: 12px;
            color: var(--text-muted);
        }
        .port-dialog-footer {
            display: flex;
            gap: 8px;
            padding: 16px;
            border-top: 1px solid var(--border);
            justify-content: flex-end;
        }
        .btn-secondary {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }
        .btn-secondary:hover { background: var(--border); color: var(--text-primary); }
        .btn-primary {
            background: var(--accent-cyan);
            border: none;
            color: #000;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
        }
        .btn-primary:hover { opacity: 0.9; }

        /* Alerts */
        .alerts-container {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 1rem;
            max-height: 120px;
            overflow-y: auto;
            display: none;
        }

        .alerts-container.has-alerts { display: block; }

        .alerts-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.375rem 0.75rem;
            background: var(--bg-tertiary);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            position: sticky;
            top: 0;
            z-index: 1;
        }

        .alerts-header .count {
            background: var(--accent-red);
            color: white;
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-size: 9px;
        }

        .alerts {
            display: flex;
            flex-direction: column;
        }

        .alert {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.375rem 0.75rem;
            font-size: 11px;
            border-bottom: 1px solid var(--border);
        }

        .alert:last-child { border-bottom: none; }

        .alert.warning { color: var(--accent-orange); }
        .alert.danger { color: var(--accent-red); }

        .alert-icon { font-size: 10px; opacity: 0.8; }
        .alert-dismiss {
            margin-left: auto;
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            opacity: 0.5;
            font-size: 12px;
            padding: 0 0.25rem;
        }
        .alert-dismiss:hover { opacity: 1; }

        /* Stats Row */
        .stats-row {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }

        .stat {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.5rem 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            min-width: 100px;
        }

        .stat-icon { font-size: 11px; opacity: 0.7; }
        .stat-value { font-weight: 600; font-size: 13px; }
        .stat-label { color: var(--text-muted); font-size: 10px; }

        .stat.gradle .stat-value { color: var(--accent-green); }
        .stat.kotlin .stat-value { color: var(--kotlin-purple); }
        .stat.studio .stat-value { color: var(--studio-green); }
        .stat.emulator .stat-value { color: var(--accent-orange); }
        .stat.ide .stat-value { color: #ec4899; }
        .stat.java .stat-value { color: var(--accent-cyan); }
        .stat.memory .stat-value { color: var(--accent-blue); }

        .stat.warning { border-color: rgba(245, 158, 11, 0.5); background: var(--warning-bg); }
        .stat.danger { border-color: rgba(239, 68, 68, 0.5); background: var(--danger-bg); }

        /* App Stats */
        .app-stats {
            display: flex;
            gap: 1rem;
            padding: 0.5rem 0.75rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 1rem;
            font-size: 11px;
            color: var(--text-muted);
        }

        .app-stats span { display: flex; align-items: center; gap: 0.25rem; }
        .app-stats .value { color: var(--text-secondary); }

        /* Sections */
        .section { margin-bottom: 1rem; }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0;
        }

        .section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .section-title .dot {
            width: 8px;
            height: 8px;
            border-radius: 2px;
        }

        .section-title.gradle .dot { background: var(--accent-green); }
        .section-title.kotlin .dot { background: var(--kotlin-purple); }
        .section-title.studio .dot { background: var(--studio-green); }
        .section-title.emulator .dot { background: var(--accent-orange); }
        .section-title.ide .dot { background: #ec4899; }
        .section-title.java .dot { background: var(--accent-cyan); }

        .section-count {
            background: var(--bg-tertiary);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-size: 10px;
        }

        /* Process Table */
        .process-table {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
        }

        .process-row {
            display: grid;
            grid-template-columns: 55px 1fr 70px 55px 40px;
            gap: 0.5rem;
            padding: 0.5rem 0.75rem;
            border-bottom: 1px solid var(--border);
            align-items: center;
            transition: background 0.1s;
        }

        .process-row:last-child { border-bottom: none; }
        .process-row:hover { background: var(--bg-tertiary); }

        .process-row.header {
            background: var(--bg-tertiary);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: var(--text-muted);
            font-weight: 500;
        }

        .process-row.warning { background: var(--warning-bg); }
        .process-row.danger { background: var(--danger-bg); }

        .pid { color: var(--accent-blue); font-size: 11px; }

        .process-info { overflow: hidden; }
        .process-name {
            font-size: 11px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: flex;
            align-items: center;
            gap: 0.375rem;
        }

        .status-badge {
            font-size: 9px;
            padding: 0.125rem 0.25rem;
            border-radius: 3px;
            font-weight: 500;
            flex-shrink: 0;
        }

        .status-badge.stuck {
            background: var(--accent-red);
            color: white;
            animation: blink 1s infinite;
        }

        .status-badge.idle {
            background: var(--accent-orange);
            color: white;
        }

        @keyframes blink { 50% { opacity: 0.6; } }
        .process-meta {
            font-size: 10px;
            color: var(--text-muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .process-meta .user { color: var(--accent-purple); }
        .process-meta .heap { color: var(--accent-orange); }

        .mem { color: var(--accent-orange); text-align: right; font-size: 11px; }
        .cpu { color: var(--accent-green); text-align: right; font-size: 11px; }
        .cpu.high { color: var(--accent-orange); }
        .cpu.critical { color: var(--accent-red); }
        .mem.high { color: var(--accent-orange); }
        .mem.critical { color: var(--accent-red); }

        .kill-btn {
            background: none;
            border: 1px solid var(--accent-red);
            color: var(--accent-red);
            padding: 0.125rem 0.25rem;
            border-radius: 3px;
            cursor: pointer;
            font-size: 9px;
            font-family: inherit;
            opacity: 0;
            transition: all 0.1s;
        }

        .process-row:hover .kill-btn { opacity: 0.7; }
        .kill-btn:hover { opacity: 1 !important; background: var(--danger-bg); }

        .empty {
            padding: 1.5rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 11px;
        }

        /* Actions */
        .actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .btn {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            font-family: inherit;
            font-size: 11px;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 0.375rem;
        }

        .btn:hover { background: var(--border); color: var(--text-primary); }
        .btn.danger { border-color: var(--accent-red); color: var(--accent-red); }
        .btn.danger:hover { background: var(--danger-bg); }

        .footer {
            text-align: center;
            padding: 0.75rem;
            color: var(--text-muted);
            font-size: 10px;
        }

        /* Responsive */
        @media (max-width: 640px) {
            .process-row { grid-template-columns: 50px 1fr 60px 40px; }
            .cpu { display: none; }
            .stats-row { gap: 0.375rem; }
            .stat { padding: 0.375rem 0.5rem; min-width: 80px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">G</div>
                <span>Gradik</span>
            </div>
            <div class="header-right">
                <div class="status">
                    <div class="status-dot"></div>
                    <span id="last-updated">-</span>
                </div>
                <button class="port-btn" onclick="showPortDialog()" title="Change port">:<span id="current-port">-</span></button>
                <button class="theme-toggle" onclick="toggleTheme()">◐</button>
                <button class="btn" onclick="refresh()">↻</button>
            </div>
        </header>
        
        <!-- Port Change Dialog -->
        <div id="port-dialog" class="port-dialog-overlay" style="display: none;">
            <div class="port-dialog">
                <div class="port-dialog-header">
                    <span>⚡ Change Port</span>
                    <button class="port-dialog-close" onclick="hidePortDialog()">×</button>
                </div>
                <div class="port-dialog-body" id="port-dialog-form">
                    <label>Port number (1024-65535)</label>
                    <input type="number" id="port-input" min="1024" max="65535" placeholder="5050">
                    <div class="port-dialog-info">
                        <small>Current: <span id="dialog-current-port">-</span></small>
                        <small>Config: ~/.gradik/config.json</small>
                    </div>
                </div>
                <div class="port-dialog-footer" id="port-dialog-buttons">
                    <button class="btn btn-secondary" onclick="hidePortDialog()">Cancel</button>
                    <button class="btn btn-primary" onclick="changePort()">Save</button>
                </div>
            </div>
        </div>

        <div class="alerts-container" id="alerts-container">
            <div class="alerts-header">
                <span>⚠ Alerts</span>
                <span class="count" id="alerts-count">0</span>
            </div>
            <div class="alerts" id="alerts"></div>
        </div>

        <div class="stats-row">
            <div class="stat gradle" id="stat-gradle">
                <span class="stat-icon">⚙</span>
                <div>
                    <div class="stat-value" id="gradle-count">-</div>
                    <div class="stat-label">Gradle</div>
                </div>
            </div>
            <div class="stat kotlin" id="stat-kotlin">
                <span class="stat-icon">K</span>
                <div>
                    <div class="stat-value" id="kotlin-count">-</div>
                    <div class="stat-label">Kotlin</div>
                </div>
            </div>
            <div class="stat studio" id="stat-studio">
                <span class="stat-icon">📱</span>
                <div>
                    <div class="stat-value" id="studio-count">-</div>
                    <div class="stat-label">Studio</div>
                </div>
            </div>
            <div class="stat emulator" id="stat-emulator">
                <span class="stat-icon">📟</span>
                <div>
                    <div class="stat-value" id="emulator-count">-</div>
                    <div class="stat-label">Emulator</div>
                </div>
            </div>
            <div class="stat ide" id="stat-ide">
                <span class="stat-icon">📝</span>
                <div>
                    <div class="stat-value" id="ide-count">-</div>
                    <div class="stat-label">IDEs</div>
                </div>
            </div>
            <div class="stat java" id="stat-java">
                <span class="stat-icon">☕</span>
                <div>
                    <div class="stat-value" id="java-count">-</div>
                    <div class="stat-label">Java</div>
                </div>
            </div>
            <div class="stat memory" id="stat-memory">
                <span class="stat-icon">💾</span>
                <div>
                    <div class="stat-value" id="total-memory">-</div>
                    <div class="stat-label">Total</div>
                </div>
            </div>
        </div>

        <div class="app-stats">
            <span>⚡ Gradik:</span>
            <span>CPU <span class="value" id="app-cpu">-</span></span>
            <span>RAM <span class="value" id="app-memory">-</span></span>
            <span>Up <span class="value" id="app-uptime">-</span></span>
            <span>PID <span class="value" id="app-pid">-</span></span>
        </div>

        <div class="section" id="section-gradle">
            <div class="section-header">
                <div class="section-title gradle"><span class="dot"></span>Gradle <span class="section-count" id="gradle-section-count">0</span></div>
            </div>
            <div class="process-table" id="gradle-list"></div>
        </div>

        <div class="section" id="section-kotlin">
            <div class="section-header">
                <div class="section-title kotlin"><span class="dot"></span>Kotlin <span class="section-count" id="kotlin-section-count">0</span></div>
            </div>
            <div class="process-table" id="kotlin-list"></div>
        </div>

        <div class="section" id="section-studio">
            <div class="section-header">
                <div class="section-title studio"><span class="dot"></span>Android Studio <span class="section-count" id="studio-section-count">0</span></div>
            </div>
            <div class="process-table" id="studio-list"></div>
        </div>

        <div class="section" id="section-emulator">
            <div class="section-header">
                <div class="section-title emulator"><span class="dot"></span>Emulators <span class="section-count" id="emulator-section-count">0</span></div>
            </div>
            <div class="process-table" id="emulator-list"></div>
        </div>

        <div class="section" id="section-ide">
            <div class="section-header">
                <div class="section-title ide"><span class="dot"></span>IDEs <span class="section-count" id="ide-section-count">0</span></div>
            </div>
            <div class="process-table" id="ide-list"></div>
        </div>

        <div class="section" id="section-java">
            <div class="section-header">
                <div class="section-title java"><span class="dot"></span>Other Java <span class="section-count" id="java-section-count">0</span></div>
            </div>
            <div class="process-table" id="java-list"></div>
        </div>

        <div class="actions">
            <button class="btn" onclick="refresh()">↻ Refresh</button>
            <button class="btn danger" onclick="stopAllDaemons()">⏹ Stop Daemons</button>
        </div>

        <div class="footer">Gradik • Auto-refresh 5s</div>
    </div>

    <script>
        // Thresholds for warnings
        const THRESHOLDS = {
            CPU_WARNING: 50,
            CPU_CRITICAL: 80,
            CPU_STUCK: 85,           // CPU threshold for "stuck" detection
            MEM_WARNING: 1024 * 1024 * 1024,  // 1 GB
            MEM_CRITICAL: 2 * 1024 * 1024 * 1024,  // 2 GB
            TOTAL_MEM_WARNING: 4 * 1024 * 1024 * 1024,  // 4 GB
            IDLE_DAEMON_MINUTES: 30, // Daemon idle for this long = zombie
            STUCK_CHECK_COUNT: 6,    // Number of consecutive checks (6 * 5s = 30s)
        };

        let alerts = new Map();
        let cpuHistory = new Map();  // pid -> array of last N cpu readings

        // Memory leak prevention
        const MAX_ALERTS = 50;
        const MAX_HISTORY_PIDS = 100;
        const CLEANUP_INTERVAL = 60000; // 1 minute

        // Theme
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
        }

        // Load saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) document.documentElement.setAttribute('data-theme', savedTheme);

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        function addAlert(id, type, message) {
            // Update timestamp if exists (keeps it from being cleaned as stale)
            if (alerts.has(id)) {
                alerts.get(id).time = Date.now();
                return;
            }
            
            // Prevent unbounded growth - remove oldest if at limit
            if (alerts.size >= MAX_ALERTS) {
                const firstKey = alerts.keys().next().value;
                alerts.delete(firstKey);
            }
            
            alerts.set(id, { type, message, time: Date.now() });
            renderAlerts();
        }

        function removeAlert(id) {
            alerts.delete(id);
            renderAlerts();
        }

        // Periodic cleanup of stale data
        function cleanupStaleData() {
            const now = Date.now();
            
            // Remove alerts older than 5 minutes that weren't refreshed
            for (const [id, alert] of alerts) {
                if (now - alert.time > 300000) {
                    alerts.delete(id);
                }
            }
            
            // Limit cpuHistory size
            if (cpuHistory.size > MAX_HISTORY_PIDS) {
                const entries = [...cpuHistory.entries()];
                entries.slice(0, entries.length - MAX_HISTORY_PIDS).forEach(([pid]) => {
                    cpuHistory.delete(pid);
                });
            }
            
            renderAlerts();
            console.log(`[Gradik] Cleanup: ${alerts.size} alerts, ${cpuHistory.size} tracked PIDs`);
        }

        // Run cleanup every minute
        setInterval(cleanupStaleData, CLEANUP_INTERVAL);

        function renderAlerts() {
            const wrapper = document.getElementById('alerts-container');
            const container = document.getElementById('alerts');
            const countEl = document.getElementById('alerts-count');
            
            container.innerHTML = '';
            countEl.textContent = alerts.size;
            
            if (alerts.size === 0) {
                wrapper.classList.remove('has-alerts');
                return;
            }
            
            wrapper.classList.add('has-alerts');
            alerts.forEach((alert, id) => {
                container.innerHTML += `
                    <div class="alert ${alert.type}">
                        <span class="alert-icon">${alert.type === 'danger' ? '●' : '▲'}</span>
                        <span>${alert.message}</span>
                        <button class="alert-dismiss" onclick="removeAlert('${id}')">×</button>
                    </div>
                `;
            });
        }

        function parseUptime(uptimeStr) {
            // Parse uptime string like "5m 30s", "2h 15m", "1d 3h" to minutes
            let minutes = 0;
            const days = uptimeStr.match(/(\d+)d/);
            const hours = uptimeStr.match(/(\d+)h/);
            const mins = uptimeStr.match(/(\d+)m/);
            if (days) minutes += parseInt(days[1]) * 24 * 60;
            if (hours) minutes += parseInt(hours[1]) * 60;
            if (mins) minutes += parseInt(mins[1]);
            return minutes;
        }

        function checkStuckProcess(proc) {
            const pid = proc.pid;
            
            // Track CPU history
            if (!cpuHistory.has(pid)) cpuHistory.set(pid, []);
            const history = cpuHistory.get(pid);
            history.push(proc.cpu);
            if (history.length > THRESHOLDS.STUCK_CHECK_COUNT) history.shift();
            
            // Check for stuck (high CPU for extended period)
            if (history.length >= THRESHOLDS.STUCK_CHECK_COUNT) {
                const allHigh = history.every(cpu => cpu > THRESHOLDS.CPU_STUCK);
                if (allHigh) {
                    addAlert(`stuck-${pid}`, 'danger', `🔄 STUCK? ${proc.name} (PID ${pid}) - High CPU for 30s+`);
                    return 'stuck';
                }
            }
            removeAlert(`stuck-${pid}`);
            
            // Check for idle daemon (only for Gradle/Kotlin daemons)
            if (proc.name.includes('Daemon')) {
                const uptimeMinutes = parseUptime(proc.uptime || '0m');
                if (uptimeMinutes > THRESHOLDS.IDLE_DAEMON_MINUTES && proc.cpu < 1 && proc.memory < 100 * 1024 * 1024) {
                    addAlert(`idle-${pid}`, 'warning', `💤 IDLE: ${proc.name} (PID ${pid}) - ${proc.uptime} with no activity`);
                    return 'idle';
                }
            }
            removeAlert(`idle-${pid}`);
            
            return null;
        }

        function checkAlerts(data) {
            // Check total memory
            if (data.total_memory > THRESHOLDS.TOTAL_MEM_WARNING) {
                addAlert('total-mem', 'warning', `High total memory: ${formatBytes(data.total_memory)}`);
            } else {
                removeAlert('total-mem');
            }

            // Track seen PIDs to clean up old history
            const seenPids = new Set();

            // Check individual processes
            const allProcs = [...data.gradle, ...data.kotlin, ...data.studio, ...data.emulator, ...data.ide, ...data.java];
            allProcs.forEach(proc => {
                seenPids.add(proc.pid);
                
                // Check for stuck/idle processes
                const stuckStatus = checkStuckProcess(proc);
                proc._status = stuckStatus;  // Attach status for rendering
                
                // Standard CPU/memory alerts (skip if already marked as stuck)
                if (stuckStatus !== 'stuck') {
                    if (proc.cpu > THRESHOLDS.CPU_CRITICAL) {
                        addAlert(`cpu-${proc.pid}`, 'danger', `${proc.name} (PID ${proc.pid}) CPU: ${proc.cpu.toFixed(1)}%`);
                    } else if (proc.cpu > THRESHOLDS.CPU_WARNING) {
                        addAlert(`cpu-${proc.pid}`, 'warning', `${proc.name} (PID ${proc.pid}) CPU: ${proc.cpu.toFixed(1)}%`);
                    } else {
                        removeAlert(`cpu-${proc.pid}`);
                    }
                }

                if (proc.memory > THRESHOLDS.MEM_CRITICAL) {
                    addAlert(`mem-${proc.pid}`, 'danger', `${proc.name} (PID ${proc.pid}) RAM: ${formatBytes(proc.memory)}`);
                } else if (proc.memory > THRESHOLDS.MEM_WARNING) {
                    addAlert(`mem-${proc.pid}`, 'warning', `${proc.name} (PID ${proc.pid}) RAM: ${formatBytes(proc.memory)}`);
                } else {
                    removeAlert(`mem-${proc.pid}`);
                }
            });

            // Clean up history for dead processes
            for (const pid of cpuHistory.keys()) {
                if (!seenPids.has(pid)) {
                    cpuHistory.delete(pid);
                    removeAlert(`stuck-${pid}`);
                    removeAlert(`idle-${pid}`);
                    removeAlert(`cpu-${pid}`);
                    removeAlert(`mem-${pid}`);
                }
            }
            
            // Self-check: warn if Gradik is using too much memory (>100MB)
            if (data.app && data.app.memory > 100 * 1024 * 1024) {
                console.warn(`[Gradik] High memory usage: ${formatBytes(data.app.memory)}`);
            }
        }

        function renderProcessList(containerId, processes, sectionCountId) {
            const container = document.getElementById(containerId);
            document.getElementById(sectionCountId).textContent = processes.length;

            if (processes.length === 0) {
                container.innerHTML = '<div class="empty">No processes</div>';
                return;
            }

            let html = `
                <div class="process-row header">
                    <div>PID</div>
                    <div>Process</div>
                    <div>Mem</div>
                    <div>CPU</div>
                    <div></div>
                </div>
            `;

            processes.forEach(proc => {
                const cpuClass = proc.cpu > THRESHOLDS.CPU_CRITICAL ? 'critical' : proc.cpu > THRESHOLDS.CPU_WARNING ? 'high' : '';
                const memClass = proc.memory > THRESHOLDS.MEM_CRITICAL ? 'critical' : proc.memory > THRESHOLDS.MEM_WARNING ? 'high' : '';
                let rowClass = proc.cpu > THRESHOLDS.CPU_CRITICAL || proc.memory > THRESHOLDS.MEM_CRITICAL ? 'danger' : 
                                 proc.cpu > THRESHOLDS.CPU_WARNING || proc.memory > THRESHOLDS.MEM_WARNING ? 'warning' : '';
                
                // Check stuck/idle status
                const status = proc._status;
                let statusBadge = '';
                if (status === 'stuck') {
                    statusBadge = '<span class="status-badge stuck">STUCK</span>';
                    rowClass = 'danger';
                } else if (status === 'idle') {
                    statusBadge = '<span class="status-badge idle">IDLE</span>';
                    rowClass = 'warning';
                }
                
                const heap = proc.heap ? `<span class="heap">${proc.heap}</span>` : '';
                const meta = `<span class="user">${proc.user}</span> · ${proc.uptime} ${heap}`;
                
                html += `
                    <div class="process-row ${rowClass}">
                        <div class="pid">${proc.pid}</div>
                        <div class="process-info">
                            <div class="process-name" title="${proc.name}">${statusBadge}${proc.name}</div>
                            <div class="process-meta">${meta}</div>
                        </div>
                        <div class="mem ${memClass}">${formatBytes(proc.memory)}</div>
                        <div class="cpu ${cpuClass}">${proc.cpu.toFixed(1)}%</div>
                        <button class="kill-btn" onclick="killProcess(${proc.pid}, '${proc.name.replace(/'/g, "\\'")}')">×</button>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        function updateStatCard(id, value, threshold = null) {
            const el = document.getElementById(id);
            el.classList.remove('warning', 'danger');
            if (threshold && value > threshold * 2) el.classList.add('danger');
            else if (threshold && value > threshold) el.classList.add('warning');
        }

        async function refresh() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                // Update counts
                document.getElementById('gradle-count').textContent = data.gradle.length;
                document.getElementById('kotlin-count').textContent = data.kotlin.length;
                document.getElementById('studio-count').textContent = data.studio.length;
                document.getElementById('emulator-count').textContent = data.emulator.length;
                document.getElementById('ide-count').textContent = data.ide.length;
                document.getElementById('java-count').textContent = data.java.length;
                document.getElementById('total-memory').textContent = formatBytes(data.total_memory);
                document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();

                // App stats
                document.getElementById('app-cpu').textContent = data.app.cpu + '%';
                document.getElementById('app-memory').textContent = formatBytes(data.app.memory);
                document.getElementById('app-uptime').textContent = data.app.uptime;
                document.getElementById('app-pid').textContent = data.app.pid;

                // Check for high consumption alerts
                checkAlerts(data);

                // Update stat card warnings
                updateStatCard('stat-memory', data.total_memory, THRESHOLDS.TOTAL_MEM_WARNING);

                // Render process lists
                renderProcessList('gradle-list', data.gradle, 'gradle-section-count');
                renderProcessList('kotlin-list', data.kotlin, 'kotlin-section-count');
                renderProcessList('studio-list', data.studio, 'studio-section-count');
                renderProcessList('emulator-list', data.emulator, 'emulator-section-count');
                renderProcessList('ide-list', data.ide, 'ide-section-count');
                renderProcessList('java-list', data.java, 'java-section-count');

            } catch (err) {
                console.error('Failed to fetch status:', err);
            }
        }

        async function killProcess(pid, name) {
            if (!confirm(`Kill ${name} (PID ${pid})?`)) return;
            try {
                const res = await fetch('/api/kill/' + pid, { method: 'POST' });
                const result = await res.json();
                if (!result.success) alert('Failed: ' + (result.error || 'Unknown'));
                setTimeout(refresh, 300);
            } catch (err) {
                alert('Failed to kill process');
            }
        }

        async function stopAllDaemons() {
            if (!confirm('Stop all Gradle daemons?')) return;
            try {
                await fetch('/api/stop-daemons', { method: 'POST' });
                setTimeout(refresh, 1000);
            } catch (err) {
                console.error('Failed:', err);
            }
        }

        refresh();
        setInterval(refresh, 5000);
        
        // Load initial config
        loadConfig();
        
        async function loadConfig() {
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                document.getElementById('current-port').textContent = data.port;
                document.getElementById('dialog-current-port').textContent = data.port;
                document.getElementById('port-input').value = data.port;
                document.getElementById('port-input').placeholder = data.port;
            } catch (err) {
                console.error('Failed to load config:', err);
            }
        }
        
        function showPortDialog() {
            document.getElementById('port-dialog').style.display = 'flex';
            document.getElementById('port-input').focus();
        }
        
        function hidePortDialog() {
            document.getElementById('port-dialog').style.display = 'none';
        }
        
        async function changePort() {
            const newPort = parseInt(document.getElementById('port-input').value);
            
            if (!newPort || newPort < 1024 || newPort > 65535) {
                alert('Please enter a valid port (1024-65535)');
                return;
            }
            
            try {
                const res = await fetch('/api/config/port', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ port: newPort })
                });
                const data = await res.json();
                
                if (data.success) {
                    alert(`✅ Port saved to ${newPort}\n\nRestart the app to use the new port.`);
                    hidePortDialog();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            } catch (err) {
                alert('Failed to change port: ' + err.message);
            }
        }
        
        // Close dialog on escape or clicking outside
        document.getElementById('port-dialog').addEventListener('click', (e) => {
            if (e.target.classList.contains('port-dialog-overlay')) {
                hidePortDialog();
            }
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') hidePortDialog();
            if (e.key === 'Enter' && document.getElementById('port-dialog').style.display === 'flex') {
                changePort();
            }
        });
    </script>
</body>
</html>
'''


def format_uptime(seconds):
    """Format seconds into human readable uptime."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"


def get_all_processes():
    """Get all relevant processes using psutil for richer info."""
    processes = {
        'gradle': [], 
        'kotlin': [], 
        'studio': [],
        'emulator': [],
        'ide': [],
        'java': []
    }
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username', 'cpu_percent', 
                                          'memory_info', 'create_time', 'cwd']):
            try:
                pinfo = proc.info
                proc_name = pinfo['name'] or ''
                cmdline = ' '.join(pinfo['cmdline'] or [])
                cmdline_lower = cmdline.lower()
                proc_name_lower = proc_name.lower()
                
                # Check if it's a relevant process
                is_java = 'java' in cmdline_lower
                is_kotlin = 'kotlin' in cmdline_lower
                is_gradle = 'gradle' in cmdline_lower
                is_studio = ('android studio' in cmdline_lower or 
                            'Android Studio.app' in cmdline or
                            'com.google.android.studio' in cmdline_lower or
                            '-Didea.platform.prefix=AndroidStudio' in cmdline)
                is_emulator = ('qemu-system' in proc_name_lower or 
                              'emulator' in proc_name_lower or
                              'emulator64' in proc_name_lower or
                              'qemu' in proc_name_lower or
                              'Android Emulator' in cmdline)
                is_adb = 'adb' in proc_name_lower and 'server' in cmdline_lower
                
                # IDE detection
                is_ide = ('cursor' in proc_name_lower or
                         'Cursor.app' in cmdline or
                         'code' in proc_name_lower or  # VS Code
                         'Code.app' in cmdline or
                         'Visual Studio Code' in cmdline or
                         'windsurf' in proc_name_lower or
                         'Windsurf.app' in cmdline or
                         'trae' in proc_name_lower or
                         'Trae.app' in cmdline or
                         'antigravity' in proc_name_lower or
                         'zed' in proc_name_lower or
                         'Zed.app' in cmdline or
                         'fleet' in proc_name_lower or
                         'Fleet.app' in cmdline or
                         'sublime' in proc_name_lower or
                         'Sublime' in cmdline or
                         'atom' in proc_name_lower or
                         'notepad++' in proc_name_lower or
                         'neovim' in proc_name_lower or
                         'nvim' in proc_name_lower)
                
                if not any([is_java, is_kotlin, is_gradle, is_studio, is_emulator, is_adb, is_ide]):
                    continue
                
                pid = pinfo['pid']
                cpu = pinfo['cpu_percent'] or 0
                memory = pinfo['memory_info'].rss if pinfo['memory_info'] else 0
                username = pinfo['username'] or 'unknown'
                
                # Calculate uptime
                create_time = pinfo['create_time']
                uptime_seconds = datetime.now().timestamp() - create_time if create_time else 0
                uptime = format_uptime(uptime_seconds)
                
                # Get working directory
                try:
                    cwd = pinfo['cwd'] or ''
                    home = os.path.expanduser('~')
                    if cwd.startswith(home):
                        cwd = '~' + cwd[len(home):]
                except:
                    cwd = ''
                
                # Simplify process name & extract extra info
                name = cmdline[:100]
                heap_size = ''
                extra_info = ''
                
                # Extract heap size from JVM args
                heap_match = re.search(r'-Xmx(\d+[mgMG])', cmdline)
                if heap_match:
                    heap_size = heap_match.group(1).upper()
                
                # Determine category and name - ORDER MATTERS!
                # Check specific daemon types FIRST before generic IDE detection
                category = 'java'
                
                if 'GradleDaemon' in cmdline:
                    # This is a Gradle Daemon - highest priority
                    category = 'gradle'
                    name = 'GradleDaemon'
                    version_match = re.search(r'GradleDaemon\s+(\d+\.\d+)', cmdline)
                    if version_match:
                        name = f'GradleDaemon {version_match.group(1)}'
                elif 'KotlinCompileDaemon' in cmdline:
                    # This is a Kotlin Compile Daemon
                    category = 'kotlin'
                    name = 'KotlinCompileDaemon'
                elif 'kotlin-daemon' in cmdline_lower or 'kotlin.daemon' in cmdline_lower:
                    category = 'kotlin'
                    name = 'Kotlin Daemon'
                elif is_emulator:
                    category = 'emulator'
                    # Try to extract AVD name
                    avd_match = re.search(r'-avd\s+([^\s]+)', cmdline)
                    if avd_match:
                        name = f'Emulator: {avd_match.group(1)}'
                    elif 'qemu-system' in proc_name_lower:
                        name = 'QEMU (Android Emulator)'
                    else:
                        name = 'Android Emulator'
                elif is_adb:
                    category = 'studio'
                    name = 'ADB Server'
                elif '-Didea.platform.prefix=AndroidStudio' in cmdline or 'Android Studio.app' in cmdline:
                    # Main Android Studio process
                    category = 'studio'
                    name = 'Android Studio'
                    version_match = re.search(r'android-studio[/-](\d+\.\d+)', cmdline_lower)
                    if version_match:
                        name = f'Android Studio {version_match.group(1)}'
                elif 'fsnotifier' in proc_name_lower:
                    category = 'studio'
                    name = 'Studio File Watcher'
                elif 'jcef_helper' in proc_name_lower or 'jcef' in cmdline_lower:
                    category = 'studio'
                    name = 'Studio Browser Helper'
                elif is_ide:
                    category = 'ide'
                    # Detect specific IDE
                    if 'cursor' in proc_name_lower or 'Cursor' in cmdline:
                        name = 'Cursor'
                    elif 'windsurf' in proc_name_lower or 'Windsurf' in cmdline:
                        name = 'Windsurf'
                    elif 'code' in proc_name_lower or 'Code.app' in cmdline or 'Visual Studio Code' in cmdline:
                        name = 'VS Code'
                    elif 'trae' in proc_name_lower or 'Trae' in cmdline:
                        name = 'Trae'
                    elif 'antigravity' in proc_name_lower:
                        name = 'Antigravity'
                    elif 'zed' in proc_name_lower or 'Zed' in cmdline:
                        name = 'Zed'
                    elif 'fleet' in proc_name_lower or 'Fleet' in cmdline:
                        name = 'Fleet'
                    elif 'sublime' in proc_name_lower or 'Sublime' in cmdline:
                        name = 'Sublime Text'
                    elif 'nvim' in proc_name_lower or 'neovim' in proc_name_lower:
                        name = 'Neovim'
                    else:
                        name = 'IDE'
                elif is_gradle and not is_kotlin:
                    category = 'gradle'
                    name = 'Gradle Process'
                elif is_kotlin:
                    category = 'kotlin'
                    name = 'Kotlin Process'
                
                proc_info = {
                    'pid': pid,
                    'name': name,
                    'memory': memory,
                    'cpu': cpu,
                    'user': username,
                    'uptime': uptime,
                    'cwd': cwd,
                    'heap': heap_size
                }
                
                processes[category].append(proc_info)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
    except Exception as e:
        print(f"Error getting processes: {e}")
    
    return processes


def get_app_stats():
    """Get Gradik app's own resource usage."""
    try:
        proc = psutil.Process(APP_PID)
        cpu = proc.cpu_percent(interval=0.1)
        memory = proc.memory_info().rss
        uptime_seconds = (datetime.now() - APP_START_TIME).total_seconds()
        
        return {
            'pid': APP_PID,
            'cpu': round(cpu, 1),
            'memory': memory,
            'uptime': format_uptime(uptime_seconds)
        }
    except:
        return {
            'pid': APP_PID,
            'cpu': 0,
            'memory': 0,
            'uptime': '0s'
        }


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
def status():
    processes = get_all_processes()
    app_stats = get_app_stats()
    
    all_procs = (processes['gradle'] + processes['kotlin'] + 
                 processes['studio'] + processes['emulator'] + 
                 processes['ide'] + processes['java'])
    total_memory = sum(p['memory'] for p in all_procs)
    
    return jsonify({
        'gradle': processes['gradle'],
        'kotlin': processes['kotlin'],
        'studio': processes['studio'],
        'emulator': processes['emulator'],
        'ide': processes['ide'],
        'java': processes['java'],
        'total_memory': total_memory,
        'app': app_stats,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/kill/<int:pid>', methods=['POST'])
def kill_process(pid):
    """Kill a specific process by PID."""
    import signal
    import os
    
    try:
        os.kill(pid, signal.SIGTERM)
        return jsonify({'success': True, 'pid': pid})
    except ProcessLookupError:
        return jsonify({'success': False, 'error': 'Process not found'})
    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/stop-daemons', methods=['POST'])
def stop_daemons():
    """Stop all Gradle daemons using gradle --stop."""
    try:
        subprocess.run(['gradle', '--stop'], capture_output=True, timeout=30)
        return jsonify({'success': True})
    except FileNotFoundError:
        # Try with gradlew if gradle not in PATH
        try:
            subprocess.run(['./gradlew', '--stop'], capture_output=True, timeout=30)
            return jsonify({'success': True})
        except:
            pass
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Gradle not found'})


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    return jsonify({
        'port': CURRENT_PORT,
        'config_file': str(CONFIG_FILE)
    })


@app.route('/api/config/port', methods=['POST'])
def change_port():
    """Change port - saves to config, used on next app start."""
    data = request.get_json() or {}
    new_port = data.get('port')
    
    if not new_port:
        return jsonify({'success': False, 'error': 'Port is required'}), 400
    
    try:
        new_port = int(new_port)
        if new_port < 1024 or new_port > 65535:
            return jsonify({'success': False, 'error': 'Port must be between 1024 and 65535'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid port number'}), 400
    
    if new_port == CURRENT_PORT:
        return jsonify({'success': True, 'message': 'Port unchanged', 'port': new_port})
    
    # Save new port to config
    config = load_config()
    config['port'] = new_port
    if not save_config(config):
        return jsonify({'success': False, 'error': 'Failed to save config'}), 500
    
    return jsonify({
        'success': True, 
        'message': f'Port saved. Will use port {new_port} on next restart.',
        'port': new_port
    })


# PID file for daemon management
PID_FILE = CONFIG_DIR / 'gradik.pid'


def get_running_pid():
    """Get PID of running Gradik instance."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process is actually running
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    if 'python' in proc.name().lower() and 'gradik' in ' '.join(proc.cmdline()).lower():
                        return pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            # Stale PID file
            PID_FILE.unlink(missing_ok=True)
        except (ValueError, OSError):
            PID_FILE.unlink(missing_ok=True)
    return None


def write_pid():
    """Write current PID to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def remove_pid():
    """Remove PID file."""
    PID_FILE.unlink(missing_ok=True)


def cmd_start(port=None, foreground=False):
    """Start Gradik dashboard."""
    running_pid = get_running_pid()
    if running_pid:
        print(f"⚠️  Gradik is already running (PID {running_pid})")
        print(f"   Stop it first: gradik stop")
        return 1
    
    actual_port = port or CURRENT_PORT
    
    if foreground:
        # Run in foreground
        write_pid()
        try:
            print(f"🚀 Gradik - Gradle Status Dashboard")
            print(f"   Port: {actual_port}")
            print(f"   Config: {CONFIG_FILE}")
            print(f"   Open http://localhost:{actual_port} in your browser")
            print(f"   Press Ctrl+C to stop")
            print()
            app.run(host='0.0.0.0', port=actual_port, debug=False)
        finally:
            remove_pid()
    else:
        # Run as daemon in background
        log_file = CONFIG_DIR / 'gradik.log'
        
        # Detect if running as PyInstaller binary or Python script
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller binary
            executable = sys.executable
        else:
            # Running as Python script
            script_path = os.path.abspath(__file__)
            executable = f'python3 "{script_path}"'
        
        # Start detached process
        cmd = f'nohup {executable} start --foreground --port {actual_port} > "{log_file}" 2>&1 &'
        os.system(cmd)
        
        # Wait a moment and check if it started
        import time
        time.sleep(1)
        
        new_pid = get_running_pid()
        if new_pid:
            print(f"✅ Gradik started (PID {new_pid})")
            print(f"   URL: http://localhost:{actual_port}")
            print(f"   Log: {log_file}")
            print(f"   Stop: gradik stop")
        else:
            print(f"❌ Failed to start Gradik")
            print(f"   Check log: {log_file}")
            return 1
    
    return 0


def cmd_stop():
    """Stop Gradik dashboard."""
    pid = get_running_pid()
    if not pid:
        print("ℹ️  Gradik is not running")
        return 0
    
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        print(f"✅ Gradik stopped (was PID {pid})")
    except psutil.TimeoutExpired:
        proc.kill()
        print(f"✅ Gradik killed (was PID {pid})")
    except psutil.NoSuchProcess:
        print("ℹ️  Gradik is not running")
    
    remove_pid()
    return 0


def cmd_status():
    """Show Gradik status."""
    pid = get_running_pid()
    if pid:
        try:
            proc = psutil.Process(pid)
            mem = proc.memory_info().rss / 1024 / 1024
            cpu = proc.cpu_percent(interval=0.1)
            print(f"✅ Gradik is running")
            print(f"   PID: {pid}")
            print(f"   Port: {CURRENT_PORT}")
            print(f"   CPU: {cpu:.1f}%")
            print(f"   RAM: {mem:.1f} MB")
            print(f"   URL: http://localhost:{CURRENT_PORT}")
        except psutil.NoSuchProcess:
            print("❌ Gradik is not running")
            return 1
    else:
        print("❌ Gradik is not running")
        print(f"   Start: gradik start")
        return 1
    return 0


def cmd_restart(port=None):
    """Restart Gradik dashboard."""
    cmd_stop()
    import time
    time.sleep(0.5)
    return cmd_start(port)


def cmd_uninstall():
    """Uninstall Gradik completely."""
    import shutil
    
    print("🗑️  Uninstalling Gradik...")
    print()
    
    # Stop if running
    if PID_FILE.exists():
        print("   Stopping service...")
        cmd_stop()
    
    # Remove config directory
    if CONFIG_DIR.exists():
        print(f"   Removing {CONFIG_DIR}")
        shutil.rmtree(CONFIG_DIR)
    
    # Remove repo directory
    repo_dir = Path.home() / '.gradik-repo'
    if repo_dir.exists():
        print(f"   Removing {repo_dir}")
        shutil.rmtree(repo_dir)
    
    print()
    print("✅ Gradik uninstalled!")
    print()
    print("   To remove pip package, run:")
    print("   pip3 uninstall gradik")
    print()
    return 0


def main():
    """Entry point for the gradik command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='gradik',
        description='Gradle Status Dashboard - Monitor Gradle, Kotlin daemons, IDEs, and more'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # start command
    start_parser = subparsers.add_parser('start', help='Start Gradik dashboard')
    start_parser.add_argument('-p', '--port', type=int, help='Port to run on')
    start_parser.add_argument('-f', '--foreground', action='store_true', help='Run in foreground')
    
    # stop command
    subparsers.add_parser('stop', help='Stop Gradik dashboard')
    
    # restart command
    restart_parser = subparsers.add_parser('restart', help='Restart Gradik dashboard')
    restart_parser.add_argument('-p', '--port', type=int, help='Port to run on')
    
    # status command
    subparsers.add_parser('status', help='Show Gradik status')
    
    # uninstall command
    subparsers.add_parser('uninstall', help='Uninstall Gradik completely')
    
    # For backwards compatibility: run directly without subcommand
    parser.add_argument('-p', '--port', type=int, help='Port to run on (when running directly)')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        return cmd_start(args.port, args.foreground)
    elif args.command == 'stop':
        return cmd_stop()
    elif args.command == 'restart':
        return cmd_restart(args.port)
    elif args.command == 'status':
        return cmd_status()
    elif args.command == 'uninstall':
        return cmd_uninstall()
    else:
        # No subcommand - show help instead of auto-starting
        parser.print_help()
        print()
        print("💡 Quick start:")
        print("   gradik start           # Run in background")
        print("   gradik start -f        # Run in foreground")
        print("   gradik status          # Check if running")
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
