"""
producer.py - Generates fake factory data and writes it to InfluxDB.

Run InfluxDB + Grafana first:
    docker compose up -d

Install the client once:
    pip install -r requirements.txt

Then start the producer:
    python producer.py

It will write a new sample every second to bucket 'factory'. Open
Grafana at http://localhost:3000 (admin/admin) to see the dashboard.

Ink injection system — the ink must stay above TEMP_MIN_FAULT (°C) to
remain fluid. A PID controller drives an electrical resistance heater.
If the heater trips (simulated randomly) and temperature falls below
the fault threshold, a fault flag is written to InfluxDB.
"""

import random
import time
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Connection settings (match docker-compose.yml) -----------------------

URL    = "http://localhost:8086"
TOKEN  = "my-super-secret-token"
ORG    = "lecture"
BUCKET = "factory"
LINE   = "A"

# --- Machine states -------------------------------------------------------

STATES       = ["Productive", "Standby", "Unscheduled Downtime"]
STATE_WEIGHTS = [0.85, 0.10, 0.05]

# --- Thermal / ink-injection parameters -----------------------------------

TEMP_SETPOINT  = 65.0   # °C  — target ink temperature
TEMP_MIN_FAULT = 55.0   # °C  — below this a fault is declared
COOLING_RATE   = 0.30   # °C/s — passive heat loss
HEATER_GAIN    = 0.50   # °C/s — output at 100 % heater power

# PID gains
PID_KP, PID_KI, PID_KD = 10.0, 2.0, 0.5

# Heater-trip probability per second and auto-recovery window
TRIP_PROB     = 0.003   # ≈ one trip every ~5.5 min on average
TRIP_MIN_TICKS = 60
TRIP_MAX_TICKS = 90


# ---------------------------------------------------------------------------
# PID Controller
# ---------------------------------------------------------------------------

class PIDController:
    
    def __init__(self, kp: float, ki: float, kd: float, setpoint: float,
                 out_min: float = 0.0, out_max: float = 100.0,
                 initial_integral: float = 0.0):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.setpoint = setpoint
        self.out_min, self.out_max = out_min, out_max
        self._integral   = initial_integral
        self._prev_error = 0.0

    def compute(self, measured: float, dt: float) -> float:
        error = self.setpoint - measured
        self._integral = max(-100.0, min(100.0, self._integral + error * dt))
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error
        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.out_min, min(self.out_max, output))


# ---------------------------------------------------------------------------

def next_state(current: str) -> str:
    if random.random() < 0.92:
        return current
    return random.choices(STATES, weights=STATE_WEIGHTS)[0]


def main() -> None:
    print(f"Sending data to {URL} (bucket={BUCKET}, line={LINE}). Ctrl+C to stop.")
    client    = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    parts_total = 0
    state       = "Productive"
    t           = 0

    # Thermal state — pre-load integral so heater starts at steady-state output
    # Steady-state output = COOLING_RATE / HEATER_GAIN * 100 = 60 %
    # initial_integral = 60 % / PID_KI = 30 s·°C
    ss_integral  = COOLING_RATE / HEATER_GAIN * 100.0 / PID_KI
    pid          = PIDController(PID_KP, PID_KI, PID_KD, TEMP_SETPOINT,
                                 initial_integral=ss_integral)
    temperature  = TEMP_SETPOINT
    heater_trip_remaining = 0   # ticks left in current heater failure

    try:
        while True:
            dt = 1.0

            # ── Heater trip simulation ────────────────────────────────
            if heater_trip_remaining > 0:
                heater_ok = False
                heater_trip_remaining -= 1
            elif random.random() < TRIP_PROB:
                heater_ok = False
                heater_trip_remaining = random.randint(TRIP_MIN_TICKS, TRIP_MAX_TICKS) - 1
            else:
                heater_ok = True

            # ── PID + temperature model ───────────────────────────────
            heater_output  = pid.compute(temperature, dt)
            effective_gain = HEATER_GAIN if heater_ok else 0.0
            dT = (-COOLING_RATE
                  + effective_gain * (heater_output / 100.0)
                  + random.uniform(-0.05, 0.05))
            temperature = max(-10.0, temperature + dT)

            fault = temperature < TEMP_MIN_FAULT

            # ── Machine state + part counter ──────────────────────────
            state = next_state(state)
            effective_state = "Fault" if fault else state
            if state == "Productive" and not fault and random.random() < 0.6:
                parts_total += 1

            # ── Write to InfluxDB ─────────────────────────────────────
            point = (
                Point("machine")
                .tag("line", LINE)
                .field("temperature",   float(temperature))
                .field("temp_setpoint", float(TEMP_SETPOINT))
                .field("heater_output", float(heater_output))
                .field("heater_ok",     int(heater_ok))
                .field("fault",         int(fault))
                .field("parts_total",   int(parts_total))
                .field("state",         effective_state)
                .time(datetime.now(timezone.utc))
            )
            write_api.write(bucket=BUCKET, record=point)

            status = "FAULT" if fault else ("TRIP" if not heater_ok else "OK  ")
            print(
                f"t={t:5d}  T={temperature:5.2f}°C  SP={TEMP_SETPOINT:.1f}°C"
                f"  Heater={heater_output:5.1f}%  [{status}]"
                f"  parts={parts_total:4d}  state={effective_state}"
            )

            t += 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
