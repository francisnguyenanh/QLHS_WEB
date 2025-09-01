from flask import jsonify
from db_utils import (create_record, read_all_records, read_record_by_id,
                      update_record, delete_record, connect_db)
from flask import flash
from flask import  redirect, session
from flask import Flask, render_template
import config
import calendar
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from flask import make_response, request, url_for


app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# Tạo dữ liệu mẫu
def setup_sample_data():
    conn = connect_db()
    conn.executescript("""
            CREATE TABLE IF NOT EXISTS Classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                class_id INTEGER,
                group_id INTEGER,
                role_id INTEGER,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (class_id) REFERENCES Classes(id),
                FOREIGN KEY (role_id) REFERENCES Roles(id),
                FOREIGN KEY (group_id) REFERENCES Groups(id)
            );

            CREATE TABLE IF NOT EXISTS Conduct (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                conduct_type TEXT,
                conduct_points INTEGER,
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                criterion_type BOOLEAN,
                criterion_points INTEGER,
                is_deleted BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS User_Conduct (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                conduct_id INTEGER NOT NULL,
                registered_date TEXT,
                total_points INTEGER,
                entry_date TEXT DEFAULT CURRENT_TIMESTAMP,
                entered_by TEXT,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (conduct_id) REFERENCES Conduct(id)
            );

            CREATE TABLE IF NOT EXISTS User_Subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                criteria_id INTEGER,
                registered_date TEXT,
                total_points INTEGER,
                entry_date TEXT DEFAULT CURRENT_TIMESTAMP,
                entered_by TEXT,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES Users(id),
                FOREIGN KEY (subject_id) REFERENCES Subjects(id),
                FOREIGN KEY (criteria_id) REFERENCES Criteria(id)
            );
        """)
    # conn.executescript("""
    #     CREATE TABLE IF NOT EXISTS Classes (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         is_deleted BOOLEAN DEFAULT 0
    #     );
    #     INSERT OR IGNORE INTO Classes (name, is_deleted) VALUES ('Lớp 10A1', 0), ('Lớp 10A2', 0);
    #
    #     CREATE TABLE IF NOT EXISTS Roles (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         is_deleted BOOLEAN DEFAULT 0
    #     );
    #     INSERT OR IGNORE INTO Roles (name, is_deleted) VALUES ('Học sinh', 0), ('Giáo viên', 0);
    #
    #     CREATE TABLE IF NOT EXISTS Groups (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         is_deleted BOOLEAN DEFAULT 0
    #     );
    #     INSERT OR IGNORE INTO Groups (name, is_deleted) VALUES ('Tổ 1', 0), ('Tổ 2', 0);
    #
    #     CREATE TABLE IF NOT EXISTS Users (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         username TEXT NOT NULL UNIQUE,
    #         password TEXT NOT NULL,
    #         class_id INTEGER,
    #         group_id INTEGER,
    #         role_id INTEGER,
    #         is_deleted BOOLEAN DEFAULT 0,
    #         FOREIGN KEY (class_id) REFERENCES Classes(id),
    #         FOREIGN KEY (role_id) REFERENCES Roles(id),
    #         FOREIGN KEY (group_id) REFERENCES Groups(id)
    #     );
    #     INSERT OR IGNORE INTO Users (name, username, password, class_id, group_id, role_id, is_deleted) VALUES
    #     ('Nguyễn Văn A', 'nguyenvana', 'pass123', 1, 1, 1, 0),
    #     ('Trần Thị B', 'tranthib', 'pass456', 2, 2, 1, 0);
    #
    #     CREATE TABLE IF NOT EXISTS Conduct (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         conduct_type TEXT,
    #         conduct_points INTEGER,
    #         is_deleted BOOLEAN DEFAULT 0
    #     );
    #     INSERT OR IGNORE INTO Conduct (name, conduct_type, conduct_points, is_deleted) VALUES
    #     ('Tốt', 'Positive', 90, 0),
    #     ('Khá', 'Positive', 70, 0);
    #
    #     CREATE TABLE IF NOT EXISTS Subjects (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         is_deleted BOOLEAN DEFAULT 0
    #     );
    #     INSERT OR IGNORE INTO Subjects (name, is_deleted) VALUES ('Toán', 0), ('Văn', 0);
    #
    #     CREATE TABLE IF NOT EXISTS Criteria (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         name TEXT NOT NULL,
    #         criterion_type BOOLEAN,
    #         criterion_points INTEGER,
    #         is_deleted BOOLEAN DEFAULT 0
    #     );
    #     INSERT OR IGNORE INTO Criteria (name, criterion_type, criterion_points, is_deleted) VALUES
    #     ('Giỏi', 1, 85, 0),
    #     ('Trung bình', 0, 60, 0);
    #
    #     CREATE TABLE IF NOT EXISTS User_Conduct (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         user_id INTEGER NOT NULL,
    #         conduct_id INTEGER NOT NULL,
    #         registered_date TEXT,
    #         total_points INTEGER,
    #         entry_date TEXT DEFAULT CURRENT_TIMESTAMP,
    #         entered_by TEXT,
    #         is_deleted BOOLEAN DEFAULT 0,
    #         FOREIGN KEY (user_id) REFERENCES Users(id),
    #         FOREIGN KEY (conduct_id) REFERENCES Conduct(id)
    #     );
    #     INSERT OR IGNORE INTO User_Conduct (user_id, conduct_id, registered_date, total_points, entered_by, is_deleted) VALUES
    #     (1, 1, '2025-03-25', 90, 'Lê Văn C', 0),
    #     (2, 2, '2025-03-15', 70, 'Lê Văn C', 0);
    #
    #     CREATE TABLE IF NOT EXISTS User_Subjects (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         user_id INTEGER NOT NULL,
    #         subject_id INTEGER NOT NULL,
    #         criteria_id INTEGER,
    #         registered_date TEXT,
    #         total_points INTEGER,
    #         entry_date TEXT DEFAULT CURRENT_TIMESTAMP,
    #         entered_by TEXT,
    #         is_deleted BOOLEAN DEFAULT 0,
    #         FOREIGN KEY (user_id) REFERENCES Users(id),
    #         FOREIGN KEY (subject_id) REFERENCES Subjects(id),
    #         FOREIGN KEY (criteria_id) REFERENCES Criteria(id)
    #     );
    #     INSERT OR IGNORE INTO User_Subjects (user_id, subject_id, criteria_id, registered_date, total_points, entered_by, is_deleted) VALUES
    #     (1, 1, 1, '2025-03-25', 85, 'Lê Văn C', 0),
    #     (2, 2, 2, '2025-03-15', 60, 'Lê Văn C', 0);
    # """)
    conn.commit()
    conn.close()

def is_user_gvcn():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        role = read_record_by_id('Roles', user[6]) # role_id is at index 6
        return (role and role[1] == 'GVCN') # role name is at index 1
    return False


