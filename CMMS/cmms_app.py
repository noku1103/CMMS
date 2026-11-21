from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, g
from datetime import datetime, timedelta
from cmms_database import CMmsDatabase
import os

app = Flask(__name__)
app.secret_key = 'cmms_secret_key_2026'

def get_db():
    """Get database connection for the current request"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = CMmsDatabase()
    return db


@app.route('/')
def index():
    """Dashboard with maintenance overview"""
    db = get_db()
    parts = db.get_all_parts()
    overdue = db.get_overdue_maintenance()
    upcoming = db.get_upcoming_maintenance(30)
    all_records = db.get_all_maintenance_records()

    now = datetime.now()
    now_iso = now.isoformat()
    future_7 = (now + timedelta(days=7)).isoformat()

    dashboard_data = {
        'total_parts': len(parts),
        'overdue_count': len(overdue),
        'upcoming_count': len(upcoming),
        'overdue': overdue,
        'upcoming': upcoming,
        'all_records': all_records,
        'now_iso': now_iso,
        'future_7': future_7,
        'now': now
    }

    return render_template('dashboard.html', data=dashboard_data)


@app.route('/parts')
def parts():
    """View all parts"""
    db = get_db()
    parts_list = db.get_all_parts()
    parts_with_records = []

    for part in parts_list:
        record = db.get_maintenance_record(part['id'])
        parts_with_records.append({
            'part': part,
            'record': record
        })

    return render_template('parts.html', parts=parts_with_records)


@app.route('/parts/add', methods=['GET', 'POST'])
def add_part():
    """Add new part"""
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        part_number = request.form.get('part_number')

        part_id = db.add_part(name, description, location, part_number)
        if part_id:
            flash(f'Part "{name}" added successfully!', 'success')
            return redirect(url_for('parts'))
        else:
            flash(f'Part "{name}" already exists!', 'error')

    return render_template('add_part.html')


@app.route('/parts/<int:part_id>')
def view_part(part_id):
    """View part details and history"""
    db = get_db()
    part = db.get_part(part_id)
    if not part:
        flash('Part not found', 'error')
        return redirect(url_for('parts'))

    record = db.get_maintenance_record(part_id)
    instructions = db.get_instructions(part_id)
    history = db.get_change_history(part_id)

    return render_template('part_detail.html',
                         part=part,
                         record=record,
                         instructions=instructions,
                         history=history)


@app.route('/parts/<int:part_id>/edit', methods=['GET', 'POST'])
def edit_part(part_id):
    """Edit part details"""
    db = get_db()
    part = db.get_part(part_id)
    if not part:
        flash('Part not found', 'error')
        return redirect(url_for('parts'))

    if request.method == 'POST':
        description = request.form.get('description')
        location = request.form.get('location')

        db.cursor.execute('''
            UPDATE parts SET description = ?, location = ? WHERE id = ?
        ''', (description, location, part_id))
        db.conn.commit()

        flash(f'Part "{part["name"]}" updated successfully!', 'success')
        return redirect(url_for('view_part', part_id=part_id))

    return render_template('edit_part.html', part=part)


@app.route('/maintenance')
def maintenance():
    """View all maintenance records"""
    db = get_db()
    records = db.get_all_maintenance_records()
    return render_template('maintenance.html', records=records)


@app.route('/maintenance/record/<int:part_id>', methods=['GET', 'POST'])
def record_maintenance(part_id):
    """Record maintenance for a part"""
    db = get_db()
    part = db.get_part(part_id)
    if not part:
        flash('Part not found', 'error')
        return redirect(url_for('parts'))

    if request.method == 'POST':
        last_changed = request.form.get('last_changed')
        frequency = int(request.form.get('frequency', 90))
        performed_by = request.form.get('performed_by')
        notes = request.form.get('notes')

        db.update_maintenance_record(
            part_id, last_changed, frequency, performed_by, notes
        )

        flash(f'Maintenance recorded for "{part["name"]}"!', 'success')
        return redirect(url_for('view_part', part_id=part_id))

    record = db.get_maintenance_record(part_id)
    today = datetime.now().date().isoformat()

    return render_template('record_maintenance.html',
                         part=part,
                         record=record,
                         today=today)


@app.route('/instructions/<int:part_id>')
def view_instructions(part_id):
    """View maintenance instructions for a part"""
    db = get_db()
    part = db.get_part(part_id)
    if not part:
        flash('Part not found', 'error')
        return redirect(url_for('parts'))

    instructions = db.get_instructions(part_id)
    return render_template('instructions.html', part=part, instructions=instructions)


@app.route('/instructions/<int:part_id>/add', methods=['GET', 'POST'])
def add_instruction(part_id):
    """Add maintenance instruction"""
    db = get_db()
    part = db.get_part(part_id)
    if not part:
        flash('Part not found', 'error')
        return redirect(url_for('parts'))

    if request.method == 'POST':
        instruction_text = request.form.get('instruction_text')
        step_number = int(request.form.get('step_number', 1))

        db.add_instruction(part_id, instruction_text, step_number)
        flash('Instruction added!', 'success')
        return redirect(url_for('view_instructions', part_id=part_id))

    instructions = db.get_instructions(part_id)
    next_step = len(instructions) + 1

    return render_template('add_instruction.html',
                         part=part,
                         next_step=next_step)


@app.route('/alerts')
def alerts():
    """View maintenance alerts"""
    db = get_db()
    overdue = db.get_overdue_maintenance()
    upcoming = db.get_upcoming_maintenance(30)
    upcoming_critical = db.get_upcoming_maintenance(7)

    alerts_data = {
        'overdue': overdue,
        'upcoming_7days': upcoming_critical,
        'upcoming_30days': upcoming
    }

    return render_template('alerts.html', data=alerts_data)


@app.route('/history/<int:part_id>')
def view_history(part_id):
    """View change history for a part"""
    db = get_db()
    part = db.get_part(part_id)
    if not part:
        flash('Part not found', 'error')
        return redirect(url_for('parts'))

    history = db.get_change_history(part_id)
    return render_template('history.html', part=part, history=history)


@app.route('/api/parts')
def api_parts():
    """API endpoint for parts data"""
    db = get_db()
    parts = db.get_all_parts()
    return jsonify([dict(p) for p in parts])


@app.route('/api/maintenance-status')
def api_maintenance_status():
    """API endpoint for maintenance status"""
    db = get_db()
    overdue = db.get_overdue_maintenance()
    upcoming = db.get_upcoming_maintenance(30)

    return jsonify({
        'overdue_count': len(overdue),
        'upcoming_count': len(upcoming),
        'total_overdue': len(overdue)
    })


@app.teardown_appcontext
def close_db(error):
    """Close database connection for this request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Ball Pen Production Line - CMMS Web Application")
    print("="*60)
    print("\nStarting web server...")
    print("Open your browser and go to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")

    app.run(debug=True, host='localhost', port=5000)
