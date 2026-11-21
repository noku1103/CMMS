import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class CMmsDatabase:
    def __init__(self, db_path="cmms.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                location TEXT,
                part_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                last_changed TIMESTAMP,
                next_scheduled_change TIMESTAMP,
                change_frequency_days INTEGER,
                performed_by TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts (id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_instructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                instruction_text TEXT NOT NULL,
                step_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts (id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS change_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                notes TEXT
            )
        ''')

        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

    def add_part(self, name, description, location, part_number):
        try:
            self.cursor.execute('''
                INSERT INTO parts (name, description, location, part_number)
                VALUES (?, ?, ?, ?)
            ''', (name, description, location, part_number))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Part '{name}' already exists.")
            return None

    def get_all_parts(self):
        self.cursor.execute('SELECT * FROM parts ORDER BY name')
        return self.cursor.fetchall()

    def get_part(self, part_id):
        self.cursor.execute('SELECT * FROM parts WHERE id = ?', (part_id,))
        return self.cursor.fetchone()

    def update_maintenance_record(self, part_id, last_changed, change_frequency_days,
                                  performed_by, notes=None):
        next_scheduled = datetime.fromisoformat(last_changed) + timedelta(days=change_frequency_days)

        self.cursor.execute('''
            INSERT OR REPLACE INTO maintenance_records
            (part_id, last_changed, next_scheduled_change, change_frequency_days, performed_by, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (part_id, last_changed, next_scheduled.isoformat(),
              change_frequency_days, performed_by, notes))

        self.cursor.execute('''
            INSERT INTO change_history (part_id, changed_by, reason, notes)
            VALUES (?, ?, ?, ?)
        ''', (part_id, performed_by, 'Maintenance', notes))

        self.conn.commit()

    def get_maintenance_record(self, part_id):
        self.cursor.execute('''
            SELECT * FROM maintenance_records WHERE part_id = ?
        ''', (part_id,))
        return self.cursor.fetchone()

    def get_all_maintenance_records(self):
        self.cursor.execute('''
            SELECT mr.*, p.name FROM maintenance_records mr
            JOIN parts p ON mr.part_id = p.id
            ORDER BY mr.next_scheduled_change
        ''')
        return self.cursor.fetchall()

    def add_instruction(self, part_id, instruction_text, step_number):
        self.cursor.execute('''
            INSERT INTO maintenance_instructions (part_id, instruction_text, step_number)
            VALUES (?, ?, ?)
        ''', (part_id, instruction_text, step_number))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_instructions(self, part_id):
        self.cursor.execute('''
            SELECT * FROM maintenance_instructions
            WHERE part_id = ?
            ORDER BY step_number
        ''', (part_id,))
        return self.cursor.fetchall()

    def get_change_history(self, part_id):
        self.cursor.execute('''
            SELECT * FROM change_history
            WHERE part_id = ?
            ORDER BY changed_at DESC
        ''', (part_id,))
        return self.cursor.fetchall()

    def get_overdue_maintenance(self):
        today = datetime.now().isoformat()
        self.cursor.execute('''
            SELECT mr.*, p.name FROM maintenance_records mr
            JOIN parts p ON mr.part_id = p.id
            WHERE mr.next_scheduled_change < ?
            ORDER BY mr.next_scheduled_change
        ''', (today,))
        return self.cursor.fetchall()

    def get_upcoming_maintenance(self, days=30):
        today = datetime.now().isoformat()
        future_date = (datetime.now() + timedelta(days=days)).isoformat()
        self.cursor.execute('''
            SELECT mr.*, p.name FROM maintenance_records mr
            JOIN parts p ON mr.part_id = p.id
            WHERE mr.next_scheduled_change BETWEEN ? AND ?
            ORDER BY mr.next_scheduled_change
        ''', (today, future_date))
        return self.cursor.fetchall()