# Trang chủ
@app.route('/')
def index():
    if 'user_id' in session:
        print(session)
        return render_template('base.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


# --- API routes for Classes ---
@app.route('/api/classes/<int:id>')
def get_class_api(id):
    if 'user_id' in session:
        class_data = read_record_by_id('Classes', id, ['id', 'name'])
        return jsonify({'id': class_data[0], 'name': class_data[1]})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/classes', methods=['POST'])
def create_class_api():
    if 'user_id' in session:
        data = {'name': request.json['name'], 'is_deleted': 0}
        create_record('Classes', data)
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/classes/<int:id>', methods=['PUT'])
def update_class_api(id):
    if 'user_id' in session:
        data = {'name': request.json['name']}
        update_record('Classes', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Classes ---
@app.route('/classes')
def classes_list():
    if 'user_id' in session:
        classes = read_all_records('Classes', ['id', 'name'])
        return render_template('classes.html', classes=classes, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))

@app.route('/classes/create', methods=['GET', 'POST'])
def class_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Classes', data)
            return redirect(url_for('classes_list'))
        return render_template('class_create.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/classes/edit/<int:id>', methods=['GET', 'POST'])
def class_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Classes', id, data)
            return redirect(url_for('classes_list'))
        class_data = read_record_by_id('Classes', id, ['id', 'name'])
        return render_template('class_edit.html', class_data=class_data, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/classes/delete/<int:id>')
def class_delete(id):
    delete_record('Classes', id)
    return redirect(url_for('classes_list'))

# --- API routes for Groups ---
@app.route('/api/groups/<int:id>')
def get_group_api(id):
    if 'user_id' in session:
        group_data = read_record_by_id('Groups', id, ['id', 'name'])
        return jsonify({'id': group_data[0], 'name': group_data[1]})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/groups', methods=['POST'])
def create_group_api():
    if 'user_id' in session:
        data = {'name': request.json['name'], 'is_deleted': 0}
        create_record('Groups', data)
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/groups/<int:id>', methods=['PUT'])
def update_group_api(id):
    if 'user_id' in session:
        data = {'name': request.json['name']}
        update_record('Groups', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Groups ---
@app.route('/groups')
def groups_list():
    if 'user_id' in session:
        groups = read_all_records('Groups', ['id', 'name'])
        return render_template('groups.html', groups=groups, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/groups/create', methods=['GET', 'POST'])
def group_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Groups', data)
            return redirect(url_for('groups_list'))
        return render_template('group_create.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/groups/edit/<int:id>', methods=['GET', 'POST'])
def group_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Groups', id, data)
            return redirect(url_for('groups_list'))
        group_data = read_record_by_id('Groups', id, ['id', 'name'])
        return render_template('group_edit.html', group_data=group_data, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/groups/delete/<int:id>')
def group_delete(id):
    delete_record('Groups', id)
    return redirect(url_for('groups_list'))

# --- API routes for Roles ---
@app.route('/api/roles/<int:id>')
def get_role_api(id):
    if 'user_id' in session:
        role_data = read_record_by_id('Roles', id, ['id', 'name'])
        return jsonify({'id': role_data[0], 'name': role_data[1]})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles', methods=['POST'])
def create_role_api():
    if 'user_id' in session:
        data = {'name': request.json['name'], 'is_deleted': 0}
        create_record('Roles', data)
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:id>', methods=['PUT'])
def update_role_api(id):
    if 'user_id' in session:
        data = {'name': request.json['name']}
        update_record('Roles', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Roles ---
@app.route('/roles')
def roles_list():
    if 'user_id' in session:
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template('roles.html', roles=roles, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/roles/create', methods=['GET', 'POST'])
def role_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Roles', data)
            return redirect(url_for('roles_list'))
        return render_template('role_create.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/roles/edit/<int:id>', methods=['GET', 'POST'])
def role_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Roles', id, data)
            return redirect(url_for('roles_list'))
        role_data = read_record_by_id('Roles', id, ['id', 'name'])
        return render_template('role_edit.html', role_data=role_data, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/roles/delete/<int:id>')
def role_delete(id):
    delete_record('Roles', id)
    return redirect(url_for('roles_list'))


# --- API routes for Conducts ---
@app.route('/api/conducts/<int:id>')
def get_conduct_api(id):
    if 'user_id' in session:
        conduct_data = read_record_by_id('Conduct', id, ['id', 'name', 'conduct_type', 'conduct_points'])
        return jsonify({
            'id': conduct_data[0], 
            'name': conduct_data[1], 
            'conduct_type': conduct_data[2], 
            'conduct_points': conduct_data[3]
        })
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/conducts', methods=['POST'])
def create_conduct_api():
    if 'user_id' in session:
        data = {
            'name': request.json['name'], 
            'conduct_type': request.json['conduct_type'],
            'conduct_points': request.json['conduct_points'],
            'is_deleted': 0
        }
        create_record('Conduct', data)
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/conducts/<int:id>', methods=['PUT'])
def update_conduct_api(id):
    if 'user_id' in session:
        data = {
            'name': request.json['name'],
            'conduct_type': request.json['conduct_type'],
            'conduct_points': request.json['conduct_points']
        }
        update_record('Conduct', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Conduct ---
@app.route('/conducts')
def conducts_list():
    if 'user_id' in session:
        conducts = read_all_records('Conduct', ['id', 'name', 'conduct_type', 'conduct_points'])
        return render_template('conducts.html', conducts=conducts, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/conducts/create', methods=['GET', 'POST'])
def conduct_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'conduct_type': request.form['conduct_type'],
                'conduct_points': request.form['conduct_points'],
                'is_deleted': 0
            }
            create_record('Conduct', data)
            return redirect(url_for('conducts_list'))
        return render_template('conduct_create.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/conducts/edit/<int:id>', methods=['GET', 'POST'])
def conduct_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'conduct_type': request.form['conduct_type'],
                'conduct_points': request.form['conduct_points']
            }
            update_record('Conduct', id, data)
            return redirect(url_for('conducts_list'))
        conduct_data = read_record_by_id('Conduct', id, ['id', 'name', 'conduct_type', 'conduct_points'])
        return render_template('conduct_edit.html', conduct_data=conduct_data, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/conducts/delete/<int:id>')
def conduct_delete(id):
    delete_record('Conduct', id)
    return redirect(url_for('conducts_list'))


# --- API routes for Subjects ---
@app.route('/api/subjects/<int:id>')
def get_subject_api(id):
    if 'user_id' in session:
        subject_data = read_record_by_id('Subjects', id, ['id', 'name'])
        return jsonify({'id': subject_data[0], 'name': subject_data[1]})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/subjects', methods=['POST'])
def create_subject_api():
    if 'user_id' in session:
        data = {'name': request.json['name'], 'is_deleted': 0}
        create_record('Subjects', data)
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/subjects/<int:id>', methods=['PUT'])
def update_subject_api(id):
    if 'user_id' in session:
        data = {'name': request.json['name']}
        update_record('Subjects', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Subjects ---
@app.route('/subjects')
def subjects_list():
    if 'user_id' in session:
        subjects = read_all_records('Subjects', ['id', 'name'])
        return render_template('subjects.html', subjects=subjects, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/subjects/create', methods=['GET', 'POST'])
def subject_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name'], 'is_deleted': 0}
            create_record('Subjects', data)
            return redirect(url_for('subjects_list'))
        return render_template('subject_create.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/subjects/edit/<int:id>', methods=['GET', 'POST'])
def subject_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {'name': request.form['name']}
            update_record('Subjects', id, data)
            return redirect(url_for('subjects_list'))
        subject_data = read_record_by_id('Subjects', id, ['id', 'name'])
        return render_template('subject_edit.html', subject_data=subject_data, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/subjects/delete/<int:id>')
def subject_delete(id):
    delete_record('Subjects', id)
    return redirect(url_for('subjects_list'))


# --- API routes for Criteria ---
@app.route('/api/criteria/<int:id>')
def get_criteria_api(id):
    if 'user_id' in session:
        criteria_data = read_record_by_id('Criteria', id, ['id', 'name', 'criterion_type', 'criterion_points'])
        return jsonify({
            'id': criteria_data[0], 
            'name': criteria_data[1], 
            'criterion_type': criteria_data[2], 
            'criterion_points': criteria_data[3]
        })
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/criteria', methods=['POST'])
def create_criteria_api():
    if 'user_id' in session:
        data = {
            'name': request.json['name'], 
            'criterion_type': request.json['criterion_type'],
            'criterion_points': request.json['criterion_points'],
            'is_deleted': 0
        }
        create_record('Criteria', data)
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/criteria/<int:id>', methods=['PUT'])
def update_criteria_api(id):
    if 'user_id' in session:
        data = {
            'name': request.json['name'],
            'criterion_type': request.json['criterion_type'],
            'criterion_points': request.json['criterion_points']
        }
        update_record('Criteria', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Criteria ---
@app.route('/criteria')
def criteria_list():
    if 'user_id' in session:
        criteria = read_all_records('Criteria', ['id', 'name', 'criterion_type', 'criterion_points'])
        return render_template('criteria.html', criteria=criteria, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/criteria/create', methods=['GET', 'POST'])
def criteria_create():
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'criterion_type': 1 if request.form.get('criterion_type') == 'on' else 0,
                'criterion_points': request.form['criterion_points'],
                'is_deleted': 0
            }
            create_record('Criteria', data)
            return redirect(url_for('criteria_list'))
        return render_template('criteria_create.html', is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/criteria/edit/<int:id>', methods=['GET', 'POST'])
def criteria_edit(id):
    if 'user_id' in session:
        if request.method == 'POST':
            data = {
                'name': request.form['name'],
                'criterion_type': 1 if request.form.get('criterion_type') == 'on' else 0,
                'criterion_points': request.form['criterion_points']
            }
            update_record('Criteria', id, data)
            return redirect(url_for('criteria_list'))
        criteria_data = read_record_by_id('Criteria', id, ['id', 'name', 'criterion_type', 'criterion_points'])
        return render_template('criteria_edit.html', criteria_data=criteria_data, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/criteria/delete/<int:id>')
def criteria_delete(id):
    delete_record('Criteria', id)
    return redirect(url_for('criteria_list'))


# --- API routes for Users ---
@app.route('/api/users/<int:id>')
def get_user_api(id):
    if 'user_id' in session:
        user_data = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
        return jsonify({
            'id': user_data[0],
            'name': user_data[1],
            'username': user_data[2],
            'password': user_data[3],
            'class_id': user_data[4],
            'group_id': user_data[5],
            'role_id': user_data[6]
        })
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/users', methods=['POST'])
def create_user_api():
    if 'user_id' in session:
        name = request.json['name']
        username = request.json['username']
        password = request.json['password']
        class_id = request.json['class_id']
        role_id = request.json['role_id']
        group_id = request.json.get('group_id')

        # Kiểm tra trùng username
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ? AND is_deleted = 0", (username,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'error': 'Tên đăng nhập đã tồn tại'}), 400

        data = {
            'name': name,
            'username': username,
            'password': password,
            'class_id': class_id,
            'group_id': group_id,
            'role_id': role_id,
            'is_deleted': 0
        }
        create_record('Users', data)
        conn.close()
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user_api(id):
    if 'user_id' in session:
        name = request.json['name']
        username = request.json['username']
        password = request.json['password']
        class_id = request.json['class_id']
        role_id = request.json['role_id']
        group_id = request.json.get('group_id')

        # Kiểm tra trùng username (trừ user hiện tại)
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ? AND id != ? AND is_deleted = 0", (username, id))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'error': 'Tên đăng nhập đã tồn tại'}), 400

        data = {
            'name': name,
            'username': username,
            'password': password,
            'class_id': class_id,
            'group_id': group_id,
            'role_id': role_id
        }
        update_record('Users', id, data)
        conn.close()
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Users ---
@app.route('/users')
def users_list():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
                SELECT u.id, u.name, u.username, c.name AS class_name, r.name AS role_name, g.name AS group_name
                FROM Users u
                LEFT JOIN Classes c ON u.class_id = c.id
                LEFT JOIN Roles r ON u.role_id = r.id
                LEFT JOIN Groups g ON u.group_id = g.id
                WHERE u.is_deleted = 0
            """)
        users = cursor.fetchall()
        
        # Lấy danh sách classes, roles, groups cho modal
        cursor.execute("SELECT id, name FROM Classes WHERE is_deleted = 0 ORDER BY name")
        classes = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM Roles WHERE is_deleted = 0 ORDER BY name") 
        roles = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 ORDER BY name")
        groups = cursor.fetchall()
        
        conn.close()
        return render_template('users.html', users=users, classes=classes, roles=roles, groups=groups, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/users/create', methods=['GET', 'POST'])
def user_create():
    if 'user_id' in session:
        error_message = None  # Biến để lưu thông báo lỗi
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['username']
            password = request.form['password']
            class_id = request.form['class_id']
            role_id = request.form['role_id']

            # Kiểm tra các trường bắt buộc
            if not all([name, username, password, class_id, role_id]):
                error_message = 'Vui lòng điền đầy đủ tất cả các trường.'
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_create.html', classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            # Kiểm tra trùng username
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Users WHERE username = ? AND is_deleted = 0", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                conn.close()
                error_message = 'Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.'
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_create.html', classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            # Tạo bản ghi mới
            data = {
                'name': name,
                'username': username,
                'password': password,  # Nên mã hóa trước khi lưu
                'class_id': class_id,
                'role_id': role_id,
                'is_deleted': 0
            }
            create_record('Users', data)
            conn.close()
            return redirect(url_for('users_list'))

        classes = read_all_records('Classes', ['id', 'name'])
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template('user_create.html', classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
def user_edit(id):
    if 'user_id' in session:
        error_message = None  # Biến để lưu thông báo lỗi
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['username']
            password = request.form['password']
            class_id = request.form['class_id']
            role_id = request.form['role_id']

            # Kiểm tra các trường bắt buộc
            if not all([name, username, password, class_id, role_id]):
                error_message = 'Vui lòng điền đầy đủ tất cả các trường.'
                user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            # Kiểm tra trùng username, ngoại trừ bản ghi hiện tại
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Users WHERE username = ? AND id != ? AND is_deleted = 0", (username, id))
            existing_user = cursor.fetchone()

            if existing_user:
                conn.close()
                error_message = 'Tên đăng nhập đã tồn tại. Vui lòng chọn tên khác.'
                user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
                classes = read_all_records('Classes', ['id', 'name'])
                roles = read_all_records('Roles', ['id', 'name'])
                return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())

            # Cập nhật bản ghi
            data = {
                'name': name,
                'username': username,
                'password': password,  # Nên mã hóa trước khi lưu
                'class_id': class_id,
                'role_id': role_id
            }
            update_record('Users', id, data)
            conn.close()
            return redirect(url_for('users_list'))

        user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
        classes = read_all_records('Classes', ['id', 'name'])
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/users/delete/<int:id>')
def user_delete(id):
    delete_record('Users', id)
    return redirect(url_for('users_list'))


# --- API lấy điểm của Conduct ---
@app.route('/get_conduct_points/<int:conduct_id>')
def get_conduct_points(conduct_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
    result = cursor.fetchone()
    conn.close()
    return jsonify({'conduct_points': result[0] if result else 0})


# --- API lấy tổng điểm của User trong ngày cụ thể (User_Conduct) ---
@app.route('/user_conduct_total_points')
def user_conduct_total_points():
    user_id = request.args.get('user_id')
    registered_date = request.args.get('registered_date')
    exclude_id = request.args.get('exclude_id')  # ID bản ghi cần loại trừ (dùng cho edit)

    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT SUM(c.conduct_points) 
        FROM User_Conduct uc
        JOIN Conduct c ON uc.conduct_id = c.id
        WHERE uc.user_id = ? AND uc.registered_date = ? AND uc.is_deleted = 0
    """
    params = [user_id, registered_date]

    if exclude_id:
        query += " AND uc.id != ?"
        params.append(exclude_id)

    cursor.execute(query, params)
    total_points = cursor.fetchone()[0] or 0
    conn.close()
    return jsonify({'total_points': total_points})


# --- API lấy điểm của Criteria ---
@app.route('/get_criteria_points/<int:criteria_id>')
def get_criteria_points(criteria_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
    result = cursor.fetchone()
    conn.close()
    return jsonify({'criterion_points': result[0] if result else 0})


# --- API lấy tổng điểm của User trong ngày cụ thể (User_Subjects) ---
@app.route('/user_subjects_total_points')
def user_subjects_total_points():
    user_id = request.args.get('user_id')
    registered_date = request.args.get('registered_date')
    exclude_id = request.args.get('exclude_id')  # ID bản ghi cần loại trừ (dùng cho edit)

    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT SUM(cr.criterion_points) 
        FROM User_Subjects us
        LEFT JOIN Criteria cr ON us.criteria_id = cr.id
        WHERE us.user_id = ? AND us.registered_date = ? AND us.is_deleted = 0
    """
    params = [user_id, registered_date]

    if exclude_id:
        query += " AND us.id != ?"
        params.append(exclude_id)

    cursor.execute(query, params)
    total_points = cursor.fetchone()[0] or 0
    conn.close()
    return jsonify({'total_points': total_points})


# --- API route để lấy dữ liệu record cho modal edit ---
@app.route('/api/user_conduct/<int:id>')
def get_user_conduct_api(id):
    if 'user_id' in session:
        record = read_record_by_id('User_Conduct', id, 
                                   ['id', 'user_id', 'conduct_id', 'registered_date', 'total_points', 'entered_by'])
        return jsonify({
            'id': record[0],
            'user_id': record[1],
            'conduct_id': record[2],
            'registered_date': record[3],
            'total_points': record[4],
            'entered_by': record[5]
        })
    return jsonify({'error': 'Unauthorized'}), 401

# --- API route để tạo mới user conduct ---
@app.route('/api/user_conduct', methods=['POST'])
def create_user_conduct_api():
    if 'user_id' in session:
        user_id = request.json['user_id']
        conduct_id = request.json['conduct_id']
        registered_date = request.json['registered_date']
        entered_by = request.json['entered_by']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(c.conduct_points) 
            FROM User_Conduct uc
            JOIN Conduct c ON uc.conduct_id = c.id
            WHERE uc.user_id = ? AND uc.registered_date = ? AND uc.is_deleted = 0
        """, (user_id, registered_date))
        total_points = cursor.fetchone()[0] or 0

        cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
        conduct_points = cursor.fetchone()[0] or 0

        total_points += conduct_points

        data = {
            'user_id': user_id,
            'conduct_id': conduct_id,
            'registered_date': registered_date,
            'total_points': total_points,
            'entered_by': entered_by,
            'is_deleted': 0
        }
        create_record('User_Conduct', data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- API route để cập nhật user conduct ---
@app.route('/api/user_conduct/<int:id>', methods=['PUT'])
def update_user_conduct_api(id):
    if 'user_id' in session:
        user_id = request.json['user_id']
        conduct_id = request.json['conduct_id']
        registered_date = request.json['registered_date']
        entered_by = request.json['entered_by']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(c.conduct_points) 
            FROM User_Conduct uc
            JOIN Conduct c ON uc.conduct_id = c.id
            WHERE uc.user_id = ? AND uc.registered_date = ? AND uc.id != ? AND uc.is_deleted = 0
        """, (user_id, registered_date, id))
        total_points = cursor.fetchone()[0] or 0

        cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
        conduct_points = cursor.fetchone()[0] or 0

        total_points += conduct_points

        data = {
            'user_id': user_id,
            'conduct_id': conduct_id,
            'registered_date': registered_date,
            'total_points': total_points,
            'entered_by': entered_by
        }
        update_record('User_Conduct', id, data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- User_Conduct ---
@app.route('/user_conduct', methods=['GET', 'POST'])
def user_conduct_list():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')

        valid_columns = {
            'user_name': 'u.name',
            'conduct_name': 'c.name',
            'group_name': 'g.name',
            'registered_date': 'uc.registered_date',
            'total_points': 'uc.total_points',
            'entered_by': 'uc.entered_by'
        }
        sort_column = valid_columns.get(sort_by, 'uc.registered_date')
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id != ?", (gvcn_role_id,))
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        users = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Conduct WHERE is_deleted = 0")
        conducts = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        # Tính toán ngày mặc định: Thứ 2~6 gần ngày hệ thống nhất
        today = datetime.today()
        if today.weekday() >= 5:  # Nếu là thứ Bảy (5) hoặc Chủ Nhật (6)
            nearest_monday = today - timedelta(days=today.weekday())  # Thứ Hai tuần hiện tại
        else:  # Nếu là thứ Hai (0) đến thứ Sáu (4)
            nearest_monday = today - timedelta(days=today.weekday() + 7)  # Thứ Hai tuần trước
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')  # Thứ Sáu gần nhất

        selected_users = []
        date_from = default_date_from
        date_to = default_date_to
        selected_conducts = []
        selected_groups = []
        select_all_users = False
        select_all_conducts = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            select_all_conducts = request.form.get('select_all_conducts') == 'on'
            selected_conducts = request.form.getlist('conducts')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            select_all_conducts = request.args.get('select_all_conducts') == 'on'
            selected_conducts = request.args.getlist('conducts')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            query = """
                    SELECT uc.id, u.name AS user_name, c.name AS conduct_name, uc.registered_date, uc.total_points, uc.entered_by, g.name AS group_name
                    FROM User_Conduct uc
                    JOIN Users u ON uc.user_id = u.id
                    JOIN Conduct c ON uc.conduct_id = c.id
                    JOIN Groups g ON u.group_id = g.id
                    WHERE uc.is_deleted = 0 AND u.role_id != ?
                """
            params = [gvcn_role_id]
        else:
            query = """
                    SELECT uc.id, u.name AS user_name, c.name AS conduct_name, uc.registered_date, uc.total_points, uc.entered_by, g.name AS group_name
                    FROM User_Conduct uc
                    JOIN Users u ON uc.user_id = u.id
                    JOIN Conduct c ON uc.conduct_id = c.id
                    JOIN Groups g ON u.group_id = g.id
                    WHERE uc.is_deleted = 0
                """
            params = []

        if select_all_users:
            all_user_ids = [user[0] for user in users]
            if all_user_ids:
                query += " AND uc.user_id IN ({})".format(','.join('?' * len(all_user_ids)))
                params.extend(all_user_ids)
        elif selected_users:
            query += " AND uc.user_id IN ({})".format(','.join('?' * len(selected_users)))
            params.extend(selected_users)

        if date_from:
            query += " AND uc.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND uc.registered_date <= ?"
            params.append(date_to)

        if select_all_conducts:
            all_conduct_ids = [conduct[0] for conduct in conducts]
            if all_conduct_ids:
                query += " AND uc.conduct_id IN ({})".format(','.join('?' * len(all_conduct_ids)))
                params.extend(all_conduct_ids)
        elif selected_conducts:
            query += " AND uc.conduct_id IN ({})".format(','.join('?' * len(selected_conducts)))
            params.extend(selected_conducts)

        if select_all_groups:
            all_group_ids = [group[0] for group in groups]
            if all_group_ids:
                query += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                params.extend(all_group_ids)
        elif selected_groups:
            query += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
            params.extend(selected_groups)

        query += f" ORDER BY {sort_column} {sort_direction}"
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()

        return render_template('user_conduct.html',
                               records=records,
                               users=users,
                               conducts=conducts,
                               groups=groups,
                               all_users=users,  # Thêm để dùng trong modal
                               all_conducts=conducts,  # Thêm để dùng trong modal
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_conducts=selected_conducts,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_conducts=select_all_conducts,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/user_conduct/create', methods=['GET', 'POST'])
def user_conduct_create():
    if 'user_id' in session:
        # Lấy các tham số lọc từ request.args
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_conducts = request.args.getlist('conducts')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_conducts = request.args.get('select_all_conducts') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        if request.method == 'POST':
            user_id = request.form['user_id']
            conduct_id = request.form['conduct_id']
            registered_date = request.form['registered_date']

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(c.conduct_points) 
                FROM User_Conduct uc
                JOIN Conduct c ON uc.conduct_id = c.id
                WHERE uc.user_id = ? AND uc.registered_date = ? AND uc.is_deleted = 0
            """, (user_id, registered_date))
            total_points = cursor.fetchone()[0] or 0

            cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
            conduct_points = cursor.fetchone()[0] or 0

            total_points += conduct_points

            data = {
                'user_id': user_id,
                'conduct_id': conduct_id,
                'registered_date': registered_date,
                'total_points': total_points,
                'entered_by': request.form['entered_by'],
                'is_deleted': 0
            }
            create_record('User_Conduct', data)
            conn.close()

            # Chuyển hướng với các tham số lọc
            return redirect(url_for('user_conduct_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    conducts=selected_conducts,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_conducts=select_all_conducts,
                                    select_all_groups=select_all_groups))

        users = read_all_records('Users', ['id', 'name'])
        conducts = read_all_records('Conduct', ['id', 'name'])
        return render_template('user_conduct_create.html',
                               users=users,
                               conducts=conducts,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_conducts=selected_conducts,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_conducts=select_all_conducts,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/user_conduct/edit/<int:id>', methods=['GET', 'POST'])
def user_conduct_edit(id):
    if 'user_id' in session:
        # Lấy các tham số lọc từ request.args
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_conducts = request.args.getlist('conducts')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_conducts = request.args.get('select_all_conducts') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        if request.method == 'POST':
            user_id = request.form['user_id']
            conduct_id = request.form['conduct_id']
            registered_date = request.form['registered_date']

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(c.conduct_points) 
                FROM User_Conduct uc
                JOIN Conduct c ON uc.conduct_id = c.id
                WHERE uc.user_id = ? AND uc.registered_date = ? AND uc.id != ? AND uc.is_deleted = 0
            """, (user_id, registered_date, id))
            total_points = cursor.fetchone()[0] or 0

            cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
            conduct_points = cursor.fetchone()[0] or 0

            total_points += conduct_points

            data = {
                'user_id': user_id,
                'conduct_id': conduct_id,
                'registered_date': registered_date,
                'total_points': total_points,
                'entered_by': request.form['entered_by']
            }
            update_record('User_Conduct', id, data)
            conn.close()

            # Chuyển hướng với các tham số lọc
            return redirect(url_for('user_conduct_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    conducts=selected_conducts,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_conducts=select_all_conducts,
                                    select_all_groups=select_all_groups))

        record = read_record_by_id('User_Conduct', id,
                                   ['id', 'user_id', 'conduct_id', 'registered_date', 'total_points', 'entered_by'])
        users = read_all_records('Users', ['id', 'name'])
        conducts = read_all_records('Conduct', ['id', 'name'])
        return render_template('user_conduct_edit.html',
                               record=record,
                               users=users,
                               conducts=conducts,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_conducts=selected_conducts,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_conducts=select_all_conducts,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/user_conduct/delete/<int:id>')
def user_conduct_delete(id):
    # Lấy các tham số lọc từ request.args
    sort_by = request.args.get('sort_by', 'registered_date')
    sort_order = request.args.get('sort_order', 'asc')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    selected_users = request.args.getlist('users')
    selected_conducts = request.args.getlist('conducts')
    selected_groups = request.args.getlist('groups')
    select_all_users = request.args.get('select_all_users') == 'on'
    select_all_conducts = request.args.get('select_all_conducts') == 'on'
    select_all_groups = request.args.get('select_all_groups') == 'on'

    delete_record('User_Conduct', id)

    # Chuyển hướng với các tham số lọc
    return redirect(url_for('user_conduct_list',
                            sort_by=sort_by,
                            sort_order=sort_order,
                            date_from=date_from,
                            date_to=date_to,
                            users=selected_users,
                            conducts=selected_conducts,
                            groups=selected_groups,
                            select_all_users=select_all_users,
                            select_all_conducts=select_all_conducts,
                            select_all_groups=select_all_groups))


# --- API routes for User_Subjects ---
@app.route('/api/user_subjects/<int:id>')
def get_user_subjects_api(id):
    if 'user_id' in session:
        record = read_record_by_id('User_Subjects', id, 
                                   ['id', 'user_id', 'subject_id', 'criteria_id', 'registered_date', 'total_points', 'entered_by'])
        return jsonify({
            'id': record[0],
            'user_id': record[1],
            'subject_id': record[2],
            'criteria_id': record[3],
            'registered_date': record[4],
            'total_points': record[5],
            'entered_by': record[6]
        })
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/user_subjects', methods=['POST'])
def create_user_subjects_api():
    if 'user_id' in session:
        user_id = request.json['user_id']
        subject_id = request.json['subject_id']
        criteria_id = request.json.get('criteria_id') or None
        registered_date = request.json['registered_date']
        entered_by = request.json['entered_by']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(cr.criterion_points) 
            FROM User_Subjects us
            LEFT JOIN Criteria cr ON us.criteria_id = cr.id
            WHERE us.user_id = ? AND us.registered_date = ? AND us.is_deleted = 0
        """, (user_id, registered_date))
        total_points = cursor.fetchone()[0] or 0

        if criteria_id:
            cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
            criteria_points = cursor.fetchone()[0] or 0
            total_points += criteria_points

        data = {
            'user_id': user_id,
            'subject_id': subject_id,
            'criteria_id': criteria_id,
            'registered_date': registered_date,
            'total_points': total_points,
            'entered_by': entered_by,
            'is_deleted': 0
        }
        create_record('User_Subjects', data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/user_subjects/<int:id>', methods=['PUT'])
def update_user_subjects_api(id):
    if 'user_id' in session:
        user_id = request.json['user_id']
        subject_id = request.json['subject_id']
        criteria_id = request.json.get('criteria_id') or None
        registered_date = request.json['registered_date']
        entered_by = request.json['entered_by']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(cr.criterion_points) 
            FROM User_Subjects us
            LEFT JOIN Criteria cr ON us.criteria_id = cr.id
            WHERE us.user_id = ? AND us.registered_date = ? AND us.id != ? AND us.is_deleted = 0
        """, (user_id, registered_date, id))
        total_points = cursor.fetchone()[0] or 0

        if criteria_id:
            cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
            criteria_points = cursor.fetchone()[0] or 0
            total_points += criteria_points

        data = {
            'user_id': user_id,
            'subject_id': subject_id,
            'criteria_id': criteria_id,
            'registered_date': registered_date,
            'total_points': total_points,
            'entered_by': entered_by
        }
        update_record('User_Subjects', id, data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- User_Subjects ---
@app.route('/user_subjects', methods=['GET', 'POST'])
def user_subjects_list():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')

        valid_columns = {
            'user_name': 'u.name',
            'subject_name': 's.name',
            'criteria_name': 'cr.name',
            'group_name': 'g.name',
            'registered_date': 'us.registered_date',
            'total_points': 'us.total_points',
            'entered_by': 'us.entered_by'
        }
        sort_column = valid_columns.get(sort_by, 'us.registered_date')
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id != ?", (gvcn_role_id,))
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        users = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0")
        subjects = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Criteria WHERE is_deleted = 0")
        criteria = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        # Tính toán ngày mặc định: Thứ 2~6 gần ngày hệ thống nhất
        today = datetime.today()
        if today.weekday() >= 5:  # Nếu là thứ Bảy (5) hoặc Chủ Nhật (6)
            nearest_monday = today - timedelta(days=today.weekday())  # Thứ Hai tuần hiện tại
        else:  # Nếu là thứ Hai (0) đến thứ Sáu (4)
            nearest_monday = today - timedelta(days=today.weekday() + 7)  # Thứ Hai tuần trước
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')  # Thứ Sáu gần nhất

        selected_users = []
        date_from = default_date_from
        date_to = default_date_to
        selected_subjects = []
        selected_groups = []
        select_all_users = False
        select_all_subjects = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            select_all_subjects = request.form.get('select_all_subjects') == 'on'
            selected_subjects = request.form.getlist('subjects')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            select_all_subjects = request.args.get('select_all_subjects') == 'on'
            selected_subjects = request.args.getlist('subjects')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            query = """
                    SELECT us.id, u.name AS user_name, s.name AS subject_name, cr.name AS criteria_name, 
                           us.registered_date, us.total_points, us.entered_by, g.name AS group_name
                    FROM User_Subjects us
                    JOIN Users u ON us.user_id = u.id
                    JOIN Subjects s ON us.subject_id = s.id
                    LEFT JOIN Criteria cr ON us.criteria_id = cr.id
                    JOIN Groups g ON u.group_id = g.id
                    WHERE us.is_deleted = 0 AND u.role_id != ?
                """
            params = [gvcn_role_id]
        else:
            query = """
                    SELECT us.id, u.name AS user_name, s.name AS subject_name, cr.name AS criteria_name, 
                           us.registered_date, us.total_points, us.entered_by, g.name AS group_name
                    FROM User_Subjects us
                    JOIN Users u ON us.user_id = u.id
                    JOIN Subjects s ON us.subject_id = s.id
                    LEFT JOIN Criteria cr ON us.criteria_id = cr.id
                    JOIN Groups g ON u.group_id = g.id
                    WHERE us.is_deleted = 0
                """
            params = []

        if select_all_users:
            all_user_ids = [user[0] for user in users]
            if all_user_ids:
                query += " AND us.user_id IN ({})".format(','.join('?' * len(all_user_ids)))
                params.extend(all_user_ids)
        elif selected_users:
            query += " AND us.user_id IN ({})".format(','.join('?' * len(selected_users)))
            params.extend(selected_users)

        if date_from:
            query += " AND us.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND us.registered_date <= ?"
            params.append(date_to)

        if select_all_subjects:
            all_subject_ids = [subject[0] for subject in subjects]
            if all_subject_ids:
                query += " AND us.subject_id IN ({})".format(','.join('?' * len(all_subject_ids)))
                params.extend(all_subject_ids)
        elif selected_subjects:
            query += " AND us.subject_id IN ({})".format(','.join('?' * len(selected_subjects)))
            params.extend(selected_subjects)

        if select_all_groups:
            all_group_ids = [group[0] for group in groups]
            if all_group_ids:
                query += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                params.extend(all_group_ids)
        elif selected_groups:
            query += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
            params.extend(selected_groups)

        query += f" ORDER BY {sort_column} {sort_direction}"
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()

        return render_template('user_subjects.html',
                               records=records,
                               users=users,
                               subjects=subjects,
                               criteria=criteria,
                               groups=groups,
                               all_users=users,  # Thêm để dùng trong modal
                               all_subjects=subjects,  # Thêm để dùng trong modal  
                               all_criteria=criteria,  # Thêm để dùng trong modal
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_subjects=selected_subjects,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_subjects=select_all_subjects,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/user_subjects/create', methods=['GET', 'POST'])
def user_subjects_create():
    if 'user_id' in session:
        # Lấy các tham số lọc từ request.args
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_subjects = request.args.getlist('subjects')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_subjects = request.args.get('select_all_subjects') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        if request.method == 'POST':
            user_id = request.form['user_id']
            subject_id = request.form['subject_id']
            criteria_id = request.form['criteria_id'] if request.form['criteria_id'] else None
            registered_date = request.form['registered_date']

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(cr.criterion_points) 
                FROM User_Subjects us
                LEFT JOIN Criteria cr ON us.criteria_id = cr.id
                WHERE us.user_id = ? AND us.registered_date = ? AND us.is_deleted = 0
            """, (user_id, registered_date))
            total_points = cursor.fetchone()[0] or 0

            if criteria_id:
                cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
                criteria_points = cursor.fetchone()[0] or 0
                total_points += criteria_points
            else:
                total_points = total_points or 0

            data = {
                'user_id': user_id,
                'subject_id': subject_id,
                'criteria_id': criteria_id,
                'registered_date': registered_date,
                'total_points': total_points,
                'entered_by': request.form['entered_by'],
                'is_deleted': 0
            }
            create_record('User_Subjects', data)
            conn.close()

            # Chuyển hướng với các tham số lọc
            return redirect(url_for('user_subjects_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    subjects=selected_subjects,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_subjects=select_all_subjects,
                                    select_all_groups=select_all_groups))

        users = read_all_records('Users', ['id', 'name'])
        subjects = read_all_records('Subjects', ['id', 'name'])
        criteria = read_all_records('Criteria', ['id', 'name'])
        return render_template('user_subjects_create.html',
                               users=users,
                               subjects=subjects,
                               criteria=criteria,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_subjects=selected_subjects,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_subjects=select_all_subjects,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/user_subjects/edit/<int:id>', methods=['GET', 'POST'])
def user_subjects_edit(id):
    if 'user_id' in session:
        # Lấy các tham số lọc từ request.args
        sort_by = request.args.get('sort_by', 'registered_date')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        selected_users = request.args.getlist('users')
        selected_subjects = request.args.getlist('subjects')
        selected_groups = request.args.getlist('groups')
        select_all_users = request.args.get('select_all_users') == 'on'
        select_all_subjects = request.args.get('select_all_subjects') == 'on'
        select_all_groups = request.args.get('select_all_groups') == 'on'

        if request.method == 'POST':
            user_id = request.form['user_id']
            subject_id = request.form['subject_id']
            criteria_id = request.form['criteria_id'] if request.form['criteria_id'] else None
            registered_date = request.form['registered_date']

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(cr.criterion_points) 
                FROM User_Subjects us
                LEFT JOIN Criteria cr ON us.criteria_id = cr.id
                WHERE us.user_id = ? AND us.registered_date = ? AND us.id != ? AND us.is_deleted = 0
            """, (user_id, registered_date, id))
            total_points = cursor.fetchone()[0] or 0

            if criteria_id:
                cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
                criteria_points = cursor.fetchone()[0] or 0
                total_points += criteria_points
            else:
                total_points = total_points or 0

            data = {
                'user_id': user_id,
                'subject_id': subject_id,
                'criteria_id': criteria_id,
                'registered_date': registered_date,
                'total_points': total_points,
                'entered_by': request.form['entered_by']
            }
            update_record('User_Subjects', id, data)
            conn.close()

            # Chuyển hướng với các tham số lọc
            return redirect(url_for('user_subjects_list',
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    date_from=date_from,
                                    date_to=date_to,
                                    users=selected_users,
                                    subjects=selected_subjects,
                                    groups=selected_groups,
                                    select_all_users=select_all_users,
                                    select_all_subjects=select_all_subjects,
                                    select_all_groups=select_all_groups))

        record = read_record_by_id('User_Subjects', id,
                                   ['id', 'user_id', 'subject_id', 'criteria_id', 'registered_date', 'total_points', 'entered_by'])
        users = read_all_records('Users', ['id', 'name'])
        subjects = read_all_records('Subjects', ['id', 'name'])
        criteria = read_all_records('Criteria', ['id', 'name'])
        return render_template('user_subjects_edit.html',
                               record=record,
                               users=users,
                               subjects=subjects,
                               criteria=criteria,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_subjects=selected_subjects,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_subjects=select_all_subjects,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/user_subjects/delete/<int:id>')
def user_subjects_delete(id):
    # Lấy các tham số lọc từ request.args
    sort_by = request.args.get('sort_by', 'registered_date')
    sort_order = request.args.get('sort_order', 'asc')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    selected_users = request.args.getlist('users')
    selected_subjects = request.args.getlist('subjects')
    selected_groups = request.args.getlist('groups')
    select_all_users = request.args.get('select_all_users') == 'on'
    select_all_subjects = request.args.get('select_all_subjects') == 'on'
    select_all_groups = request.args.get('select_all_groups') == 'on'

    delete_record('User_Subjects', id)

    # Chuyển hướng với các tham số lọc
    return redirect(url_for('user_subjects_list',
                            sort_by=sort_by,
                            sort_order=sort_order,
                            date_from=date_from,
                            date_to=date_to,
                            users=selected_users,
                            subjects=selected_subjects,
                            groups=selected_groups,
                            select_all_users=select_all_users,
                            select_all_subjects=select_all_subjects,
                            select_all_groups=select_all_groups))


@app.route('/group_summary', methods=['GET', 'POST'])
def group_summary():
    if 'user_id' in session:
        # Lấy tham số sắp xếp từ query string
        sort_by = request.args.get('sort_by', 'group_name')
        sort_order = request.args.get('sort_order', 'asc')

        # Danh sách cột hợp lệ để sắp xếp
        valid_columns = {
            'group_name': 'group_name',
            'total_points': 'total_points'
        }
        sort_column = valid_columns.get(sort_by, 'group_name')
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'

        # Lấy role_id của GVCN và group_id của "Giáo viên" để lọc
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        # Lấy danh sách groups (loại bỏ "Giáo viên")
        conn = connect_db()
        cursor = conn.cursor()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        # Tính toán ngày mặc định: Thứ 2~6 gần ngày hệ thống nhất
        today = datetime.today()
        if today.weekday() >= 5:  # Nếu là thứ Bảy (5) hoặc Chủ Nhật (6)
            nearest_monday = today - timedelta(days=today.weekday())  # Thứ Hai tuần hiện tại
        else:  # Nếu là thứ Hai (0) đến thứ Sáu (4)
            nearest_monday = today - timedelta(days=today.weekday() + 7)  # Thứ Hai tuần trước
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')  # Thứ Sáu gần nhất

        # Khởi tạo các biến lọc
        selected_groups = []
        date_from = default_date_from
        date_to = default_date_to
        data_source = 'user_conduct'
        select_all_groups = False

        # Xử lý yêu cầu POST hoặc GET
        if request.method == 'POST':
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            data_source = request.form.get('data_source', 'user_conduct')
        else:
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            data_source = request.args.get('data_source', 'user_conduct')

        # Kết nối database
        conn = connect_db()
        cursor = conn.cursor()

        # Xây dựng truy vấn SQL (loại bỏ user có role GVCN)
        queries = []
        params = []

        # Truy vấn cho User_Conduct
        if data_source in ['user_conduct', 'all']:
            if gvcn_role_id is not None:
                query_uc = """
                        SELECT g.name AS group_name, SUM(uc.total_points) AS total_points
                        FROM User_Conduct uc
                        JOIN Users u ON uc.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE uc.is_deleted = 0 AND u.role_id != ?
                    """
                params_uc = [gvcn_role_id]
            else:
                query_uc = """
                        SELECT g.name AS group_name, SUM(uc.total_points) AS total_points
                        FROM User_Conduct uc
                        JOIN Users u ON uc.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE uc.is_deleted = 0
                    """
                params_uc = []
            if select_all_groups:
                all_group_ids = [group[0] for group in groups]
                if all_group_ids:
                    query_uc += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                    params_uc.extend(all_group_ids)
            elif selected_groups:
                query_uc += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
                params_uc.extend(selected_groups)
            if date_from:
                query_uc += " AND uc.registered_date >= ?"
                params_uc.append(date_from)
            if date_to:
                query_uc += " AND uc.registered_date <= ?"
                params_uc.append(date_to)
            query_uc += " GROUP BY g.id, g.name"
            queries.append((query_uc, params_uc))

        # Truy vấn cho User_Subjects
        if data_source in ['user_subjects', 'all']:
            if gvcn_role_id is not None:
                query_us = """
                        SELECT g.name AS group_name, SUM(us.total_points) AS total_points
                        FROM User_Subjects us
                        JOIN Users u ON us.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE us.is_deleted = 0 AND u.role_id != ?
                    """
                params_us = [gvcn_role_id]
            else:
                query_us = """
                        SELECT g.name AS group_name, SUM(us.total_points) AS total_points
                        FROM User_Subjects us
                        JOIN Users u ON us.user_id = u.id
                        JOIN Groups g ON u.group_id = g.id
                        WHERE us.is_deleted = 0
                    """
                params_us = []
            if select_all_groups:
                all_group_ids = [group[0] for group in groups]
                if all_group_ids:
                    query_us += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                    params_us.extend(all_group_ids)
            elif selected_groups:
                query_us += " AND u.group_id IN ({})".format(','.join('?' * len(selected_groups)))
                params_us.extend(selected_groups)
            if date_from:
                query_us += " AND us.registered_date >= ?"
                params_us.append(date_from)
            if date_to:
                query_us += " AND us.registered_date <= ?"
                params_us.append(date_to)
            query_us += " GROUP BY g.id, g.name"
            queries.append((query_us, params_us))

        # Thực thi truy vấn và tổng hợp kết quả
        records = {}
        for query, params in queries:
            cursor.execute(query, params)
            results = cursor.fetchall()
            for group_name, total_points in results:
                if group_name in records:
                    records[group_name] += total_points if total_points else 0
                else:
                    records[group_name] = total_points if total_points else 0

        # Chuyển dict thành list để hiển thị và sắp xếp
        records_list = [(group_name, total_points) for group_name, total_points in records.items()]
        records_list.sort(key=lambda x: x[0 if sort_column == 'group_name' else 1], reverse=(sort_direction == 'DESC'))

        conn.close()

        return render_template('group_summary.html',
                               records=records_list,
                               groups=groups,
                               date_from=date_from,
                               date_to=date_to,
                               selected_groups=selected_groups,
                               select_all_groups=select_all_groups,
                               data_source=data_source,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


def generate_pdf_for_user(user_data, date_from, date_to, y_start, canvas_obj, page_height):
    """Helper function to generate content for a single user on half an A4 page."""
    pdfmetrics.registerFont(TTFont('Arial', 'ARIAL.TTF'))  # Đăng ký font hỗ trợ tiếng Việt

    # Kích thước trang A4: 595 điểm chiều rộng, mỗi nửa A5 cao 421 điểm
    page_width = 595  # Chiều rộng A4

    # Tiêu đề "Báo Cáo Rèn Luyện Học Sinh" căn giữa, font lớn hơn
    canvas_obj.setFont("Arial", 18)  # Font lớn hơn (18)
    canvas_obj.drawCentredString(page_width / 2, y_start + 360, "Báo Cáo Rèn Luyện Học Sinh")

    # Tên học sinh căn trái
    canvas_obj.setFont("Arial", 14)  # Font tiêu đề phụ
    canvas_obj.drawString(50, y_start + 330, f"Học Sinh: {user_data['name']}")

    # Khoảng thời gian căn giữa, font nhỏ hơn
    canvas_obj.setFont("Arial", 10)  # Font nhỏ hơn (10)
    canvas_obj.drawCentredString(page_width / 2, y_start + 310, f"Từ: {date_from or '-'} ～ {date_to or '-'}")

    # Dòng tiêu đề bảng
    y = y_start + 280  # Giảm y xuống để nhường chỗ cho tiêu đề
    canvas_obj.setFont("Arial", 12)
    canvas_obj.drawString(50, y, "Ngày")
    canvas_obj.drawString(150, y, "Môn Học")
    canvas_obj.drawString(250, y, "Học Tập")
    canvas_obj.drawString(350, y, "Hạnh Kiểm")
    canvas_obj.drawString(450, y, "Điểm Ngày")
    canvas_obj.line(50, y - 5, 550, y - 5)  # Đường kẻ ngang dưới tiêu đề

    # Dữ liệu
    y -= 20
    canvas_obj.setFont("Arial", 10)
    total_points_sum = 0

    # Gom nhóm theo registered_date
    for date, entries in sorted(user_data['details'].items()):  # Sắp xếp theo ngày
        canvas_obj.drawString(50, y, str(date) if date else "-")
        first_line = True
        for entry in entries:
            if not first_line:
                y -= 15
                canvas_obj.drawString(50, y, "")  # Để trống cột date cho các dòng tiếp theo
            canvas_obj.drawString(150, y, entry.get('subject_name', '-'))
            canvas_obj.drawString(250, y, entry.get('criteria_name', '-'))
            canvas_obj.drawString(350, y, entry.get('conduct_name', '-'))
            points = entry.get('total_points', 0)
            canvas_obj.drawString(450, y, str(points))
            total_points_sum += points
            first_line = False
            y -= 15
            if y < y_start + 50:  # Nếu hết chỗ trong nửa trang A5, dừng lại
                break

    # Tổng điểm
    y -= 20
    canvas_obj.setFont("Arial", 12)
    canvas_obj.drawString(50, y, f"Tổng Điểm: {total_points_sum}")

def generate_combined_pdf(users_data_list, date_from, date_to):
    """Generates a PDF with two users per A4 page."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)  # Kích thước A4: 595 x 842 điểm
    a4_height = 842
    a5_height = a4_height / 2  # Một nửa chiều cao A4 = A5 dọc

    for i in range(0, len(users_data_list), 2):
        # Học sinh đầu tiên (nửa trên của A4)
        user1_data = users_data_list[i]
        generate_pdf_for_user(user1_data, date_from, date_to, a5_height, p, a5_height)

        # Học sinh thứ hai (nửa dưới của A4), nếu có
        if i + 1 < len(users_data_list):
            user2_data = users_data_list[i + 1]
            generate_pdf_for_user(user2_data, date_from, date_to, 0, p, a5_height)

        p.showPage()  # Kết thúc trang A4 hiện tại

    p.save()
    buffer.seek(0)
    return buffer

@app.route('/print_users', methods=['POST'])
def print_users():
    """Generates and downloads PDFs for selected users with detailed data, 2 per A4 page."""
    selected_users = request.form.get('selected_users', '').split(',')
    date_from = request.form.get('date_from')
    date_to = request.form.get('date_to')

    if not selected_users or selected_users == ['']:
        return "No users selected for printing.", 400

    conn = connect_db()
    cursor = conn.cursor()

    users_data_list = []
    for user_id in selected_users:
        # Lấy thông tin user
        cursor.execute("SELECT name FROM Users WHERE id = ? AND is_deleted = 0", (user_id,))
        user_info = cursor.fetchone()
        if not user_info:
            continue

        user_data = {'name': user_info[0], 'details': {}}

        # Truy vấn User_Subjects
        us_query = """
            SELECT us.registered_date, s.name AS subject_name, c.name AS criteria_name, us.total_points
            FROM User_Subjects us
            LEFT JOIN Subjects s ON us.subject_id = s.id
            LEFT JOIN Criteria c ON us.criteria_id = c.id
            WHERE us.user_id = ? AND us.is_deleted = 0
        """
        us_params = [user_id]
        if date_from:
            us_query += " AND us.registered_date >= ?"
            us_params.append(date_from)
        if date_to:
            us_query += " AND us.registered_date <= ?"
            us_params.append(date_to)
        cursor.execute(us_query, us_params)
        us_results = cursor.fetchall()

        # Truy vấn User_Conduct
        uc_query = """
            SELECT uc.registered_date, con.name AS conduct_name, uc.total_points
            FROM User_Conduct uc
            LEFT JOIN Conduct con ON uc.conduct_id = con.id
            WHERE uc.user_id = ? AND uc.is_deleted = 0
        """
        uc_params = [user_id]
        if date_from:
            uc_query += " AND uc.registered_date >= ?"
            uc_params.append(date_from)
        if date_to:
            uc_query += " AND uc.registered_date <= ?"
            uc_params.append(date_to)  # Sửa từ us_params thành uc_params
        cursor.execute(uc_query, uc_params)
        uc_results = cursor.fetchall()

        # Gom nhóm dữ liệu theo registered_date
        for row in us_results:
            reg_date = row[0]
            subject_name = row[1] if row[1] else '-'
            criteria_name = row[2] if row[2] else '-'
            total_points = row[3] if row[3] is not None else 0

            if reg_date not in user_data['details']:
                user_data['details'][reg_date] = []
            user_data['details'][reg_date].append({
                'subject_name': subject_name,
                'criteria_name': criteria_name,
                'conduct_name': '-',
                'total_points': total_points
            })

        for row in uc_results:
            reg_date = row[0]
            conduct_name = row[1] if row[1] else '-'
            total_points = row[2] if row[2] is not None else 0

            if reg_date not in user_data['details']:
                user_data['details'][reg_date] = []
            user_data['details'][reg_date].append({
                'subject_name': '-',
                'criteria_name': '-',
                'conduct_name': conduct_name,
                'total_points': total_points
            })

        users_data_list.append(user_data)

    conn.close()

    # Tạo PDF kết hợp
    pdf_buffer = generate_combined_pdf(users_data_list, date_from, date_to)

    # Trả về file PDF
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=user_reports.pdf'
    return response


def get_last_monday():
    today = datetime.date.today()
    days_since_monday = today.weekday()
    last_monday = today - datetime.timedelta(days=days_since_monday + 7)  # +7 to get last week's Monday
    return last_monday.strftime('%Y-%m-%d')

def get_last_friday():
    today = datetime.date.today()
    days_since_friday = (today.weekday() - calendar.FRIDAY) % 7
    last_friday = today - datetime.timedelta(days=days_since_friday + 7) # +7 to get last week's friday.
    return last_friday.strftime('%Y-%m-%d')


@app.route('/user_summary', methods=['GET', 'POST'])
def user_summary():
    if 'user_id' in session:
        sort_by = request.args.get('sort_by', 'user_name')
        sort_order = request.args.get('sort_order', 'asc')

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        conn = connect_db()
        cursor = conn.cursor()
        if gvcn_role_id is not None:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id != ?", (gvcn_role_id,))
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        all_users = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        groups = cursor.fetchall()
        conn.close()

        # Tính toán ngày mặc định: Thứ 2~6 gần ngày hệ thống nhất
        today = datetime.today()
        if today.weekday() >= 5:  # Nếu là thứ Bảy (5) hoặc Chủ Nhật (6)
            nearest_monday = today - timedelta(days=today.weekday())  # Thứ Hai tuần hiện tại
        else:  # Nếu là thứ Hai (0) đến thứ Sáu (4)
            nearest_monday = today - timedelta(days=today.weekday() + 7)  # Thứ Hai tuần trước
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=4)).strftime('%Y-%m-%d')  # Thứ Sáu gần nhất

        selected_users = []
        selected_groups = []
        date_from = default_date_from
        date_to = default_date_to
        select_all_users = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to

        conn = connect_db()
        cursor = conn.cursor()

        if gvcn_role_id is not None:
            user_query = """
                    SELECT id, name
                    FROM Users
                    WHERE is_deleted = 0 AND role_id != ?
                """
            user_params = [gvcn_role_id]
        else:
            user_query = """
                    SELECT id, name
                    FROM Users
                    WHERE is_deleted = 0
                """
            user_params = []

        if select_all_users:
            all_user_ids = [user[0] for user in all_users]
            if all_user_ids:
                user_query += " AND id IN ({})".format(','.join('?' * len(all_user_ids)))
                user_params.extend(all_user_ids)
        elif selected_users:
            user_query += " AND id IN ({})".format(','.join('?' * len(selected_users)))
            user_params.extend(selected_users)
        if select_all_groups:
            all_group_ids = [group[0] for group in groups]
            if all_group_ids:
                user_query += " AND group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                user_params.extend(all_group_ids)
        elif selected_groups:
            user_query += " AND group_id IN ({})".format(','.join('?' * len(selected_groups)))
            user_params.extend(selected_groups)

        cursor.execute(user_query, user_params)
        filtered_users = cursor.fetchall()

        records = []
        for user_id, user_name in filtered_users:
            total_points = 0
            has_data = False

            uc_query = """
                    SELECT SUM(total_points)
                    FROM User_Conduct
                    WHERE user_id = ? AND is_deleted = 0
                """
            uc_params = [user_id]
            if date_from:
                uc_query += " AND registered_date >= ?"
                uc_params.append(date_from)
            if date_to:
                uc_query += " AND registered_date <= ?"
                uc_params.append(date_to)
            cursor.execute(uc_query, uc_params)
            uc_points = cursor.fetchone()[0]
            if uc_points:
                total_points += uc_points
                has_data = True

            us_query = """
                    SELECT SUM(total_points)
                    FROM User_Subjects
                    WHERE user_id = ? AND is_deleted = 0
                """
            us_params = [user_id]
            if date_from:
                us_query += " AND registered_date >= ?"
                us_params.append(date_from)
            if date_to:
                us_query += " AND registered_date <= ?"
                us_params.append(date_to)
            cursor.execute(us_query, us_params)
            us_points = cursor.fetchone()[0]
            if us_points:
                total_points += us_points
                has_data = True

            records.append((user_name, total_points if total_points else 0, has_data, user_id))

        if sort_by == 'user_name':
            records.sort(key=lambda x: x[0], reverse=(sort_order == 'desc'))
        elif sort_by == 'total_points':
            records.sort(key=lambda x: x[1], reverse=(sort_order == 'desc'))
        elif sort_by == 'in':
            records.sort(key=lambda x: x[2], reverse=(sort_order == 'desc'))

        conn.close()

        return render_template('user_summary.html',
                               records=records,
                               all_users=all_users,
                               groups=groups,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_groups=select_all_groups,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"{username}, {password}")
        user = read_all_records('Users', condition=f"username = '{username}' AND password = '{password}'")
        print(user)
        if user:
            session['user_id'] = user[0][0]
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password'

    return render_template('login.html', error=error)

@app.route('/home')
def home():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        return f'Welcome {user[1]} to the home page!'  # Hiển thị tên người dùng
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Xóa user_id khỏi session
    return redirect(url_for('login'))


if __name__ == '__main__':
    #setup_sample_data()
    app.run(debug=True)