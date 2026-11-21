"""
hmi.py
======
Tkinter HMI for the ball-pen production line.

Features:
  - Start / Stop controls
  - Production speed at 1/10 of original (STEP_DELAY per stage)
  - Pipeline stage indicator — same workflow as anim.py, station boxes
    light up in the component's colour as work passes through them
  - Live counters: assembled pens and total rejects
  - Rejection log: item, station, and reason for every reject
  - Ink temperature control: PID-controlled electrical heater
    with live gauges and a fault alarm that halts production

Run:
    python hmi.py
"""

from __future__ import annotations

import os
import queue
import random
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from tkinter import ttk

sys.path.insert(0, os.path.dirname(__file__))
from prod import ProductionLine

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG     = "#1a2332"
PANEL  = "#243044"
ACCENT = "#00b4d8"
GREEN  = "#2dc653"
RED    = "#e63946"
AMBER  = "#f4a261"
FG     = "#e0e8f0"
FG_DIM = "#7a8fa8"
HEADER = "#0d1b2a"

COMP_COLORS = {
    "barrel":    "#3498db",
    "tip":       "#9b59b6",
    "cartridge": "#2ecc71",
    "cap":       "#e74c3c",
    "pen":       "#f39c12",
}

# ---------------------------------------------------------------------------
# Pipeline canvas layout  (mirrors anim.py station positions)
# ---------------------------------------------------------------------------
_CW,  _CH    = 650, 168
_BHW, _BHH   = 30,  13

_LANE_Y = {"barrel": 26, "tip": 68, "cartridge": 110, "cap": 152}
_CTR_Y  = 89

_X_MAKE  =  50
_X_QC    = 145
_X_BIN   = 240
_X_ASSM  = 345
_X_FQC   = 435
_X_PACK  = 520
_X_SHIP  = 610

# ---------------------------------------------------------------------------
# Timing  — each stage takes STEP_DELAY seconds, giving ~1/10 original speed
# ---------------------------------------------------------------------------
STEP_DELAY = 0.40

# ---------------------------------------------------------------------------
# Thermal / ink-injection parameters
# ---------------------------------------------------------------------------
TEMP_SETPOINT   = 65.0   # °C  — target ink temperature
TEMP_MIN_FAULT  = 55.0   # °C  — below this a fault is declared
COOLING_RATE    = 0.30   # °C/s — passive heat loss
HEATER_GAIN     = 0.50   # °C/s — gain at 100 % heater output
# Simulated heater hardware failure: begins at tick 60, lasts 120 ticks.
# At 0.30 °C/s cooling, temperature falls from 65 °C to 55 °C in ~33 s,
# so the fault alarm fires roughly 93 seconds after pressing START.
HEATER_FAIL_AT  = 60
HEATER_FAIL_DUR = 120

# ---------------------------------------------------------------------------
# Internal event protocol  (worker threads → UI thread via queue)
# ---------------------------------------------------------------------------
EVT_ASSEMBLED = "assembled"
EVT_REJECTED  = "rejected"
EVT_STAGE     = "stage"
EVT_STATUS    = "status"
EVT_STOPPED   = "stopped"
EVT_TEMP           = "temp"
EVT_FAULT          = "fault"
EVT_RECOVERED      = "recovered"
EVT_HEATER_TRIPPED = "heater_tripped"

# ---------------------------------------------------------------------------
# InfluxDB / Grafana settings  (match docker-compose.yml)
# ---------------------------------------------------------------------------
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "my-super-secret-token"
INFLUX_ORG    = "lecture"
INFLUX_BUCKET = "factory"
INFLUX_LINE   = "A"


# ---------------------------------------------------------------------------
# InfluxDB writer (background thread)
# ---------------------------------------------------------------------------

