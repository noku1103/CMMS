#!/usr/bin/env python3
"""
Quick launcher for the CMMS application
Run this script to start the maintenance management system
"""

if __name__ == "__main__":
    from cmms_main import CMmsApplication

    print("\n" + "="*60)
    print("Starting Ball Pen Production Line CMMS...")
    print("="*60 + "\n")

    app = CMmsApplication()
    app.run()
