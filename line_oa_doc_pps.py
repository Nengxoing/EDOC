from datetime import datetime
from flask import Flask, json, render_template, jsonify, request, session
import os
import psycopg2
import requests
from ecom import app 
from dbconn import * 
# from dbconn_biotime import * 

# ************************ E Documents start ************************
@app.route('/pps_list')
def pps_list():

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    now = datetime.now()
    password = now.strftime("IT%d%m%Y")
    print("\nPassword:", password)
 
    doc_types = [] 
    departments = []
    
    with getcursor() as cur:
        cur.execute("""
            SELECT
                pd.doc_no,
                pd.doc_name,
                pd.creator_code,
                eml.emp_name,
                pd.department_code,
                eml.department_name,
                pd.description,
                pd.create_date AS doc_date,
                pd.create_time AS doc_time,
                et.code AS doc_type_code,
                et.name_1 AS doc_type_name,
                sd.subtype_code,
                sd.sub_type_file,
                sd.objective,
                dha.status,
                dha.approver_code,
                dha.approval_order,
                dha.remark,
                dha.create_date,
                dha.create_time
            FROM
                pps_documents pd
            LEFT JOIN
                odg_employee_list eml ON eml.emp_code = pd.creator_code
            LEFT JOIN
                subtype_data sd ON sd.doc_no = pd.doc_no
            LEFT JOIN
                edoc_type et ON et.code = sd.doc_type_code
            LEFT JOIN
                doc_history_authorize dha ON dha.doc_no = pd.doc_no
            WHERE 
                pd.creator_code = %s
        """, (emp_code,))
        pps_data = cur.fetchall();
        # print("\n Doc_no:", pps_data)

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
 
    return render_template('eDocuments/proposal/pages/pps_list.html',pps_data=pps_data, doc_types=doc_types, departments=departments)

# @app.route('/pps_add', methods=['GET'])
# def pps_add():

#     emp_data = session.get("employee_json")
#     emp_code = emp_data.get('emp_code') if emp_data else None

#     now = datetime.now()
#     password = now.strftime("ITC%d%m%Y")
#     print("\nPassword:", password)

#     with getcursor() as cur:
#         cur.execute("SELECT code, name_1 FROM edoc_type;")
#         doc_types = cur.fetchall()
        
#         user_data = None
#         if emp_code:
#             cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s ",(emp_code,))
#             user_data = cur.fetchone()
#         else:
#             print("\n Sorry, emp_code is empty!")

#     return render_template('eDocuments/proposal/pages/pps_add.html', doc_types=doc_types, emp_data=emp_data, user_data=user_data)

@app.route('/pps_add', methods=['GET'])
def pps_add():

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None

    now = datetime.now()
    password = now.strftime("IT%d%m%Y%H%M%S")
    print("\nPassword:", password)

    with getcursor() as cur:
        cur.execute("SELECT code, name_1 FROM edoc_type;")
        doc_types = cur.fetchall()
        
        user_data = None
        if emp_code:
            cur.execute("SELECT emp_code, emp_name, department_code, department_name FROM odg_employee_list WHERE emp_code = %s ",(emp_code,))
            user_data = cur.fetchone()
        else:
            print("\n Sorry, emp_code is empty!")

    return render_template('eDocuments/proposal/pages/pps_add.html', doc_types=doc_types, emp_data=emp_data, user_data=user_data)

@app.route('/insert_pps', methods=['POST'])
def insert_pps():

    emp_data = session.get("employee_json")
    # print("\n**************** emp_data **************** =", emp_data)
    emp_code = emp_data.get('emp_code') if emp_data else None

    conn = sqlite3.connect('edocuments.db')
    cur = conn.cursor()

    cur.execute("SELECT subtype_code, doc_type_name, file_name, purpose FROM subtypes")
    subtypes_data = cur.fetchall()
    conn.close()

    allData = request.get_json()
    doc_type = allData.get('doc_type')
    doc_name = allData.get('doc_name')
    doc_no = allData.get('doc_no')
    doc_date = allData.get('doc_date')
    department = allData.get('department')
    creator_name = allData.get('creator_name')
    description = allData.get('description')
    doc_type = allData.get('doc_type')
    status = '0'
    current_time = datetime.now().strftime('%H:%M:%S')
    
    with getcursor() as cur:
        cur.execute("SELECT department_code FROM odg_employee_list WHERE emp_code = %s", (emp_code,))
        user_dept = cur.fetchone()
        department_code = user_dept['department_code']

        cur.execute("""
                SELECT 
                    CAST(erp.related_level AS INTEGER) AS related_level,
                    erp.doc_type_code,
                    oll.name_1 AS related_person_name
                FROM 
                    public.edoc_related_persons erp
                LEFT JOIN 
                    public.odg_position_list rp ON erp.related_person_code = rp.code
                LEFT JOIN 
                    public.odg_level_list oll ON oll.code = erp.related_level
                WHERE 
                    erp.doc_type_code = %s
                ORDER BY 
                    CAST(erp.related_level AS INTEGER) ASC
            """, (doc_type,))
        related_data = cur.fetchall()
        print("\nrelated_data =", related_data)

        print("\ndoc_no =", doc_no)
        print("doc_name =", doc_name)
        print("doc_date =", doc_date)
        print("department_code =", department_code)
        print("creator_name =", creator_name)
        print("description =", description)
        print("doc_type =", doc_type)
        print("Current Time:", current_time)

        # cur.execute("""
        #         INSERT INTO 
        #             pps_documents
        #         VALUES (
        #             doc_no,
        #             doc_name, 
        #             creator_code, 
        #             department_code, 
        #             description, 
        #             status, 
        #             create_date, 
        #             create_time)
        # """, (doc_no, doc_name, emp_code, department_code, description, status, doc_date, current_time))
        
    return jsonify({
        "success": True,
        "message": "All Data received successfully",
        "allData": allData
    })

