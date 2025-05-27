from datetime import datetime
from flask import Flask, json, render_template, jsonify, request, session
import os
import requests
from ecom import app 
from dbconn import * 
# from dbconn_biotime import * 
import sqlite3

conitdb = sqlite3.connect('edocuments.db')
            
UPLOAD_FOLDER = 'static/edoc_sqlite'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def drop_subtypes_table():
    try:
        conn = sqlite3.connect('edocuments.db')
        cursor = conn.cursor()
        cursor.execute('''
            DROP TABLE IF EXISTS subtypes
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
drop_subtypes_table()

def create_subtypes_table():
    try:
        conn = sqlite3.connect('edocuments.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtypes 
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_code TEXT,
                subtype_code TEXT,
                doc_type_name TEXT,
                file_name TEXT,
                purpose TEXT,
                user_code TEXT,
                user_name TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if conn:
            conn.close()
create_subtypes_table()

def drop_department():
    try:
        conn = sqlite3.connect('edocuments.db')
        cursor = conn.cursor()
        cursor.execute('''
            DROP TABLE IF EXISTS department
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
drop_department()

def create_department_table():
    try:
        conn = sqlite3.connect('edocuments.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS department 
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_code TEXT,
                department_name TEXT,
                emp_code TEXT,
                doc_no TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if conn:
            conn.close()
create_department_table()

@app.route('/subtype_get', methods=['GET'])
def subtype_get():

    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    cur.execute("SELECT subtype_code, doc_type_name, file_name, purpose FROM subtypes")
    rows = cur.fetchall()
    conn.close()

    subtype_data = [{
        'subtype_code': row[0],
        'doc_type_name': row[1], 
        'file_name': row[2],
        'purpose': row[3]
    } for row in rows]
    # print("\nsubtype_data:", subtype_data)
    return jsonify(subtype_data)

@app.route('/subtype_detail', methods=['POST'])
def subtype_detail():
    data = request.get_json()
    subtype_code = data.get('subtype_code')
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    cur.execute("SELECT subtype_code, doc_type_name, file_name, purpose, type_code FROM subtypes WHERE subtype_code = ?", (subtype_code,))
    row = cur.fetchone()
    conn.close()
    
    if row: 
        subtype_detail = {
            'subtype_code': row[0],
            'doc_type_name': row[1],
            'file_name': row[2],
            'purpose': row[3],
            'type_code': row[4]
        }
        # print("\nsubtype_detail:", subtype_detail)
        return jsonify(subtype_detail), 200
    else:
        return jsonify({'error': 'Subtype not found'}), 404

@app.route('/add_subtype', methods=['POST'])
def add_subtype():

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None
    emp_name = emp_data.get('emp_name') if emp_data else None

    subtype_code = request.form.get('doc_subtype')
    type_code = request.form.get('doc_type')
    purpose = request.form.get('purpose')
    file = request.files.get('subtype_file')
    doc_type_name = request.form.get('doc_subtype_display')

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    file_name = file.filename

    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO subtypes (type_code, subtype_code, doc_type_name, file_name, purpose, user_code, user_name) 
        VALUES (?, ?, ?, ?, ?, ?, ?) 
    ''', (type_code, subtype_code, doc_type_name, file_name, purpose, emp_code, emp_name))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Data received successfully'}), 200

@app.route('/delete_subtype', methods=['POST'])
def delete_subtype():
    data = request.get_json()
    subtype_code = data.get('subtype_code')

    if not subtype_code:
        return jsonify({'error': 'subtype_code is required'}), 400

    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    
    cur.execute("DELETE FROM subtypes WHERE subtype_code = ?", (subtype_code,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Data deleted successfully'}), 200

@app.route('/check_type_code', methods=['POST'])
def check_type_code():
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    cur.execute("SELECT type_code FROM subtypes")
    row = cur.fetchone()
    conn.close()

    # if row:
    #     print("\ntype_code row:", row)
    # else:
    #     print("\nNo type row !")
    
    if row:
        type_code = {
            'type_code': row[0]
        }
        # print("\ntype_code:", type_code)
        return jsonify(type_code), 200
    else:
        return jsonify({'error': 'Subtype not found'}), 404

@app.route('/restoreDoctype', methods=['POST'])
def restoreDoctype():
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    cur.execute("SELECT type_code FROM subtypes")
    row = cur.fetchone()
    conn.close()

    # if row:
    #     print("\ntype_code row for restore:", row)
    # else:
    #     print("\nNo type row for restore !")
    #     return jsonify({'error': 'Subtype not found'}), 404
    
    with getcursor() as cur:
        cur.execute("SELECT code, name_1 FROM edoc_type WHERE code = %s", (row[0],))
        docTypeRestore = cur.fetchone()

    if docTypeRestore:
        result = {
            'code': docTypeRestore['code'], 
            'name': docTypeRestore['name_1'],
        }
        # print("\ndocTypeRestore:", result)
        return jsonify(result), 200
    else:
        return jsonify({'error': 'Document type not found'}), 404
    
@app.route('/restoreDoctypeReload', methods=['POST'])
def restoreDoctypeReload():
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()
    cur.execute("SELECT type_code FROM subtypes LIMIT 1")
    row = cur.fetchone()
    conn.close()

    if row:
        type_code = row[0]
        # print("\nType code found:", type_code)

        with getcursor() as cur:
            cur.execute("SELECT code, name_1 FROM edoc_type WHERE code = %s", (type_code,))
            docTypeRestore = cur.fetchone()

        if docTypeRestore:
            result = {'code': docTypeRestore['code'], 'name': docTypeRestore['name_1']}
            return jsonify(result), 200
        # print("\nrestoreDoctypeReload:", result)

    return jsonify({'error': 'No document type found'}), 404

@app.route('/get_last_type_code', methods=['GET'])
def get_last_type_code():
    try:
        conn = sqlite3.connect('edocuments.db')
        cur = conn.cursor()
        cur.execute("SELECT type_code FROM subtypes LIMIT 1")
        row = cur.fetchone()
        conn.close()

        if row:
            return jsonify({'type_code': row[0]}), 200
        else:
            return jsonify({'error': 'No type_code found'}), 404

    except Exception as e:
        print("Error fetching type_code:", str(e))
        return jsonify({'error': 'Internal server error'}), 500
    
@app.route('/back_pps_list')
def back_pps_list():
    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    if emp_code is None:
        return jsonify({"error": "No emp_code found"}), 400

    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM subtypes WHERE user_code = ?", (emp_code,))
        conn.commit()
        return jsonify({"message": "Data deleted successfully"})
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
        
@app.route('/post_department', methods=['POST'])
def post_department():
    
    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    # Get JSON data from the request
    data = request.get_json()
    dept_code = data.get('dept_code')
    dept_text = data.get('dept_text')

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    if not dept_code or not dept_text:
        return jsonify({"error": "Invalid input. Department code and name are required."}), 400
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    try:    
        cur.execute(
            "INSERT INTO department (department_code, department_name, emp_code) VALUES (?, ?, ?)",
            (dept_code, dept_text, emp_code)
        )
        conn.commit()

        cur.execute("SELECT department_code, department_name FROM department")
        departments = cur.fetchall()

    except sqlite3.IntegrityError as e: 
        print("Database Integrity Error:", e)
        return jsonify({"error": "Department already exists or invalid data."}), 409
    except Exception as e:
        print("Database Error:", e)
        return jsonify({"error": "An error occurred while saving the department."}), 500
    finally:
        conn.close()
        
    return jsonify({
        "message": "Department saved successfully",
        "departments": departments
    }), 200

@app.route('/post_department_update', methods=['POST'])
def post_department_update():
    
    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    # Get JSON data from the request
    data = request.get_json()
    dept_code = data.get('dept_code')
    dept_text = data.get('dept_text')
    docNo = data.get('docNo')

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    if not dept_code or not dept_text:
        return jsonify({"error": "Invalid input. Department code and name are required."}), 400
    
    with getcursor() as cur:
            cur.execute("""
                SELECT 
                    department_code, 
                    department_name, 
                    doc_no 
                FROM 
                    choose_department_view 
                WHERE 
                    doc_no = %s
            """, (docNo,))
            choose_department_view = cur.fetchone()
            print("\nchoose_department_view:", choose_department_view)
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    try:    
        cur.execute(
            "INSERT INTO department (department_code, department_name, emp_code, doc_no) VALUES (?, ?, ?, ?)",
            (dept_code, dept_text, emp_code, choose_department_view['doc_no'])
        )
        conn.commit()

        cur.execute("SELECT department_code, department_name FROM department")
        departments = cur.fetchall()

    except sqlite3.IntegrityError as e: 
        print("Database Integrity Error:", e)
        return jsonify({"error": "Department already exists or invalid data."}), 409
    except Exception as e:
        print("Database Error:", e)
        return jsonify({"error": "An error occurred while saving the department."}), 500
    finally:
        conn.close()
        
    return jsonify({
        "message": "Department saved successfully",
        "departments": departments
    }), 200

@app.route('/get_departments', methods=['GET'])
def get_departments():

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None
    # print("\nemp_code", emp_code)
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    try:
        cur.execute("SELECT department_code, department_name FROM department WHERE emp_code = ?", (emp_code,))
        departments = cur.fetchall()
    except Exception as e:
        print("Database Error:", e)
        return jsonify({"error": "Database error"}), 500
    finally:
        conn.close()
        
    return jsonify({"departments": departments}), 200

@app.route('/delete_department', methods=['POST'])
def delete_department():
    
    data = request.get_json()
    dept_code = data.get('dept_code')

    if not dept_code:
        return jsonify({"error": "No department code provided"}), 400
    
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM department WHERE department_code = ?", (dept_code,))
        if cur.rowcount == 0:
            return jsonify({"error": "Department not found"}), 404

        conn.commit()
    except Exception as e:
        print("Database Error:", e)
        return jsonify({"error": "An error occurred while deleting the department."}), 500
    finally:
        conn.close()

    return jsonify({"message": "Department deleted successfully"}), 200

@app.route('/delete_department_all', methods=['POST'])
def delete_department_all():
    
    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None
    
    if not emp_code:
        return jsonify({"error": "Employee code not found"}), 400

    try:
        conn = sqlite3.connect('edocuments.db')
        cur = conn.cursor()
        
        cur.execute("DELETE FROM department WHERE emp_code = ?", (emp_code,))
        if cur.rowcount == 0:
            return jsonify({"error": "Department not found"}), 404
        conn.commit()

    except Exception as e:
        return jsonify({"error": "An error occurred while deleting the department."}), 500
    finally:
        conn.close()

    return jsonify({"message": "Department deleted successfully"}), 200
