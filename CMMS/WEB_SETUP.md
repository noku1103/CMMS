# CMMS Web Application Setup Guide

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

## Installation & Setup

### 1. Install Dependencies

```bash
cd CMMS
pip install -r requirements.txt
```

### 2. Run the Web Application

```bash
python cmms_app.py
```

### 3. Open in Browser

Open your web browser and navigate to:
```
http://localhost:5000
```

You should see the CMMS dashboard with your maintenance data.

## Features

### Dashboard
- Quick overview of maintenance status
- Cards showing total parts, overdue maintenance, and upcoming tasks
- Maintenance status table with color-coded badges

### Parts Management
- View all tracked parts in card layout
- Add new parts with detailed information
- Edit part details
- Quick access to maintenance, instructions, and history

### Part Details Page
- Complete part information
- Current maintenance schedule
- Maintenance instructions (numbered steps)
- Change history log
- Update maintenance records

### Maintenance Recording
- Form-based interface to record maintenance
- Pre-fills with today's date
- Configure maintenance frequency per part
- Add notes about the maintenance performed
- Automatic calculation of next due date

### Instructions
- View step-by-step procedures for each part
- Easy-to-read numbered format
- Add new instructions as needed

### Alerts Section
- Separate page for maintenance alerts
- Overdue maintenance highlighted in red
- Due within 7 days highlighted in orange
- Upcoming 30-day maintenance view
- Quick action links to record or view instructions

### Change History
- Complete audit trail of all maintenance activities
- Track who performed maintenance and when
- View notes and reasons for changes

## Web Interface Pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | / | Overview and quick stats |
| Parts | /parts | View all parts |
| Add Part | /parts/add | Create new part |
| Part Details | /parts/<id> | View part information |
| Edit Part | /parts/<id>/edit | Modify part details |
| Maintenance | /maintenance | All maintenance records |
| Record Maintenance | /maintenance/record/<id> | Log maintenance activity |
| Instructions | /instructions/<id> | View part procedures |
| Add Instruction | /instructions/<id>/add | Add new step |
| Alerts | /alerts | Maintenance alerts |
| History | /history/<id> | Change history log |

## Customization

### Change Port

Edit `cmms_app.py` and change the port number:

```python
if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=8000)  # Change 5000 to 8000
```

### Enable Remote Access

To allow access from other machines on your network:

```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # Change localhost to 0.0.0.0
```

Then access from other machines using: `http://<your-ip>:5000`

### Disable Debug Mode

For production use, disable debug mode:

```python
if __name__ == '__main__':
    app.run(debug=False, host='localhost', port=5000)
```

## Styling

The web interface uses a modern, responsive design with:

- Professional color scheme
- Gradient backgrounds for headers
- Card-based layouts
- Mobile-responsive grid system
- Color-coded status badges
- Hover effects and transitions

All styling is in `static/style.css`

## Database

The system uses SQLite database (`cmms.db`) which:
- Stores all parts, maintenance records, and history
- Automatically created on first run
- Can be backed up by copying the `cmms.db` file
- No external database server required

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, change it in `cmms_app.py`:

```python
app.run(debug=True, host='localhost', port=5001)  # Use different port
```

### Module Not Found Error

Ensure Flask is installed:

```bash
pip install -r requirements.txt
```

### Database Issues

If you have database issues, reinitialize:

```bash
python cmms_init.py
```

This will create a fresh database with default parts.

## Tips

- **Backups**: Regular backup `cmms.db` file to prevent data loss
- **Records**: Always record maintenance immediately after performing it
- **Notes**: Use the notes field to document any issues or special observations
- **Instructions**: Keep instructions up-to-date if procedures change
- **Frequency**: Adjust maintenance frequency per part as needed

## Security Notes

- The application uses a simple secret key for session management
- For production deployment, use a strong, random secret key
- Consider running behind a reverse proxy (nginx, Apache) for production
- Database is stored locally - ensure proper file permissions