@app.route('/get_doc_subtypes', methods=['GET'])
def get_doc_subtypes():
    
    doc_type_code = request.args.get('type_code')
    # print(f"Received doc_type_code: {doc_type_code}")

    with getcursor() as cur:
        cur.execute("SELECT code, name_1 FROM doc_subtype WHERE type_code = %s", (doc_type_code,))
        doc_subtypes = cur.fetchall()

        cur.execute("""
            SELECT 
                CAST(erp.related_level AS INTEGER) AS related_level,
                erp.doc_type_code,
                oll.name_1 AS related_person_name
            FROM 
                public.edoc_related_persons erp
            LEFT JOIN 
                public.odg_position_list rp ON erp.related_person_code = rp.code
            LEFT JOIN 
                public.odg_level_list oll ON oll.code = erp.related_level
            WHERE 
                erp.doc_type_code = %s
            ORDER BY 
                CAST(erp.related_level AS INTEGER) ASC
        """, (doc_type_code,))
        related_data = cur.fetchall()
 
        # print("\nrelated_data:", related_data)
        
    return jsonify(doc_subtypes, related_data)

@app.route('/manage_related', methods=['GET'])
def manage_related():

    with getcursor() as cur:
        cur.execute("SELECT code, name_1 FROM edoc_type ORDER BY code ASC")
        docType_data = cur.fetchall()

        cur.execute("""
            SELECT code, name_1
            FROM odg_level_list
            ORDER BY
            CAST(code AS INTEGER) ASC
        """)
        related_data = cur.fetchall()
        
    return render_template('eDocuments/proposal/pages/manage_related.html', docType_data=docType_data, related_data=related_data)

