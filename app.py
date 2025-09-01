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

            CREATE TABLE IF NOT EXISTS Role_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                permission_type TEXT NOT NULL,
                permission_level TEXT NOT NULL,
                is_deleted BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id)
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

def get_user_permissions():
    """Get current user's permissions including CRUD capabilities"""
    if 'user_id' not in session:
        return {}
    
    user = read_record_by_id('Users', session['user_id'])
    if not user or not user[6]:  # role_id at index 6
        return {}
    
    role_id = user[6]
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT permission_type, permission_level, can_create, can_update, can_delete
        FROM Role_Permissions 
        WHERE role_id = ? AND is_deleted = 0
    """, (role_id,))
    permissions_data = cursor.fetchall()
    conn.close()
    
    permissions = {}
    for perm_type, perm_level, can_create, can_update, can_delete in permissions_data:
        if perm_type == 'master':
            permissions[perm_type] = perm_level == 'true'
            # Master has full CRUD on everything
            permissions['master_create'] = True
            permissions['master_update'] = True
            permissions['master_delete'] = True
        else:
            permissions[perm_type] = perm_level
            # Store CRUD permissions for each permission type
            permissions[f'{perm_type}_create'] = bool(can_create)
            permissions[f'{perm_type}_update'] = bool(can_update)
            permissions[f'{perm_type}_delete'] = bool(can_delete)
    
    return permissions

def get_user_group_id(user_id):
    """Get group_id for a given user_id"""
    user = read_record_by_id('Users', user_id)
    return user[5] if user else None  # group_id is at index 5

def has_permission(permission_type, required_level=None):
    """Check if current user has specific permission"""
    permissions = get_user_permissions()
    
    # Master permission overrides all
    if permissions.get('master', False):
        return True
    
    if permission_type not in permissions:
        return False
    
    if required_level is None:
        return permissions[permission_type] != 'none'
    
    return permissions[permission_type] == required_level

def can_create(permission_type):
    """Check if user can create records for given permission type"""
    permissions = get_user_permissions()
    
    # Master can create everything
    if permissions.get('master', False):
        return True
    
    return permissions.get(f'{permission_type}_create', False)

def can_update(permission_type):
    """Check if user can update records for given permission type"""
    permissions = get_user_permissions()
    
    # Master can update everything
    if permissions.get('master', False):
        return True
    
    return permissions.get(f'{permission_type}_update', False)

def can_delete(permission_type):
    """Check if user can delete records for given permission type"""
    permissions = get_user_permissions()
    
    # Master can delete everything
    if permissions.get('master', False):
        return True
    
    return permissions.get(f'{permission_type}_delete', False)

def get_user_data_filters():
    """Get data filters based on user permissions"""
    if 'user_id' not in session:
        return {}
    
    user = read_record_by_id('Users', session['user_id'])
    permissions = get_user_permissions()
    
    filters = {
        'user_id': user[0],
        'group_id': user[5],  # group_id at index 5
        'class_id': user[4],  # class_id at index 4
    }
    
    return filters

def can_access_master():
    """Check if user can access master functions"""
    permissions = get_user_permissions()
    return permissions.get('master', False)

def can_access_conduct_management():
    """Check if user can access conduct management"""
    permissions = get_user_permissions()
    return (permissions.get('master', False) or 
            permissions.get('conduct_management', 'none') != 'none')

def can_access_academic_management():
    """Check if user can access academic management"""
    permissions = get_user_permissions()
    return (permissions.get('master', False) or 
            permissions.get('academic_management', 'none') != 'none')

def can_access_group_statistics():
    """Check if user can access group statistics"""
    permissions = get_user_permissions()
    return (permissions.get('master', False) or 
            permissions.get('group_statistics', 'none') != 'none')

def can_access_student_statistics():
    """Check if user can access student statistics"""
    permissions = get_user_permissions()
    return (permissions.get('master', False) or 
            permissions.get('student_statistics', 'none') != 'none')

def can_access_comment_management():
    """Check if user can access comment management"""
    permissions = get_user_permissions()
    return (permissions.get('master', False) or 
            permissions.get('comment_management', 'none') != 'none')

def render_template_with_permissions(template_name, **kwargs):
    """Helper function to render template with permissions always included"""
    if 'user_id' in session:
        permissions = get_user_permissions()
        kwargs['permissions'] = permissions
        kwargs['is_gvcn'] = is_user_gvcn()
    return render_template(template_name, **kwargs)

def filter_users_by_permission(users, permission_type):
    """Filter users based on permission level"""
    if 'user_id' not in session:
        return []
    
    permissions = get_user_permissions()
    
    # If user has master permission, return all users
    if permissions.get('master', False):
        return users
    
    permission_level = permissions.get(permission_type, 'none')
    
    if permission_level == 'none':
        return []
    elif permission_level == 'self_only':
        # Only return current user
        current_user_id = session['user_id']
        return [user for user in users if user[0] == current_user_id]
    elif permission_level == 'group_only':
        # Only return users from the same group
        current_user = read_record_by_id('Users', session['user_id'])
        current_group_id = current_user[5]  # group_id is at index 5
        return [user for user in users if len(user) > 2 and get_user_group_id(user[0]) == current_group_id]
    elif permission_level == 'all':
        return users
    else:
        return []

def filter_groups_by_permission(groups, permission_type):
    """Filter groups based on permission level"""
    if 'user_id' not in session:
        return []
    
    permissions = get_user_permissions()
    
    # If user has master permission, return all groups
    if permissions.get('master', False):
        return groups
    
    permission_level = permissions.get(permission_type, 'none')
    
    if permission_level == 'none':
        return []
    elif permission_level in ['self_only', 'group_only']:
        # Only return current user's group
        current_user = read_record_by_id('Users', session['user_id'])
        current_group_id = current_user[5]  # group_id is at index 5
        return [group for group in groups if group[0] == current_group_id]
    elif permission_level == 'all':
        return groups
    else:
        return []

def get_user_group_id(user_id):
    """Get group_id for a specific user"""
    try:
        user = read_record_by_id('Users', user_id)
        return user[5] if user else None  # group_id is at index 5
    except:
        return None


# Trang chủ
@app.route('/')
def index():
    if 'user_id' in session:
        print(session)
        permissions = get_user_permissions()
        return render_template('base.html', is_gvcn=is_user_gvcn(), permissions=permissions)
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
        class_id = create_record('Classes', data)
        
        # Cập nhật tất cả users có class_id = null thành class mới tạo
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET class_id = ? WHERE class_id IS NULL AND is_deleted = 0", (class_id,))
        conn.commit()
        conn.close()
        
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
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        classes = read_all_records('Classes', ['id', 'name'])
        # Kiểm tra xem đã có class nào tồn tại chưa
        has_existing_class = len(classes) > 0
        permissions = get_user_permissions()
        return render_template_with_permissions('classes.html', classes=classes, has_existing_class=has_existing_class, 
                             is_gvcn=is_user_gvcn())
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
    # Cập nhật tất cả users có class_id = id thành null
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET class_id = NULL WHERE class_id = ?", (id,))
    conn.commit()
    conn.close()
    
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
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        groups = read_all_records('Groups', ['id', 'name'])
        permissions = get_user_permissions()
        return render_template_with_permissions('groups.html', groups=groups, is_gvcn=is_user_gvcn())
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
    # Kiểm tra xem có user nào đang thuộc nhóm này không
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Users WHERE group_id = ? AND is_deleted = 0", (id,))
    user_count = cursor.fetchone()[0]
    conn.close()
    
    if user_count > 0:
        flash(f'Không thể xóa nhóm này vì đang có {user_count} người liên kết với nhóm', 'error')
    else:
        delete_record('Groups', id)
        flash('Xóa nhóm thành công', 'success')
    
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
        # Kiểm tra role hiện tại
        role_data = read_record_by_id('Roles', id, ['id', 'name'])
        if role_data and role_data[1] in ['GVCN', 'Master']:
            return jsonify({'success': False, 'error': 'Không thể thay đổi role hệ thống'}), 400
        
        data = {'name': request.json['name']}
        update_record('Roles', id, data)
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- API routes for Permissions ---
@app.route('/api/permissions/structure')
def get_permissions_structure():
    if 'user_id' in session:
        import json
        with open('permissions.json', 'r', encoding='utf-8') as f:
            permissions_data = json.load(f)
        return jsonify(permissions_data)
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/permissions')
def get_role_permissions(role_id):
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT permission_type, permission_level, can_create, can_update, can_delete
            FROM Role_Permissions 
            WHERE role_id = ? AND is_deleted = 0
        """, (role_id,))
        permissions_data = cursor.fetchall()
        conn.close()
        
        # Convert to dict with CRUD permissions
        permissions = {}
        for perm_type, perm_level, can_create, can_update, can_delete in permissions_data:
            if perm_type == 'master':
                permissions[perm_type] = {
                    'level': perm_level == 'true',
                    'can_create': bool(can_create),
                    'can_update': bool(can_update), 
                    'can_delete': bool(can_delete)
                }
            else:
                permissions[perm_type] = {
                    'level': perm_level,
                    'can_create': bool(can_create),
                    'can_update': bool(can_update),
                    'can_delete': bool(can_delete)
                }
        
        return jsonify(permissions)
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/permissions', methods=['POST'])
def save_role_permissions(role_id):
    if 'user_id' in session:
        permissions = request.json
        conn = connect_db()
        cursor = conn.cursor()
        
        # Delete existing permissions for this role
        cursor.execute("DELETE FROM Role_Permissions WHERE role_id = ?", (role_id,))
        
        # Insert new permissions with CRUD capabilities
        for perm_type, perm_data in permissions.items():
            if isinstance(perm_data, dict):
                # New format with CRUD permissions
                level = perm_data.get('level')
                can_create = perm_data.get('can_create', 0)
                can_update = perm_data.get('can_update', 0) 
                can_delete = perm_data.get('can_delete', 0)
                
                if perm_type == 'master':
                    level_value = 'true' if level else 'false'
                else:
                    level_value = level
                    
                if level and level != 'none':
                    cursor.execute("""
                        INSERT INTO Role_Permissions 
                        (role_id, permission_type, permission_level, can_create, can_update, can_delete, is_deleted)
                        VALUES (?, ?, ?, ?, ?, ?, 0)
                    """, (role_id, perm_type, level_value, can_create, can_update, can_delete))
            else:
                # Legacy format - backward compatibility
                if perm_type == 'master':
                    level_value = 'true' if perm_data else 'false'
                else:
                    level_value = perm_data
                    
                if perm_data and perm_data != 'none':
                    cursor.execute("""
                        INSERT INTO Role_Permissions (role_id, permission_type, permission_level, is_deleted)
                        VALUES (?, ?, ?, 0)
                    """, (role_id, perm_type, level_value))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Lưu phân quyền thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

