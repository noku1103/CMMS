import sys
from datetime import datetime, timedelta
from cmms_database import CMmsDatabase


class CMmsApplication:
    def __init__(self):
        self.db = CMmsDatabase()
        self.running = True

    def print_menu(self):
        print("\n" + "="*60)
        print("BALL PEN PRODUCTION LINE - CMMS (Maintenance Management)")
        print("="*60)
        print("1. View All Parts")
        print("2. Add New Part")
        print("3. Record Maintenance")
        print("4. View Maintenance Record")
        print("5. View Part Instructions")
        print("6. Add Instructions for Part")
        print("7. View Change History")
        print("8. View Overdue Maintenance")
        print("9. View Upcoming Maintenance (30 days)")
        print("10. View All Maintenance Records")
        print("0. Exit")
        print("="*60)

    def view_all_parts(self):
        print("\n--- ALL PARTS ---")
        parts = self.db.get_all_parts()
        if not parts:
            print("No parts found.")
            return

        for part in parts:
            print(f"\nID: {part['id']}")
            print(f"Name: {part['name']}")
            print(f"Description: {part['description']}")
            print(f"Location: {part['location']}")
            print(f"Part Number: {part['part_number']}")

    def add_new_part(self):
        print("\n--- ADD NEW PART ---")
        name = input("Part Name: ").strip()
        description = input("Description: ").strip()
        location = input("Location (e.g., Ink Injection System): ").strip()
        part_number = input("Part Number: ").strip()

        part_id = self.db.add_part(name, description, location, part_number)
        if part_id:
            print(f"[+] Part '{name}' added successfully (ID: {part_id})")
        else:
            print("[-] Failed to add part.")

    def record_maintenance(self):
        print("\n--- RECORD MAINTENANCE ---")
        self.view_all_parts()

        try:
            part_id = int(input("\nEnter Part ID: "))
            part = self.db.get_part(part_id)

            if not part:
                print("[-] Part not found.")
                return

            print(f"\nRecording maintenance for: {part['name']}")

            last_changed = input("Last Changed Date (YYYY-MM-DD) [Today]: ").strip()
            if not last_changed:
                last_changed = datetime.now().date().isoformat()

            frequency = int(input("Change Frequency (days) [90]: ").strip() or "90")
            performed_by = input("Performed By (Name): ").strip()
            notes = input("Notes (optional): ").strip() or None

            self.db.update_maintenance_record(
                part_id, last_changed, frequency, performed_by, notes
            )
            print(f"[+] Maintenance record updated for {part['name']}")
        except ValueError:
            print("[-] Invalid input.")

    def view_maintenance_record(self):
        print("\n--- VIEW MAINTENANCE RECORD ---")
        self.view_all_parts()

        try:
            part_id = int(input("\nEnter Part ID: "))
            record = self.db.get_maintenance_record(part_id)
            part = self.db.get_part(part_id)

            if not record:
                print(f"[-] No maintenance record found for {part['name']}.")
                return

            print(f"\nMaintenance Record for: {part['name']}")
            print(f"Last Changed: {record['last_changed']}")
            print(f"Next Scheduled Change: {record['next_scheduled_change']}")
            print(f"Change Frequency: {record['change_frequency_days']} days")
            print(f"Performed By: {record['performed_by']}")
            if record['notes']:
                print(f"Notes: {record['notes']}")
        except ValueError:
            print("[-] Invalid input.")

    def view_instructions(self):
        print("\n--- VIEW PART INSTRUCTIONS ---")
        self.view_all_parts()

        try:
            part_id = int(input("\nEnter Part ID: "))
            part = self.db.get_part(part_id)

            if not part:
                print("[-] Part not found.")
                return

            instructions = self.db.get_instructions(part_id)

            if not instructions:
                print(f"[-] No instructions found for {part['name']}.")
                return

            print(f"\nInstructions for: {part['name']}")
            print("-" * 60)
            for instr in instructions:
                print(f"\nStep {instr['step_number']}:")
                print(f"  {instr['instruction_text']}")
        except ValueError:
            print("[-] Invalid input.")

    def add_instructions(self):
        print("\n--- ADD INSTRUCTIONS ---")
        self.view_all_parts()

        try:
            part_id = int(input("\nEnter Part ID: "))
            part = self.db.get_part(part_id)

            if not part:
                print("[-] Part not found.")
                return

            print(f"\nAdding instructions for: {part['name']}")
            step_num = 1
            while True:
                instruction = input(f"Step {step_num} (or 'done' to finish): ").strip()
                if instruction.lower() == 'done':
                    break
                if instruction:
                    self.db.add_instruction(part_id, instruction, step_num)
                    step_num += 1
            print(f"[+] Instructions added for {part['name']}")
        except ValueError:
            print("[-] Invalid input.")

    def view_change_history(self):
        print("\n--- CHANGE HISTORY ---")
        self.view_all_parts()

        try:
            part_id = int(input("\nEnter Part ID: "))
            part = self.db.get_part(part_id)

            if not part:
                print("[-] Part not found.")
                return

            history = self.db.get_change_history(part_id)

            if not history:
                print(f"[-] No change history for {part['name']}.")
                return

            print(f"\nChange History for: {part['name']}")
            print("-" * 60)
            for change in history:
                print(f"\nDate: {change['changed_at']}")
                print(f"Changed By: {change['changed_by']}")
                print(f"Reason: {change['reason']}")
                if change['notes']:
                    print(f"Notes: {change['notes']}")
        except ValueError:
            print("[-] Invalid input.")

    def view_overdue_maintenance(self):
        print("\n--- OVERDUE MAINTENANCE ---")
        overdue = self.db.get_overdue_maintenance()

        if not overdue:
            print("[+] No overdue maintenance!")
            return

        print(f"[!] {len(overdue)} part(s) require maintenance:")
        for record in overdue:
            days_overdue = (datetime.now() - datetime.fromisoformat(record['next_scheduled_change'])).days
            print(f"\n  {record['name']}")
            print(f"    Was due: {record['next_scheduled_change']}")
            print(f"    Days overdue: {days_overdue}")
            print(f"    Last changed by: {record['performed_by']}")

    def view_upcoming_maintenance(self):
        print("\n--- UPCOMING MAINTENANCE (Next 30 Days) ---")
        upcoming = self.db.get_upcoming_maintenance(30)

        if not upcoming:
            print("[+] No maintenance scheduled in the next 30 days.")
            return

        print(f"[*] {len(upcoming)} part(s) scheduled for maintenance:")
        for record in upcoming:
            days_until = (datetime.fromisoformat(record['next_scheduled_change']) - datetime.now()).days
            print(f"\n  {record['name']}")
            print(f"    Scheduled for: {record['next_scheduled_change']}")
            print(f"    Days until: {days_until}")
            print(f"    Last changed by: {record['performed_by']}")

    def view_all_maintenance_records(self):
        print("\n--- ALL MAINTENANCE RECORDS ---")
        records = self.db.get_all_maintenance_records()

        if not records:
            print("No maintenance records found.")
            return

        print(f"\n{'Part':<25} {'Last Changed':<20} {'Next Due':<20} {'Frequency':<12}")
        print("-" * 77)
        for record in records:
            print(f"{record['name']:<25} {record['last_changed']:<20} {record['next_scheduled_change']:<20} {record['change_frequency_days']} days")

    def run(self):
        while self.running:
            self.print_menu()
            choice = input("Select option: ").strip()

            if choice == '1':
                self.view_all_parts()
            elif choice == '2':
                self.add_new_part()
            elif choice == '3':
                self.record_maintenance()
            elif choice == '4':
                self.view_maintenance_record()
            elif choice == '5':
                self.view_instructions()
            elif choice == '6':
                self.add_instructions()
            elif choice == '7':
                self.view_change_history()
            elif choice == '8':
                self.view_overdue_maintenance()
            elif choice == '9':
                self.view_upcoming_maintenance()
            elif choice == '10':
                self.view_all_maintenance_records()
            elif choice == '0':
                print("\nGoodbye!")
                self.running = False
            else:
                print("[-] Invalid option. Please try again.")

        self.db.close()


if __name__ == "__main__":
    app = CMmsApplication()
    app.run()
