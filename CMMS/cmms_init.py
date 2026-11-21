from datetime import datetime, timedelta
from cmms_database import CMmsDatabase


def initialize_cmms():
    db = CMmsDatabase()

    parts_data = [
        {
            "name": "Injection Pump",
            "description": "Primary pump for ink injection system",
            "location": "Ink Injection System - Unit A",
            "part_number": "INK-PUMP-001"
        },
        {
            "name": "Electrical Resistance Heater",
            "description": "Heating element for ink temperature regulation",
            "location": "Ink Injection System - Temperature Control",
            "part_number": "INK-HEAT-001"
        },
        {
            "name": "Ink Filter Cartridge",
            "description": "Filter for ink impurities and contaminants",
            "location": "Ink Injection System - Pre-Injection",
            "part_number": "INK-FILT-001"
        }
    ]

    instructions_data = {
        "Injection Pump": [
            "Turn off the ink injection system power",
            "Close the main ink supply valve",
            "Depressurize the system using the relief valve",
            "Disconnect inlet and outlet tubing",
            "Unbolt the pump mounting bracket (4 bolts)",
            "Remove the old pump carefully",
            "Install new pump with same orientation",
            "Reattach tubing and ensure tight connections",
            "Refill the system and check for leaks",
            "Test pump operation at low speed",
            "Restore power and resume normal operation"
        ],
        "Electrical Resistance Heater": [
            "Turn off power to the heating system",
            "Allow heater to cool for 15 minutes minimum",
            "Disconnect the heater power leads",
            "Remove the thermocouple sensor",
            "Unbolt the heater unit from mounting bracket",
            "Carefully remove old heater from housing",
            "Insert new heater into housing with same orientation",
            "Secure with mounting bolts (torque to 25 Nm)",
            "Reconnect thermocouple sensor",
            "Reconnect power leads with proper polarity",
            "Test temperature control at low setting",
            "Verify temperature readout on display"
        ],
        "Ink Filter Cartridge": [
            "Shut down the ink system",
            "Open the filter housing lid",
            "Place a container under the filter drain",
            "Loosen the drain valve to relieve pressure",
            "Remove the old filter cartridge",
            "Clean the filter housing interior with lint-free cloth",
            "Install new filter cartridge with arrows pointing toward flow direction",
            "Hand tighten the filter housing lid",
            "Open main supply valve slowly",
            "Check for leaks around the filter housing",
            "Prime the system by running at low speed for 2 minutes",
            "Verify ink flow is normal and clear"
        ]
    }

    print("Initializing CMMS Database...")
    print("-" * 60)

    for part in parts_data:
        part_id = db.add_part(
            name=part["name"],
            description=part["description"],
            location=part["location"],
            part_number=part["part_number"]
        )

        if part_id:
            print(f"[+] Added part: {part['name']} (ID: {part_id})")

            last_changed = (datetime.now() - timedelta(days=45)).date().isoformat()
            db.update_maintenance_record(
                part_id=part_id,
                last_changed=last_changed,
                change_frequency_days=90,
                performed_by="Initial Setup",
                notes="Initial installation and configuration"
            )

            if part["name"] in instructions_data:
                for step_num, instruction in enumerate(instructions_data[part["name"]], 1):
                    db.add_instruction(part_id, instruction, step_num)
                print(f"    [+] Added {len(instructions_data[part['name']])} maintenance instructions")

    print("\n" + "="*60)
    print("[+] CMMS Database initialized successfully!")
    print("="*60)
    print("\nDefault Maintenance Schedule:")
    print("  * All parts: 90-day maintenance cycle")
    print("  * Check 'cmms.db' for the database file")
    print("\nRun 'python cmms_main.py' to start the CMMS application")

    db.close()


if __name__ == "__main__":
    initialize_cmms()
