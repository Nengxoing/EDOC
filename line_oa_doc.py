from datetime import datetime
from flask import Flask, json, render_template, jsonify, request, session
import os
import requests
from ecom import app
from dbconn import * 
# from dbconn_biotime import * 

# ************************ E Documents start ************************
@app.route('/edocument_menu')
def edocument_menu():
    return render_template('eDocuments/layouts/edocument_menu.html')

@app.route('/delete_doc/<doc_no>', methods=['POST'])
def delete_doc(doc_no):
    try:
        
        with getcursor() as cur:
            cur.execute("SELECT file_name FROM edoc_department WHERE doc_no = %s", (doc_no,))
            file_data = cur.fetchone()
        
        if file_data and file_data['file_name']:
            file_path = os.path.join('static', 'edoc_files', file_data['file_name'])
            
             
            if os.path.exists(file_path):
                os.remove(file_path)  
            
        
        with getcursor() as cur:
            cur.execute("DELETE FROM edoc_department WHERE doc_no = %s", (doc_no,))
        
        return jsonify({"success": True})  
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/doc_list_mb')
def doc_list_mb():

    log_data = session.get("employee_json")
    # log_code = log_data.get('emp_code') if log_data else None

    log_code = '24062'

    try:
        documents = []
        doc_types = []
        departments = []
        user_title = None

        with getcursor() as cur:
            cur.execute("""
                SELECT
                    oel.department_code,
                    oel.department_name,
                    eu.title
                FROM 
                    odg_employee_list oel
                LEFT JOIN 
                    erp_user eu ON eu.code = oel.emp_code
                WHERE 
                    oel.emp_code = %s
            """, (log_code,))
            user = cur.fetchone()

            if user:
                user_title = user['title']
                department_code = user['department_code']
                department_name = user['department_name']
                # print("\n******* department_code *******", department_code)
            else:
                return "User not found", 404
 
            if user_title == 'manager': 
                # print("\n******* it is if *******")
                cur.execute('''
                    SELECT   
                        d.doc_no,
                        d.doc_date,
                        d.doc_time,
                        d.doc_name,
                        u.name_1 AS creator_name,
                        dl.name_1 AS department_name,
                        dt.name_1 AS document_type_name
                    FROM 
                        public.edoc_department d
                    LEFT JOIN 
                        public.odg_department_list dl ON d.department_code = dl.code
                    LEFT JOIN 
                        public.edoc_type dt ON d.doc_group = dt.code
                    LEFT JOIN 
                        public.erp_user u ON d.creator_code = u.code
                    ORDER BY 
                        d.doc_date DESC
                    LIMIT 30;
                ''')
            else:
                # print("\n******* it is else *******")
                cur.execute('''
                    WITH ranked AS (
                        SELECT   
                            d.doc_no,
                            d.doc_date,
                            d.doc_time,
                            d.doc_name,
                            u.name_1 AS creator_name,
                            dl.name_1 AS department_name,  -- department_name จาก odg_department_list
                            dt.name_1 AS document_type_name,
                            cdv.department_code,
                            cdv.department_name AS cdv_department_name,  -- department_name จาก choose_department_view
                            ROW_NUMBER() OVER (PARTITION BY d.doc_no ORDER BY cdv.department_code) AS rn
                        FROM 
                            edoc_department d
                        LEFT JOIN 
                            odg_department_list dl ON d.department_code = dl.code
                        LEFT JOIN 
                            edoc_type dt ON d.doc_group = dt.code
                        LEFT JOIN 
                            erp_user u ON d.creator_code = u.code
                        LEFT JOIN 
                            choose_department_view cdv ON cdv.doc_no = d.doc_no
                        WHERE
                            cdv.department_code = %s
                    )
                    SELECT 
                        doc_no,
                        doc_date,
                        doc_time,
                        doc_name,
                        creator_name,
                        department_name,
                        cdv_department_name,
                        document_type_name
                    FROM 
                        ranked
                    WHERE 
                        rn = 1
                    ORDER BY 
                        doc_no DESC;
                ''', (department_code,))
                
            for row in cur:
                documents.append({
                    'doc_no': row['doc_no'],
                    'doc_date': row['doc_date'].strftime('%d/%m/%Y') if row['doc_date'] else None,
                    'doc_name': row['doc_name'],
                    'creator_name': row['creator_name'],
                    'department_name': row['department_name'],
                    'document_type_name': row['document_type_name'],
                })
            
            cur.execute('''
                SELECT code, name_1
                FROM public.edoc_type;
            ''')
            for row in cur:
                doc_types.append({
                    'code': row['code'],
                    'name_1': row['name_1']
                })

            cur.execute("SELECT code, name_1 FROM public.odg_department_list")
            for doc in cur:
                departments.append({
                    'code': doc['code'],
                    'name_1': doc['name_1']
                })
                 
        return render_template('eDocuments/documents/pages/documents/doc_list_mb.html',departments=departments, documents=documents, doc_types=doc_types, user_title=user_title)

    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/add_document', methods=['GET'])
