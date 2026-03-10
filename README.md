# Robot Deployment & QA — Sander Stall Investigation

Investigation into a recurring `ERR_SANDER_STALL` failure on a robotic drywall sander deployed at construction sites. The motor stalls mid-operation, the arm sags, and the UI tablet freezes — requiring an E-Stop to recover.

## Files

| File | Description |
|------|-------------|
| `robot_state_log.csv` | Raw 10 Hz telemetry from the robot during the failure |
| `log_analysis.py` | Python script that analyses the telemetry (stall count, pre-stall pressure, correlation) |
| `doe_experiment.md` | Design of Experiments — methodology for reproducing the bug in the lab |
| `bug_report.md` | Formal bug report with root cause, severity, and fix suggestions |
| `explanation.md` | Detailed explanation of concepts and reasoning behind each deliverable |

## Running the analysis script

```bash
python3 log_analysis.py                    # uses robot_state_log.csv by default
python3 log_analysis.py path/to/other.csv  # or pass a different CSV
```

No external dependencies — just Python 3 standard library.

## Key Finding

The stall is caused by a **speed × RPM interaction**: when base speed exceeds 0.5 m/s and target RPM is at or below 5000, the sander disc can't clear material fast enough. Friction spikes, the motor bogs down, and everything cascades from there. Reproduced at ≥ 90% reliability in lab testing.

## Author

Shubhkarman Singh
