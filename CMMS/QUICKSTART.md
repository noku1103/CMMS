# CMMS Quick Start Guide

## Running the Application

### Option 1: Web Interface (Recommended)
```bash
cd CMMS
pip install -r requirements.txt
python cmms_app.py
```
Then open your browser to: **http://localhost:5000**

### Option 2: Command Line Interface (Terminal)
```bash
cd CMMS
python cmms_main.py
```

### Option 3: Using Launcher Script
```bash
cd CMMS
python run_cmms.py
```

### Option 4: Initialize Fresh Database (if needed)
```bash
cd CMMS
python cmms_init.py
```

## Folder Structure

```
CMMS/
├── cmms_app.py                # Flask web application
├── cmms_main.py               # CLI application
├── cmms_database.py           # Database layer and queries
├── cmms_init.py               # Database initialization
├── run_cmms.py                # Quick launcher script
├── cmms.db                    # SQLite database (created on first run)
├── requirements.txt           # Python dependencies for web app
├── templates/                 # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── parts.html
│   ├── alerts.html
│   └── ... (more templates)
├── static/                    # CSS and JavaScript
│   ├── style.css
│   └── script.js
├── CMMS_README.md             # Full documentation
└── QUICKSTART.md              # This file
```

## What's Inside

- **3 default parts** pre-configured for the ink injection system
- **90-day maintenance cycles** for each part
- **11-12 step instructions** for each maintenance procedure
- **Complete audit trail** of all changes
- **Overdue & upcoming maintenance** alerts

## First Time Setup

The system comes pre-initialized with:
- Injection Pump
- Electrical Resistance Heater
- Ink Filter Cartridge

All with full maintenance schedules and instructions. Just run and start using!

## Database File

The `cmms.db` SQLite database stores:
- Parts inventory
- Maintenance schedules
- Change history
- Instructions
- Maintenance records

Back this file up regularly for data protection.

## Web Interface Features

The web interface provides a user-friendly dashboard with:

- **Dashboard**: At-a-glance maintenance overview with alerts
- **Parts Management**: View, add, and edit parts with maintenance history
- **Part Details**: Comprehensive view of each part including maintenance schedule
- **Maintenance Recording**: Easy forms to record maintenance activities
- **Instructions**: Step-by-step procedures for each part
- **Alerts**: Dedicated page for overdue and upcoming maintenance
- **Change History**: Complete audit trail of all maintenance activities
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## CLI Menu Options

1. View all parts and maintenance status
2. Add new parts to track
3. Record maintenance activities
4. View/manage maintenance schedules
5. Access step-by-step instructions
6. View complete change history
7. Check for overdue maintenance
8. Plan upcoming maintenance

## Tips

- Always record maintenance immediately after completion
- Review overdue maintenance daily
- Back up cmms.db weekly
- Update instructions if procedures change
- Use the "Notes" field for special observations
