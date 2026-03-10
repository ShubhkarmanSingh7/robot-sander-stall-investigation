#!/usr/bin/env python3
"""
Part 1 — Log Analysis & Scripting
Robotics Deployment and QA Assignment

Analyses the robot telemetry CSV (robot_state_log.csv) to:
  1. Count ERR_SANDER_STALL events
  2. Compute average arm_pressure_kg in the 1s window before each stall
  3. Identify variables that correlate with the pressure spike

Author : Shubhkarman Singh
Usage  : python3 log_analysis.py [path_to_csv]
         Defaults to robot_state_log.csv in the same directory.
"""

import csv
import sys
import os


def load_csv(filepath):
    """Load the CSV into a list of dicts with proper types."""
    rows = []
    with open(filepath, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({
                "timestamp":       float(row["timestamp"]),
                "state":           row["state"].strip(),
                "base_speed_ms":   float(row["base_speed_ms"]),
                "target_rpm":      float(row["target_rpm"]),
                "actual_rpm":      float(row["actual_rpm"]),
                "arm_pressure_kg": float(row["arm_pressure_kg"]),
                "error_code":      row["error_code"].strip(),
            })
    return rows


# Requirement 1: Count stall events 
def count_stall_events(rows):
    """Count how many rows have ERR_SANDER_STALL."""
    return sum(1 for r in rows if r["error_code"] == "ERR_SANDER_STALL")

# Requirement 2: Average pressure in the 1s window before each stall
def avg_pressure_before_stalls(rows, window_sec=1.0):
    """
    For each stall event, grab the arm_pressure_kg values from the 1s
    window right before it and compute the average.

    Consecutive stall rows get grouped into one event (we take the first
    timestamp as the event time so we don't double-count).

    Returns list of dicts with stall_timestamp, avg_pressure, sample count.
    """
    # group consecutive stall rows into single events
    stall_times = []
    prev_stall = False
    for r in rows:
        is_stall = r["error_code"] == "ERR_SANDER_STALL"
        if is_stall and not prev_stall:
            stall_times.append(r["timestamp"])
        prev_stall = is_stall

    results = []
    for ts in stall_times:
        t_start = ts - window_sec
        pressures = [
            r["arm_pressure_kg"] for r in rows
            if t_start <= r["timestamp"] < ts
            and r["error_code"] != "ERR_SANDER_STALL"
        ]
        avg = sum(pressures) / len(pressures) if pressures else 0.0
        results.append({
            "stall_timestamp": ts,
            "avg_pressure": round(avg, 3),
            "samples_in_window": len(pressures),
        })
    return results


# Requirement 3: Correlation analysis

def correlate_variables(rows, window_sec=1.0):
    """
    For the pre-stall window, compute min/max/mean of the key numeric
    variables so we can see what's different vs normal operation.
    """
    # same stall grouping logic
    stall_times = []
    prev_stall = False
    for r in rows:
        is_stall = r["error_code"] == "ERR_SANDER_STALL"
        if is_stall and not prev_stall:
            stall_times.append(r["timestamp"])
        prev_stall = is_stall

    summaries = []
    for ts in stall_times:
        t_start = ts - window_sec
        window = [
            r for r in rows
            if t_start <= r["timestamp"] < ts
            and r["error_code"] != "ERR_SANDER_STALL"
        ]
        if not window:
            continue

        def stats(key):
            vals = [r[key] for r in window]
            return {
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "mean": round(sum(vals) / len(vals), 2),
            }

        summaries.append({
            "stall_timestamp": ts,
            "samples": len(window),
            "base_speed_ms": stats("base_speed_ms"),
            "target_rpm": stats("target_rpm"),
            "actual_rpm": stats("actual_rpm"),
            "arm_pressure_kg": stats("arm_pressure_kg"),
        })
    return summaries


def baseline_stats(rows):
    """Stats from normal sanding rows (no warnings, low speed) for comparison."""
    normal = [
        r for r in rows
        if r["state"] == "SANDING"
        and r["error_code"] == "NONE"
        and r["base_speed_ms"] <= 0.3
    ]
    if not normal:
        return {}

    def stats(key):
        vals = [r[key] for r in normal]
        return {
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "mean": round(sum(vals) / len(vals), 2),
        }

    return {
        "samples": len(normal),
        "base_speed_ms": stats("base_speed_ms"),
        "target_rpm": stats("target_rpm"),
        "actual_rpm": stats("actual_rpm"),
        "arm_pressure_kg": stats("arm_pressure_kg"),
    }


# Report output

def print_report(csv_path):
    rows = load_csv(csv_path)

    print("=" * 65)
    print("  ROBOT STATE LOG — ANALYSIS REPORT")
    print("=" * 65)
    print(f"\nLog file: {csv_path}")
    print(f"Rows parsed: {len(rows)}")

    # 1) Stall count
    stall_count = count_stall_events(rows)
    print(f"\n{'─' * 65}")
    print("  Req 1: ERR_SANDER_STALL Count")
    print(f"{'─' * 65}")
    print(f"  Total ERR_SANDER_STALL rows: {stall_count}")

    # 2) Pre-stall pressure
    pre_stall = avg_pressure_before_stalls(rows)
    print(f"\n{'─' * 65}")
    print("  Req 2: Avg Pressure in 1.0s Before Each Stall")
    print(f"{'─' * 65}")
    for ev in pre_stall:
        print(f"  Stall @ t={ev['stall_timestamp']:.1f}s  |  "
              f"Avg pressure = {ev['avg_pressure']:.3f} kg  "
              f"({ev['samples_in_window']} samples)")

    # 3) Correlation
    corr = correlate_variables(rows)
    base = baseline_stats(rows)
    print(f"\n{'─' * 65}")
    print("  Req 3: Pre-Stall vs Baseline Comparison")
    print(f"{'─' * 65}")

    if base:
        print("\n  [Baseline — normal SANDING, no warnings]")
        print(f"    base_speed_ms   : {base['base_speed_ms']}")
        print(f"    target_rpm      : {base['target_rpm']}")
        print(f"    actual_rpm      : {base['actual_rpm']}")
        print(f"    arm_pressure_kg : {base['arm_pressure_kg']}")

    for s in corr:
        print(f"\n  [Pre-stall: t={s['stall_timestamp'] - 1.0:.1f}–{s['stall_timestamp']:.1f}s  "
              f"({s['samples']} samples)]")
        print(f"    base_speed_ms   : {s['base_speed_ms']}")
        print(f"    target_rpm      : {s['target_rpm']}")
        print(f"    actual_rpm      : {s['actual_rpm']}")
        print(f"    arm_pressure_kg : {s['arm_pressure_kg']}")

    # Summary
    print(f"\n{'─' * 65}")
    print("  Summary")
    print(f"{'─' * 65}")
    print("""
  Observations:

  1. BASE SPEED was 0.6 m/s in the pre-stall window — 3x the normal
     0.2 m/s. Faster traverse = more friction on the sander head.

  2. TARGET RPM dropped from 8000 to 5000. Lower RPM means less
     cutting efficiency, so the disc bites into the material instead
     of skimming over it.

  3. ACTUAL RPM collapsed from ~4900 down to ~800 in the second
     before the stall. The motor was clearly being overloaded.

  4. ARM PRESSURE climbed from the normal ~2.0 kg up to 4.8–6.2 kg,
     way outside safe range.

  => The combination of high base speed (>=0.6 m/s) and low RPM
     (<=5000) creates a situation where the sander can't clear
     material fast enough. Friction spikes, arm gets dragged,
     motor stalls.
""")
    print("=" * 65)
    print("  END OF REPORT")
    print("=" * 65)


if __name__ == "__main__":
    default_csv = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "robot_state_log.csv"
    )
    path = sys.argv[1] if len(sys.argv) > 1 else default_csv
    print_report(path)