# --- Roles ---
@app.route('/roles')
def roles_list():
    if 'user_id' in session:
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        roles = read_all_records('Roles', ['id', 'name'])
        permissions = get_user_permissions()
        return render_template_with_permissions('roles.html', roles=roles, is_gvcn=is_user_gvcn())
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
    # Kiểm tra role hiện tại
    role_data = read_record_by_id('Roles', id, ['id', 'name'])
    if role_data and role_data[1] in ['GVCN', 'Master']:
        flash('Không thể xóa role hệ thống', 'error')
        return redirect(url_for('roles_list'))
    
    # Kiểm tra xem có user nào đang liên kết với role này không
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Users WHERE role_id = ? AND is_deleted = 0", (id,))
    user_count = cursor.fetchone()[0]
    conn.close()
    
    if user_count > 0:
        flash(f'Không thể xóa chức vụ này vì đang có {user_count} người liên kết với chức vụ', 'error')
    else:
        delete_record('Roles', id)
        flash('Xóa chức vụ thành công', 'success')
    
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
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        # Lấy tham số sắp xếp
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Validate sort parameters
        valid_sort_fields = ['name', 'conduct_type', 'conduct_points']
        if sort_by not in valid_sort_fields:
            sort_by = 'name'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
        
        conn = connect_db()
        cursor = conn.cursor()
        
        order_clause = f"{sort_by} {sort_order.upper()}"
        
        query = f"""
                SELECT id, name, conduct_type, conduct_points
                FROM Conduct 
                WHERE is_deleted = 0
                ORDER BY {order_clause}
            """
        
        cursor.execute(query)
        conducts = cursor.fetchall()
        conn.close()
        
        permissions = get_user_permissions()
        return render_template_with_permissions('conducts.html', conducts=conducts, sort_by=sort_by, sort_order=sort_order, 
                             is_gvcn=is_user_gvcn())
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
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        # Lấy tham số sắp xếp
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Validate sort parameters
        valid_sort_fields = ['name']
        if sort_by not in valid_sort_fields:
            sort_by = 'name'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
        
        conn = connect_db()
        cursor = conn.cursor()
        
        order_clause = f"{sort_by} {sort_order.upper()}"
        
        query = f"""
                SELECT id, name
                FROM Subjects 
                WHERE is_deleted = 0
                ORDER BY {order_clause}
            """
        
        cursor.execute(query)
        subjects = cursor.fetchall()
        conn.close()
        
        permissions = get_user_permissions()
        return render_template_with_permissions('subjects.html', subjects=subjects, sort_by=sort_by, sort_order=sort_order, 
                             is_gvcn=is_user_gvcn())
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
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        # Lấy tham số sắp xếp
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Validate sort parameters
        valid_sort_fields = ['name', 'criterion_type', 'criterion_points']
        if sort_by not in valid_sort_fields:
            sort_by = 'name'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
        
        conn = connect_db()
        cursor = conn.cursor()
        
        order_clause = f"{sort_by} {sort_order.upper()}"
        
        query = f"""
                SELECT id, name, criterion_type, criterion_points
                FROM Criteria 
                WHERE is_deleted = 0
                ORDER BY {order_clause}
            """
        
        cursor.execute(query)
        criteria = cursor.fetchall()
        conn.close()
        
        permissions = get_user_permissions()
        return render_template_with_permissions('criteria.html', criteria=criteria, sort_by=sort_by, sort_order=sort_order, 
                             is_gvcn=is_user_gvcn())
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
        # Kiểm tra user hiện tại có role Master không
        user_data = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
        if user_data and user_data[6]:  # role_id at index 6
            role_data = read_record_by_id('Roles', user_data[6], ['id', 'name'])
            if role_data and role_data[1] == 'Master':
                return jsonify({'success': False, 'error': 'Không thể thay đổi user Master'}), 400
        
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
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        # Lấy tham số sắp xếp
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Validate sort parameters
        valid_sort_fields = ['first_name', 'username', 'group_name', 'role_name']
        if sort_by not in valid_sort_fields:
            sort_by = 'first_name'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'
        
        conn = connect_db()
        cursor = conn.cursor()
        
        # Build ORDER BY clause based on sort parameters
        order_clause = ""
        if sort_by == 'first_name':
            # Tạm thời sắp xếp theo toàn bộ tên, sau này có thể tối ưu
            order_clause = f"u.name {sort_order.upper()}"
        elif sort_by == 'username':
            order_clause = f"u.username {sort_order.upper()}"
        elif sort_by == 'group_name':
            order_clause = f"g.name {sort_order.upper()}"
        elif sort_by == 'role_name':
            order_clause = f"r.name {sort_order.upper()}"
        
        query = f"""
                SELECT u.id, u.name, u.username, c.name AS class_name, r.name AS role_name, g.name AS group_name
                FROM Users u
                LEFT JOIN Classes c ON u.class_id = c.id
                LEFT JOIN Roles r ON u.role_id = r.id
                LEFT JOIN Groups g ON u.group_id = g.id
                WHERE u.is_deleted = 0
                ORDER BY {order_clause}
            """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        # Nếu sắp xếp theo first_name, thực hiện sắp xếp lại trong Python
        if sort_by == 'first_name':
            def get_first_name(user):
                name_parts = user[1].split() if user[1] else []
                return name_parts[-1] if name_parts else ''
            
            reverse_order = (sort_order == 'desc')
            users = sorted(users, key=get_first_name, reverse=reverse_order)
        
        # Lấy danh sách classes, roles, groups cho modal
        cursor.execute("SELECT id, name FROM Classes WHERE is_deleted = 0 ORDER BY name")
        classes = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM Roles WHERE is_deleted = 0 ORDER BY name") 
        roles = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 ORDER BY name")
        groups = cursor.fetchall()
        
        conn.close()
        permissions = get_user_permissions()
        return render_template_with_permissions('users.html', users=users, classes=classes, roles=roles, groups=groups, 
                               sort_by=sort_by, sort_order=sort_order, is_gvcn=is_user_gvcn())
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
    # Kiểm tra user có role Master không
    user_data = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
    if user_data and user_data[6]:  # role_id at index 6
        role_data = read_record_by_id('Roles', user_data[6], ['id', 'name'])
        if role_data and role_data[1] == 'Master':
            flash('Không thể xóa user Master', 'error')
            return redirect(url_for('users_list'))
    
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
        if not can_access_conduct_management():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
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
        cursor.execute("SELECT id FROM Roles WHERE name = 'Master'")
        master_role_result = cursor.fetchone()
        master_role_id = master_role_result[0] if master_role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        conn = connect_db()
        cursor = conn.cursor()
        # Loại trừ GVCN và Master khỏi danh sách
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            cursor.execute(f"SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id NOT IN ({placeholders})", excluded_roles)
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        all_users = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Conduct WHERE is_deleted = 0")
        conducts = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        all_groups = cursor.fetchall()
        conn.close()

        # Filter users and groups based on permissions
        users = filter_users_by_permission(all_users, 'conduct_management')
        groups = filter_groups_by_permission(all_groups, 'conduct_management')
        
        # Create modal_users for modal dropdowns based on permissions
        permissions = get_user_permissions()
        if not permissions.get('master', False):
            permission_level = permissions.get('conduct_management', 'none')
            if permission_level == 'group_only':
                # For group_only, show only users from same group in modal
                current_user = read_record_by_id('Users', session['user_id'])
                current_group_id = current_user[5]  # group_id is at index 5
                modal_users = [user for user in all_users if get_user_group_id(user[0]) == current_group_id]
            elif permission_level == 'self_only':
                # For self_only, show only current user in modal
                modal_users = [user for user in all_users if user[0] == session['user_id']]
            else:
                modal_users = users
        else:
            modal_users = users

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
        
        # Base query
        query = """
                SELECT uc.id, u.name AS user_name, c.name AS conduct_name, uc.registered_date, uc.total_points, uc.entered_by, g.name AS group_name
                FROM User_Conduct uc
                JOIN Users u ON uc.user_id = u.id
                JOIN Conduct c ON uc.conduct_id = c.id
                JOIN Groups g ON u.group_id = g.id
                WHERE uc.is_deleted = 0
            """
        params = []
        
        # Add permission-based filtering
        permissions = get_user_permissions()
        if not permissions.get('master', False):
            permission_level = permissions.get('conduct_management', 'none')
            if permission_level == 'self_only':
                query += " AND u.id = ?"
                params.append(session['user_id'])
            elif permission_level == 'group_only':
                current_user = read_record_by_id('Users', session['user_id'])
                current_group_id = current_user[5]  # group_id is at index 5
                query += " AND u.group_id = ?"
                params.append(current_group_id)
        
        # Add GVCN and Master role filtering (existing logic)
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            query += f" AND u.role_id NOT IN ({placeholders})"
            params.extend(excluded_roles)

        if select_all_users:
            all_user_ids = [user[0] for user in modal_users]  # Use modal_users for consistency
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

        permissions = get_user_permissions()
        return render_template_with_permissions('user_conduct.html',
                               records=records,
                               users=modal_users,  # Use filtered users for both filter and modal
                               conducts=conducts,
                               groups=groups,
                               all_users=modal_users,  # Use filtered users for modal
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
                               is_gvcn=is_user_gvcn(),
                               permissions=permissions)
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
        if not can_access_academic_management():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
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
        cursor.execute("SELECT id FROM Roles WHERE name = 'Master'")
        master_role_result = cursor.fetchone()
        master_role_id = master_role_result[0] if master_role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        conn = connect_db()
        cursor = conn.cursor()
        # Loại trừ GVCN và Master khỏi danh sách
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            cursor.execute(f"SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id NOT IN ({placeholders})", excluded_roles)
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        all_users = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0")
        subjects = cursor.fetchall()
        cursor.execute("SELECT id, name FROM Criteria WHERE is_deleted = 0")
        criteria = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        all_groups = cursor.fetchall()
        conn.close()

        # Filter users and groups based on permissions
        users = filter_users_by_permission(all_users, 'academic_management')
        groups = filter_groups_by_permission(all_groups, 'academic_management')
        
        # Create modal_users for modal dropdowns based on permissions
        permissions = get_user_permissions()
        if not permissions.get('master', False):
            permission_level = permissions.get('academic_management', 'none')
            if permission_level == 'group_only':
                # For group_only, show only users from same group in modal
                current_user = read_record_by_id('Users', session['user_id'])
                current_group_id = current_user[5]  # group_id is at index 5
                modal_users = [user for user in all_users if get_user_group_id(user[0]) == current_group_id]
            elif permission_level == 'self_only':
                # For self_only, show only current user in modal
                modal_users = [user for user in all_users if user[0] == session['user_id']]
            else:
                modal_users = users
        else:
            modal_users = users

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
        
        # Base query
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
        
        # Add permission-based filtering
        permissions = get_user_permissions()
        if not permissions.get('master', False):
            permission_level = permissions.get('academic_management', 'none')
            if permission_level == 'self_only':
                query += " AND u.id = ?"
                params.append(session['user_id'])
            elif permission_level == 'group_only':
                current_user = read_record_by_id('Users', session['user_id'])
                current_group_id = current_user[5]  # group_id is at index 5
                query += " AND u.group_id = ?"
                params.append(current_group_id)
        
        # Add GVCN and Master role filtering (existing logic)
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            query += f" AND u.role_id NOT IN ({placeholders})"
            params.extend(excluded_roles)

        if select_all_users:
            all_user_ids = [user[0] for user in modal_users]  # Use modal_users for consistency
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

        return render_template_with_permissions('user_subjects.html',
                               records=records,
                               users=modal_users,  # Use filtered users for both filter and modal
                               subjects=subjects,
                               criteria=criteria,
                               groups=groups,
                               all_users=modal_users,  # Use filtered users for modal
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
        if not can_access_group_statistics():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
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

        # Lấy role_id của GVCN, Master và group_id của "Giáo viên" để lọc
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Roles WHERE name = 'Master'")
        master_role_result = cursor.fetchone()
        master_role_id = master_role_result[0] if master_role_result else None
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
        all_groups = cursor.fetchall()
        
        # Lấy danh sách users (loại bỏ GVCN và Master) - giống user_summary
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            cursor.execute(f"SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id NOT IN ({placeholders})", excluded_roles)
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        all_users = cursor.fetchall()
        conn.close()

        # Filter users and groups based on permissions - giống user_summary
        filtered_users = filter_users_by_permission(all_users, 'student_statistics')
        groups = filter_groups_by_permission(all_groups, 'student_statistics')

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
            query_uc = """
                    SELECT g.name AS group_name, SUM(uc.total_points) AS total_points
                    FROM User_Conduct uc
                    JOIN Users u ON uc.user_id = u.id
                    JOIN Groups g ON u.group_id = g.id
                    WHERE uc.is_deleted = 0
                """
            params_uc = []
            
            # Add permission-based filtering
            permissions = get_user_permissions()
            if not permissions.get('master', False):
                permission_level = permissions.get('student_statistics', 'none')
                if permission_level == 'group_only':
                    current_user = read_record_by_id('Users', session['user_id'])
                    current_group_id = current_user[5]  # group_id is at index 5
                    query_uc += " AND u.group_id = ?"
                    params_uc.append(current_group_id)
            
            # Add GVCN and Master role filtering (existing logic)
            excluded_roles = []
            if gvcn_role_id is not None:
                excluded_roles.append(gvcn_role_id)
            if master_role_id is not None:
                excluded_roles.append(master_role_id)
            
            if excluded_roles:
                placeholders = ','.join('?' * len(excluded_roles))
                query_uc += f" AND u.role_id NOT IN ({placeholders})"
                params_uc.extend(excluded_roles)
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
            query_us = """
                    SELECT g.name AS group_name, SUM(us.total_points) AS total_points
                    FROM User_Subjects us
                    JOIN Users u ON us.user_id = u.id
                    JOIN Groups g ON u.group_id = g.id
                    WHERE us.is_deleted = 0
                """
            params_us = []
            
            # Add permission-based filtering (same as User_Conduct)
            permissions = get_user_permissions()
            if not permissions.get('master', False):
                permission_level = permissions.get('student_statistics', 'none')
                if permission_level == 'group_only':
                    current_user = read_record_by_id('Users', session['user_id'])
                    current_group_id = current_user[5]  # group_id is at index 5
                    query_us += " AND u.group_id = ?"
                    params_us.append(current_group_id)
            
            # Add GVCN and Master role filtering (existing logic)
            excluded_roles = []
            if gvcn_role_id is not None:
                excluded_roles.append(gvcn_role_id)
            if master_role_id is not None:
                excluded_roles.append(master_role_id)
            
            if excluded_roles:
                placeholders = ','.join('?' * len(excluded_roles))
                query_us += f" AND u.role_id NOT IN ({placeholders})"
                params_us.extend(excluded_roles)
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

        return render_template_with_permissions('group_summary.html',
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
        if not can_access_student_statistics():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        sort_by = request.args.get('sort_by', 'user_name')
        sort_order = request.args.get('sort_order', 'asc')

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
        role_result = cursor.fetchone()
        gvcn_role_id = role_result[0] if role_result else None
        cursor.execute("SELECT id FROM Roles WHERE name = 'Master'")
        master_role_result = cursor.fetchone()
        master_role_id = master_role_result[0] if master_role_result else None
        cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
        group_result = cursor.fetchone()
        teacher_group_id = group_result[0] if group_result else None
        conn.close()

        conn = connect_db()
        cursor = conn.cursor()
        # Loại trừ GVCN và Master khỏi danh sách
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            cursor.execute(f"SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id NOT IN ({placeholders})", excluded_roles)
        else:
            cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0")
        all_users = cursor.fetchall()
        if teacher_group_id is not None:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
        else:
            cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
        all_groups = cursor.fetchall()
        conn.close()

        # Filter users and groups based on permissions  
        filtered_users = filter_users_by_permission(all_users, 'student_statistics')
        groups = filter_groups_by_permission(all_groups, 'student_statistics')

        # Tính toán ngày mặc định: Tuần hiện tại (Thứ Hai đến Chủ Nhật)
        today = datetime.today()
        # Lấy thứ Hai của tuần hiện tại
        days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        
        default_date_from = monday.strftime('%Y-%m-%d')
        default_date_to = sunday.strftime('%Y-%m-%d')

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

        # Base user query with permission filtering
        user_query = """
                SELECT id, name
                FROM Users
                WHERE is_deleted = 0
            """
        user_params = []
        
        # Add permission-based filtering
        permissions = get_user_permissions()
        if not permissions.get('master', False):
            permission_level = permissions.get('student_statistics', 'none')
            if permission_level == 'self_only':
                user_query += " AND id = ?"
                user_params.append(session['user_id'])
            elif permission_level == 'group_only':
                current_user = read_record_by_id('Users', session['user_id'])
                current_group_id = current_user[5]  # group_id is at index 5
                user_query += " AND group_id = ?"
                user_params.append(current_group_id)
        
        # Add GVCN and Master role filtering (existing logic)
        excluded_roles = []
        if gvcn_role_id is not None:
            excluded_roles.append(gvcn_role_id)
        if master_role_id is not None:
            excluded_roles.append(master_role_id)
        
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            user_query += f" AND role_id NOT IN ({placeholders})"
            user_params.extend(excluded_roles)

        if select_all_users:
            filtered_user_ids = [user[0] for user in filtered_users]
            if filtered_user_ids:
                user_query += " AND id IN ({})".format(','.join('?' * len(filtered_user_ids)))
                user_params.extend(filtered_user_ids)
        elif selected_users:
            user_query += " AND id IN ({})".format(','.join('?' * len(selected_users)))
            user_params.extend(selected_users)
        if select_all_groups:
            group_ids = [group[0] for group in groups]
            if group_ids:
                user_query += " AND group_id IN ({})".format(','.join('?' * len(group_ids)))
                user_params.extend(group_ids)
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

            # Tính toán nhận xét tự động
            current_comment = ""
            auto_comment = ""
            
            # Lấy nhận xét hiện tại từ User_Comments
            cursor.execute('''
                SELECT comment_text FROM User_Comments 
                WHERE user_id = ? AND period_start = ? AND period_end = ?
                ORDER BY updated_date DESC LIMIT 1
            ''', (user_id, date_from, date_to))
            comment_result = cursor.fetchone()
            if comment_result:
                current_comment = comment_result[0] or ""
            
            # Tính điểm kỳ trước (cùng khoảng thời gian tuần trước)
            if date_from and date_to:
                try:
                    period_start = datetime.strptime(date_from, '%Y-%m-%d')
                    period_end = datetime.strptime(date_to, '%Y-%m-%d')
                    period_duration = (period_end - period_start).days
                    
                    # Tính ngày của kỳ trước (cùng khoảng thời gian)
                    prev_period_end = period_start - timedelta(days=1)
                    prev_period_start = prev_period_end - timedelta(days=period_duration)
                    
                    prev_date_from = prev_period_start.strftime('%Y-%m-%d')
                    prev_date_to = prev_period_end.strftime('%Y-%m-%d')
                    
                    # Tính điểm kỳ trước
                    prev_total_points = 0
                    
                    # Điểm hạnh kiểm kỳ trước
                    cursor.execute('''
                        SELECT SUM(total_points) FROM User_Conduct
                        WHERE user_id = ? AND is_deleted = 0 
                        AND registered_date >= ? AND registered_date <= ?
                    ''', (user_id, prev_date_from, prev_date_to))
                    prev_uc = cursor.fetchone()[0]
                    if prev_uc:
                        prev_total_points += prev_uc
                    
                    # Điểm học tập kỳ trước
                    cursor.execute('''
                        SELECT SUM(total_points) FROM User_Subjects
                        WHERE user_id = ? AND is_deleted = 0 
                        AND registered_date >= ? AND registered_date <= ?
                    ''', (user_id, prev_date_from, prev_date_to))
                    prev_us = cursor.fetchone()[0]
                    if prev_us:
                        prev_total_points += prev_us
                    
                    # Tính sự thay đổi và gợi ý nhận xét
                    current_points = total_points if total_points else 0
                    score_difference = current_points - prev_total_points
                    
                    if score_difference != 0:
                        auto_comment = get_auto_comment(score_difference)
                    
                except:
                    pass

            records.append((user_name, total_points if total_points else 0, has_data, user_id, current_comment, auto_comment))

        if sort_by == 'user_name':
            records.sort(key=lambda x: x[0], reverse=(sort_order == 'desc'))
        elif sort_by == 'total_points':
            records.sort(key=lambda x: x[1], reverse=(sort_order == 'desc'))
        elif sort_by == 'in':
            records.sort(key=lambda x: x[2], reverse=(sort_order == 'desc'))

        conn.close()

        permissions = get_user_permissions()
        return render_template_with_permissions('user_summary.html',
                               records=records,
                               all_users=filtered_users,
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
    class_name = None
    
    # Lấy thông tin lớp nếu có
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Classes WHERE is_deleted = 0 LIMIT 1")
    class_result = cursor.fetchone()
    if class_result:
        class_name = class_result[0]
    conn.close()
    
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

    return render_template('login.html', error=error, class_name=class_name, permissions={})

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

# --- Reset Data Page ---
@app.route('/reset')
def reset_page():
    if 'user_id' in session:
        if not can_access_master():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        
        # Danh sách các table và mô tả
        tables = [
            {'name': 'Users', 'description': 'Dữ liệu người dùng'},
            {'name': 'Classes', 'description': 'Dữ liệu lớp học'},
            {'name': 'Groups', 'description': 'Dữ liệu nhóm'},
            {'name': 'Roles', 'description': 'Dữ liệu chức vụ'},
            {'name': 'Role_Permissions', 'description': 'Dữ liệu phân quyền'},
            {'name': 'Conduct', 'description': 'Dữ liệu hạnh kiểm'},
            {'name': 'Subjects', 'description': 'Dữ liệu môn học'},
            {'name': 'Criteria', 'description': 'Dữ liệu tiêu chí đánh giá'},
            {'name': 'User_Conduct', 'description': 'Dữ liệu hạnh kiểm học sinh'},
            {'name': 'User_Subjects', 'description': 'Dữ liệu học tập học sinh'}
        ]
        
        return render_template_with_permissions('reset.html', tables=tables)
    else:
        return redirect(url_for('login'))

@app.route('/reset/table/<table_name>', methods=['POST'])
def reset_table(table_name):
    if 'user_id' in session:
        if not can_access_master():
            return jsonify({'error': 'Không có quyền truy cập'}), 403
        
        # Danh sách table được phép xóa
        allowed_tables = ['Users', 'Classes', 'Groups', 'Roles', 'Role_Permissions', 
                         'Conduct', 'Subjects', 'Criteria', 'User_Conduct', 'User_Subjects']
        
        if table_name not in allowed_tables:
            return jsonify({'error': 'Table không hợp lệ'}), 400
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Xóa dữ liệu với điều kiện đặc biệt cho bảng Roles và Users
            if table_name == 'Roles':
                # Không xóa role GVCN và Master
                cursor.execute("DELETE FROM Roles WHERE name NOT IN ('GVCN', 'Master')")
            elif table_name == 'Users':
                # Không xóa user có role Master
                cursor.execute("""
                    DELETE FROM Users 
                    WHERE role_id NOT IN (
                        SELECT id FROM Roles WHERE name = 'Master'
                    )
                """)
            elif table_name in ['Classes', 'Groups', 'Role_Permissions', 
                             'Conduct', 'Subjects', 'Criteria', 'User_Conduct', 'User_Subjects']:
                cursor.execute(f"DELETE FROM {table_name}")
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': f'Đã xóa toàn bộ dữ liệu bảng {table_name}'})
        except Exception as e:
            return jsonify({'error': f'Lỗi khi xóa dữ liệu: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Chưa đăng nhập'}), 401

# === COMMENT MANAGEMENT ROUTES ===
@app.route('/comment_management')
def comment_management():
    if 'user_id' in session:
        if not can_access_comment_management():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Lấy danh sách mẫu nhận xét
            cursor.execute('''
                SELECT id, comment_type, score_range_min, score_range_max, comment_text, created_date
                FROM Comment_Templates 
                WHERE is_deleted = 0
                ORDER BY comment_type, score_range_min
            ''')
            templates = cursor.fetchall()
            
            conn.close()
            
            return render_template_with_permissions('comment_management.html', templates=templates)
        except Exception as e:
            flash(f'Lỗi khi tải dữ liệu: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))

@app.route('/comment_template/create', methods=['GET', 'POST'])
def comment_template_create():
    if 'user_id' in session:
        if not can_access_comment_management():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            try:
                comment_type = request.form['comment_type']
                score_range_min = int(request.form['score_range_min'])
                score_range_max = int(request.form['score_range_max'])
                comment_text = request.form['comment_text']
                
                conn = connect_db()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO Comment_Templates (comment_type, score_range_min, score_range_max, comment_text)
                    VALUES (?, ?, ?, ?)
                ''', (comment_type, score_range_min, score_range_max, comment_text))
                
                conn.commit()
                conn.close()
                
                flash('Đã thêm mẫu nhận xét thành công!', 'success')
                return redirect(url_for('comment_management'))
            except Exception as e:
                flash(f'Lỗi khi thêm mẫu nhận xét: {str(e)}', 'error')
        
        return render_template_with_permissions('comment_template_create.html')
    else:
        return redirect(url_for('login'))

@app.route('/comment_template/edit/<int:template_id>', methods=['GET', 'POST'])
def comment_template_edit(template_id):
    if 'user_id' in session:
        if not can_access_comment_management():
            flash('Bạn không có quyền truy cập chức năng này', 'error')
            return redirect(url_for('index'))
        
        conn = connect_db()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            try:
                comment_type = request.form['comment_type']
                score_range_min = int(request.form['score_range_min'])
                score_range_max = int(request.form['score_range_max'])
                comment_text = request.form['comment_text']
                
                cursor.execute('''
                    UPDATE Comment_Templates 
                    SET comment_type=?, score_range_min=?, score_range_max=?, comment_text=?
                    WHERE id=? AND is_deleted=0
                ''', (comment_type, score_range_min, score_range_max, comment_text, template_id))
                
                conn.commit()
                conn.close()
                
                flash('Đã cập nhật mẫu nhận xét thành công!', 'success')
                return redirect(url_for('comment_management'))
            except Exception as e:
                flash(f'Lỗi khi cập nhật mẫu nhận xét: {str(e)}', 'error')
        
        # Lấy thông tin mẫu nhận xét
        cursor.execute('SELECT * FROM Comment_Templates WHERE id=? AND is_deleted=0', (template_id,))
        template = cursor.fetchone()
        conn.close()
        
        if not template:
            flash('Không tìm thấy mẫu nhận xét!', 'error')
            return redirect(url_for('comment_management'))
        
        return render_template_with_permissions('comment_template_edit.html', template=template)
    else:
        return redirect(url_for('login'))

@app.route('/comment_template/delete/<int:template_id>', methods=['POST'])
def comment_template_delete(template_id):
    if 'user_id' in session:
        if not can_access_comment_management():
            return jsonify({'error': 'Không có quyền truy cập'}), 403
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            cursor.execute('UPDATE Comment_Templates SET is_deleted=1 WHERE id=?', (template_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Đã xóa mẫu nhận xét thành công!'})
        except Exception as e:
            return jsonify({'error': f'Lỗi khi xóa mẫu nhận xét: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Chưa đăng nhập'}), 401

def get_auto_comment(score_difference):
    """Lấy nhận xét tự động dựa trên sự thay đổi điểm số"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        abs_diff = abs(score_difference)
        comment_type = 'encouragement' if score_difference > 0 else 'reminder'
        
        cursor.execute('''
            SELECT comment_text FROM Comment_Templates 
            WHERE comment_type = ? AND ? BETWEEN score_range_min AND score_range_max 
            AND is_deleted = 0
            ORDER BY score_range_min LIMIT 1
        ''', (comment_type, abs_diff))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    except:
        return None

@app.route('/save_user_comment', methods=['POST'])
def save_user_comment():
    if 'user_id' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
    
    try:
        data = request.get_json()
        user_id = data['user_id']
        comment_text = data['comment_text']
        period_start = data['period_start']
        period_end = data['period_end']
        
        conn = connect_db()
        cursor = conn.cursor()
        
        # Tính điểm hiện tại và điểm kỳ trước
        current_points = 0
        previous_points = 0
        
        # Tính điểm hiện tại
        if period_start and period_end:
            cursor.execute('''
                SELECT SUM(total_points) FROM User_Conduct
                WHERE user_id = ? AND is_deleted = 0 
                AND registered_date >= ? AND registered_date <= ?
            ''', (user_id, period_start, period_end))
            uc_points = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT SUM(total_points) FROM User_Subjects
                WHERE user_id = ? AND is_deleted = 0 
                AND registered_date >= ? AND registered_date <= ?
            ''', (user_id, period_start, period_end))
            us_points = cursor.fetchone()[0] or 0
            
            current_points = uc_points + us_points
            
            # Tính điểm kỳ trước
            try:
                period_start_date = datetime.strptime(period_start, '%Y-%m-%d')
                period_end_date = datetime.strptime(period_end, '%Y-%m-%d')
                period_duration = (period_end_date - period_start_date).days
                
                prev_period_end = period_start_date - timedelta(days=1)
                prev_period_start = prev_period_end - timedelta(days=period_duration)
                
                prev_date_from = prev_period_start.strftime('%Y-%m-%d')
                prev_date_to = prev_period_end.strftime('%Y-%m-%d')
                
                cursor.execute('''
                    SELECT SUM(total_points) FROM User_Conduct
                    WHERE user_id = ? AND is_deleted = 0 
                    AND registered_date >= ? AND registered_date <= ?
                ''', (user_id, prev_date_from, prev_date_to))
                prev_uc = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT SUM(total_points) FROM User_Subjects
                    WHERE user_id = ? AND is_deleted = 0 
                    AND registered_date >= ? AND registered_date <= ?
                ''', (user_id, prev_date_from, prev_date_to))
                prev_us = cursor.fetchone()[0] or 0
                
                previous_points = prev_uc + prev_us
            except:
                pass
        
        score_difference = current_points - previous_points
        
        # Kiểm tra xem đã có nhận xét cho kỳ này chưa
        cursor.execute('''
            SELECT id FROM User_Comments 
            WHERE user_id = ? AND period_start = ? AND period_end = ?
        ''', (user_id, period_start, period_end))
        existing = cursor.fetchone()
        
        if existing:
            # Cập nhật nhận xét hiện tại
            cursor.execute('''
                UPDATE User_Comments 
                SET comment_text = ?, current_score = ?, previous_score = ?, 
                    score_difference = ?, is_auto_generated = 0, updated_date = CURRENT_TIMESTAMP
                WHERE user_id = ? AND period_start = ? AND period_end = ?
            ''', (comment_text, current_points, previous_points, score_difference, 
                  user_id, period_start, period_end))
        else:
            # Thêm nhận xét mới
            cursor.execute('''
                INSERT INTO User_Comments 
                (user_id, period_start, period_end, previous_score, current_score, 
                 score_difference, comment_text, is_auto_generated)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (user_id, period_start, period_end, previous_points, current_points, 
                  score_difference, comment_text))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Đã lưu nhận xét thành công!'})
    except Exception as e:
        return jsonify({'error': f'Lỗi khi lưu nhận xét: {str(e)}'}), 500


if __name__ == '__main__':
    setup_sample_data()
    app.run(debug=True)