def add_document():

    log_data = session.get("employee_json")
    emp_code = log_data.get('emp_code') if log_data else None

    user_data = None

    with getcursor() as cur: 
        cur.execute('SELECT code, name_1 FROM edoc_type;')
        doc_types = cur.fetchall()

        cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s ",(emp_code,))
        user_data = cur.fetchone()

        cur.execute("SELECT code, name_1 FROM odg_department_list ORDER BY code ASC")
        department = cur.fetchall()

    return render_template('eDocuments/documents/pages/documents/add_document.html', doc_types=doc_types, user_data=user_data, department=department)

@app.route('/insert_document', methods=['POST'])
def insert_document():

    log_data = session.get("employee_json")
    emp_code = log_data.get('emp_code') if log_data else None

    with getcursor() as cur:
        cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s ",(emp_code,))
        user_data = cur.fetchone()

    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    cur.execute("SELECT department_code, department_name FROM department WHERE emp_code = ?",(emp_code,))
    choose_dept = cur.fetchall()
    print("\nchoose_dept:", choose_dept)

    if user_data is None:
        return "User data not found!", 400

    doc_no = request.form['doc_no']
    doc_date = request.form['doc_date']
    doc_type = request.form['doc_type']
    doc_ref = request.form['doc_ref']
    doc_name = request.form['doc_name']
    doc_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 
    file_name = None
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        file_path = f'static/edoc_files/{file.filename}'
        try:
            file.save(file_path)
            file_name = file.filename
        except Exception as e:
            return f'Error saving file: {str(e)}', 500

    with getcursor() as cur:
        cur.execute('''
            INSERT INTO edoc_department (
                doc_no, doc_date, doc_time, doc_ref, doc_name, creator_code, department_code, doc_group, file_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        ''', (doc_no, doc_date, doc_time, doc_ref, doc_name, user_data['emp_code'], user_data['department_code'], doc_type, file_name))

        # select and insert step
        for dept in choose_dept:
            cur.execute("INSERT INTO choose_department_view (department_code, department_name, doc_no) VALUES (%s, %s, %s)", 
                        (dept[0], dept[1], doc_no))
            
    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM department WHERE emp_code = ?",(emp_code,))
    conn.commit()
    conn.close()

    return redirect(url_for('doc_list_mb'))

@app.route('/get_update/<doc_no>', methods=['GET'])
def get_update(doc_no):
    
    log_data = session.get("employee_json")
    emp_code = log_data.get('emp_code') if log_data else None
    
    doc_types = []

    with getcursor() as cur:
        cur.execute('''
                SELECT 
                    d.doc_no,
                    d.doc_date,
                    d.doc_time,
                    d.doc_name,
                    d.doc_ref,
                    u.name_1 AS creator_name,
                    dl.name_1 AS department_name,
                    dt.code AS type_code,
                    dt.name_1 AS type_name,
                    d.file_name AS file
                FROM 
                    public.edoc_department d
                LEFT JOIN 
                    public.odg_department_list dl ON d.department_code = dl.code
                LEFT JOIN 
                    public.edoc_type dt ON d.doc_group = dt.code 
                LEFT JOIN 
                    public.erp_user u ON d.creator_code = u.code 
                WHERE 
                    d.doc_no = %s 
                ORDER BY 
                    d.doc_date DESC; 
            ''', (doc_no,))
        get_update = cur.fetchone()
        # print("\nData:", get_update)
        
        cur.execute("SELECT code, name_1 FROM edoc_type;")
        doc_types = cur.fetchall()

        cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s ",(emp_code,))
        user_data = cur.fetchone()

        cur.execute("SELECT code, name_1 FROM odg_department_list ORDER BY code ASC")
        department = cur.fetchall()
        
        # select from postgresql 
        cur.execute("SELECT department_code, department_name, doc_no FROM choose_department_view WHERE doc_no = %s",(doc_no,))
        choose_dept = cur.fetchall()
        print("\nchoose_dept:", choose_dept)

        conn = sqlite3.connect('edocuments.db')
        cur = conn.cursor()

        cur.execute("DELETE FROM department WHERE doc_no = ?",(doc_no,))
        conn.commit()

        # insert into sqlite 
        for dept in choose_dept:
            cur.execute(
                "INSERT INTO department (department_code, department_name, emp_code, doc_no) VALUES (?, ?, ?, ?)",
                (dept['department_code'], dept['department_name'], emp_code, doc_no,)
            )
        conn.commit()
        cur.close()
        conn.close()

    return render_template('eDocuments/documents/pages/documents/update_doc.html', 
                            documents=get_update, 
                            doc_types=doc_types, 
                            user_data=user_data, 
                            department=department, 
                            choose_dept=choose_dept
                        )