@app.route('/insert_related', methods=['POST'])
def insert_related():
    data = request.json
    related_code = data.get('related_code')
    doc_type_code = data.get('doc_type_code')
    # print("\nrelated_code:", related_code)
    # print("\ndoc_type_code:", doc_type_code)

    with getcursor() as cur:
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM edoc_related_persons 
            WHERE doc_type_code = %s AND related_level = %s
        """, (doc_type_code, related_code))
        row_count = cur.fetchone()

        if row_count['count'] > 0:
            
            return jsonify({'error': 'ຕຳແໜ່ງນີ້ມີແລ້ວ'}), 400
        
        cur.execute("SELECT COUNT(*) FROM edoc_related_persons WHERE doc_type_code = %s", (doc_type_code,))
        row_count = cur.fetchone()
        related_no = row_count['count'] + 1
        # print("\nrel_no;", related_no)

        cur.execute("""
            INSERT INTO edoc_related_persons (
                doc_type_code, 
                related_no,
                related_level
            ) 
            VALUES (%s, %s, %s)
        """, (doc_type_code, related_no, related_code))

    return jsonify({'success': True})

@app.route('/get_related_data', methods=['POST'])
def get_related_data():

    data = request.json
    docType_code = data.get('type_code')
    response_data = []

    with getcursor() as cur:
        cur.execute("""
            SELECT 
            CAST(erp.related_level AS INTEGER) AS related_level,
                erp.doc_type_code,
                oll.name_1 AS related_person_name
            FROM 
                public.edoc_related_persons erp
            LEFT JOIN 
                public.odg_position_list rp ON erp.related_person_code = rp.code
            LEFT JOIN 
                public.odg_level_list oll ON oll.code = erp.related_level
            WHERE 
                erp.doc_type_code = %s
            ORDER BY 
                CAST(erp.related_level AS INTEGER) ASC
        """, (docType_code,))
        related_data = cur.fetchall()
        
        response_data = [
            {
                "related_person_code": row['related_level'], 
                "related_person_name": row['related_person_name']
            }
            for row in related_data
        ]
    return jsonify(response_data)

@app.route('/del_related', methods=['POST'])
def del_related():
    
    data = request.json
    docType_code = data.get('type_code')
    # print("\ndocType_code:", docType_code)

    with getcursor() as cur:
        cur.execute("DELETE FROM edoc_related_persons WHERE doc_type_code = %s", (docType_code,))

    return jsonify({})

@app.route('/manage_docType', methods=['GET'])
def manage_docType():

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None
    print("\nemp_data: ", emp_data)
    print("\nemp_code: ", emp_code)

    with getcursor() as cur:
        cur.execute("""
            SELECT 
                oel.emp_code,
                oel.emp_name,
                odl.code AS department_code,
                odl.name_1 AS department_name,
                et.code AS doc_type_code,
                et.name_1 AS doc_type_name
            FROM 
                odg_department_list odl
            LEFT JOIN 
                odg_employee_list oel ON oel.department_code = odl.code
            LEFT JOIN 
                edoc_type et ON et.department_code = odl.code
            WHERE 
                oel.emp_code = %s
        """, (emp_code,))
        docType_data = cur.fetchall()
        # print("\ndocType_data:", docType_data)
        
        if docType_data:
            department_code = docType_data[0]['department_code'] if isinstance(docType_data[0], dict) else docType_data[0][2]
            # print("\ndepartment_code:", department_code)
        else:
            department_code = None
            print("\nNo data found for department_code.")

    return render_template('eDocuments/proposal/pages/manage_docType.html', docType_data=docType_data)

@app.route('/manage_docType_pss', methods=['GET'])
def manage_docType_pss():

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None
    print("\nemp_data: ", emp_data)
    print("\nemp_code: ", emp_code)

    with getcursor() as cur:
        cur.execute("""
            SELECT 
                oel.emp_code,
                oel.emp_name,
                odl.code AS department_code,
                odl.name_1 AS department_name,
                et.code AS doc_type_code,
                et.name_1 AS doc_type_name
            FROM 
                odg_department_list odl
            LEFT JOIN 
                odg_employee_list oel ON oel.department_code = odl.code
            LEFT JOIN 
                edoc_type et ON et.department_code = odl.code
            WHERE 
                oel.emp_code = %s
        """, (emp_code,))
        docType_data = cur.fetchall()
        # print("\ndocType_data:", docType_data)
        
        if docType_data:
            department_code = docType_data[0]['department_code'] if isinstance(docType_data[0], dict) else docType_data[0][2]
            # print("\ndepartment_code:", department_code)
        else:
            department_code = None
            print("\nNo data found for department_code.")

    return render_template('eDocuments/proposal/pages/manage_docType_pss.html', docType_data=docType_data)

@app.route('/manageDocType', methods=['POST'])
def manageDocType():
    data = request.json
    action = data.get("action")

    emp_data = session.get("employee_json")
    emp_code = emp_data.get('emp_code') if emp_data else None
    print("\nemp_data: ", emp_data)
    
    if not action:
        return jsonify({"success": False, "message": "Missing action type"}), 400

    if action == "insert":
        docType_code = data.get('docType_text')
        if not docType_code:
            return jsonify({"success": False, "message": "Missing docType_code"}), 400
        
        try:
            with getcursor() as cur:
                cur.execute("""
                    SELECT 
                        oel.emp_code,
                        oel.emp_name,
                        odl.code AS department_code,
                        odl.name_1 AS department_name,
                        et.code AS doc_type_code,
                        et.name_1 AS doc_type_name
                    FROM 
                        odg_department_list odl
                    LEFT JOIN 
                        odg_employee_list oel ON oel.department_code = odl.code
                    LEFT JOIN 
                        edoc_type et ON et.department_code = odl.code
                    WHERE 
                        oel.emp_code = %s
                """, (emp_code,))
                docType_data = cur.fetchall()
                print("\ndocType_data:", docType_data)

                # Process the result safely
                if docType_data:
                    department_code = docType_data[0]['department_code'] if isinstance(docType_data[0], dict) else docType_data[0][2]
                    print("\ndepartment_code:", department_code)
                else:
                    return jsonify({"success": False, "message": "Department code not found"}), 400

                # Generate subtype code
                cur.execute("SELECT COUNT(*) count FROM edoc_type")
                subtype_row = cur.fetchone()
                subtype_count = (subtype_row['count'] if subtype_row else 0) + 1

                subtype_no = str(subtype_count).zfill(3)
                current_date = datetime.now().strftime("%y%m%d")
                full_code = f"{subtype_no}{current_date}"
                
                cur.execute(
                    "INSERT INTO edoc_type (code, name_1, creator_code, department_code) VALUES (%s, %s, %s, %s)",
                    (full_code, docType_code, emp_code, department_code)
                )

            return jsonify({ 
                "success": True,
                "message": "Document type inserted successfully",
                "data": docType_code
            })
        
        except psycopg2.Error as e:
            return jsonify({"success": False, "message": f"Database error: {e}"}), 500

    elif action == "delete":
        docType_code = data.get("docType_code")

        if not docType_code:
            return jsonify({"success": False, "message": "Missing docType_code"}), 400

        try:
            with getcursor() as cur:
                cur.execute("SELECT COUNT(*) count FROM doc_subtype WHERE type_code = %s", (docType_code,))
                ref_count = cur.fetchone()

                if ref_count['count'] > 0:
                    return jsonify({"success": False, "message": "ລຶບຂໍ້ມູນປະເພດເອກະສານຍ່ອຍກ່ອນ"}), 400
                
                cur.execute("DELETE FROM edoc_type WHERE code = %s", (docType_code,))
                cur.connection.commit()

            return jsonify({"success": True, "message": "Document type deleted successfully"})

        except psycopg2.Error as e:
            return jsonify({"success": False, "message": f"Database error: {e}"}), 500

    else:
        return jsonify({"success": False, "message": "Invalid action"}), 400

@app.route('/deleteDocType', methods=['POST'])
def deleteDocType():
    data = request.json
    docType_code = data.get("docType_code")
    print("\ndocType_code:", docType_code)

    if not docType_code:
        return jsonify({"success": False, "message": "Missing docType_code"}), 400

    try:
        with getcursor() as cur:
            cur.execute("DELETE FROM edoc_type WHERE code = %s", (docType_code,))
            
            cur.connection.commit()
    except psycopg2.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500

    return jsonify({"success": True, "message": "Document type deleted successfully"})

@app.route('/get_data', methods=['POST'])
def get_data(): 

    data = request.json
    docType_code = data.get('docType_code')
    subtype_text = data.get('subtype_text')
    
    # print("\ndocType_code:", docType_code)
    # print("\nsubtype_text:", subtype_text)

    with getcursor() as cur:

        cur.execute("SELECT COUNT(*) FROM doc_subtype WHERE type_code = %s", (docType_code,))
        subtype_row = cur.fetchone()
        subtype_count = subtype_row['count'] + 1
        subtype_no = str(subtype_count).zfill(3)
        full_code = f"{docType_code}-{subtype_no}"

        # print("\nfull_code:", full_code)

        cur.execute("INSERT INTO doc_subtype (code, name_1, type_code) VALUES (%s, %s, %s)", (full_code, subtype_text, docType_code))

        cur.execute("""
                SELECT 
                    code, 
                    name_1, 
                    type_code 
                FROM 
                    doc_subtype 
                WHERE 
                    type_code = %s
                ORDER BY type_code ASC
        """, (docType_code,))
        subtype_data = cur.fetchall()

        # print("\nsubtype_data:", subtype_data)
    
    return jsonify({ 
        "success": True,
        "message": "All Data received successfully",
        "data": subtype_data
    })

@app.route('/get_subtype', methods=['POST'])
def get_subtype():
    
    data = request.json
    docType_code = data.get('docType_code')
    
    with getcursor() as cur:
        cur.execute("""
                SELECT 
                    code, 
                    name_1, 
                    type_code 
                FROM 
                    doc_subtype 
                WHERE 
                    type_code = %s
                ORDER BY type_code ASC
        """, (docType_code,))
        subtype_data = cur.fetchall()

    return jsonify({ "success": True, "message": "Data received successfully", "allData": subtype_data })

@app.route('/del_subtype', methods=['POST'])
def del_subtype():
    data = request.json
    docType_code = data.get('docType_code')
    subtypeCode = data.get('subtypeCode')

    # print("\ncode:", docType_code)
    # print("\ntype_code:", subtypeCode)
    
    with getcursor() as cur:
        
        cur.execute("DELETE FROM doc_subtype WHERE code = %s AND type_code = %s", (subtypeCode, docType_code))
        
        cur.execute("""
            SELECT 
                code, 
                name_1, 
                type_code 
            FROM 
                doc_subtype 
            WHERE 
                type_code = %s
            ORDER BY type_code ASC
        """, (docType_code,))
        subtype_data = cur.fetchall()

    return jsonify({
        "success": True,
        "message": "Data deleted successfully",
        "allData": subtype_data
    })