class InfluxDBWriter(threading.Thread):
    """Forwards HMI data points to InfluxDB in a background thread.

    Uses a bounded queue so a slow or unavailable InfluxDB never blocks
    the UI thread.  If the influxdb-client package is not installed, or
    the server is unreachable, the thread exits silently and the HMI
    continues to work without Grafana integration.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True, name="InfluxDBWriter")
        self._q: queue.Queue = queue.Queue(maxsize=120)   # ~2 min buffer

    # called from UI thread — must never block
    def push(self, data: dict) -> None:
        try:
            self._q.put_nowait(data)
        except queue.Full:
            pass   # drop oldest-not-written point; dashboard will show a gap

    def stop(self) -> None:
        self._q.put(None)   # sentinel

    def run(self) -> None:
        try:
            from influxdb_client import InfluxDBClient, Point
            from influxdb_client.client.write_api import SYNCHRONOUS
            client    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
            write_api = client.write_api(write_options=SYNCHRONOUS)
        except Exception:
            return   # package missing or server unreachable — exit silently

        try:
            while True:
                data = self._q.get()
                if data is None:
                    break
                try:
                    point = (
                        Point("machine")
                        .tag("line", INFLUX_LINE)
                        .field("temperature",   float(data["temperature"]))
                        .field("temp_setpoint", float(TEMP_SETPOINT))
                        .field("heater_output", float(data["heater_output"]))
                        .field("heater_on",     int(data["manual_on"]))
                        .field("fault",         int(data["fault"]))
                        .field("parts_total",   int(data["parts_total"]))
                        .field("rejects",       int(data["rejects"]))
                        .field("state",         data["state"])
                        .time(datetime.now(timezone.utc))
                    )
                    write_api.write(bucket=INFLUX_BUCKET, record=point)
                except Exception:
                    pass   # drop failed write; keep running
        finally:
            try:
                client.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Instrumented production line
# ---------------------------------------------------------------------------

class InstrumentedLine(ProductionLine):
    """ProductionLine that emits stage/counter events and respects a stop flag."""

    def __init__(self, event_queue: queue.Queue, stop_event: threading.Event):
        super().__init__()
        self._q    = event_queue
        self._stop = stop_event

    def _stage(self, key: str, component: str) -> None:
        if not self._stop.is_set():
            self._q.put({"type": EVT_STAGE, "stage": key, "component": component})
            time.sleep(STEP_DELAY)

    def _refill_bins(self) -> None:
        for name in self.COMPONENT_NAMES:
            while not self.bins[name]:
                if self._stop.is_set():
                    return
                self._stage(f"make_{name}", name)
                raw = self.makers[name].process()

                self._stage(f"qc_{name}", name)
                inspected = self.qcs[name].process(raw)

                if inspected is None:
                    self._q.put({
                        "type":    EVT_REJECTED,
                        "item":    f"{name.capitalize()} #{raw.serial}",
                        "station": f"QC – {name}",
                        "reason":  "Defective component",
                    })
                else:
                    self._stage(f"bin_{name}", name)
                    self.bins[name].append(inspected)

    def _assemble_one(self):
        if self._stop.is_set():
            return None

        self._stage("assembly", "pen")
        parts  = {n: self.bins[n].popleft() for n in self.COMPONENT_NAMES}
        pen    = self.assembly.process(parts)

        self._stage("final_qc", "pen")
        pen_ok = self.final_qc.process(pen)
        if pen_ok is None:
            self._q.put({
                "type":    EVT_REJECTED,
                "item":    f"Pen #{pen.serial}",
                "station": "Final QC",
                "reason":  "Assembly defect",
            })
            return None

        self._stage("packaging", "pen")
        result = self.packaging.process(pen_ok)
        self._q.put({"type": EVT_ASSEMBLED, "serial": result.serial})

        self._stage("shipped", "pen")
        return result

    def run_until_stopped(self) -> None:
        self._q.put({"type": EVT_STATUS, "msg": "● Running"})
        while not self._stop.is_set():
            self._refill_bins()
            if self._stop.is_set():
                break
            pen = self._assemble_one()
            if pen is not None:
                self.shipped.append(pen)
        self._q.put({
            "type": EVT_STATUS,
            "msg":  f"■ Stopped  —  {len(self.shipped)} pens shipped",
        })
        self._q.put({"type": EVT_STOPPED})


# ---------------------------------------------------------------------------
# PID Controller
# ---------------------------------------------------------------------------

class PIDController:
    """Discrete PID with anti-windup integral clamping."""

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
# Thermal Controller thread
# ---------------------------------------------------------------------------

class ThermalController(threading.Thread):
    """Simulates ink temperature with a PID-controlled electrical heater.

    Posts EVT_TEMP each second and a single EVT_FAULT when temperature
    drops below TEMP_MIN_FAULT.  Uses HEATER_FAIL_AT / HEATER_FAIL_DUR to
    simulate a hardware trip that the PID cannot compensate.
    """

    # Pre-load integral so the PID outputs the steady-state value from tick 1:
    # steady-state output = COOLING_RATE / HEATER_GAIN * 100 = 60 %
    # integral_0 = 60 % / Ki(2.0) = 30 s·°C
    _SS_INTEGRAL = COOLING_RATE / HEATER_GAIN * 100.0 / 2.0   # 30.0

    def __init__(self, event_queue: queue.Queue, thermal_stop: threading.Event,
                 heater_enabled: threading.Event):
        super().__init__(daemon=True)
        self._q               = event_queue
        self._stop            = thermal_stop
        self._heater_enabled  = heater_enabled
        self._pid  = PIDController(
            kp=10.0, ki=2.0, kd=0.5,
            setpoint=TEMP_SETPOINT,
            initial_integral=self._SS_INTEGRAL,
        )
        self.temperature   = TEMP_SETPOINT
        self.heater_output = COOLING_RATE / HEATER_GAIN * 100.0  # 60 %
        self._fault      = False
        self._tick       = 0
        self._hw_tripped = False   # tracks whether the auto-trip has fired

    def run(self) -> None:
        while not self._stop.is_set():
            self._tick += 1
            dt = 1.0

            # At HEATER_FAIL_AT, simulate a hardware trip by clearing the
            # heater-enabled flag — the operator must press ON to recover.
            if self._tick == HEATER_FAIL_AT and not self._hw_tripped:
                self._hw_tripped = True
                self._heater_enabled.clear()
                self._q.put({"type": EVT_HEATER_TRIPPED})

            manual_on      = self._heater_enabled.is_set()
            effective_gain = HEATER_GAIN if manual_on else 0.0

            self.heater_output = self._pid.compute(self.temperature, dt)
            dT = (-COOLING_RATE
                  + effective_gain * (self.heater_output / 100.0)
                  + random.uniform(-0.05, 0.05))
            self.temperature = max(-10.0, self.temperature + dT)

            if not self._fault:
                if self.temperature < TEMP_MIN_FAULT:
                    self._fault        = True
                    self.heater_output = 0.0
                    self._q.put({"type": EVT_FAULT, "temp": self.temperature})
            else:
                # Fault active — keep simulating so the heater can recover.
                if self.temperature >= TEMP_MIN_FAULT:
                    self._fault = False
                    self._q.put({"type": EVT_RECOVERED, "temp": self.temperature})

            # Post a temperature update regardless of fault state
            self._q.put({
                "type":      EVT_TEMP,
                "temp":      self.temperature,
                "heater":    self.heater_output,
                "fault":     self._fault,
                "manual_on": manual_on,
            })

            # Responsive sleep: exits immediately if stop_event is set
            if self._stop.wait(timeout=dt):
                break


# ---------------------------------------------------------------------------
# HMI window
# ---------------------------------------------------------------------------

class HMI(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Ball Pen Production Line — HMI")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._q              : queue.Queue             = queue.Queue()
        self._stop_event                               = threading.Event()
        self._thermal_stop_event                       = threading.Event()
        self._heater_enabled                           = threading.Event()
        self._heater_enabled.set()   # heater on by default
        self._thread         : threading.Thread | None = None
        self._thermal_thread : threading.Thread | None = None
        self._thermal_fault  = False
        self._current_temp   = TEMP_SETPOINT
        self._machine_state  = "Standby"
        self._influx         = InfluxDBWriter()
        self._influx.start()
        self._n_assembled    = 0
        self._n_rejected     = 0
        self._active_stage   : str | None              = None
        self._stage_items    : dict[str, tuple]        = {}

        self._build_ui()
        self._poll()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── Title bar ──────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=HEADER, pady=10)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="BALL PEN PRODUCTION LINE — HMI",
            bg=HEADER, fg=ACCENT,
            font=("Courier New", 15, "bold"),
        ).pack()

        # ── Counters + controls ────────────────────────────────────────
        mid = tk.Frame(self, bg=BG, padx=20, pady=14)
        mid.pack(fill="x")

        self._assembled_var = tk.StringVar(value="0")
        self._rejected_var  = tk.StringVar(value="0")

        self._counter_tile("Assembled Pens", self._assembled_var, GREEN, mid, col=0)
        self._counter_tile("Total Rejects",  self._rejected_var,  RED,   mid, col=1)

        btn_col = tk.Frame(mid, bg=BG)
        btn_col.grid(row=0, column=2, padx=30)

        self._btn_start = tk.Button(
            btn_col, text="▶  START",
            bg=GREEN, fg="#000", activebackground="#22a844",
            font=("Courier New", 12, "bold"),
            width=12, relief="flat", cursor="hand2",
            command=self._start,
        )
        self._btn_start.pack(pady=5)

        self._btn_stop = tk.Button(
            btn_col, text="■  STOP",
            bg=RED, fg="#fff", activebackground="#c0303a",
            font=("Courier New", 12, "bold"),
            width=12, relief="flat", cursor="hand2",
            state="disabled",
            command=self._stop_all,
        )
        self._btn_stop.pack(pady=5)

        # ── Status line ────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="■ Idle")
        tk.Label(
            self, textvariable=self._status_var,
            bg=BG, fg=AMBER,
            font=("Courier New", 10),
        ).pack(anchor="w", padx=22, pady=(0, 4))

        # ── Thermal control panel ──────────────────────────────────────
        self._build_thermal_panel()

        # ── Pipeline diagram ───────────────────────────────────────────
        pipe_frame = tk.Frame(self, bg=BG)
        pipe_frame.pack(fill="x", padx=10)
        tk.Label(
            pipe_frame, text="PRODUCTION PIPELINE",
            bg=BG, fg=FG_DIM,
            font=("Courier New", 9, "bold"),
        ).pack(anchor="w", padx=10, pady=(0, 3))
        self._build_pipeline(pipe_frame)

        # ── Divider ────────────────────────────────────────────────────
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

        # ── Rejection log ──────────────────────────────────────────────
        log_area = tk.Frame(self, bg=BG, padx=20, pady=10)
        log_area.pack(fill="both", expand=True)

        tk.Label(
            log_area, text="REJECTION LOG",
            bg=BG, fg=FG_DIM,
            font=("Courier New", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("HMI.Treeview",
                        background=PANEL, foreground=FG,
                        fieldbackground=PANEL, rowheight=22,
                        font=("Courier New", 9))
        style.configure("HMI.Treeview.Heading",
                        background=HEADER, foreground=ACCENT,
                        font=("Courier New", 9, "bold"), relief="flat")
        style.map("HMI.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#000")])

        cols = ("Item", "Station", "Reason")
        wrap = tk.Frame(log_area, bg=BG)
        wrap.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(
            wrap, columns=cols, show="headings",
            style="HMI.Treeview", height=10,
        )
        for col, w in zip(cols, (170, 180, 260)):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor="w")

        sb = ttk.Scrollbar(wrap, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        tk.Frame(self, bg=BG, height=8).pack()

    def _counter_tile(self, label: str, var: tk.StringVar,
                      color: str, parent: tk.Frame, col: int) -> None:
        tile = tk.Frame(parent, bg=PANEL, padx=22, pady=10)
        tile.grid(row=0, column=col, padx=10)
        tk.Label(tile, text=label, bg=PANEL, fg=FG_DIM,
                 font=("Courier New", 9)).pack()
        tk.Label(tile, textvariable=var, bg=PANEL, fg=color,
                 font=("Courier New", 30, "bold")).pack()

    # ------------------------------------------------------------------
    # Thermal panel
    # ------------------------------------------------------------------

    def _build_thermal_panel(self) -> None:
        outer = tk.Frame(self, bg=BG, padx=20, pady=6)
        outer.pack(fill="x")

        tk.Label(
            outer, text="INK TEMPERATURE CONTROL  (PID)",
            bg=BG, fg=FG_DIM,
            font=("Courier New", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        tiles = tk.Frame(outer, bg=BG)
        tiles.pack(anchor="w")

        # ── Temperature tile ───────────────────────────────────────────
        t_tile = tk.Frame(tiles, bg=PANEL, padx=18, pady=8)
        t_tile.grid(row=0, column=0, padx=(0, 8))
        tk.Label(t_tile, text="TEMPERATURE", bg=PANEL, fg=FG_DIM,
                 font=("Courier New", 9)).pack()
        self._temp_var   = tk.StringVar(value="—")
        self._temp_label = tk.Label(t_tile, textvariable=self._temp_var,
                                    bg=PANEL, fg=FG_DIM,
                                    font=("Courier New", 22, "bold"))
        self._temp_label.pack()
        tk.Label(t_tile, text=f"SP: {TEMP_SETPOINT:.1f} °C  |  FAULT < {TEMP_MIN_FAULT:.0f} °C",
                 bg=PANEL, fg=FG_DIM, font=("Courier New", 8)).pack()

        # ── Heater tile ────────────────────────────────────────────────
        h_tile = tk.Frame(tiles, bg=PANEL, padx=18, pady=8)
        h_tile.grid(row=0, column=1, padx=8)
        tk.Label(h_tile, text="HEATER OUTPUT", bg=PANEL, fg=FG_DIM,
                 font=("Courier New", 9)).pack()
        self._heater_var   = tk.StringVar(value="—")
        self._heater_label = tk.Label(h_tile, textvariable=self._heater_var,
                                      bg=PANEL, fg=FG_DIM,
                                      font=("Courier New", 22, "bold"))
        self._heater_label.pack()
        self._heater_hw_var   = tk.StringVar(value="—")
        self._heater_hw_label = tk.Label(h_tile, textvariable=self._heater_hw_var,
                                         bg=PANEL, fg=FG_DIM,
                                         font=("Courier New", 8))
        self._heater_hw_label.pack()

        # ── Controller status tile ─────────────────────────────────────
        p_tile = tk.Frame(tiles, bg=PANEL, padx=18, pady=8)
        p_tile.grid(row=0, column=2, padx=8)
        tk.Label(p_tile, text="CONTROLLER", bg=PANEL, fg=FG_DIM,
                 font=("Courier New", 9)).pack()
        self._pid_var   = tk.StringVar(value="—")
        self._pid_label = tk.Label(p_tile, textvariable=self._pid_var,
                                   bg=PANEL, fg=FG_DIM,
                                   font=("Courier New", 13, "bold"))
        self._pid_label.pack(pady=6)

        # ── Heater toggle button ───────────────────────────────────────
        tog_tile = tk.Frame(tiles, bg=BG, padx=8, pady=8)
        tog_tile.grid(row=0, column=3, padx=8)
        tk.Label(tog_tile, text="MANUAL CONTROL", bg=BG, fg=FG_DIM,
                 font=("Courier New", 9)).pack()
        self._heater_btn = tk.Button(
            tog_tile, text="● HEATER ON",
            bg=GREEN, fg="#000", activebackground="#22a844",
            font=("Courier New", 11, "bold"),
            width=14, relief="flat", cursor="hand2",
            command=self._toggle_heater,
        )
        self._heater_btn.pack(pady=6)

        # ── Alarm bar ──────────────────────────────────────────────────
        self._alarm_var   = tk.StringVar(value="  ■  THERMAL: IDLE")
        self._alarm_bar   = tk.Frame(outer, bg=PANEL, padx=10, pady=5)
        self._alarm_bar.pack(fill="x", pady=(8, 0))
        self._alarm_label = tk.Label(
            self._alarm_bar, textvariable=self._alarm_var,
            bg=PANEL, fg=FG_DIM,
            font=("Courier New", 10, "bold"),
        )
        self._alarm_label.pack(side="left")
        self._reset_btn = tk.Button(
            self._alarm_bar, text="RESET ALARM",
            bg=AMBER, fg="#000", activebackground="#d4892f",
            font=("Courier New", 9, "bold"),
            relief="flat", cursor="hand2",
            state="disabled",
            command=self._reset_alarm,
        )
        self._reset_btn.pack(side="right", padx=(8, 0))

    # ------------------------------------------------------------------
    # Pipeline canvas
    # ------------------------------------------------------------------

    def _build_pipeline(self, parent: tk.Frame) -> None:
        c = tk.Canvas(parent, bg=PANEL, width=_CW, height=_CH,
                      highlightthickness=0)
        c.pack(padx=10, pady=(0, 8))
        self._pipe_canvas = c

        abbr = {"barrel": "BAR", "tip": "TIP", "cartridge": "CART", "cap": "CAP"}

        def box(cx: int, cy: int, label: str, key: str) -> None:
            x0, y0 = cx - _BHW, cy - _BHH
            x1, y1 = cx + _BHW, cy + _BHH
            r = c.create_rectangle(x0, y0, x1, y1,
                                   fill=PANEL, outline=FG_DIM, width=1)
            t = c.create_text(cx, cy, text=label, fill=FG_DIM,
                              font=("Courier New", 7, "bold"), justify="center")
            self._stage_items[key] = (r, t)

        def arrow(x1: int, y1: int, x2: int, y2: int) -> None:
            c.create_line(x1, y1, x2, y2, fill=FG_DIM, width=1,
                          arrow=tk.LAST, arrowshape=(5, 7, 3))

        for name, y in _LANE_Y.items():
            s = abbr[name]
            box(_X_MAKE, y, f"MAKE\n{s}",   f"make_{name}")
            box(_X_QC,   y, f"QC\n{s}",     f"qc_{name}")
            box(_X_BIN,  y, f"BIN\n{s}",    f"bin_{name}")
            arrow(_X_MAKE + _BHW, y,          _X_QC  - _BHW, y)
            arrow(_X_QC  + _BHW, y,          _X_BIN - _BHW, y)
            arrow(_X_BIN + _BHW, y,          _X_ASSM - _BHW, _CTR_Y)

        box(_X_ASSM, _CTR_Y, "ASSM",        "assembly")
        box(_X_FQC,  _CTR_Y, "FINAL\nQC",   "final_qc")
        box(_X_PACK, _CTR_Y, "PACK",        "packaging")
        box(_X_SHIP, _CTR_Y, "SHIP",        "shipped")

        arrow(_X_ASSM + _BHW, _CTR_Y,       _X_FQC  - _BHW, _CTR_Y)
        arrow(_X_FQC  + _BHW, _CTR_Y,       _X_PACK - _BHW, _CTR_Y)
        arrow(_X_PACK + _BHW, _CTR_Y,       _X_SHIP - _BHW, _CTR_Y)

    # ------------------------------------------------------------------
    # Stage highlighting
    # ------------------------------------------------------------------

    def _highlight_stage(self, stage: str, component: str) -> None:
        if self._active_stage and self._active_stage in self._stage_items:
            r, t = self._stage_items[self._active_stage]
            self._pipe_canvas.itemconfig(r, fill=PANEL, outline=FG_DIM)
            self._pipe_canvas.itemconfig(t, fill=FG_DIM)

        self._active_stage = stage
        if stage not in self._stage_items:
            return
        color = COMP_COLORS.get(component, ACCENT)
        r, t = self._stage_items[stage]
        self._pipe_canvas.itemconfig(r, fill=color, outline=color)
        self._pipe_canvas.itemconfig(t, fill="#111111")

    def _reset_pipeline(self) -> None:
        for r, t in self._stage_items.values():
            self._pipe_canvas.itemconfig(r, fill=PANEL, outline=FG_DIM)
            self._pipe_canvas.itemconfig(t, fill=FG_DIM)
        self._active_stage = None

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        # Reset production counters
        self._n_assembled = 0
        self._n_rejected  = 0
        self._assembled_var.set("0")
        self._rejected_var.set("0")
        self._tree.delete(*self._tree.get_children())
        self._status_var.set("● Running")
        self._reset_pipeline()

        # Reset thermal display
        self._thermal_fault = False
        self._temp_var.set("—")
        self._heater_var.set("—")
        self._heater_hw_var.set("—")
        self._pid_var.set("—")
        self._temp_label.config(fg=FG_DIM)
        self._heater_label.config(fg=FG_DIM)
        self._heater_hw_label.config(fg=FG_DIM)
        self._pid_label.config(fg=FG_DIM)
        self._alarm_var.set("  ●  THERMAL STATUS: OK")
        self._alarm_bar.config(bg=PANEL)
        self._alarm_label.config(bg=PANEL, fg=FG_DIM)
        self._reset_btn.config(state="disabled")

        # Reset heater to ON
        self._heater_enabled.set()
        self._heater_btn.config(text="● HEATER ON", bg=GREEN, fg="#000",
                                activebackground="#22a844")

        self._machine_state = "Productive"
        self._stop_event.clear()
        random.seed(42)

        line = InstrumentedLine(self._q, self._stop_event)
        self._thread = threading.Thread(target=line.run_until_stopped, daemon=True)
        self._thread.start()

        # Only start a new thermal controller if one is not already running
        # (after a fault, the thermal thread stays alive for temperature recovery)
        if self._thermal_thread is None or not self._thermal_thread.is_alive():
            self._thermal_stop_event.clear()
            thermal = ThermalController(self._q, self._thermal_stop_event, self._heater_enabled)
            self._thermal_thread = thermal
            self._thermal_thread.start()

        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")

    def _stop(self) -> None:
        """Stop the production line only (used by fault handler)."""
        self._stop_event.set()
        self._btn_stop.config(state="disabled")

    def _stop_all(self) -> None:
        """Stop both the production line and the thermal controller (manual stop)."""
        self._machine_state = "Standby"
        self._stop_event.set()
        self._thermal_stop_event.set()
        self._btn_stop.config(state="disabled")

    def _update_start_btn(self) -> None:
        """Enable START only when idle, alarm cleared, and temperature is safe."""
        prod_running = self._thread is not None and self._thread.is_alive()
        if (not prod_running
                and not self._thermal_fault
                and self._current_temp >= TEMP_MIN_FAULT):
            self._btn_start.config(state="normal")
        else:
            self._btn_start.config(state="disabled")

    def _toggle_heater(self) -> None:
        if self._heater_enabled.is_set():
            self._heater_enabled.clear()
            self._heater_btn.config(text="■ HEATER OFF", bg=RED, fg="#fff",
                                    activebackground="#c0303a")
        else:
            self._heater_enabled.set()
            self._heater_btn.config(text="● HEATER ON", bg=GREEN, fg="#000",
                                    activebackground="#22a844")

    # ------------------------------------------------------------------
    # Event pump  (UI thread, every 50 ms)
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        try:
            while True:
                evt = self._q.get_nowait()
                t = evt["type"]

                if t == EVT_ASSEMBLED:
                    self._n_assembled += 1
                    self._assembled_var.set(str(self._n_assembled))

                elif t == EVT_REJECTED:
                    self._n_rejected += 1
                    self._rejected_var.set(str(self._n_rejected))
                    self._tree.insert("", "end", values=(
                        evt["item"], evt["station"], evt["reason"],
                    ))
                    self._tree.yview_moveto(1.0)

                elif t == EVT_STAGE:
                    self._highlight_stage(evt["stage"], evt["component"])

                elif t == EVT_STATUS:
                    self._status_var.set(evt["msg"])

                elif t == EVT_STOPPED:
                    self._machine_state = "Standby"
                    self._reset_pipeline()
                    self._update_start_btn()

                elif t == EVT_TEMP:
                    self._handle_temp_event(evt)

                elif t == EVT_FAULT:
                    self._handle_fault_event(evt)

                elif t == EVT_RECOVERED:
                    self._handle_recovered_event()

                elif t == EVT_HEATER_TRIPPED:
                    self._heater_btn.config(text="■ HEATER OFF", bg=RED,
                                            fg="#fff", activebackground="#c0303a")

        except queue.Empty:
            pass
        self.after(50, self._poll)

    def _handle_temp_event(self, evt: dict) -> None:
        temp      = evt["temp"]
        heater    = evt["heater"]
        fault     = evt["fault"]
        manual_on = evt.get("manual_on", True)

        self._current_temp = temp
        self._temp_var.set(f"{temp:.1f} °C")
        self._heater_var.set(f"{heater:.1f} %")
        self._update_start_btn()

        self._influx.push({
            "temperature":   temp,
            "heater_output": heater,
            "manual_on":     manual_on,
            "fault":         fault,
            "parts_total":   self._n_assembled,
            "rejects":       self._n_rejected,
            "state":         self._machine_state,
        })

        if fault:
            self._temp_label.config(fg=RED)
            self._heater_label.config(fg=RED)
            self._heater_hw_var.set("OFFLINE")
            self._heater_hw_label.config(fg=RED)
            self._pid_var.set("FAULT")
            self._pid_label.config(fg=RED)

        elif not manual_on:
            color = RED if temp < TEMP_SETPOINT - 5 else AMBER
            self._temp_label.config(fg=color)
            self._heater_label.config(fg=FG_DIM)
            self._heater_hw_var.set("HEATER OFF")
            self._heater_hw_label.config(fg=AMBER)
            self._pid_var.set("STANDBY")
            self._pid_label.config(fg=AMBER)

        elif abs(temp - TEMP_SETPOINT) <= 2.0:
            self._temp_label.config(fg=GREEN)
            self._heater_label.config(fg=ACCENT)
            self._heater_hw_var.set("HEATER OK")
            self._heater_hw_label.config(fg=GREEN)
            self._pid_var.set("PID ACTIVE")
            self._pid_label.config(fg=GREEN)

        else:
            self._temp_label.config(fg=AMBER)
            self._heater_label.config(fg=AMBER)
            self._heater_hw_var.set("HEATER OK")
            self._heater_hw_label.config(fg=AMBER)
            self._pid_var.set("ADJUSTING")
            self._pid_label.config(fg=AMBER)

    def _handle_fault_event(self, evt: dict) -> None:
        temp = evt["temp"]
        self._thermal_fault  = True
        self._machine_state  = "Fault"
        msg = (
            f"  ⚠  ALARM — INK TEMP TOO LOW: {temp:.1f} °C"
            f"  (min {TEMP_MIN_FAULT:.0f} °C) — Turn heater ON to recover  ⚠"
        )
        self._alarm_var.set(msg)
        self._alarm_bar.config(bg=RED)
        self._alarm_label.config(bg=RED, fg="#ffffff")
        self._status_var.set("⚠ FAULT — Turn heater ON to recover temperature")
        # Stop only the production line; thermal controller keeps running
        # so the operator can turn the heater on and let temperature recover.
        self._stop()

    def _handle_recovered_event(self) -> None:
        # Temperature is back above minimum — enable RESET so operator can
        # acknowledge and clear the alarm.  Do not auto-clear: the operator
        # must confirm the system is safe before restarting.
        self._alarm_var.set(
            f"  ⚠  ALARM ACTIVE — Temperature recovered above {TEMP_MIN_FAULT:.0f} °C"
            "  — press RESET ALARM to clear"
        )
        self._reset_btn.config(state="normal")
        self._status_var.set("● Temperature recovered — reset alarm then press START")

    def _reset_alarm(self) -> None:
        self._thermal_fault = False
        self._machine_state = "Standby"
        self._alarm_var.set("  ●  THERMAL STATUS: OK")
        self._alarm_bar.config(bg=PANEL)
        self._alarm_label.config(bg=PANEL, fg=FG_DIM)
        self._reset_btn.config(state="disabled")
        self._status_var.set("■ Idle — press START to run")
        self._update_start_btn()

    def destroy(self) -> None:
        self._influx.stop()
        super().destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    HMI().mainloop()
