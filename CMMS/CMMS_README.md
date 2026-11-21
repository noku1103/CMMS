# Ball Pen Production Line - CMMS System

**Computerized Maintenance Management System** for managing the ink injection system and its critical components.

## Overview

This CMMS system tracks maintenance schedules, change history, and maintenance instructions for the ball pen production line's ink injection system components.

### Default Parts

1. **Injection Pump** - Primary pump for ink delivery system
   - Part Number: INK-PUMP-001
   - Maintenance Frequency: 90 days
   - Critical for consistent ink injection

2. **Electrical Resistance Heater** - Ink temperature regulation
   - Part Number: INK-HEAT-001
   - Maintenance Frequency: 90 days
   - Ensures optimal ink viscosity

3. **Ink Filter Cartridge** - Contaminant removal
   - Part Number: INK-FILT-001
   - Maintenance Frequency: 90 days
   - Prevents nozzle clogging

## Getting Started

### 1. Initialize the Database

Run the initialization script to set up the system with default parts:

```bash
python cmms_init.py
```

This will:
- Create the SQLite database (`cmms.db`)
- Add the three default parts
- Load maintenance instructions for each part
- Set initial maintenance schedules

### 2. Start the CMMS Application

```bash
python cmms_main.py
```

## Features

### Part Management
- **View All Parts** - See complete list of tracked parts
- **Add New Part** - Add additional components to track
- **Part Details** - Location, description, and part number

### Maintenance Tracking
- **Record Maintenance** - Log when maintenance is performed
- **View Maintenance Records** - Check last changed date and next scheduled change
- **Change Frequency** - Configurable maintenance intervals (default: 90 days)

### Personnel Tracking
- **Performed By** - Records who performed the maintenance
- **Change History** - Complete audit trail of all changes

### Instructions & Alerts
- **Maintenance Instructions** - Step-by-step guides for each part (11-12 steps per part)
- **Overdue Maintenance** - Alerts for parts requiring immediate attention
- **Upcoming Maintenance** - View scheduled maintenance for next 30 days

## Database Structure

### Tables

#### `parts`
- Stores information about tracked components
- Fields: id, name, description, location, part_number, created_at

#### `maintenance_records`
- Tracks maintenance schedule and history for each part
- Fields: id, part_id, last_changed, next_scheduled_change, change_frequency_days, performed_by, notes

#### `maintenance_instructions`
- Detailed step-by-step instructions for changing parts
- Fields: id, part_id, instruction_text, step_number

#### `change_history`
- Complete audit trail of all maintenance activities
- Fields: id, part_id, changed_by, changed_at, reason, notes

## Menu Options

```
1. View All Parts           - Display all tracked components
2. Add New Part             - Create a new part record
3. Record Maintenance       - Log maintenance activity
4. View Maintenance Record  - Check maintenance history for a part
5. View Part Instructions   - Read step-by-step instructions
6. Add Instructions         - Add new instructions for a part
7. View Change History      - See complete change log
8. View Overdue Maintenance - Alert for overdue maintenance
9. View Upcoming Maintenance - Schedule for next 30 days
10. View All Maintenance Records - Summary view of all parts
0. Exit                     - Close the application
```

## Typical Workflow

### Recording Maintenance

1. Select **Option 3: Record Maintenance**
2. Choose the part to maintain
3. Enter the date (or today's date)
4. Set maintenance frequency (default: 90 days)
5. Enter your name (who performed the maintenance)
6. Add any notes
7. System automatically calculates next scheduled change

### Before Maintenance

1. Select **Option 8: View Overdue Maintenance** to check critical items
2. Select **Option 5: View Part Instructions** to get the procedure
3. Follow the step-by-step instructions carefully
4. Record the maintenance when complete

### Auditing

- **Option 7: View Change History** - See who changed what and when
- **Option 10: View All Maintenance Records** - Summary of all maintenance status

## Example Data

Default setup includes:

- All parts with initial maintenance date 45 days ago
- Next maintenance due in 45 days
- Complete 11-12 step instructions for each part
- Performed by "Initial Setup"

## Files

- `cmms_database.py` - Database layer and SQL operations
- `cmms_main.py` - CLI application interface
- `cmms_init.py` - Database initialization with default data
- `cmms.db` - SQLite database (created after first run)
- `CMMS_README.md` - This documentation

## Technical Details

- **Database**: SQLite (cmms.db)
- **Language**: Python 3.7+
- **Dependencies**: Standard library only (sqlite3, datetime)
- **No external packages required**

## Future Enhancements

- Web UI dashboard
- Email alerts for overdue maintenance
- Predictive maintenance based on usage patterns
- Integration with production line monitoring
- Parts inventory management
- Cost tracking and reporting

## Notes

- All timestamps are stored in ISO format (YYYY-MM-DD HH:MM:SS)
- Database is stored as `cmms.db` in the application directory
- Regular backups of `cmms.db` are recommended
- Maintenance frequency can be adjusted per part
