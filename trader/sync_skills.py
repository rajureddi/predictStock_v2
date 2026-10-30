#!/usr/bin/env python3
"""Syncs updated trader tools to .agents/skills/ and global config skills."""

import os
import shutil

PROJECT = "c:\\Users\\rajub\\Downloads\\marketmind-pro-WINDOWS-FINAL"
LOCAL_SKILLS = os.path.join(PROJECT, ".agents", "skills")
GLOBAL_SKILLS = "C:\\Users\\rajub\\.gemini\\config\\skills"
TRADER_DIR = os.path.join(PROJECT, "trader")

MAP = {
    "trader-entry": ["entry.py"],
    "trader-exit": ["exit.py"],
    "trader-timemachine": ["timemachine.py"],
    "trader-alerts": ["alerts.py"],
    "trader-check": ["check.py"],
    "trader-risk": ["check.py"],
    "trader-budget": ["size.py"],
    "trader-news": ["news.py"],
    "trader-scanner": ["scan.py"],
    "trader-broker": ["ticket.py"],
}

for dest_root in (LOCAL_SKILLS, GLOBAL_SKILLS):
    if not os.path.exists(dest_root):
        continue
    for skill_name, py_files in MAP.items():
        skill_dir = os.path.join(dest_root, skill_name)
        if not os.path.exists(skill_dir):
            continue
        # Copy market.py into each skill dir so it can be imported self-contained
        shutil.copy2(os.path.join(TRADER_DIR, "market.py"), os.path.join(skill_dir, "market.py"))
        for py_file in py_files:
            src_file = os.path.join(TRADER_DIR, py_file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, os.path.join(skill_dir, py_file))
                print(f"Synced {py_file} -> {dest_root}/{skill_name}")

print("Sync completed!")

