# Part 2 — Design of Experiments (DOE): Reproducing `ERR_SANDER_STALL`

## 1. Background

From the Part 1 log analysis, we know that about 1 second before every stall, `arm_pressure_kg` spikes well above 5.0 kg (baseline is around 2.0 kg). The pre-stall window also shows:

- Base speed at **0.6 m/s** (normally ~0.2)
- Commanded RPM dropped to **5000** (normally 8000)
- Actual RPM falling fast toward 0

So the question is: which variable(s) actually *cause* the pressure spike? And can we reproduce `ERR_SANDER_STALL` reliably in the lab?

---

## 2. Variables

### Factors we're testing

| # | Variable | How we control it | Values to test |
|---|----------|--------------------|---------------|
| 1 | Base Drive Speed (`base_speed_ms`) | Motion planner param | 0.1, 0.2, 0.3, 0.4, 0.5, **0.6**, 0.7 m/s |
| 2 | Target Sander RPM (`target_rpm`) | Motor controller setpoint | 3000, 4000, **5000**, 6000, 7000, 8000 RPM |
| 3 | Wall Material | Swap panel in test fixture | Smooth drywall, Rough drywall, Plywood |

**Rationale:**
- Faster traverse → sander gets dragged harder → more friction on the arm
- Lower RPM → disc can't clear material well → it "bites" in → drag goes up
- Rougher/harder surface → higher friction coefficient → could amplify the other two

### Held constant

We keep these fixed so they don't confound the results:

| Variable | Fixed at | Why |
|----------|----------|-----|
| Mast height | 1.5 m (mid-range) | Avoids leverage ratio changes |
| Pad grit | 120-grit | Standard field pad |
| Normal force setpoint | Default (controller-managed) | Isolates speed/RPM effects |
| Ambient temp | ~22 °C (lab) | No motor thermal de-rating |
| Power supply | Full charge / bench PSU | No voltage sag |

---

## 3. Test Methodology

### Phase A — OFAT Screening

Quick check to see if any single factor can trigger the stall on its own.

**A1: Speed sweep** (RPM = 8000, smooth drywall)

| Run | Speed (m/s) | RPM | Material | Expected |
|-----|-------------|-----|----------|----------|
| A1-1 | 0.2 | 8000 | Smooth drywall | No stall (baseline) |
| A1-2 | 0.3 | 8000 | Smooth drywall | No stall |
| A1-3 | 0.4 | 8000 | Smooth drywall | No stall |
| A1-4 | 0.5 | 8000 | Smooth drywall | Maybe a warning |
| A1-5 | 0.6 | 8000 | Smooth drywall | Possible stall |
| A1-6 | 0.7 | 8000 | Smooth drywall | Likely stall |

**A2: RPM sweep** (speed = 0.2 m/s, smooth drywall)

| Run | Speed (m/s) | RPM | Material | Expected |
|-----|-------------|-----|----------|----------|
| A2-1 | 0.2 | 8000 | Smooth drywall | No stall (baseline) |
| A2-2 | 0.2 | 6000 | Smooth drywall | No stall |
| A2-3 | 0.2 | 5000 | Smooth drywall | Maybe a warning |
| A2-4 | 0.2 | 4000 | Smooth drywall | Possible stall |
| A2-5 | 0.2 | 3000 | Smooth drywall | Likely stall |

**A3: Material sweep** (speed = 0.2, RPM = 8000)

| Run | Speed (m/s) | RPM | Material | Expected |
|-----|-------------|-----|----------|----------|
| A3-1 | 0.2 | 8000 | Smooth drywall | No stall |
| A3-2 | 0.2 | 8000 | Rough drywall  | Maybe a warning |
| A3-3 | 0.2 | 8000 | Plywood        | Possible stall |

### Phase B — Factorial (Speed × RPM Interaction)

Once OFAT tells us which factors matter most (expecting speed + RPM), we run a full 3×3 grid with 3 reps each = 27 total runs. Wall material fixed to smooth drywall.

| Run | Speed (m/s) | RPM | Reps |
|-----|-------------|-----|------|
| B-1 | 0.2 | 8000 | ×3 |
| B-2 | 0.2 | 5000 | ×3 |
| B-3 | 0.2 | 3000 | ×3 |
| B-4 | 0.4 | 8000 | ×3 |
| B-5 | 0.4 | 5000 | ×3 |
| B-6 | 0.4 | 3000 | ×3 |
| B-7 | 0.6 | 8000 | ×3 |
| B-8 | 0.6 | 5000 | ×3 |
| B-9 | 0.6 | 3000 | ×3 |

3 reps per combo so we can separate real effects from noise (motor warm-up, pad wear, surface inconsistencies all add variability).

### Phase C — Boundary Confirmation

After B-8 (0.6 m/s, 5000 RPM) is confirmed to stall, we bisect around the boundary to find the exact threshold:

- 0.5 m/s @ 5000 RPM
- 0.6 m/s @ 5500 RPM
- 0.55 m/s @ 5000 RPM
- ...and so on until we narrow it down

This gives the engineering team a precise limit to guard against.

---

## 4. Data Collection

For every single run, we record:

1. Full `robot_state_log.csv` at 10 Hz
2. Peak `arm_pressure_kg`
3. `WARNING_HIGH_LOAD` triggered? (Y/N)
4. `ERR_SANDER_STALL` triggered? (Y/N)
5. Time-to-failure (seconds from sanding start to stall, if it happens)
6. Visual inspection notes — swirl mark depth, pad condition after run

---

## 5. Success Criteria

The field bug counts as **reliably reproduced** when ALL of these show up together in one run:

1. `arm_pressure_kg` exceeds 5.0 kg within 1 s before the stall
2. `actual_rpm` decays noticeably (motor bogging down)
3. `ERR_SANDER_STALL` gets logged
4. State goes `SANDING → ERROR → IDLE`
5. UI tablet freezes (unresponsive to touch)
6. Visible swirl mark / gouge on the wall

**Reliability bar:** same parameter combo must trigger the full failure in ≥ 80% of runs (e.g., 8/10 or better). Below that, it's not deterministic enough.

If we get a stall but miss some symptoms (e.g., stall but no UI freeze), that gets documented as a partial reproduction and we'd open a separate investigation for whatever's missing.
