#!/usr/bin/env python3
"""
GitHub CI Auto-Fix 自动化脚本
"""
import os
import sys
import json
import subprocess
import re
from datetime import datetime
from typing import Optional, Dict, List

REPO_OWNER = "daisyfilfi1-lgtm"
REPO_NAME = "AI-Native-IP"
AUTO_MERGE = True
AUTO_FIX = True

def run_gh(args):
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def get_failed_workflows():
    code, stdout, stderr = run_gh([
        "run", "list",
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--limit", "10",
        "--json", "databaseId,name,status,conclusion,headBranch,headSha"
    ])
    
    if code != 0:
        print(f"Error: {stderr}")
        return []
    
    try:
        workflows = json.loads(stdout)
        return [w for w in workflows if w.get("conclusion") == "failure"]
    except:
        return []

def get_workflow_run_id(branch="master"):
    code, stdout, stderr = run_gh([
        "run", "list",
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--branch", branch,
        "--limit", "1",
        "--json", "databaseId"
    ])
    
    try:
        data = json.loads(stdout)
        return data[0]["databaseId"] if data else None
    except:
        return None

def rerun_workflow(run_id):
    code, stdout, stderr = run_gh([
        "run", "rerun", str(run_id),
        "--repo", f"{REPO_OWNER}/{REPO_NAME}"
    ])
    return code == 0

def get_pr_for_branch(branch):
    code, stdout, stderr = run_gh([
        "pr", "list",
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--head", branch,
        "--json", "number,title,state,mergeable"
    ])
    
    try:
        data = json.loads(stdout)
        return data[0] if data else None
    except:
        return None

def merge_pr(pr_number):
    code, stdout, stderr = run_gh([
        "pr", "merge", str(pr_number),
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--admin", "--merge"
    ])
    return code == 0

def analyze_ci_failure(run_id):
    code, stdout, stderr = run_gh([
        "run", "view", str(run_id),
        "--repo", f"{REPO_OWNER}/{REPO_NAME}",
        "--log-failed"
    ])
    
    if code != 0:
        return "Cannot get CI logs"
    
    errors = []
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if 'error' in line.lower() or 'failed' in line.lower():
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            errors.append('\n'.join(lines[start:end]))
    
    return '\n\n'.join(errors[:5])

def attempt_fix(error_summary):
    print(f"Analyzing error: {error_summary[:200]}...")
    print("Auto-fix requires deeper integration")
    print("Consider using Claude Code CLI auto-fix feature")
    return False

def check_and_fix():
    print(f"=== CI Auto-Fix ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    failed = get_failed_workflows()
    
    if not failed:
        print("OK - No failed CI")
        return
    
    print(f"WARNING - Found {len(failed)} failed CI(s)")
    
    for workflow in failed:
        run_id = workflow["databaseId"]
        branch = workflow["headBranch"]
        sha = workflow["headSha"]
        
        print(f"\nProcessing: {branch} ({sha[:7]})")
        
        error_summary = analyze_ci_failure(run_id)
        
        if AUTO_FIX:
            if attempt_fix(error_summary):
                print("Fix applied, rerunning CI")
                rerun_workflow(run_id)
        
        pr = get_pr_for_branch(branch)
        if pr and pr.get("mergeable"):
            if AUTO_MERGE:
                print(f"Merging PR #{pr['number']}")
                merge_pr(pr["number"])

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--rerun", type=str)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    
    if args.rerun:
        if rerun_workflow(args.rerun):
            print(f"OK - Reran workflow {args.rerun}")
        else:
            print(f"ERROR - Failed to rerun")
    
    elif args.watch:
        import time
        print(f"Monitoring CI (interval {args.interval}s)...")
        while True:
            check_and_fix()
            time.sleep(args.interval)
    
    else:
        check_and_fix()

if __name__ == "__main__":
    main()