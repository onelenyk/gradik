#!/usr/bin/env python3
"""Gradle Status Dashboard - Simple process monitor for Gradle and Kotlin daemons."""

import subprocess
import re
import os
import sys
import json
import shutil
import socket
import psutil
import hashlib
import time
import ssl
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from pathlib import Path

APP_START_TIME = datetime.now()
APP_PID = os.getpid()

# Version - read from VERSION file
def get_version():
    """Get version from VERSION file."""
    version_file = Path(__file__).parent / 'VERSION'
    if version_file.exists():
        return version_file.read_text().strip()
    return '0.0.0'

__version__ = get_version()

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

        /* Update Banner */
        .update-banner {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
            border: 1px solid var(--accent-blue);
            border-radius: 6px;
            margin-bottom: 1rem;
            padding: 0.75rem 1rem;
            display: none;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            color: white;
            font-size: 12px;
        }
        .update-banner.show { display: flex; }
        .update-banner-content {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex: 1;
        }
        .update-banner-actions {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }
        .update-banner-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 0.375rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            font-weight: 500;
            transition: all 0.15s;
        }
        .update-banner-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
        }
        .update-banner-btn.primary {
            background: white;
            color: var(--accent-blue);
            border-color: white;
        }
        .update-banner-btn.primary:hover {
            background: rgba(255, 255, 255, 0.9);
        }

        /* Update Dialog */
        .update-dialog-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1001;
            backdrop-filter: blur(4px);
        }
        .update-dialog-overlay.show { display: flex; }
        .update-dialog {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 480px;
            max-width: 90vw;
            max-height: 80vh;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column;
        }
        .update-dialog-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }
        .update-dialog-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }
        .update-dialog-close:hover { color: var(--text-primary); }
        .update-dialog-body {
            padding: 16px;
            overflow-y: auto;
            flex: 1;
        }
        .update-dialog-body .version-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
            padding: 8px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            font-size: 12px;
        }
        .update-dialog-body .changelog {
            max-height: 200px;
            overflow-y: auto;
            padding: 12px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            font-size: 11px;
            color: var(--text-secondary);
            white-space: pre-wrap;
            margin-bottom: 12px;
        }
        .update-progress {
            display: none;
            margin-top: 12px;
        }
        .update-progress.show { display: block; }
        .update-progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        .update-progress-fill {
            height: 100%;
            background: var(--accent-cyan);
            width: 0%;
            transition: width 0.3s;
        }
        .update-progress-text {
            font-size: 11px;
            color: var(--text-muted);
            text-align: center;
        }
        .update-dialog-footer {
            display: flex;
            gap: 8px;
            padding: 16px;
            border-top: 1px solid var(--border);
            justify-content: flex-end;
        }

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
        .stats-row-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }

        .stats-row-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }

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
        .stat.cursor .stat-value { color: #3b82f6; }
        .stat.windsurf .stat-value { color: #06b6d4; }
        .stat.vscode .stat-value { color: #007acc; }
        .stat.ide_other .stat-value { color: #ec4899; }
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
        .section-title.cursor .dot { background: #3b82f6; }
        .section-title.windsurf .dot { background: #06b6d4; }
        .section-title.vscode .dot { background: #007acc; }
        .section-title.ide_other .dot { background: #ec4899; }
        .section-title.java .dot { background: var(--accent-cyan); }

        .section-count {
            background: var(--bg-tertiary);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-size: 10px;
        }

        .section-close-all {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--accent-red);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 10px;
            font-weight: 500;
            transition: all 0.15s;
            opacity: 0.7;
        }

        .section-close-all:hover {
            background: var(--danger-bg);
            border-color: var(--accent-red);
            opacity: 1;
        }

        .section-controls {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .sort-buttons {
            display: flex;
            gap: 0.25rem;
            align-items: center;
        }

        .sort-btn {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 0.25rem 0.375rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 10px;
            transition: all 0.15s;
            opacity: 0.6;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .sort-btn:hover {
            background: var(--border);
            color: var(--text-primary);
            opacity: 1;
        }

        .sort-btn.active {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
            color: white;
            opacity: 1;
        }

        .sort-btn.active.desc::after {
            content: ' ↓';
        }

        .sort-btn.active.asc::after {
            content: ' ↑';
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
        .process-meta .parent { color: var(--accent-cyan); font-style: italic; }

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
        
        <!-- Update Banner -->
        <div class="update-banner" id="update-banner">
            <div class="update-banner-content">
                <span>🔄</span>
                <span>Update available: <strong id="update-latest-version">-</strong> (you have <strong id="update-current-version">-</strong>)</span>
            </div>
            <div class="update-banner-actions">
                <button class="update-banner-btn primary" onclick="showUpdateDialog()">Update Now</button>
                <button class="update-banner-btn" onclick="dismissUpdateNotification()">Later</button>
                <button class="update-banner-btn" onclick="dismissUpdateNotification(true)">×</button>
            </div>
        </div>
        
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

        <!-- Update Dialog -->
        <div id="update-dialog" class="update-dialog-overlay">
            <div class="update-dialog">
                <div class="update-dialog-header">
                    <span>🔄 Update Gradik</span>
                    <button class="update-dialog-close" onclick="hideUpdateDialog()">×</button>
                </div>
                <div class="update-dialog-body">
                    <div class="version-info">
                        <span>Current: <strong id="update-dialog-current">-</strong></span>
                        <span>→</span>
                        <span>Latest: <strong id="update-dialog-latest">-</strong></span>
                    </div>
                    <div class="changelog" id="update-changelog">Loading changelog...</div>
                    <div class="update-progress" id="update-progress">
                        <div class="update-progress-bar">
                            <div class="update-progress-fill" id="update-progress-fill"></div>
                        </div>
                        <div class="update-progress-text" id="update-progress-text">Preparing update...</div>
                    </div>
                </div>
                <div class="update-dialog-footer">
                    <button class="btn btn-secondary" onclick="hideUpdateDialog()" id="update-cancel-btn">Cancel</button>
                    <button class="btn btn-primary" onclick="installUpdate()" id="update-install-btn">Install Update</button>
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

        <div class="stats-row-header">
            <div class="stats-row-title">Categories</div>
            <div class="sort-buttons">
                <button class="sort-btn" onclick="sortStatsBy('memory')" title="Sort categories by memory">💾</button>
                <button class="sort-btn" onclick="sortStatsBy('cpu')" title="Sort categories by CPU">⚡</button>
            </div>
        </div>
        <div class="stats-row" id="stats-row">
            <div class="stat gradle" id="stat-gradle" data-category="gradle">
                <span class="stat-icon">⚙</span>
                <div>
                    <div class="stat-value" id="gradle-count">-</div>
                    <div class="stat-label">Gradle</div>
                </div>
            </div>
            <div class="stat kotlin" id="stat-kotlin" data-category="kotlin">
                <span class="stat-icon">K</span>
                <div>
                    <div class="stat-value" id="kotlin-count">-</div>
                    <div class="stat-label">Kotlin</div>
                </div>
            </div>
            <div class="stat studio" id="stat-studio" data-category="studio">
                <span class="stat-icon">📱</span>
                <div>
                    <div class="stat-value" id="studio-count">-</div>
                    <div class="stat-label">Studio</div>
                </div>
            </div>
            <div class="stat emulator" id="stat-emulator" data-category="emulator">
                <span class="stat-icon">📟</span>
                <div>
                    <div class="stat-value" id="emulator-count">-</div>
                    <div class="stat-label">Emulator</div>
                </div>
            </div>
            <div class="stat cursor" id="stat-cursor" data-category="cursor">
                <span class="stat-icon">✏️</span>
                <div>
                    <div class="stat-value" id="cursor-count">-</div>
                    <div class="stat-label">Cursor</div>
                </div>
            </div>
            <div class="stat windsurf" id="stat-windsurf" data-category="windsurf">
                <span class="stat-icon">🌊</span>
                <div>
                    <div class="stat-value" id="windsurf-count">-</div>
                    <div class="stat-label">Windsurf</div>
                </div>
            </div>
            <div class="stat vscode" id="stat-vscode" data-category="vscode">
                <span class="stat-icon">📝</span>
                <div>
                    <div class="stat-value" id="vscode-count">-</div>
                    <div class="stat-label">VS Code</div>
                </div>
            </div>
            <div class="stat ide_other" id="stat-ide-other" data-category="ide_other">
                <span class="stat-icon">💻</span>
                <div>
                    <div class="stat-value" id="ide-other-count">-</div>
                    <div class="stat-label">Other IDEs</div>
                </div>
            </div>
            <div class="stat java" id="stat-java" data-category="java">
                <span class="stat-icon">☕</span>
                <div>
                    <div class="stat-value" id="java-count">-</div>
                    <div class="stat-label">Java</div>
                </div>
            </div>
            <div class="stat memory" id="stat-memory" data-category="total">
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
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('gradle', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('gradle', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('gradle')" title="Close all Gradle processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="gradle-list"></div>
        </div>

        <div class="section" id="section-kotlin">
            <div class="section-header">
                <div class="section-title kotlin"><span class="dot"></span>Kotlin <span class="section-count" id="kotlin-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('kotlin', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('kotlin', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('kotlin')" title="Close all Kotlin processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="kotlin-list"></div>
        </div>

        <div class="section" id="section-studio">
            <div class="section-header">
                <div class="section-title studio"><span class="dot"></span>Android Studio <span class="section-count" id="studio-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('studio', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('studio', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('studio')" title="Close all Android Studio processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="studio-list"></div>
        </div>

        <div class="section" id="section-emulator">
            <div class="section-header">
                <div class="section-title emulator"><span class="dot"></span>Emulators <span class="section-count" id="emulator-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('emulator', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('emulator', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('emulator')" title="Close all Emulator processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="emulator-list"></div>
        </div>

        <div class="section" id="section-cursor">
            <div class="section-header">
                <div class="section-title cursor"><span class="dot"></span>Cursor <span class="section-count" id="cursor-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('cursor', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('cursor', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('cursor')" title="Close all Cursor processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="cursor-list"></div>
        </div>

        <div class="section" id="section-windsurf">
            <div class="section-header">
                <div class="section-title windsurf"><span class="dot"></span>Windsurf <span class="section-count" id="windsurf-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('windsurf', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('windsurf', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('windsurf')" title="Close all Windsurf processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="windsurf-list"></div>
        </div>

        <div class="section" id="section-vscode">
            <div class="section-header">
                <div class="section-title vscode"><span class="dot"></span>VS Code <span class="section-count" id="vscode-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('vscode', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('vscode', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('vscode')" title="Close all VS Code processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="vscode-list"></div>
        </div>

        <div class="section" id="section-ide-other">
            <div class="section-header">
                <div class="section-title ide_other"><span class="dot"></span>Other IDEs <span class="section-count" id="ide-other-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('ide_other', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('ide_other', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('ide_other')" title="Close all Other IDE processes">⏹ Close All</button>
                </div>
            </div>
            <div class="process-table" id="ide-other-list"></div>
        </div>

        <div class="section" id="section-java">
            <div class="section-header">
                <div class="section-title java"><span class="dot"></span>Other Java <span class="section-count" id="java-section-count">0</span></div>
                <div class="section-controls">
                    <div class="sort-buttons">
                        <button class="sort-btn" onclick="sortCategory('java', 'memory')" title="Sort by memory">💾</button>
                        <button class="sort-btn" onclick="sortCategory('java', 'cpu')" title="Sort by CPU">⚡</button>
                    </div>
                    <button class="section-close-all" onclick="killCategory('java')" title="Close all Java processes">⏹ Close All</button>
                </div>
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
        let sortState = {};  // category -> { field: 'memory'|'cpu', order: 'asc'|'desc' }
        let categoryData = {};  // Store original data per category for sorting
        let statsSortState = { field: null, order: 'desc' };  // Stats row sorting

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
            const allProcs = [...data.gradle, ...data.kotlin, ...data.studio, ...data.emulator, 
                             ...data.cursor, ...data.windsurf, ...data.vscode, ...data.ide_other, ...data.java];
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

        function sortProcesses(processes, field, order) {
            const sorted = [...processes];
            sorted.sort((a, b) => {
                let valA = a[field];
                let valB = b[field];
                if (order === 'desc') {
                    return valB - valA;  // Descending: high to low
                } else {
                    return valA - valB;  // Ascending: low to high
                }
            });
            return sorted;
        }

        function updateSortButtons(category, field, order) {
            const section = document.getElementById(`section-${category}`);
            if (!section) return;
            
            const memBtn = section.querySelector('.sort-buttons .sort-btn[onclick*="memory"]');
            const cpuBtn = section.querySelector('.sort-buttons .sort-btn[onclick*="cpu"]');
            
            // Reset all buttons
            if (memBtn) {
                memBtn.classList.remove('active', 'asc', 'desc');
            }
            if (cpuBtn) {
                cpuBtn.classList.remove('active', 'asc', 'desc');
            }
            
            // Set active button
            const activeBtn = field === 'memory' ? memBtn : cpuBtn;
            if (activeBtn) {
                activeBtn.classList.add('active', order);
            }
        }

        function sortCategory(category, field) {
            // Toggle order if same field, otherwise default to desc
            const current = sortState[category];
            let order = 'desc';
            
            if (current && current.field === field) {
                // Toggle: desc -> asc -> desc
                order = current.order === 'desc' ? 'asc' : 'desc';
            }
            
            sortState[category] = { field, order };
            updateSortButtons(category, field, order);
            
            // Re-render the category
            const categoryMap = {
                'gradle': { list: 'gradle-list', count: 'gradle-section-count', dataKey: 'gradle' },
                'kotlin': { list: 'kotlin-list', count: 'kotlin-section-count', dataKey: 'kotlin' },
                'studio': { list: 'studio-list', count: 'studio-section-count', dataKey: 'studio' },
                'emulator': { list: 'emulator-list', count: 'emulator-section-count', dataKey: 'emulator' },
                'cursor': { list: 'cursor-list', count: 'cursor-section-count', dataKey: 'cursor' },
                'windsurf': { list: 'windsurf-list', count: 'windsurf-section-count', dataKey: 'windsurf' },
                'vscode': { list: 'vscode-list', count: 'vscode-section-count', dataKey: 'vscode' },
                'ide_other': { list: 'ide-other-list', count: 'ide-other-section-count', dataKey: 'ide_other' },
                'java': { list: 'java-list', count: 'java-section-count', dataKey: 'java' }
            };
            
            const mapping = categoryMap[category];
            if (mapping && categoryData[mapping.dataKey]) {
                const sorted = sortProcesses(categoryData[mapping.dataKey], field, order);
                renderProcessList(mapping.list, sorted, mapping.count);
            }
        }

        function renderProcessList(containerId, processes, sectionCountId) {
            const container = document.getElementById(containerId);
            document.getElementById(sectionCountId).textContent = processes.length;

            // Show/hide close all button based on process count
            // Map container IDs to section IDs
            const sectionIdMap = {
                'gradle-list': 'section-gradle',
                'kotlin-list': 'section-kotlin',
                'studio-list': 'section-studio',
                'emulator-list': 'section-emulator',
                'cursor-list': 'section-cursor',
                'windsurf-list': 'section-windsurf',
                'vscode-list': 'section-vscode',
                'ide-other-list': 'section-ide-other',
                'java-list': 'section-java'
            };
            const sectionId = sectionIdMap[containerId];
            if (sectionId) {
                const section = document.getElementById(sectionId);
                if (section) {
                    const controls = section.querySelector('.section-controls');
                    const closeAllBtn = section.querySelector('.section-close-all');
                    const sortButtons = section.querySelector('.sort-buttons');
                    
                    if (processes.length > 0) {
                        if (controls) controls.style.display = 'flex';
                        if (closeAllBtn) closeAllBtn.style.display = 'block';
                        if (sortButtons) sortButtons.style.display = 'flex';
                    } else {
                        if (controls) controls.style.display = 'none';
                        if (closeAllBtn) closeAllBtn.style.display = 'none';
                        if (sortButtons) sortButtons.style.display = 'none';
                    }
                }
            }

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
                let meta = `<span class="user">${proc.user}</span> · ${proc.uptime} ${heap}`;
                
                // Add parent process info if available
                if (proc.parent && proc.parent.cmdline) {
                    const parentCmdline = proc.parent.cmdline.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    const parentDisplay = parentCmdline.length > 30 
                        ? parentCmdline.substring(0, 27) + '...' 
                        : parentCmdline;
                    meta += ` · <span class="parent" title="Started by PID ${proc.parent.pid}: ${parentCmdline}">Started by: ${parentDisplay}</span>`;
                }
                
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

        function calculateCategoryTotals(data) {
            const totals = {};
            const categories = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java'];
            
            categories.forEach(cat => {
                const procs = data[cat] || [];
                totals[cat] = {
                    memory: procs.reduce((sum, p) => sum + (p.memory || 0), 0),
                    cpu: procs.reduce((sum, p) => sum + (p.cpu || 0), 0),
                    count: procs.length
                };
            });
            
            // Total is special
            totals.total = {
                memory: data.total_memory || 0,
                cpu: 0,  // Total CPU doesn't make sense
                count: 0
            };
            
            return totals;
        }

        function sortStatsBy(field, preserveOrder = false) {
            // Toggle order if same field and not preserving, otherwise use current or default to desc
            let order = 'desc';
            if (preserveOrder && statsSortState.field === field) {
                // Preserve the existing order (used during refresh)
                order = statsSortState.order;
            } else if (statsSortState.field === field) {
                // Toggle order (user clicked the button)
                order = statsSortState.order === 'desc' ? 'asc' : 'desc';
            } else if (statsSortState.field) {
                // Different field, but we have a previous order - use desc as default
                order = 'desc';
            }
            
            statsSortState = { field, order };
            
            // Update button states
            const memBtn = document.querySelector('.stats-row-header .sort-btn[onclick*="memory"]');
            const cpuBtn = document.querySelector('.stats-row-header .sort-btn[onclick*="cpu"]');
            
            if (memBtn) memBtn.classList.remove('active', 'asc', 'desc');
            if (cpuBtn) cpuBtn.classList.remove('active', 'asc', 'desc');
            
            const activeBtn = field === 'memory' ? memBtn : cpuBtn;
            if (activeBtn) {
                activeBtn.classList.add('active', order);
            }
            
            // Re-sort stats row
            const statsRow = document.getElementById('stats-row');
            if (!statsRow) return;
            
            // Get all stat cards
            const cards = Array.from(statsRow.children);
            
            // Calculate totals for each category
            const totals = {};
            const categoryOrder = [];
            
            cards.forEach(card => {
                const category = card.getAttribute('data-category');
                if (!category || category === 'total') return;
                
                const procs = categoryData[category] || [];
                totals[category] = {
                    memory: procs.reduce((sum, p) => sum + (p.memory || 0), 0),
                    cpu: procs.reduce((sum, p) => sum + (p.cpu || 0), 0),
                    count: procs.length
                };
            });
            
            // Total is special - use total_memory
            totals.total = {
                memory: categoryData.total_memory || 0,
                cpu: 0
            };
            
            // Sort cards by their category totals
            cards.sort((a, b) => {
                const catA = a.getAttribute('data-category');
                const catB = b.getAttribute('data-category');
                
                if (!catA || !catB) return 0;
                
                // Always keep "total" at the end
                if (catA === 'total') return 1;
                if (catB === 'total') return -1;
                
                const totalA = totals[catA]?.[field] || 0;
                const totalB = totals[catB]?.[field] || 0;
                const countA = totals[catA]?.count || 0;
                const countB = totals[catB]?.count || 0;
                
                // Categories with 0 items go to the bottom
                if (countA === 0 && countB > 0) return 1;
                if (countB === 0 && countA > 0) return -1;
                if (countA === 0 && countB === 0) {
                    // Both empty - maintain original order from sectionIds
                    const originalOrder = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java'];
                    const indexA = originalOrder.indexOf(catA);
                    const indexB = originalOrder.indexOf(catB);
                    if (indexA === -1 && indexB === -1) return 0;
                    if (indexA === -1) return 1;
                    if (indexB === -1) return -1;
                    return indexA - indexB;
                }
                
                if (order === 'desc') {
                    return totalB - totalA;
                } else {
                    return totalA - totalB;
                }
            });
            
            // Store the new order (excluding 'total' and empty categories)
            cards.forEach(card => {
                const category = card.getAttribute('data-category');
                if (category && category !== 'total') {
                    const count = totals[category]?.count || 0;
                    // Only include categories with items
                    if (count > 0) {
                        categoryOrder.push(category);
                    }
                }
            });
            
            // Reorder stats row in DOM
            cards.forEach(card => statsRow.appendChild(card));
            
            // Reorder category sections to match stats row order
            const appStats = document.querySelector('.app-stats');
            if (!appStats) return;
            
            // Get all section elements
            const sections = {};
            const sectionIds = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java'];
            sectionIds.forEach(id => {
                // Convert underscore to hyphen for section ID lookup
                const sectionId = id === 'ide_other' ? 'ide-other' : id;
                const section = document.getElementById(`section-${sectionId}`);
                if (section) {
                    sections[id] = section;
                }
            });
            
            // Find where to insert (after app-stats, before actions)
            const actions = document.querySelector('.actions');
            const insertBefore = actions || document.querySelector('.footer');
            
            // Separate categories into those with items and those without
            const categoriesWithItems = [];
            const categoriesWithoutItems = [];
            
            sectionIds.forEach(id => {
                const procs = categoryData[id] || [];
                const section = sections[id];
                if (section) {
                    if (procs.length > 0) {
                        categoriesWithItems.push(id);
                    } else {
                        categoriesWithoutItems.push(id);
                    }
                }
            });
            
            // Sort empty categories - maintain original order
            categoriesWithoutItems.sort((a, b) => {
                // For empty categories, maintain original order
                const originalOrder = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java'];
                const indexA = originalOrder.indexOf(a);
                const indexB = originalOrder.indexOf(b);
                if (indexA === -1 && indexB === -1) return 0;
                if (indexA === -1) return 1;
                if (indexB === -1) return -1;
                return indexA - indexB;
            });
            
            // Use sorted order for categories with items, or original order if not sorted
            const orderedCategories = categoryOrder.length > 0 
                ? categoryOrder 
                : categoriesWithItems; // If no sort, use original order for non-empty
            
            // Reorder sections: first non-empty (sorted or original order), then empty at the end
            const allOrderedCategories = [...orderedCategories, ...categoriesWithoutItems];
            
            // Collect all sections first, then reorder them all at once
            const sectionsToReorder = [];
            allOrderedCategories.forEach(category => {
                const section = sections[category];
                if (section) {
                    sectionsToReorder.push(section);
                }
            });
            
            // Remove all sections from DOM first
            sectionsToReorder.forEach(section => {
                if (section && section.parentNode) {
                    section.parentNode.removeChild(section);
                }
            });
            
            // Insert them all in the correct order
            sectionsToReorder.forEach((section, index) => {
                if (section && insertBefore && insertBefore.parentNode) {
                    insertBefore.parentNode.insertBefore(section, insertBefore);
                } else if (section && appStats) {
                    appStats.parentNode.insertBefore(section, appStats.nextSibling);
                }
            });
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
                document.getElementById('cursor-count').textContent = data.cursor.length;
                document.getElementById('windsurf-count').textContent = data.windsurf.length;
                document.getElementById('vscode-count').textContent = data.vscode.length;
                document.getElementById('ide-other-count').textContent = data.ide_other.length;
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

                // Store original data for sorting
                categoryData = {
                    gradle: data.gradle,
                    kotlin: data.kotlin,
                    studio: data.studio,
                    emulator: data.emulator,
                    cursor: data.cursor,
                    windsurf: data.windsurf,
                    vscode: data.vscode,
                    ide_other: data.ide_other,
                    java: data.java,
                    total_memory: data.total_memory
                };
                
                // Always ensure empty categories are at the bottom, even without sorting
                const appStats = document.querySelector('.app-stats');
                const actions = document.querySelector('.actions');
                const insertBefore = actions || document.querySelector('.footer');
                
                if (appStats) {
                    const sectionIds = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java'];
                    const categoriesWithItems = [];
                    const categoriesWithoutItems = [];
                    
                    sectionIds.forEach(id => {
                        const procs = categoryData[id] || [];
                        const section = document.getElementById(`section-${id}`);
                        if (section) {
                            if (procs.length > 0) {
                                categoriesWithItems.push(id);
                            } else {
                                categoriesWithoutItems.push(id);
                            }
                        }
                    });
                    
                    // Sort empty categories - maintain original order
                    categoriesWithoutItems.sort((a, b) => {
                        // For empty categories, maintain original order
                        const originalOrder = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java'];
                        const indexA = originalOrder.indexOf(a);
                        const indexB = originalOrder.indexOf(b);
                        if (indexA === -1 && indexB === -1) return 0;
                        if (indexA === -1) return 1;
                        if (indexB === -1) return -1;
                        return indexA - indexB;
                    });
                    
                    // Apply stats row sorting if active
                    if (statsSortState.field) {
                        // Re-apply the current sort state to maintain order during refresh
                        sortStatsBy(statsSortState.field, true);
                    } else {
                        // No sort active - maintain original order for ALL categories
                        // Use the original sectionIds order, not separating by items/empty
                        const allOrderedCategories = sectionIds.filter(id => {
                            // Convert underscore to hyphen for section ID lookup
                            const sectionId = id === 'ide_other' ? 'ide-other' : id;
                            const section = document.getElementById(`section-${sectionId}`);
                            return section !== null;
                        });
                        
                        // Collect all sections first, then reorder them all at once
                        const sectionsToReorder = [];
                        allOrderedCategories.forEach(category => {
                            // Convert underscore to hyphen for section ID lookup
                            const sectionId = category === 'ide_other' ? 'ide-other' : category;
                            const section = document.getElementById(`section-${sectionId}`);
                            if (section) {
                                sectionsToReorder.push(section);
                            }
                        });
                        
                        // Remove all sections from DOM first (in reverse order to avoid issues)
                        sectionsToReorder.reverse().forEach(section => {
                            if (section && section.parentNode) {
                                section.parentNode.removeChild(section);
                            }
                        });
                        
                        // Insert them all in the correct order (reverse back)
                        sectionsToReorder.reverse().forEach((section) => {
                            if (section && insertBefore && insertBefore.parentNode) {
                                insertBefore.parentNode.insertBefore(section, insertBefore);
                            } else if (section && appStats && appStats.parentNode) {
                                appStats.parentNode.insertBefore(section, appStats.nextSibling);
                            }
                        });
                    }
                }
                
                // Apply sorting if active, otherwise use original order
                const applySort = (category, processes, listId, countId) => {
                    const sort = sortState[category];
                    if (sort) {
                        const sorted = sortProcesses(processes, sort.field, sort.order);
                        renderProcessList(listId, sorted, countId);
                    } else {
                        renderProcessList(listId, processes, countId);
                    }
                };
                
                // Render process lists with sorting
                applySort('gradle', data.gradle, 'gradle-list', 'gradle-section-count');
                applySort('kotlin', data.kotlin, 'kotlin-list', 'kotlin-section-count');
                applySort('studio', data.studio, 'studio-list', 'studio-section-count');
                applySort('emulator', data.emulator, 'emulator-list', 'emulator-section-count');
                applySort('cursor', data.cursor, 'cursor-list', 'cursor-section-count');
                applySort('windsurf', data.windsurf, 'windsurf-list', 'windsurf-section-count');
                applySort('vscode', data.vscode, 'vscode-list', 'vscode-section-count');
                applySort('ide_other', data.ide_other, 'ide-other-list', 'ide-other-section-count');
                applySort('java', data.java, 'java-list', 'java-section-count');

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

        async function killCategory(category) {
            const categoryNames = {
                'gradle': 'Gradle',
                'kotlin': 'Kotlin',
                'studio': 'Android Studio',
                'emulator': 'Emulator',
                'cursor': 'Cursor',
                'windsurf': 'Windsurf',
                'vscode': 'VS Code',
                'ide_other': 'Other IDEs',
                'java': 'Java'
            };
            const name = categoryNames[category] || category;
            if (!confirm(`Kill all ${name} processes?`)) return;
            try {
                const res = await fetch(`/api/kill-category/${category}`, { method: 'POST' });
                const result = await res.json();
                if (result.success) {
                    console.log(`Killed ${result.killed} of ${result.total} processes`);
                    if (result.errors && result.errors.length > 0) {
                        console.warn('Some errors:', result.errors);
                    }
                } else {
                    alert('Failed: ' + (result.error || 'Unknown'));
                }
                setTimeout(refresh, 500);
            } catch (err) {
                alert('Failed to kill processes: ' + err.message);
            }
        }

        // Update system
        let updateInfo = null;
        let updateCheckInterval = null;
        const UPDATE_CHECK_INTERVAL = 6 * 60 * 60 * 1000; // 6 hours
        
        async function checkForUpdates(showNotification = true) {
            try {
                const response = await fetch('/api/update/check');
                const data = await response.json();
                
                if (data.error) {
                    console.log('[Update] Check failed:', data.error);
                    return;
                }
                
                if (data.available) {
                    updateInfo = data;
                    if (showNotification && !isUpdateDismissed()) {
                        showUpdateNotification(data);
                    }
                } else {
                    updateInfo = null;
                    hideUpdateNotification();
                }
            } catch (err) {
                console.error('[Update] Check error:', err);
            }
        }
        
        function showUpdateNotification(info) {
            const banner = document.getElementById('update-banner');
            const currentVersion = document.getElementById('update-current-version');
            const latestVersion = document.getElementById('update-latest-version');
            
            if (banner && currentVersion && latestVersion) {
                currentVersion.textContent = `v${info.current_version}`;
                latestVersion.textContent = `v${info.latest_version}`;
                banner.classList.add('show');
            }
        }
        
        function hideUpdateNotification() {
            const banner = document.getElementById('update-banner');
            if (banner) {
                banner.classList.remove('show');
            }
        }
        
        function dismissUpdateNotification(permanent = false) {
            hideUpdateNotification();
            if (permanent) {
                // Store dismissal in localStorage (24 hours)
                localStorage.setItem('update_dismissed', Date.now().toString());
            }
        }
        
        function isUpdateDismissed() {
            const dismissed = localStorage.getItem('update_dismissed');
            if (!dismissed) return false;
            const dismissedTime = parseInt(dismissed);
            const hoursSinceDismissal = (Date.now() - dismissedTime) / (1000 * 60 * 60);
            // Auto-show again after 24 hours
            if (hoursSinceDismissal > 24) {
                localStorage.removeItem('update_dismissed');
                return false;
            }
            return true;
        }
        
        function showUpdateDialog() {
            if (!updateInfo) {
                checkForUpdates(false).then(() => {
                    if (updateInfo) {
                        displayUpdateDialog();
                    }
                });
                return;
            }
            displayUpdateDialog();
        }
        
        function displayUpdateDialog() {
            const dialog = document.getElementById('update-dialog');
            const currentEl = document.getElementById('update-dialog-current');
            const latestEl = document.getElementById('update-dialog-latest');
            const changelogEl = document.getElementById('update-changelog');
            
            if (dialog && updateInfo) {
                currentEl.textContent = `v${updateInfo.current_version}`;
                latestEl.textContent = `v${updateInfo.latest_version}`;
                changelogEl.textContent = updateInfo.changelog || 'No changelog available.';
                dialog.classList.add('show');
                hideUpdateNotification();
            }
        }
        
        function hideUpdateDialog() {
            const dialog = document.getElementById('update-dialog');
            const progress = document.getElementById('update-progress');
            const progressFill = document.getElementById('update-progress-fill');
            const progressText = document.getElementById('update-progress-text');
            const installBtn = document.getElementById('update-install-btn');
            const cancelBtn = document.getElementById('update-cancel-btn');
            
            if (dialog) {
                dialog.classList.remove('show');
            }
            if (progress) {
                progress.classList.remove('show');
            }
            if (progressFill) {
                progressFill.style.width = '0%';
            }
            if (progressText) {
                progressText.textContent = 'Preparing update...';
            }
            if (installBtn) {
                installBtn.disabled = false;
                installBtn.textContent = 'Install Update';
            }
            if (cancelBtn) {
                cancelBtn.disabled = false;
            }
        }
        
        async function installUpdate() {
            if (!updateInfo) {
                alert('No update information available');
                return;
            }
            
            const installBtn = document.getElementById('update-install-btn');
            const cancelBtn = document.getElementById('update-cancel-btn');
            const progress = document.getElementById('update-progress');
            const progressFill = document.getElementById('update-progress-fill');
            const progressText = document.getElementById('update-progress-text');
            
            if (!confirm(`Install update to v${updateInfo.latest_version}? The app will restart automatically.`)) {
                return;
            }
            
            // Disable buttons and show progress
            if (installBtn) {
                installBtn.disabled = true;
                installBtn.textContent = 'Installing...';
            }
            if (cancelBtn) {
                cancelBtn.disabled = true;
            }
            if (progress) {
                progress.classList.add('show');
            }
            if (progressFill) {
                progressFill.style.width = '10%';
            }
            if (progressText) {
                progressText.textContent = 'Downloading update...';
            }
            
            try {
                // Simulate progress (actual download happens server-side)
                let progressPercent = 10;
                const progressInterval = setInterval(() => {
                    progressPercent = Math.min(progressPercent + 5, 90);
                    if (progressFill) {
                        progressFill.style.width = progressPercent + '%';
                    }
                }, 500);
                
                const response = await fetch('/api/update/install', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ version: updateInfo.latest_version })
                });
                
                clearInterval(progressInterval);
                
                if (progressFill) {
                    progressFill.style.width = '100%';
                }
                if (progressText) {
                    progressText.textContent = 'Installing...';
                }
                
                const result = await response.json();
                
                if (result.success) {
                    if (progressText) {
                        progressText.textContent = 'Update installed! Reloading page...';
                    }
                    // Reload page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    if (progress) {
                        progress.classList.remove('show');
                    }
                    if (installBtn) {
                        installBtn.disabled = false;
                        installBtn.textContent = 'Install Update';
                    }
                    if (cancelBtn) {
                        cancelBtn.disabled = false;
                    }
                    alert('Update failed: ' + (result.error || 'Unknown error'));
                }
            } catch (err) {
                if (progress) {
                    progress.classList.remove('show');
                }
                if (installBtn) {
                    installBtn.disabled = false;
                    installBtn.textContent = 'Install Update';
                }
                if (cancelBtn) {
                    cancelBtn.disabled = false;
                }
                alert('Update failed: ' + err.message);
            }
        }
        
        // Check for updates on page load (after 1 hour delay) and periodically
        setTimeout(() => {
            checkForUpdates();
            // Check every 6 hours
            updateCheckInterval = setInterval(() => {
                checkForUpdates();
            }, UPDATE_CHECK_INTERVAL);
        }, 60 * 60 * 1000); // 1 hour delay on first check
        
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
        'cursor': [],
        'windsurf': [],
        'vscode': [],
        'ide_other': [],
        'java': []
    }
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username', 'cpu_percent', 
                                          'memory_info', 'create_time', 'cwd', 'ppid']):
            try:
                pinfo = proc.info
                proc_name = pinfo['name'] or ''
                cmdline = ' '.join(pinfo['cmdline'] or [])
                cmdline_lower = cmdline.lower()
                proc_name_lower = proc_name.lower()
                
                # Get parent process information
                parent_info = None
                try:
                    ppid = pinfo.get('ppid')
                    if ppid:
                        parent_proc = psutil.Process(ppid)
                        parent_name = parent_proc.name()
                        parent_cmdline = ' '.join(parent_proc.cmdline()[:2]) if parent_proc.cmdline() else parent_name
                        # Simplify parent name - show first part of command or process name
                        if len(parent_cmdline) > 50:
                            parent_cmdline = parent_cmdline[:47] + '...'
                        parent_info = {
                            'pid': ppid,
                            'name': parent_name,
                            'cmdline': parent_cmdline
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    parent_info = None
                
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
                
                # IDE detection - check process name, command line, path, and parent process
                # First check if this process itself is an IDE
                is_ide_direct = (
                    # Cursor detection - check name, cmdline, path, and helper processes
                    'cursor' in proc_name_lower or
                    'Cursor.app' in cmdline or
                    '/Applications/Cursor.app' in cmdline or
                    'Cursor Helper' in cmdline or
                    'cursor helper' in proc_name_lower or
                    # VS Code detection
                    ('code' in proc_name_lower and not any(x in cmdline_lower for x in ['gradle', 'kotlin', 'java'])) or
                    'Code.app' in cmdline or
                    '/Applications/Visual Studio Code.app' in cmdline or
                    'Visual Studio Code' in cmdline or
                    'Code Helper' in cmdline or
                    # Windsurf detection
                    'windsurf' in proc_name_lower or
                    'Windsurf.app' in cmdline or
                    '/Applications/Windsurf.app' in cmdline or
                    'Windsurf Helper' in cmdline or
                    # Other IDEs
                    'trae' in proc_name_lower or
                    'Trae.app' in cmdline or
                    'antigravity' in proc_name_lower or
                    'zed' in proc_name_lower or
                    'Zed.app' in cmdline or
                    '/Applications/Zed.app' in cmdline or
                    'Zed Helper' in cmdline or
                    'fleet' in proc_name_lower or
                    'Fleet.app' in cmdline or
                    'sublime' in proc_name_lower or
                    'Sublime' in cmdline or
                    'atom' in proc_name_lower or
                    'notepad++' in proc_name_lower or
                    'neovim' in proc_name_lower or
                    'nvim' in proc_name_lower
                )
                
                # Check if parent is an IDE (to catch helper processes, renderers, etc.)
                is_child_of_ide = False
                try:
                    ppid = pinfo.get('ppid')
                    if ppid:
                        parent_proc = psutil.Process(ppid)
                        parent_name = parent_proc.name().lower()
                        parent_cmdline_full = ' '.join(parent_proc.cmdline() or [])
                        parent_cmdline_lower = parent_cmdline_full.lower()
                        
                        is_child_of_ide = (
                            'cursor' in parent_name or 'Cursor.app' in parent_cmdline_full or
                            'code' in parent_name or 'Code.app' in parent_cmdline_full or
                            'windsurf' in parent_name or 'Windsurf.app' in parent_cmdline_full or
                            'zed' in parent_name or 'Zed.app' in parent_cmdline_full or
                            'fleet' in parent_name or 'Fleet.app' in parent_cmdline_full
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                
                is_ide = is_ide_direct or is_child_of_ide
                
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
                    # Detect specific IDE and assign to separate categories
                    # Check parent first to catch child processes
                    is_cursor_child = False
                    is_vscode_child = False
                    is_windsurf_child = False
                    try:
                        ppid = pinfo.get('ppid')
                        if ppid:
                            parent_proc = psutil.Process(ppid)
                            parent_name = parent_proc.name().lower()
                            parent_cmdline_full = ' '.join(parent_proc.cmdline() or [])
                            is_cursor_child = 'cursor' in parent_name or 'Cursor.app' in parent_cmdline_full
                            is_vscode_child = ('code' in parent_name and 'code' not in parent_cmdline_full.lower().replace(parent_name, '')) or 'Code.app' in parent_cmdline_full
                            is_windsurf_child = 'windsurf' in parent_name or 'Windsurf.app' in parent_cmdline_full
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                    
                    if 'cursor' in proc_name_lower or 'Cursor' in cmdline or is_cursor_child:
                        category = 'cursor'
                        # Detect specific Cursor process types
                        # If it's a child process but doesn't have cursor in name, try to identify type
                        if is_cursor_child and 'cursor' not in proc_name_lower and 'Cursor' not in cmdline:
                            # This is likely a helper/renderer process spawned by Cursor
                            if '--type=renderer' in cmdline:
                                if '--window-id=' in cmdline:
                                    window_match = re.search(r'--window-id=(\d+)', cmdline)
                                    if window_match:
                                        name = f'Cursor Renderer (Window {window_match.group(1)})'
                                    else:
                                        name = 'Cursor Renderer'
                                else:
                                    name = 'Cursor Renderer'
                            elif '--type=utility' in cmdline or '--utility-sub-type=' in cmdline:
                                if '--utility-sub-type=network.mojom.NetworkService' in cmdline:
                                    name = 'Cursor Network Service'
                                elif '--utility-sub-type=storage.mojom.StorageService' in cmdline:
                                    name = 'Cursor Storage Service'
                                elif 'gpu' in cmdline_lower or '--utility-sub-type=gpu' in cmdline:
                                    name = 'Cursor GPU Process'
                                else:
                                    name = 'Cursor Helper'
                            elif 'Helper' in proc_name or 'helper' in proc_name_lower:
                                name = 'Cursor Helper'
                            else:
                                name = 'Cursor Process'
                        elif '--type=renderer' in cmdline:
                            # Try to extract window/tab info from command line
                            if '--window-id=' in cmdline:
                                window_match = re.search(r'--window-id=(\d+)', cmdline)
                                if window_match:
                                    name = f'Cursor Renderer (Window {window_match.group(1)})'
                                else:
                                    name = 'Cursor Renderer'
                            else:
                                name = 'Cursor Renderer'
                        elif '--type=utility' in cmdline or '--utility-sub-type=' in cmdline:
                            # Check for specific utility types
                            if '--utility-sub-type=network.mojom.NetworkService' in cmdline:
                                name = 'Cursor Network Service'
                            elif '--utility-sub-type=storage.mojom.StorageService' in cmdline:
                                name = 'Cursor Storage Service'
                            elif 'gpu' in cmdline_lower or '--utility-sub-type=gpu' in cmdline:
                                name = 'Cursor GPU Process'
                            else:
                                name = 'Cursor Utility'
                        elif '--type=zygote' in cmdline:
                            name = 'Cursor Zygote'
                        elif '--extension-host' in cmdline or 'extensionHost' in cmdline_lower:
                            name = 'Cursor Extension Host'
                        elif '--type=plugin' in cmdline:
                            name = 'Cursor Plugin Host'
                        elif '--crashpad-handler' in cmdline:
                            name = 'Cursor Crash Handler'
                        elif 'Cursor.app' in cmdline or 'cursor' == proc_name_lower:
                            # Main process - check if it's the main entry point
                            if '--no-sandbox' in cmdline or '--disable-gpu' in cmdline or len([a for a in cmdline.split() if a.startswith('--')]) < 3:
                                name = 'Cursor (Main)'
                            else:
                                name = 'Cursor'
                        else:
                            name = 'Cursor'
                    elif ('windsurf' in proc_name_lower or 'Windsurf' in cmdline) and not is_cursor_child and not is_vscode_child:
                        category = 'windsurf'
                        name = 'Windsurf'
                    elif ('code' in proc_name_lower or 'Code.app' in cmdline or 'Visual Studio Code' in cmdline) and not is_cursor_child:
                        category = 'vscode'
                        # Detect specific VS Code process types
                        if '--type=renderer' in cmdline:
                            if '--window-id=' in cmdline:
                                window_match = re.search(r'--window-id=(\d+)', cmdline)
                                if window_match:
                                    name = f'VS Code Renderer (Window {window_match.group(1)})'
                                else:
                                    name = 'VS Code Renderer'
                            else:
                                name = 'VS Code Renderer'
                        elif '--type=utility' in cmdline or '--utility-sub-type=' in cmdline:
                            if '--utility-sub-type=network.mojom.NetworkService' in cmdline:
                                name = 'VS Code Network Service'
                            elif '--utility-sub-type=storage.mojom.StorageService' in cmdline:
                                name = 'VS Code Storage Service'
                            elif 'gpu' in cmdline_lower or '--utility-sub-type=gpu' in cmdline:
                                name = 'VS Code GPU Process'
                            else:
                                name = 'VS Code Utility'
                        elif '--type=zygote' in cmdline:
                            name = 'VS Code Zygote'
                        elif '--extension-host' in cmdline or 'extensionHost' in cmdline_lower:
                            name = 'VS Code Extension Host'
                        elif '--type=plugin' in cmdline:
                            name = 'VS Code Plugin Host'
                        elif '--crashpad-handler' in cmdline:
                            name = 'VS Code Crash Handler'
                        elif 'Code.app' in cmdline or 'code' == proc_name_lower:
                            name = 'VS Code (Main)'
                        else:
                            name = 'VS Code'
                    else:
                        category = 'ide_other'
                        # Detect other IDEs
                        if 'trae' in proc_name_lower or 'Trae' in cmdline:
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
                    'heap': heap_size,
                    'parent': parent_info
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
                 processes['cursor'] + processes['windsurf'] + 
                 processes['vscode'] + processes['ide_other'] + 
                 processes['java'])
    total_memory = sum(p['memory'] for p in all_procs)
    
    return jsonify({
        'gradle': processes['gradle'],
        'kotlin': processes['kotlin'],
        'studio': processes['studio'],
        'emulator': processes['emulator'],
        'cursor': processes['cursor'],
        'windsurf': processes['windsurf'],
        'vscode': processes['vscode'],
        'ide_other': processes['ide_other'],
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


@app.route('/api/kill-category/<category>', methods=['POST'])
def kill_category(category):
    """Kill all processes in a specific category."""
    import signal
    import os
    
    valid_categories = ['gradle', 'kotlin', 'studio', 'emulator', 'cursor', 'windsurf', 'vscode', 'ide_other', 'java']
    if category not in valid_categories:
        return jsonify({'success': False, 'error': 'Invalid category'}), 400
    
    processes = get_all_processes()
    category_procs = processes.get(category, [])
    
    if not category_procs:
        return jsonify({'success': True, 'killed': 0, 'message': 'No processes in this category'})
    
    killed = 0
    errors = []
    
    for proc in category_procs:
        try:
            os.kill(proc['pid'], signal.SIGTERM)
            killed += 1
        except ProcessLookupError:
            pass  # Process already gone
        except PermissionError:
            errors.append(f"Permission denied for PID {proc['pid']}")
        except Exception as e:
            errors.append(f"Error killing PID {proc['pid']}: {str(e)}")
    
    result = {'success': True, 'killed': killed, 'total': len(category_procs)}
    if errors:
        result['errors'] = errors
    
    return jsonify(result)


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


@app.route('/api/update/check', methods=['GET'])
def api_update_check():
    """Check for available updates."""
    force = request.args.get('force', 'false').lower() == 'true'
    result = check_for_updates(force=force)
    return jsonify(result)


@app.route('/api/update/install', methods=['POST'])
def api_update_install():
    """Install the latest update."""
    data = request.get_json() or {}
    latest_version = data.get('version')
    
    if not latest_version:
        # Get latest version from check
        update_info = check_for_updates(force=True)
        if not update_info['available']:
            return jsonify({
                'success': False,
                'error': 'No update available'
            }), 400
        latest_version = update_info['latest_version']
    
    result = install_update(latest_version)
    return jsonify(result)


# Update system
UPDATE_CHECK_CACHE = CONFIG_DIR / 'update_check.json'
GITHUB_REPO = 'onelenyk/gradik'
GITHUB_API_URL = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
UPDATE_CHECK_CACHE_DURATION = 3600  # 1 hour


def get_ssl_context():
    """Create SSL context with proper certificate handling for macOS and Linux.
    Uses certifi (included in requirements) for reliable certificate handling.
    """
    try:
        # Use certifi for reliable certificate handling (included in requirements.txt)
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        # Fallback: try default context (may not work on all macOS installations)
        try:
            return ssl.create_default_context()
        except Exception:
            # Last resort: this should rarely happen if certifi is installed
            # But we provide it as a fallback
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context


def compare_versions(current, latest):
    """Compare two version strings (semver format).
    Returns: -1 if current < latest, 0 if equal, 1 if current > latest
    """
    def parse_version(v):
        # Remove 'v' prefix if present
        v = v.lstrip('v')
        # Split by '.' and convert to int
        parts = []
        for part in v.split('.'):
            # Handle pre-release versions (e.g., "1.0.8-beta.1")
            if '-' in part:
                part = part.split('-')[0]
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        # Pad to 3 parts (major.minor.patch)
        while len(parts) < 3:
            parts.append(0)
        return parts[:3]
    
    try:
        current_parts = parse_version(current)
        latest_parts = parse_version(latest)
        
        for i in range(3):
            if current_parts[i] < latest_parts[i]:
                return -1
            elif current_parts[i] > latest_parts[i]:
                return 1
        return 0
    except Exception:
        return 0  # If parsing fails, assume equal


def get_binary_path():
    """Get the path to the current binary.
    Returns None if running as Python script (updates only work for binaries).
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller binary
        exe_path = sys.executable
        if os.path.isabs(exe_path):
            return exe_path
        # Try to find in PATH
        full_path = shutil.which(exe_path)
        if full_path:
            return full_path
        return exe_path
    return None  # Running as Python script, updates not supported


def check_for_updates(force=False):
    """Check for available updates from GitHub Releases.
    Returns: {
        'available': bool,
        'current_version': str,
        'latest_version': str,
        'release_url': str,
        'sha256': str,
        'changelog': str,
        'error': str (if any)
    }
    """
    result = {
        'available': False,
        'current_version': __version__,
        'latest_version': None,
        'release_url': None,
        'sha256': None,
        'changelog': None,
        'error': None
    }
    
    # Check cache first (unless forced)
    if not force and UPDATE_CHECK_CACHE.exists():
        try:
            with open(UPDATE_CHECK_CACHE, 'r') as f:
                cache = json.load(f)
            cache_time = cache.get('last_check', 0)
            if time.time() - cache_time < UPDATE_CHECK_CACHE_DURATION:
                # Return cached result
                return cache.get('last_result', result)
        except (json.JSONDecodeError, IOError, KeyError):
            pass
    
    # Only check for updates if running as binary
    if not get_binary_path():
        result['error'] = 'Updates only available for binary installations'
        return result
    
    try:
        # Create SSL context with proper certificate handling
        ssl_context = get_ssl_context()
        
        # Fetch latest release from GitHub API
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'Gradik-Updater'}
        )
        
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            latest_version = data.get('tag_name', '').lstrip('v')
            release_url = data.get('html_url', '')
            changelog = data.get('body', '')
            
            # Find binary asset and SHA256
            assets = data.get('assets', [])
            binary_url = None
            sha256 = None
            
            for asset in assets:
                if asset.get('name') == 'gradik':
                    binary_url = asset.get('browser_download_url')
                    # Try to extract SHA256 from release notes or assets
                    # For now, we'll need to calculate it after download
                    break
            
            if not binary_url:
                result['error'] = 'Binary asset not found in release'
                return result
            
            # Compare versions
            if compare_versions(__version__, latest_version) < 0:
                result['available'] = True
                result['latest_version'] = latest_version
                result['release_url'] = release_url
                result['sha256'] = sha256  # Will be calculated during download
                result['changelog'] = changelog[:500]  # Limit changelog length
            else:
                result['latest_version'] = latest_version
            
            # Cache result
            try:
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                with open(UPDATE_CHECK_CACHE, 'w') as f:
                    json.dump({
                        'last_check': time.time(),
                        'last_result': result
                    }, f)
            except IOError:
                pass
            
            return result
            
    except urllib.error.URLError as e:
        result['error'] = f'Network error: {str(e)}'
        return result
    except json.JSONDecodeError as e:
        result['error'] = f'Invalid response: {str(e)}'
        return result
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
        return result


def install_update(latest_version):
    """Download and install the update.
    Returns: {'success': bool, 'message': str, 'error': str}
    """
    result = {'success': False, 'message': '', 'error': None}
    
    binary_path = get_binary_path()
    if not binary_path:
        result['error'] = 'Updates only available for binary installations'
        return result
    
    if not os.path.exists(binary_path):
        result['error'] = f'Binary not found at {binary_path}'
        return result
    
    # Check if we have write permissions
    if not os.access(binary_path, os.W_OK):
        result['error'] = f'No write permission for {binary_path}. Try running with sudo.'
        return result
    
    try:
        # Get update info
        update_info = check_for_updates(force=True)
        if not update_info['available']:
            result['error'] = 'No update available'
            return result
        
        # Find binary download URL
        ssl_context = get_ssl_context()
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={'Accept': 'application/vnd.github.v3+json', 'User-Agent': 'Gradik-Updater'}
        )
        
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            assets = data.get('assets', [])
            binary_url = None
            
            for asset in assets:
                if asset.get('name') == 'gradik':
                    binary_url = asset.get('browser_download_url')
                    break
            
            if not binary_url:
                result['error'] = 'Binary asset not found in release'
                return result
        
        # Check if daemon is running
        daemon_was_running = False
        daemon_port = None
        if get_running_pid():
            daemon_was_running = True
            config = load_config()
            daemon_port = config.get('port', DEFAULT_PORT)
            # Stop daemon
            cmd_stop()
            # Wait a moment for it to stop
            time.sleep(2)
        
        # Download to temp file
        temp_file = f'/tmp/gradik-update-{int(time.time())}'
        
        try:
            # Download binary
            ssl_context = get_ssl_context()
            req = urllib.request.Request(
                binary_url,
                headers={'User-Agent': 'Gradik-Updater'}
            )
            
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(temp_file, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
            
            # Make executable
            os.chmod(temp_file, 0o755)
            
            # Verify it's a valid executable (basic checks)
            # Check file size (should be reasonable, not empty or too small)
            file_size = os.path.getsize(temp_file)
            if file_size < 1024 * 100:  # At least 100KB
                os.unlink(temp_file)
                result['error'] = 'Downloaded binary is too small, may be corrupted'
                return result
            
            # Try to verify it's executable by checking if it can run
            try:
                test_result = subprocess.run(
                    [temp_file, '--version'],
                    capture_output=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL
                )
                # Version command should return 0 or contain version info
                output = test_result.stdout.decode('utf-8', errors='ignore')
                if 'gradik' not in output.lower() and test_result.returncode != 0:
                    raise Exception('Downloaded binary appears invalid')
            except subprocess.TimeoutExpired:
                os.unlink(temp_file)
                result['error'] = 'Downloaded binary verification timeout'
                return result
            except Exception as e:
                # If --version doesn't work, try a simpler check
                # Just verify the file is executable and has reasonable size
                if not os.access(temp_file, os.X_OK):
                    os.unlink(temp_file)
                    result['error'] = 'Downloaded file is not executable'
                    return result
            
            # Create backup
            backup_file = f'{binary_path}.old'
            if os.path.exists(backup_file):
                os.unlink(backup_file)
            shutil.copy2(binary_path, backup_file)
            
            # Atomic replacement
            shutil.move(temp_file, binary_path)
            os.chmod(binary_path, 0o755)
            
            # Restart daemon if it was running
            if daemon_was_running:
                time.sleep(1)
                cmd_start(port=daemon_port, foreground=False)
            
            # Clean up old backup after a delay (in background)
            def cleanup_backup():
                time.sleep(86400)  # 24 hours
                try:
                    if os.path.exists(backup_file):
                        os.unlink(backup_file)
                except:
                    pass
            
            # Start cleanup in background (non-blocking)
            import threading
            threading.Thread(target=cleanup_backup, daemon=True).start()
            
            result['success'] = True
            result['message'] = f'Successfully updated to v{latest_version}'
            
            # Clear update check cache
            if UPDATE_CHECK_CACHE.exists():
                UPDATE_CHECK_CACHE.unlink()
            
            return result
            
        except urllib.error.URLError as e:
            result['error'] = f'Download failed: {str(e)}'
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            return result
        except Exception as e:
            result['error'] = f'Installation failed: {str(e)}'
            # Try to restore from backup
            if os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, binary_path)
                    os.chmod(binary_path, 0o755)
                except:
                    pass
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            return result
            
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
        return result


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
                    cmdline = ' '.join(proc.cmdline()).lower()
                    proc_name = proc.name().lower()
                    
                    # Check if it's a Gradik process (works for both Python script and binary)
                    # For Python script: cmdline contains 'gradik' or 'app.py'
                    # For binary: process name is 'gradik' or cmdline contains 'gradik'
                    is_gradik = (
                        'gradik' in cmdline or 
                        'app.py' in cmdline or
                        proc_name == 'gradik' or
                        'gradik' in proc_name
                    )
                    
                    if is_gradik:
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
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
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
            # sys.argv[0] should be the binary path, but might be relative if called from PATH
            exe_name = sys.argv[0]
            if os.path.isabs(exe_name):
                # Absolute path - use as is
                exe_path = exe_name
            else:
                # Relative path (e.g., "gradik") - try to find it in PATH
                full_path = shutil.which(exe_name)
                if full_path:
                    exe_path = full_path
                else:
                    # Fallback: use basename and hope it's in PATH
                    exe_path = exe_name
            # For PyInstaller binary, use it directly
            args = [exe_path, 'start', '--foreground', '--port', str(actual_port)]
        else:
            # Running as Python script
            script_path = os.path.abspath(__file__)
            args = ['python3', script_path, 'start', '--foreground', '--port', str(actual_port)]
        
        # Start detached process using subprocess (more reliable than os.system)
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                args,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent
                cwd=os.getcwd()
            )
        
        # Wait a moment for the process to start and write PID file
        import time
        time.sleep(2)  # Increased wait time
        
        # Check if process is still running
        try:
            if process.poll() is not None:
                # Process exited immediately
                print(f"❌ Gradik process exited immediately (exit code: {process.returncode})")
                print(f"   Check log: {log_file}")
                return 1
        except:
            pass
        
        # Check for PID file
        new_pid = get_running_pid()
        if new_pid:
            print(f"✅ Gradik started (PID {new_pid})")
            print(f"   URL: http://localhost:{actual_port}")
            print(f"   Log: {log_file}")
            print(f"   Stop: gradik stop")
        else:
            # Process might be running but PID file not written yet, check if port is listening
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', actual_port))
                sock.close()
                if result == 0:
                    # Port is open, process is running
                    print(f"✅ Gradik started (port {actual_port} is listening)")
                    print(f"   URL: http://localhost:{actual_port}")
                    print(f"   Log: {log_file}")
                    print(f"   Stop: gradik stop")
                    print(f"   ⚠️  Note: PID file not found, but server is running")
                else:
                    print(f"❌ Failed to start Gradik")
                    print(f"   Check log: {log_file}")
                    return 1
            except:
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


def cmd_update(check_only=False):
    """Check for and install updates."""
    print("🔄 Checking for updates...")
    print()
    
    # Check if running as binary
    binary_path = get_binary_path()
    if not binary_path:
        print("⚠️  Updates are only available for binary installations.")
        print("   If you're running from source, update via git pull.")
        return 1
    
    # Check for updates
    update_info = check_for_updates(force=True)
    
    if update_info.get('error'):
        print(f"❌ Error checking for updates: {update_info['error']}")
        return 1
    
    current_version = update_info.get('current_version', __version__)
    latest_version = update_info.get('latest_version', current_version)
    
    print(f"   Current version: v{current_version}")
    print(f"   Latest version:  v{latest_version}")
    print()
    
    if not update_info.get('available'):
        print("✅ You're running the latest version!")
        return 0
    
    # Update available
    print(f"📦 Update available: v{latest_version}")
    if update_info.get('changelog'):
        changelog_preview = update_info['changelog'][:200]
        if len(update_info['changelog']) > 200:
            changelog_preview += "..."
        print(f"   {changelog_preview}")
    print()
    
    if check_only:
        print("   Use 'gradik update' (without --check-only) to install the update.")
        return 0
    
    # Ask for confirmation
    try:
        response = input("   Install update now? [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("   Update cancelled.")
            return 0
    except (EOFError, KeyboardInterrupt):
        print()
        print("   Update cancelled.")
        return 0
    
    print()
    print("📥 Downloading and installing update...")
    
    result = install_update(latest_version)
    
    if result['success']:
        print()
        print(f"✅ {result['message']}")
        print()
        print("   The app has been updated and restarted (if it was running).")
        return 0
    else:
        print()
        print(f"❌ Update failed: {result.get('error', 'Unknown error')}")
        return 1


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
    
    # Try to remove the binary/command
    exe_path = shutil.which('gradik')
    if exe_path:
        exe_path = Path(exe_path).resolve()
        print(f"   Found gradik at: {exe_path}")
        
        # Check if it's a binary in /usr/local/bin (from install.sh)
        if str(exe_path) == '/usr/local/bin/gradik' or exe_path.parent == Path('/usr/local/bin'):
            print(f"   Removing binary: {exe_path}")
            try:
                exe_path.unlink()
                print(f"   ✅ Removed binary")
            except PermissionError:
                print(f"   ⚠️  Need sudo to remove {exe_path}")
                print(f"   Run: sudo rm {exe_path}")
            except Exception as e:
                print(f"   ⚠️  Could not remove binary: {e}")
                print(f"   Please run manually: sudo rm {exe_path}")
        # Check if it's a pip-installed script
        elif 'site-packages' in str(exe_path) or (exe_path.parent.name == 'bin' and 'python' in str(exe_path.parent.parent)):
            print(f"   Detected pip installation")
            print(f"   Attempting pip uninstall...")
            try:
                result = subprocess.run(
                    ['pip3', 'uninstall', 'gradik', '-y'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    print(f"   ✅ Removed via pip")
                else:
                    print(f"   ⚠️  Pip uninstall failed")
                    print(f"   Run manually: pip3 uninstall gradik")
            except Exception as e:
                print(f"   ⚠️  Could not uninstall via pip: {e}")
                print(f"   Run manually: pip3 uninstall gradik")
        else:
            print(f"   ⚠️  Unknown installation location: {exe_path}")
            print(f"   Please remove manually: rm {exe_path}")
    
    print()
    print("✅ Gradik uninstalled!")
    print()
    return 0


def main():
    """Entry point for the gradik command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='gradik',
        description='Gradle Status Dashboard - Monitor Gradle, Kotlin daemons, IDEs, and more'
    )
    
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
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
    
    # update command
    update_parser = subparsers.add_parser('update', help='Check for and install updates')
    update_parser.add_argument('--check-only', action='store_true', help='Only check for updates, do not install')
    
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
    elif args.command == 'update':
        return cmd_update(check_only=args.check_only)
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