@app.route('/update_doc', methods=['POST'])
def update_doc():

    user_data = session.get("employee_json")
    emp_code = user_data.get('emp_code') if user_data else None

    doc_no = request.form['doc_no']
    doc_date = request.form['doc_date']
    doc_type = request.form['doc_type']
    doc_ref = request.form['doc_ref']
    doc_name = request.form['doc_name']
    doc_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    file_name = None
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        file_path = f'static/edoc_files/{file.filename}'
        try:
            file.save(file_path)
            file_name = file.filename
        except Exception as e:
            return f'Error saving file: {str(e)}', 500
    else:
        with getcursor() as cur:
            cur.execute("""
                SELECT file_name 
                FROM edoc_department 
                WHERE doc_no = %s
            """, (doc_no,))
            existing_file = cur.fetchone()
            if existing_file:
                file_name = existing_file['file_name']

    with getcursor() as cur:
        cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s", (emp_code,))
        user_data = cur.fetchone()

        print("\nData update: ", doc_no, doc_date, doc_time, doc_ref, doc_name, user_data['emp_code'], user_data['department_code'], doc_type, file_name)
        print("\n")

        cur.execute("""
            UPDATE 
                edoc_department 
            SET 
                doc_no = %s, 
                doc_date = %s, 
                doc_time = %s, 
                doc_ref = %s, 
                doc_name = %s, 
                creator_code = %s, 
                department_code = %s, 
                doc_group = %s, 
                file_name = %s
            WHERE 
                doc_no = %s
        """, (doc_no, 
              doc_date, 
              doc_time, 
              doc_ref, 
              doc_name, 
              user_data['emp_code'], 
              user_data['department_code'], 
              doc_type, 
              file_name, 
              doc_no))
        
        conn = sqlite3.connect('edocuments.db')
        cur = conn.cursor()

        cur.execute("SELECT department_code, department_name, doc_no FROM department WHERE doc_no = ?",(doc_no,))
        choose_dept = cur.fetchall()
        print("\nchoose_dept:", choose_dept)

        with getcursor() as cur:
            cur.execute("DELETE FROM choose_department_view WHERE doc_no = %s",(doc_no,))
            
            for dept in choose_dept:
                cur.execute("INSERT INTO choose_department_view (department_code, department_name, doc_no) VALUES (%s, %s, %s)", 
                            (dept[0], dept[1], doc_no))

        conn = sqlite3.connect('edocuments.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM department WHERE doc_no = ?",(doc_no,))
        conn.commit()

    return redirect(url_for('doc_list_mb'))

@app.route('/report_doc', methods=['GET'])
def report_doc():

    log_data = session.get("employee_json")
    log_code = log_data.get('emp_code') if log_data else None

    try:
        documents = []
        doc_types = []
        departments = []
        user_title = None

        with getcursor() as cur:
            cur.execute('SELECT title, department FROM public.erp_user WHERE code = %s', (log_code,))
            user = cur.fetchone()

            if user:
                user_title = user['title']
                department_code = user['department']
            else:
                return "User not found", 404

            if user_title == 'manager':
                cur.execute('''
                    SELECT 
                        d.doc_no,
                        d.doc_date,
                        d.doc_time,
                        d.doc_name,
                        u.name_1 AS creator_name,
                        dl.name_1 AS department_name,
                        dt.name_1 AS document_type_name
                    FROM 
                        public.edoc_department d
                    LEFT JOIN 
                        public.odg_department_list dl ON d.department_code = dl.code
                    LEFT JOIN 
                        public.edoc_type dt ON d.doc_group = dt.code
                    LEFT JOIN 
                        public.erp_user u ON d.creator_code = u.code
                    ORDER BY 
                        d.doc_date DESC;
                ''')
            else:
                cur.execute('''
                    SELECT 
                        d.doc_no,
                        d.doc_date,
                        d.doc_time,
                        d.doc_name,
                        u.name_1 AS creator_name,
                        dl.name_1 AS department_name,
                        dt.name_1 AS document_type_name
                    FROM 
                        public.edoc_department d
                    LEFT JOIN 
                        public.odg_department_list dl ON d.department_code = dl.code
                    LEFT JOIN 
                        public.edoc_type dt ON d.doc_group = dt.code
                    LEFT JOIN 
                        public.erp_user u ON d.creator_code = u.code
                    WHERE 
                        d.department_code = %s
                    ORDER BY 
                        d.doc_date DESC;
                ''', (department_code,))
                
            for row in cur:
                documents.append({
                    'doc_no': row['doc_no'],
                    'doc_date': row['doc_date'].strftime('%d/%m/%Y') if row['doc_date'] else None,
                    'doc_name': row['doc_name'],
                    'creator_name': row['creator_name'],
                    'department_name': row['department_name'],
                    'document_type_name': row['document_type_name'],
                })

            print("\nDocuments:", documents)
            print("\n")
            
            cur.execute('''
                SELECT code, name_1
                FROM public.edoc_type;
            ''')

            for row in cur:
                doc_types.append({
                    'code': row['code'],
                    'name_1': row['name_1']
                })

            cur.execute("SELECT code, name_1 FROM public.erp_department_list")
            for doc in cur:
                departments.append({
                    'code': doc['code'],
                    'name_1': doc['name_1']
                })

        return render_template('eDocuments/documents/pages/documents/report_doc.html', departments=departments, documents=documents, doc_types=doc_types, user_title=user_title)
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500
    
@app.route('/doc_detail/<doc_no>', methods = ['GET'])
def doc_detail(doc_no):
    log_data = session.get("employee_json")
    emp_code = log_data.get('emp_code') if log_data else None
    
    doc_types = []

    with getcursor() as cur:
        cur.execute('''
                SELECT 
                    d.doc_no,
                    d.doc_date,
                    d.doc_time,
                    d.doc_name,
                    d.doc_ref,
                    u.name_1 AS creator_name,
                    dl.name_1 AS department_name,
                    dt.code AS type_code,
                    dt.name_1 AS type_name,
                    d.file_name AS file
                FROM 
                    public.edoc_department d
                LEFT JOIN 
                    public.odg_department_list dl ON d.department_code = dl.code
                LEFT JOIN 
                    public.edoc_type dt ON d.doc_group = dt.code
                LEFT JOIN 
                    public.erp_user u ON d.creator_code = u.code
                WHERE 
                    d.doc_no = %s
                ORDER BY 
                    d.doc_date DESC;
            ''', (doc_no,))
        get_update = cur.fetchone()
        # print("\nGet data:", get_update)
        
        cur.execute("SELECT code, name_1 FROM edoc_type;")
        doc_types = cur.fetchall()

        cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s ",(emp_code,))
        user_data = cur.fetchone()

    return render_template('eDocuments/documents/pages/documents/doc_detail.html', get_update=get_update, doc_types=doc_types, user_data=user_data)

@app.route('/viewed_documents', methods=['POST'])
def viewed_documents():
    
    log_data = session.get("employee_json")
    emp_code = log_data.get('emp_code') if log_data else None
    
    data = request.get_json()
    docNo = data.get('docNo')
    
    with getcursor() as cur:
        
        log_data = session.get("employee_json")
        emp_code = log_data.get('emp_code') if log_data else None
        docNo = data.get('docNo')
        
        cur.execute("SELECT 1 FROM viewed_documents WHERE emp_code = %s AND doc_no = %s", (emp_code, docNo))
        existing_record = cur.fetchone()

        if existing_record:
            print("This employee has already viewed this document!")
        else:
            cur.execute('''
                INSERT INTO viewed_documents (emp_code, doc_no)
                VALUES (%s, %s);
            ''', (emp_code, docNo))

    return jsonify({'message': 'Document viewed successfully!'}), 200