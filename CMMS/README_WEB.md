# CMMS Web Frontend - User Guide

## Starting the Web Application

### Quick Start (3 steps)

1. **Install Dependencies** (first time only):
```bash
cd CMMS
pip install -r requirements.txt
```

2. **Start the Web Server**:
```bash
python cmms_app.py
```

3. **Open Your Browser**:
Navigate to `http://localhost:5000`

## Dashboard Overview

The main dashboard shows:
- **Total Parts**: Number of tracked components
- **Overdue Maintenance**: Parts requiring immediate attention
- **Upcoming (30 days)**: Parts scheduled for maintenance soon
- **Maintenance Status Table**: Quick view of all parts and their schedules

## Main Navigation

The top navigation bar has 4 main sections:

### Dashboard (Home)
- Central hub for maintenance overview
- Quick stats and alerts
- Full maintenance schedule table
- Direct links to record maintenance

### Parts
- Grid view of all tracked parts
- Each part card shows:
  - Part name and number
  - Location
  - Description
  - Current maintenance schedule
  - Quick action buttons
- Add button to create new parts

### Maintenance
- Table view of all maintenance records
- Shows last changed date, next due date, frequency
- Quick access to update any part's maintenance

### Alerts
- Dedicated alert management page
- **Overdue Section**: Red alerts for parts needing immediate maintenance
- **Due Within 7 Days**: Orange alerts for upcoming maintenance
- **Next 30 Days**: All scheduled maintenance
- Quick action buttons for each alert

## Common Tasks

### Adding a New Part

1. Click **Parts** in navigation
2. Click **+ Add New Part** button
3. Fill in:
   - Part Name (required)
   - Description
   - Location (required)
   - Part Number (required)
4. Click **Add Part**

### Recording Maintenance

**Method 1: From Dashboard**
1. Find the overdue part in the table
2. Click **Record Now** button

**Method 2: From Part Details**
1. Click **Parts** → select a part
2. Click **Record Maintenance** button

**Recording Form**:
1. Last Changed Date (defaults to today)
2. Change Frequency in days (default 90)
3. Your name/ID
4. Optional notes
5. Click **Record Maintenance**

The system automatically calculates the next due date.

### Viewing Maintenance Instructions

1. Click **Parts** → select a part
2. Click **Instructions** button
3. View numbered steps
4. Click **Add Step** to add new instructions

Each instruction should be a clear, numbered step.

### Checking for Overdue Maintenance

1. Click **Alerts** in navigation
2. Top section shows all overdue parts
3. Click **Record Now** to immediately update
4. Use notes to document why maintenance was delayed

### Viewing Part History

1. Click **Parts** → select a part
2. Scroll to "Change History" section
3. See all maintenance activities:
   - When it was changed
   - Who changed it
   - Reason and notes

## Color Coding

- **Green Badges**: "On Schedule" - maintenance current
- **Orange Badges**: "Due Soon" - needs attention within 7 days
- **Red Badges**: "Overdue" - requires immediate action
- **Red Highlighted Rows**: Overdue maintenance items
- **Orange Highlighted Rows**: Due within 7 days

## Tips & Tricks

### Mobile Friendly
The interface works on phones and tablets. Try resizing your browser or accessing from your phone.

### Responsive Design
- Desktop: Full multi-column layout
- Tablet: 2-column grid
- Mobile: Single column, optimized for touch

### Quick Record Maintenance
- From any part card, use the **Record Maintenance** button
- From the dashboard, use **Record Now** on overdue items

### Export Data
- Right-click any table and select "Print" to print or save as PDF
- All data is stored in the SQLite database

### Keyboard Shortcuts
- **Ctrl+S** (or Cmd+S on Mac): Submit forms
- **Escape**: Close alerts

## Database Information

- All data stored in `cmms.db` (SQLite database)
- Located in the CMMS folder
- **Backup**: Copy the `cmms.db` file to backup your data
- No external database server needed

## Default Data

The system comes pre-configured with three parts:
1. **Injection Pump** (INK-PUMP-001)
2. **Electrical Resistance Heater** (INK-HEAT-001)
3. **Ink Filter Cartridge** (INK-FILT-001)

Each part has:
- 11-12 detailed maintenance instructions
- 90-day maintenance schedule
- Complete change history

## URLs Available

| URL | Purpose |
|-----|---------|
| / | Dashboard |
| /parts | All parts |
| /parts/add | Add new part |
| /parts/\<id\> | Part details |
| /parts/\<id\>/edit | Edit part |
| /maintenance | All maintenance records |
| /maintenance/record/\<id\> | Record maintenance |
| /instructions/\<id\> | View instructions |
| /instructions/\<id\>/add | Add instruction |
| /alerts | Maintenance alerts |
| /history/\<id\> | Change history |

## Troubleshooting

### Can't Access the Site
- Make sure Flask is running (terminal shows "Running on")
- Try `http://localhost:5000` (not `127.0.0.1`)
- Check if port 5000 is available

### Port Already in Use
Edit `cmms_app.py` and change port from 5000 to something else (e.g., 5001)

### Missing Data
- Check that `cmms.db` exists in the CMMS folder
- Run `python cmms_init.py` to reinitialize with default data

### Styling Issues
- Clear browser cache (Ctrl+Shift+Delete)
- Hard refresh (Ctrl+F5)
- Try a different browser

## Support

- Full documentation: `CMMS_README.md`
- Setup guide: `WEB_SETUP.md`
- CLI version: `cmms_main.py` (text-based interface)
- Database layer: `cmms_database.py`

## Features at a Glance

✓ Dashboard with quick overview  
✓ Parts management  
✓ Maintenance scheduling  
✓ Step-by-step instructions  
✓ Maintenance recording  
✓ Overdue alerts  
✓ Change history tracking  
✓ Mobile responsive  
✓ No setup required  
✓ SQLite database  
✓ Professional UI  
✓ Color-coded status badges  

Enjoy using your CMMS!
