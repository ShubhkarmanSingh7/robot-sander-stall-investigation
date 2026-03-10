# Part 3 — Formal Bug Report

---

## BUG-2026-0042: Sander Motor Stall + UI Freeze at High Speed / Low RPM

| Field | Value |
|-------|-------|
| **Reporter** | Shubhkarman Singh |
| **Date Filed** | 2026-03-07 |
| **Component** | Sander Motor Controller / Arm Pressure Safety / UI Watchdog |
| **Affected Robot(s)** | Unit deployed at Hallway B, Building 12; also confirmed in lab |
| **Firmware / SW Version** | v3.4.1 |

---

### Severity / Priority

**Severity: Critical** — We're seeing physical wall damage (deep gouge/swirl marks), a full UI freeze that needs E-Stop to recover, and arm sag. This is a safety and quality risk.

**Priority: P1 — Immediate** — This robot is on an active site right now. Every failure damages sellable finish work and needs manual E-Stop intervention. Operators are starting to lose trust in the system.

---

### Summary

When the robot traverses at **≥ 0.5 m/s** with sander RPM set to **≤ 5000**, the disc can't clear material fast enough. Arm pressure spikes past 5.0 kg, the motor bogs down and stalls (`ERR_SANDER_STALL`), the arm visibly sags, and the UI tablet goes completely unresponsive. Only the physical E-Stop gets you out of it.

---

### Steps to Reproduce

> Reproduced deterministically in the lab — see `doe_experiment.md` for full DOE.

1. Power on the robot, make sure it has a 120-grit pad.
2. Position it in front of smooth finished drywall at mid-mast height (~1.5 m).
3. Set target sander RPM to **5000**.
4. Start sanding, set base speed to **0.6 m/s**.
5. Watch for ~1–2 seconds after wall contact.

**Result:** Failure sequence starts within about 1 second.

---

### Expected vs. Actual Behavior

**Expected:** Sander spins at ~5000 RPM, arm sits around 2.0 kg pressure, robot moves along smoothly. Operation finishes normally with a uniform surface.

**What actually happens:**

- **t – 1.0 s:** `arm_pressure_kg` starts climbing past 2.5 kg, `actual_rpm` drifts below target
- **t – 0.5 s:** Pressure shoots past 5.0 kg, RPM collapses (4900 → 800), `WARNING_HIGH_LOAD` shows up in logs
- **t = 0:** `ERR_SANDER_STALL` fires, robot goes to `ERROR` state, motor stops, arm sags
- **t + 0.1 s:** UI tablet freezes dead — no touch response. Double-beep alarm.
- **Recovery:** Operator hits the physical E-Stop. Wall has a visible gouge at the stall point.

---

### Root Cause (from DOE results)

This is a **speed × RPM interaction**:

- At 0.6 m/s the sander head gets dragged across the wall faster than it can handle.
- At 5000 RPM (instead of the usual 8000), the disc doesn't have enough cutting speed to clear material smoothly.
- The disc basically "bites" into the wall. Friction load ramps up fast.
- Once arm pressure crosses ~5.0 kg, the motor can't hold RPM any more. RPM collapses to 0 in about half a second → `ERR_SANDER_STALL`.
- The stall event seems to block the main control loop, which then cascades to the UI watchdog timing out → frozen tablet.

**Failure threshold:** `base_speed > 0.5 m/s` AND `target_rpm ≤ 5000` → stall within 1–2 s (≥ 90% reproducible).

---

### Suggested Fixes

These are suggestions for the engineering team based on our analysis:

1. **Parameter guard (software)** — Don't allow `base_speed > 0.5` when `target_rpm < 6000`. If the planner or operator requests this combo, reject it with a clear warning message.

2. **Pressure safety cutoff (firmware)** — If `arm_pressure_kg > 4.0` for more than 0.3 s straight, auto-reduce base speed to 0 and ramp `target_rpm` to max. Catch it before it cascades.

3. **UI watchdog isolation (software)** — The UI really shouldn't freeze because of a motor control error. Whatever's happening with the stall event blocking the UI thread needs to be investigated. These should be decoupled.

---

### Attached Data / Logs

| # | File | What it is |
|---|------|------------|
| 1 | `robot_state_log.csv` | Raw 10 Hz telemetry from the unit that had the field failure |
| 2 | `log_analysis.py` | Analysis script — prints stall counts, pre-stall pressure, correlations |
| 3 | `doe_experiment.md` | DOE methodology, test matrix, reproduction results |
| 4 | Lab telemetry (available on request) | 10 Hz logs from all 27+ lab runs |
| 5 | Wall damage photos | Swirl mark / gouge at stall location on lab test panel |

---

### Environment

- Robot Model: Drywall Sander Unit (production variant)
- Firmware: v3.4.1
- Sanding Pad: 120-grit, standard issue
- Wall Surface: smooth finished drywall (lab), hallway drywall (field)
- Power: fully charged battery (field) / bench PSU (lab)

---

*Filed by Shubh — Deployment & QA Engineer*
