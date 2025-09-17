from flask import jsonify
from db_utils import (create_record, read_all_records, read_record_by_id,
                      update_record, delete_record, connect_db)
from flask import flash
from flask import  redirect, session
from flask import Flask, render_template, render_template_string, send_from_directory, abort
import config
import calendar
import os
import uuid
import json
import requests
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from flask import make_response, request, url_for
from werkzeug.utils import secure_filename
import random
import logging
import pandas as pd
import re
from unicodedata import normalize
import base64
import string

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# Helper function to normalize Vietnamese text for sorting
def normalize_vietnamese_for_sort(text):
    """Normalize Vietnamese text for proper sorting"""
    if not text:
        return ""
    
    # Convert to lowercase first
    normalized = text.lower()
    
    # Define complete Vietnamese character mapping for proper sorting
    # Ensure correct ordering: a, ă, â, b, c, d, đ, e, ê, ...
    vietnamese_map = {
        # Basic characters - assign explicit order
        'a': 'a0',
        'ă': 'a1', 'ắ': 'a1', 'ằ': 'a1', 'ẳ': 'a1', 'ẵ': 'a1', 'ặ': 'a1',
        'â': 'a2', 'ấ': 'a2', 'ầ': 'a2', 'ẩ': 'a2', 'ẫ': 'a2', 'ậ': 'a2',
        'á': 'a0', 'à': 'a0', 'ả': 'a0', 'ã': 'a0', 'ạ': 'a0',
        
        'b': 'b0',
        'c': 'c0',
        'd': 'd0',
        'đ': 'd1',  # đ comes after d
        
        'e': 'e0',
        'é': 'e0', 'è': 'e0', 'ẻ': 'e0', 'ẽ': 'e0', 'ẹ': 'e0',
        'ê': 'e1', 'ế': 'e1', 'ề': 'e1', 'ể': 'e1', 'ễ': 'e1', 'ệ': 'e1',
        
        'f': 'f0', 'g': 'g0', 'h': 'h0',
        
        'i': 'i0',
        'í': 'i0', 'ì': 'i0', 'ỉ': 'i0', 'ĩ': 'i0', 'ị': 'i0',
        
        'j': 'j0', 'k': 'k0', 'l': 'l0', 'm': 'm0', 'n': 'n0',
        
        'o': 'o0',
        'ó': 'o0', 'ò': 'o0', 'ỏ': 'o0', 'õ': 'o0', 'ọ': 'o0',
        'ô': 'o1', 'ố': 'o1', 'ồ': 'o1', 'ổ': 'o1', 'ỗ': 'o1', 'ộ': 'o1',
        'ơ': 'o2', 'ớ': 'o2', 'ờ': 'o2', 'ở': 'o2', 'ỡ': 'o2', 'ợ': 'o2',
        
        'p': 'p0', 'q': 'q0', 'r': 'r0', 's': 's0', 't': 't0',
        
        'u': 'u0',
        'ú': 'u0', 'ù': 'u0', 'ủ': 'u0', 'ũ': 'u0', 'ụ': 'u0',
        'ư': 'u1', 'ứ': 'u1', 'ừ': 'u1', 'ử': 'u1', 'ữ': 'u1', 'ự': 'u1',
        
        'v': 'v0', 'w': 'w0', 'x': 'x0',
        
        'y': 'y0',
        'ý': 'y0', 'ỳ': 'y0', 'ỷ': 'y0', 'ỹ': 'y0', 'ỵ': 'y0',
        
        'z': 'z0'
    }
    
    # Apply Vietnamese character mapping
    result = ""
    for char in normalized:
        if char in vietnamese_map:
            result += vietnamese_map[char]
        else:
            result += char
    
    return result

def extract_first_name(full_name):
    """Extract the first name (last word) from full name"""
    if not full_name:
        return ""
    return full_name.strip().split()[-1]

def vietnamese_sort_key(text, sort_by_first_name=False):
    """Generate sort key for Vietnamese text, optionally sorting by first name"""
    if sort_by_first_name:
        first_name = extract_first_name(text)
        return normalize_vietnamese_for_sort(first_name)
    else:
        return normalize_vietnamese_for_sort(text)


# URL Encryption Functions for User Report Security
def generate_report_token(user_id, date_from=None, date_to=None, expiry_hours=24):
    """Generate encrypted token for user report access"""
    # Create timestamp for expiry
    expiry_timestamp = int((datetime.now() + timedelta(hours=expiry_hours)).timestamp())
    
    # Create payload
    payload = {
        'user_id': user_id,
        'date_from': date_from,
        'date_to': date_to,
        'expires': expiry_timestamp
    }
    
    # Convert to JSON string
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    # Encode with base64
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    # Create HMAC signature using app secret key
    signature = hmac.new(
        app.secret_key.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()[:16]  # Take first 16 chars for shorter URL
    
    # Combine payload and signature
    token = f"{payload_b64}.{signature}"
    
    return token

def verify_report_token(token):
    """Verify and decode report token"""
    try:
        # Split token and signature
        if '.' not in token:
            return None
            
        payload_b64, signature = token.rsplit('.', 1)
        
        # Verify signature
        expected_signature = hmac.new(
            app.secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        
        # Check expiry
        if payload.get('expires', 0) < int(datetime.now().timestamp()):
            return None
            
        return payload
        
    except Exception as e:
        print(f"Token verification error: {e}")
        return None


# Generic URL Encryption Functions for Edit/Delete Operations
def generate_action_token(action_type, record_id, table_name, expiry_hours=2):
    """Generate encrypted token for edit/delete operations"""
    # Create timestamp for expiry (shorter expiry for security)
    expiry_timestamp = int((datetime.now() + timedelta(hours=expiry_hours)).timestamp())
    
    # Create payload
    payload = {
        'action': action_type,  # 'edit' or 'delete'
        'id': record_id,
        'table': table_name,
        'expires': expiry_timestamp
    }
    
    # Convert to JSON string
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    # Encode with base64
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    # Create HMAC signature
    signature = hmac.new(
        app.secret_key.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    # Combine payload and signature
    token = f"{payload_b64}.{signature}"
    
    return token

def verify_action_token(token, expected_action=None, expected_table=None):
    """Verify and decode action token"""
    try:
        # Split token and signature
        if '.' not in token:
            return None
            
        payload_b64, signature = token.rsplit('.', 1)
        
        # Verify signature
        expected_signature = hmac.new(
            app.secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        
        # Check expiry
        if payload.get('expires', 0) < int(datetime.now().timestamp()):
            return None
        
        # Validate action and table if specified
        if expected_action and payload.get('action') != expected_action:
            return None
        
        if expected_table and payload.get('table') != expected_table:
            return None
            
        return payload
        
    except Exception as e:
        print(f"Action token verification error: {e}")
        return None

def delete_record_by_key(table_name, key_name, key_value):
    """Delete records from table_name where key_name = key_value"""
    conn = connect_db()
    cursor = conn.cursor()
    query = f"DELETE FROM {table_name} WHERE {key_name} = ?"
    cursor.execute(query, (key_value,))
    conn.commit()
    conn.close()

def delete_all_role_permissions_except_system():
    system_roles = [5, 9, 15]
    tables = [
        'Role_Permissions',
        'Role_Menu_Permissions',
        'Role_Subject_Permissions',
        'Role_Criteria_Permissions',
        'Role_User_Permissions',
        'Role_Conduct_Permissions'
    ]
    conn = connect_db()
    cursor = conn.cursor()
    for table in tables:
        query = f"DELETE FROM {table} WHERE role_id NOT IN ({','.join(str(r) for r in system_roles)})"
        cursor.execute(query)
    conn.commit()
    conn.close()
     
@app.route('/secure/<action>/<table>/<token>', methods=['GET', 'POST'])
def secure_action_handler(action, table, token):
    """Generic handler for secure edit/delete operations"""
    # Verify token
    payload = verify_action_token(token, expected_action=action, expected_table=table)
    if not payload:
        flash('Link đã hết hạn hoặc không hợp lệ', 'error')
        return redirect(url_for('login'))
    
    record_id = payload.get('id')
    
    # Route to appropriate handler based on action and table
    if action == 'edit':
        if table == 'users':
            return user_edit_secure(record_id, token)
        elif table == 'user_conduct':
            return user_conduct_edit_secure(record_id, token)
        elif table == 'user_subjects':
            return user_subjects_edit_secure(record_id, token)
        elif table == 'classes':
            return class_edit_secure(record_id, token)
        elif table == 'groups':
            return group_edit_secure(record_id, token)
        elif table == 'roles':
            return role_edit_secure(record_id, token)
        elif table == 'conducts':
            return conduct_edit_secure(record_id, token)
        elif table == 'subjects':
            return subject_edit_secure(record_id, token)
        elif table == 'criteria':
            return criteria_edit_secure(record_id, token)
        elif table == 'comment_templates':
            return comment_template_edit_secure(record_id, token)
    elif action == 'delete':
        if table == 'users':
            return user_delete_secure(record_id, token)
        elif table == 'user_conduct':
            return user_conduct_delete_secure(record_id, token)
        elif table == 'user_subjects':
            return user_subjects_delete_secure(record_id, token)
        elif table == 'classes':
            return class_delete_secure(record_id, token)
        elif table == 'groups':
            return group_delete_secure(record_id, token)
        elif table == 'roles':
            return role_delete_secure(record_id, token)
        elif table == 'conducts':
            return conduct_delete_secure(record_id, token)
        elif table == 'subjects':
            return subject_delete_secure(record_id, token)
        elif table == 'criteria':
            return criteria_delete_secure(record_id, token)
        elif table == 'comment_templates':
            return comment_template_delete_secure(record_id, token)
    
    flash('Thao tác không hợp lệ', 'error')
    return redirect(url_for('login'))

@app.route('/generate_action_link', methods=['POST'])
def generate_action_link():
    """Generate secure action link for authenticated users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        action = data.get('action')  # 'edit' or 'delete'
        record_id = data.get('id')
        table = data.get('table')
        expiry_hours = data.get('expiry_hours', 2)  # Default 2 hours
        
        if not all([action, record_id, table]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Generate token
        token = generate_action_token(action, record_id, table, expiry_hours)
        
        # Generate URL
        action_url = url_for('secure_action_handler', action=action, table=table, token=token, _external=True)
        
        return jsonify({
            'success': True,
            'url': action_url,
            'token': token,
            'expires_in_hours': expiry_hours
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# System config management functions
def load_system_config():
    """Load system configuration from JSON file"""
    try:
        with open('system_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default config if file doesn't exist or is invalid
        default_config = {
            "system_expiry_date": None,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": None
        }
        save_system_config_to_file(default_config)
        return default_config

def save_system_config_to_file(config):
    """Save system configuration to JSON file"""
    try:
        config['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('system_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_current_date_online():
    """Get current date from online API (Vietnam timezone)"""
    try:
        # Use World Time API for Vietnam timezone
        response = requests.get('http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh', timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Parse the datetime string and extract date
            datetime_str = data['datetime']
            # Format: 2024-01-15T10:30:45.123456+07:00
            current_datetime = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return current_datetime.date()
        else:
            return None
    except Exception as e:
        print(f"Error getting online time: {e}")
        return None

def check_system_expiry():
    """Check if system has expired using online time API"""
    config = load_system_config()
    expiry_date = config.get('system_expiry_date')
    
    if not expiry_date:
        return False  # No expiry date set
    
    try:
        # Get current date from online API (Vietnam timezone)
        current_date = get_current_date_online()
        if current_date is None:
            # Fallback to local time if API fails
            current_date = datetime.now().date()
        
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        return current_date > expiry
    except ValueError:
        return False  # Invalid date format

def is_master_user(user_id):
    """Check if user has master role"""
    if not user_id:
        return False
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.name 
            FROM Users u 
            JOIN Roles r ON u.role_id = r.id 
            WHERE u.id = ? AND u.is_deleted = 0
        """, (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0].lower() == 'master':
            return True
        return False
    except Exception as e:
        print(f"Error checking master role: {e}")
        return False


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

            CREATE TABLE IF NOT EXISTS Role_Menu_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                menu_name TEXT NOT NULL,
                is_allowed BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id)
            );

            CREATE TABLE IF NOT EXISTS Role_Subject_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                subject_id INTEGER,
                is_all BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id),
                FOREIGN KEY (subject_id) REFERENCES Subjects(id)
            );

            CREATE TABLE IF NOT EXISTS Role_Criteria_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                criteria_id INTEGER,
                is_all BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id),
                FOREIGN KEY (criteria_id) REFERENCES Criteria(id)
            );

            CREATE TABLE IF NOT EXISTS Role_Conduct_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                conduct_id INTEGER,
                is_all BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id),
                FOREIGN KEY (conduct_id) REFERENCES Conduct(id)
            );

            CREATE TABLE IF NOT EXISTS Role_Group_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                group_id INTEGER,
                is_all BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id),
                FOREIGN KEY (group_id) REFERENCES Groups(id)
            );

            CREATE TABLE IF NOT EXISTS Role_User_Permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                user_id INTEGER,
                is_all BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES Roles(id),
                FOREIGN KEY (user_id) REFERENCES Users(id)
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

            CREATE TABLE IF NOT EXISTS Settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES Users(id)
            );

            CREATE TABLE IF NOT EXISTS User_Comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                previous_score INTEGER DEFAULT 0,
                current_score INTEGER DEFAULT 0,
                score_difference INTEGER DEFAULT 0,
                comment_text TEXT,
                is_auto_generated BOOLEAN DEFAULT 0,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(id)
            );

            CREATE TABLE IF NOT EXISTS Comment_Templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_category TEXT NOT NULL, -- 'academic' hoặc 'conduct'
                comment_type TEXT NOT NULL, -- 'encouragement' hoặc 'reminder'
                score_range_min INTEGER,
                score_range_max INTEGER,
                comment_text TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
    # Thêm setting mặc định cho background
    conn.execute("""
        INSERT OR IGNORE INTO Settings (setting_key, setting_value) 
        VALUES ('background_image', '')
    """)
    
    # Thêm các cột mới cho Users table nếu chưa tồn tại
    try:
        conn.execute("ALTER TABLE Users ADD COLUMN role_username TEXT")
    except:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE Users ADD COLUMN role_password TEXT")
    except:
        pass  # Column already exists
    
    # Thêm cột color cho Comment_Templates table nếu chưa tồn tại
    try:
        conn.execute("ALTER TABLE Comment_Templates ADD COLUMN color TEXT DEFAULT '#2e800b'")
    except:
        pass  # Column already exists
    
    conn.commit()
    conn.close()

def is_user_gvcn():
    if 'user_id' in session:
        user = read_record_by_id('Users', session['user_id'])
        if not user or not user[6]:  # Check if user exists and has role_id
            return False
        role = read_record_by_id('Roles', user[6]) # role_id is at index 6
        return (role and role[1] == 'GVCN') # role name is at index 1
    return False



def get_user_by_id(user_id):
    """Get user information by user_id"""
    user_record = read_record_by_id('Users', user_id)
    if not user_record:
        return None
    
    # Convert tuple to dictionary for easier access
    # Correct mapping: id, name, username, password, class_id, group_id, role_id, is_deleted
    return {
        'id': user_record[0],
        'name': user_record[1],           # name is at index 1
        'username': user_record[2],       # username is at index 2  
        'password': user_record[3],       # password is at index 3
        'class_id': user_record[4],       # class_id is at index 4
        'group_id': user_record[5],       # group_id is at index 5
        'role_id': user_record[6],        # role_id is at index 6
        'is_deleted': user_record[7]      # is_deleted is at index 7
    }



def get_user_data_filters():
    """Get data filters based on user permissions"""
    if 'user_id' not in session:
        return {}
    
    user = read_record_by_id('Users', session['user_id'])
    
    filters = {
        'user_id': user[0],
        'group_id': user[5],  # group_id at index 5
        'class_id': user[4],  # class_id at index 4
    }
    
    return filters

def can_access_master():
    """Check if user can access master functions"""
    if session.get('role_name') == 'Master' or session.get('role_name') == 'GVCN':
        return True
    else:
        return False

def can_access_menu(menu_name):
    """Check if user can access specific menu based on role permissions"""
    if 'role_id' not in session:
        return False
    
    role_id = session['role_id']
    
    # Master role always has access
    if session.get('role_name') == 'Master':
        return True
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_allowed FROM Role_Menu_Permissions WHERE role_id = ? AND menu_name = ?", 
                   (role_id, menu_name))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else False

def can_access_conduct_management():
    """Check if user can access conduct management"""
    return True

def can_access_academic_management():
    """Check if user can access academic management"""
    return True

def can_access_group_statistics():
    """Check if user can access group statistics"""
    return True

def can_access_student_statistics():
    """Check if user can access student statistics"""
    return True

def can_access_comment_management():
    """Check if user can access comment management"""
    return True

def render_template_with_permissions(template_name, **kwargs):
    """Helper function to render template with permissions always included"""
    if 'user_id' in session:
        # permissions = get_user_permissions()
        # kwargs['permissions'] = permissions
        kwargs['is_gvcn'] = is_user_gvcn()
        # Thêm thông tin user hiện tại cho footer
        kwargs['current_user_info'] = get_current_user_info()
        # Thêm thông tin master role để kiểm tra trong template
        kwargs['is_master'] = is_master_user(session['user_id'])
        # Thêm menu permissions
        kwargs['menu_permissions'] = get_menu_permissions()
        
    return render_template(template_name, **kwargs)

def get_menu_permissions():
    """Get menu permissions for current user's role"""
    if 'role_id' not in session:
        return {}
    
    role_id = session['role_id']
    
    # Master role has all permissions
    if session.get('role_name') == 'Master':
        return {
            'master': True,
            'user_conduct': True,
            'user_subject': True,
            'group_summary': True,
            'user_summary': True,
            'student_report': True
        }
    
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT menu_name, is_allowed FROM Role_Menu_Permissions WHERE role_id = ?", (role_id,))
    results = cursor.fetchall()
    conn.close()
    
    menu_permissions = {}
    for menu_name, is_allowed in results:
        menu_permissions[menu_name] = bool(is_allowed)
    
    return menu_permissions

def get_current_user_info():
    """Get current user information for display"""
    if 'user_id' not in session:
        return None
    
    user = read_record_by_id('Users', session['user_id'])
    if not user:
        return None
    
    role = None
    if user[6]:  # role_id
        role = read_record_by_id('Roles', user[6])
    
    return {
        'id': user[0],
        'name': user[1],
        'username': user[2],
        'role_name': role[1] if role else None
    }

def require_menu_permission(menu_key):
    """Kiểm tra quyền menu, nếu không có thì chuyển hướng về trang chủ"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    menu_permissions = get_menu_permissions()
    if not menu_permissions.get(menu_key, False):
        return redirect(url_for('home'))
    return None  # Có quyền, tiếp tục xử lý

def get_setting(key, default_value=''):
    """Get setting value from Settings table"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM Settings WHERE setting_key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default_value
    except:
        return default_value

def set_setting(key, value, updated_by=None):
    """Set setting value in Settings table"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO Settings (setting_key, setting_value, updated_at, updated_by)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        """, (key, value, updated_by))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting value: {e}")
        return False

def allowed_file(filename):
    """Check if uploaded file is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder):
    """Save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        # Tạo tên file unique để tránh trùng lặp
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Đảm bảo thư mục tồn tại với đường dẫn tuyệt đối
        app_root = os.path.dirname(os.path.abspath(__file__))
        full_upload_folder = os.path.join(app_root, upload_folder)
        os.makedirs(full_upload_folder, exist_ok=True)
        
        file_path = os.path.join(full_upload_folder, filename)
        file.save(file_path)
        return filename
    return None



def get_background_image():
    """Tìm ảnh background trong folder upload"""
    try:
        app_root = os.path.dirname(os.path.abspath(__file__))
        backgrounds_dir = os.path.join(app_root, 'static', 'uploads', 'backgrounds')
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(backgrounds_dir, exist_ok=True)
        
        # Tìm ảnh trong thư mục
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        for filename in os.listdir(backgrounds_dir):
            if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                return filename
        
        return None
    except:
        return None

def clear_all_background_images():
    """Xóa tất cả ảnh background trong folder upload"""
    try:
        app_root = os.path.dirname(os.path.abspath(__file__))
        backgrounds_dir = os.path.join(app_root, 'static', 'uploads', 'backgrounds')
        
        if os.path.exists(backgrounds_dir):
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            for filename in os.listdir(backgrounds_dir):
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    file_path = os.path.join(backgrounds_dir, filename)
                    os.remove(file_path)
        return True
    except Exception as e:
        print(f"Error clearing background images: {e}")
        return False

def get_filtered_users_by_role():
    """Get filtered users based on current user's role permissions"""
    if 'role_id' not in session:
        return []
    
    role_id = session['role_id']
    
    # Master role gets all users
    if session.get('role_name') == 'Master':
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, name FROM Users WHERE is_deleted = 0 ORDER BY name")
        users = cursor.fetchall()
        conn.close()
        return [{'id': user[0], 'username': user[1], 'name': user[2]} for user in users]
    
    # Get user permissions for this role
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get specific user IDs for this role
    cursor.execute("SELECT user_id FROM Role_User_Permissions WHERE role_id = ?", (role_id,))
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not user_ids:
        return []
    
    # Get user details
    conn = connect_db()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(user_ids))
    cursor.execute(f"SELECT id, name FROM Users WHERE id IN ({placeholders}) AND is_deleted = 0 ORDER BY name", user_ids)
    users = cursor.fetchall()
    conn.close()
    

    return [{'id': user[0], 'name': user[1]} for user in users]

def get_filtered_groups_by_role():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 ORDER BY name")
    groups = cursor.fetchall()
    conn.close()
    return [{'id': group[0], 'name': group[1]} for group in groups]

def get_filtered_conducts_by_role():
    """Get filtered conducts based on current user's role permissions"""
    if 'role_id' not in session:
        return []
    
    role_id = session['role_id']
    
    # Master role gets all conducts
    if session.get('role_name') == 'Master':
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, conduct_type, conduct_points FROM Conduct WHERE is_deleted = 0 ORDER BY conduct_type, name DESC")
        conducts = cursor.fetchall()
        conn.close()
        return [{'id': conduct[0], 'name': conduct[1], 'conduct_type': conduct[2], 'conduct_points': conduct[3]} for conduct in conducts]
    
    # Get conduct permissions for this role
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if role has permission to all conducts
    cursor.execute("SELECT is_all FROM Role_Conduct_Permissions WHERE role_id = ? LIMIT 1", (role_id,))
    is_all_result = cursor.fetchone()
    
    if is_all_result and is_all_result[0]:
        # Role has access to all conducts
        cursor.execute("SELECT id, name, conduct_type, conduct_points FROM Conduct WHERE is_deleted = 0 ORDER BY conduct_type, name DESC")
        conducts = cursor.fetchall()
        conn.close()
        return [{'id': conduct[0], 'name': conduct[1], 'conduct_type': conduct[2], 'conduct_points': conduct[3]} for conduct in conducts]
    
    # Get specific conduct IDs for this role
    cursor.execute("SELECT conduct_id FROM Role_Conduct_Permissions WHERE role_id = ?", (role_id,))
    conduct_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not conduct_ids:
        return []
    
    # Get conduct details
    conn = connect_db()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(conduct_ids))
    cursor.execute(f"SELECT id, name, conduct_type, conduct_points FROM Conduct WHERE id IN ({placeholders}) AND is_deleted = 0 ORDER BY conduct_type, conduct_points DESC", conduct_ids)
    conducts = cursor.fetchall()
    conn.close()
    
    return [{'id': conduct[0], 'name': conduct[1], 'conduct_type': conduct[2], 'conduct_points': conduct[3]} for conduct in conducts]

def get_filtered_subjects_by_role():
    """Get filtered subjects based on current user's role permissions"""
    if 'role_id' not in session:
        return []
    
    role_id = session['role_id']
    
    # Master role gets all subjects
    if session.get('role_name') == 'Master':
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0 ORDER BY name")
        subjects = cursor.fetchall()
        conn.close()
        return [{'id': subject[0], 'name': subject[1]} for subject in subjects]
    
    # Get subject permissions for this role
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if role has permission to all subjects
    cursor.execute("SELECT is_all FROM Role_Subject_Permissions WHERE role_id = ? LIMIT 1", (role_id,))
    is_all_result = cursor.fetchone()
    
    if is_all_result and is_all_result[0]:
        # Role has access to all subjects
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0 ORDER BY name")
        subjects = cursor.fetchall()
        conn.close()
        return [{'id': subject[0], 'name': subject[1]} for subject in subjects]
    
    # Get specific subject IDs for this role
    cursor.execute("SELECT subject_id FROM Role_Subject_Permissions WHERE role_id = ?", (role_id,))
    subject_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not subject_ids:
        return []
    
    # Get subject details
    conn = connect_db()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(subject_ids))
    cursor.execute(f"SELECT id, name FROM Subjects WHERE id IN ({placeholders}) AND is_deleted = 0 ORDER BY name", subject_ids)
    subjects = cursor.fetchall()
    conn.close()
    
    return [{'id': subject[0], 'name': subject[1]} for subject in subjects]

def get_filtered_criteria_by_role():
    """Get filtered criteria based on current user's role permissions"""
    if 'role_id' not in session:
        return []
    
    role_id = session['role_id']
    
    # Master role gets all criteria
    if session.get('role_name') == 'Master':
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, criterion_type, criterion_points FROM Criteria WHERE is_deleted = 0 ORDER BY criterion_type, name")
        criteria = cursor.fetchall()
        conn.close()
        return [{'id': criterion[0], 'name': criterion[1], 'criterion_type': criterion[2], 'criterion_points': criterion[3]} for criterion in criteria]
    
    # Get criteria permissions for this role
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if role has permission to all criteria
    cursor.execute("SELECT is_all FROM Role_Criteria_Permissions WHERE role_id = ? LIMIT 1", (role_id,))
    is_all_result = cursor.fetchone()
    
    if is_all_result and is_all_result[0]:
        # Role has access to all criteria
        cursor.execute("SELECT id, name, criterion_type, criterion_points FROM Criteria WHERE is_deleted = 0 ORDER BY criterion_type, name")
        criteria = cursor.fetchall()
        conn.close()
        return [{'id': criterion[0], 'name': criterion[1], 'criterion_type': criterion[2], 'criterion_points': criterion[3]} for criterion in criteria]
    
    # Get specific criteria IDs for this role
    cursor.execute("SELECT criteria_id FROM Role_Criteria_Permissions WHERE role_id = ?", (role_id,))
    criteria_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not criteria_ids:
        return []
    
    # Get criteria details
    conn = connect_db()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(criteria_ids))
    cursor.execute(f"SELECT id, name, criterion_type, criterion_points FROM Criteria WHERE id IN ({placeholders}) AND is_deleted = 0 ORDER BY criterion_type, name", criteria_ids)
    criteria = cursor.fetchall()
    conn.close()
    
    return [{'id': criterion[0], 'name': criterion[1], 'criterion_type': criterion[2], 'criterion_points': criterion[3]} for criterion in criteria]

def format_date_ddmmyyyy(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return date_str  # Nếu lỗi thì trả về nguyên bản
    
def generate_random_string(length=6):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))

# Trang chủ
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        classes = read_all_records('Classes', ['id', 'name'])
        # Kiểm tra xem đã có class nào tồn tại chưa
        has_existing_class = len(classes) > 0
        return render_template_with_permissions('classes.html', classes=classes, has_existing_class=has_existing_class, 
                             is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))

@app.route('/classes/create', methods=['GET', 'POST'])
def class_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        groups = read_all_records('Groups', ['id', 'name'])
        return render_template_with_permissions('groups.html', groups=groups, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/groups/create', methods=['GET', 'POST'])
def group_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        roles = read_all_records('Roles', ['id', 'name'])
        return render_template_with_permissions('roles.html', roles=roles, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/roles/create', methods=['GET', 'POST'])
def role_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    if role_data and (role_data[1] in ['GVCN', 'Master', 'Học sinh']):
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
        delete_record_by_key('Role_Permissions', 'role_id', id)
        delete_record_by_key('Role_Menu_Permissions', 'role_id', id)
        delete_record_by_key('Role_Subject_Permissions', 'role_id', id)
        delete_record_by_key('Role_Criteria_Permissions', 'role_id', id)
        delete_record_by_key('Role_User_Permissions', 'role_id', id)
        delete_record_by_key('Role_Conduct_Permissions', 'role_id', id)

        flash('Xóa chức vụ thành công', 'success')
    
    return redirect(url_for('roles_list'))

# --- API routes for Role Permissions ---
@app.route('/api/roles/<int:role_id>/menu-permissions')
def get_role_menu_permissions(role_id):
    if 'user_id' in session:
        
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT menu_name FROM Role_Menu_Permissions WHERE role_id = ? AND is_allowed = 1", (role_id,))
        menus = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'menus': menus})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/menu-permissions', methods=['POST'])
def save_role_menu_permissions(role_id):
    if 'user_id' in session:
        
        menus = request.json.get('menus', [])
        
        conn = connect_db()
        cursor = conn.cursor()
        
        # Delete existing permissions
        cursor.execute("DELETE FROM Role_Menu_Permissions WHERE role_id = ?", (role_id,))
        
        # Insert new permissions
        menu_options = ['master', 'user_conduct', 'user_subject', 'group_summary', 'user_summary', 'student_report']
        for menu in menu_options:
            is_allowed = 1 if menu in menus else 0
            cursor.execute("INSERT INTO Role_Menu_Permissions (role_id, menu_name, is_allowed) VALUES (?, ?, ?)", 
                         (role_id, menu, is_allowed))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Lưu quyền menu thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/subject-permissions')
def get_role_subject_permissions(role_id):
    if 'user_id' in session:
        
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_all FROM Role_Subject_Permissions WHERE role_id = ? LIMIT 1", (role_id,))
        is_all_row = cursor.fetchone()
        is_all = is_all_row[0] if is_all_row else False
        
        cursor.execute("SELECT subject_id FROM Role_Subject_Permissions WHERE role_id = ? AND subject_id IS NOT NULL", (role_id,))
        subject_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'is_all': is_all, 'subject_ids': subject_ids})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/subject-permissions', methods=['POST'])
def save_role_subject_permissions(role_id):
    if 'user_id' in session:
        
        is_all = request.json.get('is_all', False)
        subject_ids = request.json.get('subject_ids', [])
        
        conn = connect_db()
        cursor = conn.cursor()
        
        # Delete existing permissions
        cursor.execute("DELETE FROM Role_Subject_Permissions WHERE role_id = ?", (role_id,))
        
        # Insert new permissions
        if is_all:
            cursor.execute("INSERT INTO Role_Subject_Permissions (role_id, subject_id, is_all) VALUES (?, NULL, 1)", (role_id,))
        else:
            for subject_id in subject_ids:
                cursor.execute("INSERT INTO Role_Subject_Permissions (role_id, subject_id, is_all) VALUES (?, ?, 0)", 
                             (role_id, subject_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Lưu quyền môn học thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/subjects')
def get_subjects_api():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Subjects WHERE is_deleted = 0 ORDER BY name")
        subjects = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(subjects)
    return jsonify({'error': 'Unauthorized'}), 401

# --- API routes for Criteria Permissions ---
@app.route('/api/roles/<int:role_id>/criteria-permissions')
def get_role_criteria_permissions(role_id):
    if 'user_id' in session:
        
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_all FROM Role_Criteria_Permissions WHERE role_id = ? LIMIT 1", (role_id,))
        is_all_row = cursor.fetchone()
        is_all = is_all_row[0] if is_all_row else False
        
        cursor.execute("SELECT criteria_id FROM Role_Criteria_Permissions WHERE role_id = ? AND criteria_id IS NOT NULL", (role_id,))
        criteria_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
                
        return jsonify({'is_all': is_all, 'criteria_ids': criteria_ids})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/criteria-permissions', methods=['POST'])
def save_role_criteria_permissions(role_id):
    if 'user_id' in session:
        
        is_all = request.json.get('is_all', False)
        criteria_ids = request.json.get('criteria_ids', [])
        
        conn = connect_db()
        cursor = conn.cursor()
        
        # Delete existing permissions
        cursor.execute("DELETE FROM Role_Criteria_Permissions WHERE role_id = ?", (role_id,))
        
        # Insert new permissions
        if is_all:
            cursor.execute("INSERT INTO Role_Criteria_Permissions (role_id, criteria_id, is_all) VALUES (?, NULL, 1)", (role_id,))
        else:
            for criteria_id in criteria_ids:
                cursor.execute("INSERT INTO Role_Criteria_Permissions (role_id, criteria_id, is_all) VALUES (?, ?, 0)", 
                             (role_id, criteria_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Lưu quyền tiêu chí thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/criteria')
def get_all_criteria_api():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Criteria WHERE is_deleted = 0 ORDER BY name")
        criteria = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(criteria)
    return jsonify({'error': 'Unauthorized'}), 401

# --- API routes for Conduct Permissions ---
@app.route('/api/roles/<int:role_id>/conduct-permissions')
def get_role_conduct_permissions(role_id):
    if 'user_id' in session:       
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_all FROM Role_Conduct_Permissions WHERE role_id = ? LIMIT 1", (role_id,))
        is_all_row = cursor.fetchone()
        is_all = is_all_row[0] if is_all_row else False
        
        cursor.execute("SELECT conduct_id FROM Role_Conduct_Permissions WHERE role_id = ? AND conduct_id IS NOT NULL", (role_id,))
        conduct_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({'is_all': is_all, 'conduct_ids': conduct_ids})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/conduct-permissions', methods=['POST'])
def save_role_conduct_permissions(role_id):
    if 'user_id' in session:
        
        is_all = request.json.get('is_all', False)
        conduct_ids = request.json.get('conduct_ids', [])
        
        conn = connect_db()
        cursor = conn.cursor()
        
        # Delete existing permissions
        cursor.execute("DELETE FROM Role_Conduct_Permissions WHERE role_id = ?", (role_id,))
        
        # Insert new permissions
        if is_all:
            cursor.execute("INSERT INTO Role_Conduct_Permissions (role_id, conduct_id, is_all) VALUES (?, NULL, 1)", (role_id,))
        else:
            for conduct_id in conduct_ids:
                cursor.execute("INSERT INTO Role_Conduct_Permissions (role_id, conduct_id, is_all) VALUES (?, ?, 0)", 
                             (role_id, conduct_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Lưu quyền hạnh kiểm thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/conducts')
def get_conducts_api():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Conduct WHERE is_deleted = 0 ORDER BY name")
        conducts = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(conducts)
    return jsonify({'error': 'Unauthorized'}), 401


@app.route('/api/groups')
def get_groups_api():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 ORDER BY name")
        groups = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        conn.close()
        return jsonify(groups)
    return jsonify({'error': 'Unauthorized'}), 401

# --- API routes for User Permissions ---
@app.route('/api/roles/<int:role_id>/user-permissions')
def get_role_user_permissions(role_id):
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Role_User_Permissions WHERE role_id = ? AND user_id IS NOT NULL", (role_id,))
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        return jsonify({'user_ids': user_ids})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/roles/<int:role_id>/user-permissions', methods=['POST'])
def save_role_user_permissions(role_id):
    if 'user_id' in session:
        user_ids = request.json.get('user_ids', [])  # Chỉ nhận danh sách user

        conn = connect_db()
        cursor = conn.cursor()

        # Xóa quyền cũ
        cursor.execute("DELETE FROM Role_User_Permissions WHERE role_id = ?", (role_id,))

        # Lưu từng user được chọn
        for user_id in user_ids:
            cursor.execute("INSERT INTO Role_User_Permissions (role_id, user_id, is_all) VALUES (?, ?, 0)", 
                         (role_id, user_id))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Lưu danh sách user thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/users-by-groups')
def get_users_by_groups_api():
    if 'user_id' in session:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, g.id, g.name
            FROM Users u
            LEFT JOIN Roles r ON u.role_id = r.id
            LEFT JOIN Groups g ON u.group_id = g.id
            WHERE u.is_deleted = 0 
            AND (r.name IS NULL OR r.name NOT IN ('GVCN', 'Master'))
            ORDER BY g.name, u.name
        """)
        rows = cursor.fetchall()
        conn.close()
        # Group users by group
        groups = {}
        for user_id, user_name, group_id, group_name in rows:
            if group_id not in groups:
                groups[group_id] = {
                    'group_id': group_id,
                    'group_name': group_name or 'Chưa có nhóm',
                    'users': []
                }
            groups[group_id]['users'].append({'id': user_id, 'name': user_name})
        return jsonify(list(groups.values()))
    return jsonify({'error': 'Unauthorized'}), 401


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

@app.route('/api/conducts/filtered')
def get_filtered_conducts_api():
    """Get conducts filtered by current user's role permissions for modals"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conducts = get_filtered_conducts_by_role()
    conducts.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
    
    return jsonify({'conducts': conducts})

@app.route('/api/users/filtered')
def get_filtered_users_api():
    """Get users filtered by current user's role permissions for modals"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    users = get_filtered_users_by_role()
    return jsonify({'users': users})

@app.route('/api/groups/filtered')
def get_filtered_groups_api():
    """Get groups filtered by current user's role permissions for modals"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    groups = get_filtered_groups_by_role()
    return jsonify({'groups': groups})

@app.route('/api/subjects/filtered')
def get_filtered_subjects_api():
    """Get subjects filtered by current user's role permissions for modals"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    subjects = get_filtered_subjects_by_role()
    subjects.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
    
    
    return jsonify({'subjects': subjects})

@app.route('/api/criteria/filtered')
def get_filtered_criteria_api():
    """Get criteria filtered by current user's role permissions for modals"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    criteria = get_filtered_criteria_by_role()
    criteria.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
    return jsonify({'criteria': criteria})

# --- Conduct ---
@app.route('/conducts')
def conducts_list():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
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
        
        if sort_by == 'name':
            conducts.sort(key=lambda u: vietnamese_sort_key(u[1], sort_by_first_name=False))
        
        return render_template_with_permissions('conducts.html', conducts=conducts, sort_by=sort_by, sort_order=sort_order, 
                             is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/conducts/create', methods=['GET', 'POST'])
def conduct_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    delete_record_by_key('Role_Conduct_Permissions', 'conduct_id', id)
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
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
        
        if sort_by == 'name':
            subjects.sort(key=lambda u: vietnamese_sort_key(u[1], sort_by_first_name=False))
        
        return render_template_with_permissions('subjects.html', subjects=subjects, sort_by=sort_by, sort_order=sort_order, 
                             is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/subjects/create', methods=['GET', 'POST'])
def subject_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    delete_record_by_key('Role_Subject_Permissions', 'subject_id', id)
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        # Lấy tham số sắp xếp
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Validate sort parameters
        valid_sort_fields = ['name', 'criterion_type', 'criterion_points']
        if sort_by not in valid_sort_fields:
            sort_by = 'criterion_type'
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
        
        if sort_by == 'name':
            criteria.sort(key=lambda u: vietnamese_sort_key(u[1], sort_by_first_name=False))
            
        return render_template_with_permissions('criteria.html', criteria=criteria, sort_by=sort_by, sort_order=sort_order, 
                             is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))



@app.route('/criteria/create', methods=['GET', 'POST'])
def criteria_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    delete_record_by_key('Role_Criteria_Permissions', 'criteria_id', id)
    return redirect(url_for('criteria_list'))


# --- API routes for Users ---
@app.route('/api/users/<int:id>')
def get_user_api(id):
    if 'user_id' in session:
        user_data = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id', 'role_username', 'role_password'])
        return jsonify({
            'id': user_data[0],
            'name': user_data[1],
            'username': user_data[2],
            'password': user_data[3],
            'class_id': user_data[4],
            'group_id': user_data[5],
            'role_id': user_data[6],
            'role_username': user_data[7] if len(user_data) > 7 else None,
            'role_password': user_data[8] if len(user_data) > 8 else None
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
        role_username = request.json.get('role_username')
        role_password = request.json.get('role_password')

        # Kiểm tra trùng username
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ? AND password = ? AND is_deleted = 0", (username, password))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'error': 'Cặp tên đăng nhập và mật khẩu đã tồn tại'}), 400

        # Nếu có role_username và role_password, kiểm tra trùng cặp
        if role_username and role_password:
            cursor.execute("SELECT COUNT(*) FROM Users WHERE role_username = ? AND role_password = ? AND is_deleted = 0", (role_username, role_password))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return jsonify({'error': 'Cặp role username và role password đã tồn tại'}), 400

        data = {
            'name': name,
            'username': username,
            'password': password,
            'class_id': class_id,
            'group_id': group_id,
            'role_id': role_id,
            'role_username': role_username,
            'role_password': role_password,
            'is_deleted': 0
        }
        create_record('Users', data)
        conn.close()
        return jsonify({'success': True, 'message': 'Tạo mới thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user_api(id):
    if 'user_id' in session:
        # Kiểm tra user hiện tại có role Master hoặc GVCN không
        user_data = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
        
        name = request.json['name']
        username = request.json['username']
        password = request.json['password']
        class_id = request.json['class_id']
        role_id = request.json['role_id']
        group_id = request.json.get('group_id')
        role_username = request.json.get('role_username')
        role_password = request.json.get('role_password')

        # Kiểm tra trùng username (trừ user hiện tại)
        conn = connect_db()
        cursor = conn.cursor()
        # Kiểm tra trùng cặp username + password
        cursor.execute("SELECT COUNT(*) FROM Users WHERE username = ? AND password = ? AND is_deleted = 0", (username, password))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return jsonify({'error': 'Cặp tên đăng nhập và mật khẩu đã tồn tại'}), 400

        # Nếu có role_username và role_password, kiểm tra trùng cặp
        if role_username and role_password:
            cursor.execute("SELECT COUNT(*) FROM Users WHERE role_username = ? AND role_password = ? AND is_deleted = 0", (role_username, role_password))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return jsonify({'error': 'Cặp role username và role password đã tồn tại'}), 400
        

        if user_data is not None and user_data[6] == 5:  # Nếu user hiện tại là GVCN
            data = {
            'name': name,
            'username': username,
            'password': password,
            'class_id': class_id,
            'group_id': group_id,
            'role_id': 5,
            'role_username': username,
            'role_password': password
        }
        else:
            data = {
                'name': name,
                'username': username,
                'password': password,
                'class_id': class_id,
                'group_id': group_id,
                'role_id': role_id,
                'role_username': role_username,
                'role_password': role_password
            }
        update_record('Users', id, data)
        conn.close()
        return jsonify({'success': True, 'message': 'Cập nhật thành công'})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/upload_users_excel', methods=['POST'])
def upload_users_excel():    
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'excel_file' not in request.files:
        return jsonify({'error': 'Không có file được chọn'}), 400
    
    file = request.files['excel_file']
    if file.filename == '':
        return jsonify({'error': 'Không có file được chọn'}), 400
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Chỉ chấp nhận file Excel (.xlsx, .xls)'}), 400
    
    try:       
        
        # Đọc file Excel
        df = pd.read_excel(file)
        
        # Kiểm tra cấu trúc file
        if len(df.columns) < 1:
            return jsonify({'error': 'File Excel phải có cột Name'}), 400
        
        conn = connect_db()
        cursor = conn.cursor()
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Lấy STT và Họ tên
                ho_ten = str(row.iloc[0]).strip()
                
                # Bỏ qua dòng trống hoặc header
                if pd.isna(row.iloc[0]) or ho_ten.lower() in ['Name', 'name']:
                    continue
                
                # Tạo username từ từ cuối của họ tên
                words = ho_ten.split()
                if len(words) == 0:
                    errors.append(f"Dòng {index + 1}: Họ tên không hợp lệ")
                    continue
                
                # Lấy từ cuối và chuẩn hóa thành username
                last_word = words[-1]
                # Loại bỏ dấu tiếng Việt
                firstname = normalize('NFD', last_word).encode('ascii', 'ignore').decode('ascii').lower()
                # Loại bỏ ký tự đặc biệt, chỉ giữ chữ và số
                firstname = re.sub(r'[^a-z0-9]', '', firstname)
                
                if not firstname:
                    errors.append(f"Dòng {index + 1}: Không thể tạo username từ '{ho_ten}'")
                    continue
                
                # Tạo password: STT + username
                random_pass = generate_random_string()
                password = f"{random_pass}"
                
                random_number = random.randint(100, 999)
                username = f"{firstname}{random_number}"
                
                # Kiểm tra username đã tồn tại
                cursor.execute("SELECT id FROM Users WHERE username = ?", (username,))
                if cursor.fetchone():
                    errors.append(f"Dòng {index + 1}: Username '{username}' đã tồn tại")
                    continue
                
                # Thêm user mới
                data = {
                    'name': ho_ten,
                    'username': username,
                    'password': password,
                    'class_id': None,
                    'group_id': None,
                    'role_id': 9,  # Học sinh
                    'role_username': None,
                    'role_password': None
                }
                
                
                create_record('Users', data)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Dòng {index + 1}: Lỗi xử lý - {str(e)}")
                continue
        
        conn.close()
        
        message = f"Upload thành công! Đã import {imported_count} học sinh."
        if errors:
            message += f" Có {len(errors)} lỗi."
            
        return jsonify({
            'success': True, 
            'message': message,
            'imported_count': imported_count,
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'error': f'Lỗi xử lý file: {str(e)}'}), 500


@app.route('/api/generate_user_credentials', methods=['POST'])
def generate_user_credentials():
    data = request.get_json()
    name = data.get('name', '')
    if not name:
        return jsonify({'error': 'Thiếu họ tên'}), 400

    words = name.strip().split()
    if not words:
        return jsonify({'error': 'Tên không hợp lệ'}), 400

    last_word = words[-1]
    firstname = normalize('NFD', last_word).encode('ascii', 'ignore').decode('ascii').lower()
    firstname = re.sub(r'[^a-z0-9]', '', firstname)
    random_pass = generate_random_string()
    password = f"{random_pass}"
    
    random_number = random.randint(100, 999)
    username = f"{firstname}{random_number}"

    return jsonify({'username': username, 'password': password})

# --- Users ---
@app.route('/users')
def users_list():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
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
                WHERE u.is_deleted = 0 AND (r.name != 'Master' OR r.name IS NULL)
                ORDER BY {order_clause}
            """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        # Nếu sắp xếp theo first_name, thực hiện sắp xếp lại trong Python
        if sort_by == 'first_name':
            def get_first_name(user):
                name_parts = user[1].split() if user[1] else []
                last_name = name_parts[-1] if name_parts else ''
                return normalize_vietnamese_for_sort(last_name)
            
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
        return render_template_with_permissions('users.html', users=users, classes=classes, roles=roles, groups=groups, 
                               sort_by=sort_by, sort_order=sort_order, is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/users/create', methods=['GET', 'POST'])
def user_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    """Old route - redirect to secure version"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate secure token
    token = generate_action_token('edit', id, 'users', expiry_hours=2)
    
    # Redirect to secure route
    return redirect(url_for('secure_action_handler', action='edit', table='users', token=token))

def user_edit_secure(id, token):
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    error_message = None
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
            return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn(), token=token)

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
            return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn(), token=token)

        # Cập nhật bản ghi
        data = {
            'name': name,
            'username': username,
            'password': password,
            'class_id': class_id,
            'role_id': role_id
        }
        update_record('Users', id, data)
        conn.close()
        flash('Cập nhật người dùng thành công', 'success')
        return redirect(url_for('users_list'))

    user = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
    if not user:
        flash('Không tìm thấy người dùng', 'error')
        return redirect(url_for('users_list'))
    
    classes = read_all_records('Classes', ['id', 'name'])
    roles = read_all_records('Roles', ['id', 'name'])
    return render_template('user_edit.html', user=user, classes=classes, roles=roles, error_message=error_message, is_gvcn=is_user_gvcn(), token=token)

def user_delete_secure(id, token):
    """Secure user delete function"""
    if 'user_id' not in session:
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
        if is_ajax:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return redirect(url_for('login'))
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'json' in request.headers.get('Accept', '').lower()
    
    # Kiểm tra user có role Master hoặc GVCN không
    user_data = read_record_by_id('Users', id, ['id', 'name', 'username', 'password', 'class_id', 'group_id', 'role_id'])
    if user_data and user_data[6]:  # role_id at index 6
        role_data = read_record_by_id('Roles', user_data[6], ['id', 'name'])
        if role_data and role_data[1] in ['Master', 'GVCN']:
            error_msg = f'Không thể xóa user {role_data[1]}'
            if is_ajax:
                return jsonify({'success': False, 'error': error_msg})
            flash(error_msg, 'error')
            return redirect(url_for('users_list'))
    
    if not user_data:
        error_msg = 'Không tìm thấy người dùng'
        if is_ajax:
            return jsonify({'success': False, 'error': error_msg})
        flash(error_msg, 'error')
        return redirect(url_for('users_list'))
    
    delete_record('Users', id)
    delete_record_by_key('Role_User_Permissions', 'user_id', id)
    
    success_msg = 'Xóa người dùng thành công'
    if is_ajax:
        return jsonify({'success': True, 'message': success_msg})
    flash(success_msg, 'success')
    return redirect(url_for('users_list'))
    

@app.route('/users/delete/<int:id>', methods=['POST', 'GET'])
def user_delete(id):
    """Old route - redirect to secure version"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate secure token
    token = generate_action_token('delete', id, 'users', expiry_hours=1)  # Shorter expiry for delete
    
    # Redirect to secure route
    return redirect(url_for('secure_action_handler', action='delete', table='users', token=token))


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
        
        # Get individual points for this specific conduct only
        individual_points = 0
        cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
        conduct_result = cursor.fetchone()
        if conduct_result:
            individual_points = conduct_result[0] or 0

        data = {
            'user_id': user_id,
            'conduct_id': conduct_id,
            'registered_date': registered_date,
            'total_points': individual_points,  # Use individual points, not cumulative
            'entered_by': entered_by,
            'is_deleted': 0
        }
        new_id = create_record('User_Conduct', data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Tạo mới thành công', 'id': new_id})
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
        
        # Get individual points for this specific conduct only
        individual_points = 0
        cursor.execute("SELECT conduct_points FROM Conduct WHERE id = ? AND is_deleted = 0", (conduct_id,))
        conduct_result = cursor.fetchone()
        if conduct_result:
            individual_points = conduct_result[0] or 0

        data = {
            'user_id': user_id,
            'conduct_id': conduct_id,
            'registered_date': registered_date,
            'total_points': individual_points,  # Use individual points, not cumulative
            'entered_by': entered_by
        }
        update_record('User_Conduct', id, data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Cập nhật thành công', 'id': id})
    return jsonify({'error': 'Unauthorized'}), 401

# --- User_Conduct ---
@app.route('/user_conduct', methods=['GET', 'POST'])
def user_conduct_list():    
    permission_check = require_menu_permission('user_conduct')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        
        # Get sort parameters from both GET and POST requests
        sort_by = request.form.get('sort_by') or request.args.get('sort_by', 'registered_date')
        sort_order = request.form.get('sort_order') or request.args.get('sort_order', 'asc')
        
        # Debug logging for AJAX requests
        if request.form.get('ajax') == '1' or request.args.get('ajax') == '1':
            print(f"AJAX Request - sort_by: {sort_by}, sort_order: {sort_order}")

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
        
        # Special handling for user_name sorting (sort by first name)
        sort_by_first_name = (sort_by == 'user_name')

        # Get filtered data based on role permissions
        users = get_filtered_users_by_role()
        groups = get_filtered_groups_by_role()
        conducts = get_filtered_conducts_by_role()
        
        # Sort users by first name using Vietnamese normalization
        users.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=True))
        conducts.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
        groups.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
        
        # Modal users same as filtered users for consistency
        modal_users = users.copy()

        # Tính toán ngày mặc định: Thứ 2 của tuần hiện tại
        today = datetime.today()
        days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
        nearest_monday = today - timedelta(days=days_since_monday)
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=6)).strftime('%Y-%m-%d')  # Chủ Nhật của tuần

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
        
        # Base query with role-based filtering
        query = """
                SELECT uc.id, u.name AS user_name, c.name AS conduct_name, uc.registered_date, uc.total_points, uc.entered_by, g.name AS group_name
                FROM User_Conduct uc
                JOIN Users u ON uc.user_id = u.id
                JOIN Conduct c ON uc.conduct_id = c.id
                JOIN Groups g ON u.group_id = g.id
                WHERE uc.is_deleted = 0
            """
        params = []
        
        # Add role-based filtering for users
        if users:
            user_id = [user['id'] for user in users]
            query += " AND uc.user_id IN ({})".format(','.join('?' * len(user_id)))
            params.extend(user_id)
        else:
            # If no users allowed, return empty result
            query += " AND 1 = 0"
        
        # Add role-based filtering for conducts
        if conducts:
            conduct_ids = [conduct['id'] for conduct in conducts]
            query += " AND uc.conduct_id IN ({})".format(','.join('?' * len(conduct_ids)))
            params.extend(conduct_ids)
        else:
            # If no conducts allowed, return empty result
            query += " AND 1 = 0"
        
        # Add role-based filtering for groups
        if groups:
            group_ids = [group['id'] for group in groups]
            query += " AND u.group_id IN ({})".format(','.join('?' * len(group_ids)))
            params.extend(group_ids)
        else:
            # If no groups allowed, return empty result
            query += " AND 1 = 0"

        # Additional filtering based on search criteria
        if select_all_users:
            # Already filtered by role permissions above, no additional filter needed
            pass
        elif selected_users:
            # Intersect with role-allowed users
            allowed_user_id = [user['id'] for user in users]
            filtered_selected_users = [uid for uid in selected_users if int(uid) in allowed_user_id]
            if filtered_selected_users:
                query += " AND uc.user_id IN ({})".format(','.join('?' * len(filtered_selected_users)))
                params.extend(filtered_selected_users)
            else:
                query += " AND 1 = 0"

        if date_from:
            query += " AND uc.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND uc.registered_date <= ?"
            params.append(date_to)

        if select_all_conducts:
            # Already filtered by role permissions above, no additional filter needed
            pass
        elif selected_conducts:
            # Intersect with role-allowed conducts
            allowed_conduct_ids = [conduct['id'] for conduct in conducts]
            filtered_selected_conducts = [cid for cid in selected_conducts if int(cid) in allowed_conduct_ids]
            if filtered_selected_conducts:
                query += " AND uc.conduct_id IN ({})".format(','.join('?' * len(filtered_selected_conducts)))
                params.extend(filtered_selected_conducts)
            else:
                query += " AND 1 = 0"

        if select_all_groups:
            # Already filtered by role permissions above, no additional filter needed
            pass
        elif selected_groups:
            # Intersect with role-allowed groups
            allowed_group_ids = [group['id'] for group in groups]
            filtered_selected_groups = [gid for gid in selected_groups if int(gid) in allowed_group_ids]
            if filtered_selected_groups:
                query += " AND u.group_id IN ({})".format(','.join('?' * len(filtered_selected_groups)))
                params.extend(filtered_selected_groups)
            else:
                query += " AND 1 = 0"

        query += f" ORDER BY {sort_column} {sort_direction}"
        
        cursor.execute(query, params)
        db_rows = cursor.fetchall()

        # If sorting by user_name, apply Vietnamese first name sorting
        if sort_by_first_name:
            db_rows = sorted(db_rows, 
                           key=lambda r: vietnamese_sort_key(r[1], sort_by_first_name=True),
                           reverse=(sort_order == 'desc'))
        
        conn.close()
        
        records = []
        for row in db_rows:
            # row[3] là trường ngày (registered_date)
            formatted_date = format_date_ddmmyyyy(row[3])
            # Tạo tuple mới với ngày đã format
            record = (row[0], row[1], row[2], formatted_date, row[4], row[5], row[6])
            records.append(record)
    
        # Check if this is an AJAX request
        if request.form.get('ajax') == '1' or request.args.get('ajax') == '1':
            # Generate table HTML for AJAX response
            table_html = "<tbody>"
            for record in records:
                edit_button = ""
                delete_button = ""
                
                edit_button = f'<button class="btn btn-sm btn-info me-1" onclick="openEditModal({record[0]})">Edit</button>'

                delete_url = url_for('user_conduct_delete', id=record[0], sort_by=sort_by, sort_order=sort_order, 
                                    date_from=date_from, date_to=date_to, users=selected_users, 
                                    conducts=selected_conducts, groups=selected_groups)
                delete_button = f'<button class="btn btn-sm btn-danger" data-delete-url="{delete_url}" onclick="confirmDeleteRecord(this)">Delete</button>'
                
                table_html += f'<tr data-id="{record[0]}"><td>{record[1]}</td><td>{record[2]}</td><td>{record[6]}</td><td>{record[3]}</td><td style="display: none;">{record[4]}</td><td>{record[5]}</td><td class="text-nowrap">{edit_button}{delete_button}</td></tr>'
            
            table_html += "</tbody>"
            return jsonify({'html': table_html})

     
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
                               role_name=session.get('role_name'))
    else:
        return redirect(url_for('login'))


@app.route('/user_conduct/create', methods=['GET', 'POST'])
def user_conduct_create():
    permission_check = require_menu_permission('user_conduct')
    if permission_check:
        return permission_check
    
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
    """Old route - redirect to secure version"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate secure token
    token = generate_action_token('edit', id, 'user_conduct', expiry_hours=2)
    
    # Redirect to secure route
    return redirect(url_for('secure_action_handler', action='edit', table='user_conduct', token=token))

def user_conduct_edit_secure(id, token):
    permission_check = require_menu_permission('user_conduct')
    if permission_check:
        return permission_check
    
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
        
        flash('Cập nhật hạnh kiểm thành công', 'success')
        return redirect(url_for('user_conduct_list'))

    record = read_record_by_id('User_Conduct', id,
                               ['id', 'user_id', 'conduct_id', 'registered_date', 'total_points', 'entered_by'])
    if not record:
        flash('Không tìm thấy bản ghi', 'error')
        return redirect(url_for('user_conduct_list'))
    
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
                           is_gvcn=is_user_gvcn(),
                           token=token)



@app.route('/user_conduct/delete/<int:id>')
def user_conduct_delete(id):
    """Old route - redirect to secure version"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate secure token
    token = generate_action_token('delete', id, 'user_conduct', expiry_hours=1)
    
    # Redirect to secure route
    return redirect(url_for('secure_action_handler', action='delete', table='user_conduct', token=token))

def user_conduct_delete_secure(id, token):
    """Secure user conduct delete function"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Verify record exists
    record = read_record_by_id('User_Conduct', id)
    if not record:
        flash('Không tìm thấy bản ghi', 'error')
        return redirect(url_for('user_conduct_list'))
    
    delete_record('User_Conduct', id)
    flash('Xóa bản ghi thành công', 'success')
    return redirect(url_for('user_conduct_list'))


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

@app.route('/api/user_subjects/batch', methods=['POST'])
def create_user_subjects_batch_api():
    if 'user_id' in session:
        try:
            data = request.json
            user_id = data['user_id']
            registered_date = data['registered_date']
            entered_by = data['entered_by']
            subjects = data['subjects']
            
            if not subjects or len(subjects) == 0:
                return jsonify({'error': 'Không có môn học nào được chọn'}), 400
            
            conn = connect_db()
            cursor = conn.cursor()
            
            created_records = []
            
            # Create records for each selected subject
            for subject_data in subjects:
                subject_id = subject_data['subject_id']
                criteria_id = subject_data.get('criteria_id') or None
                
                # Get individual points for this specific criteria
                individual_points = 0
                if criteria_id:
                    cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
                    criteria_result = cursor.fetchone()
                    if criteria_result:
                        individual_points = criteria_result[0] or 0
                
                record_data = {
                    'user_id': user_id,
                    'subject_id': subject_id,
                    'criteria_id': criteria_id,
                    'registered_date': registered_date,
                    'total_points': individual_points,  # Use individual points for each subject
                    'entered_by': entered_by,
                    'is_deleted': 0
                }
                
                new_id = create_record('User_Subjects', record_data)
                created_records.append(new_id)
            
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': f'Tạo mới thành công {len(created_records)} bản ghi', 
                'created_count': len(created_records),
                'ids': created_records
            })
            
        except Exception as e:
            print(f"Error in batch creation: {str(e)}")
            return jsonify({'error': f'Có lỗi xảy ra: {str(e)}'}), 500
    
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
        
        # Get individual points for this specific criteria only
        individual_points = 0
        if criteria_id:
            cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
            criteria_result = cursor.fetchone()
            if criteria_result:
                individual_points = criteria_result[0] or 0

        data = {
            'user_id': user_id,
            'subject_id': subject_id,
            'criteria_id': criteria_id,
            'registered_date': registered_date,
            'total_points': individual_points,  # Use individual points, not cumulative
            'entered_by': entered_by,
            'is_deleted': 0
        }
        new_id = create_record('User_Subjects', data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Tạo mới thành công', 'id': new_id})
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
        
        # Get individual points for this specific criteria only
        individual_points = 0
        if criteria_id:
            cursor.execute("SELECT criterion_points FROM Criteria WHERE id = ? AND is_deleted = 0", (criteria_id,))
            criteria_result = cursor.fetchone()
            if criteria_result:
                individual_points = criteria_result[0] or 0

        data = {
            'user_id': user_id,
            'subject_id': subject_id,
            'criteria_id': criteria_id,
            'registered_date': registered_date,
            'total_points': individual_points,  # Use individual points, not cumulative
            'entered_by': entered_by
        }
        update_record('User_Subjects', id, data)
        conn.close()
        
        return jsonify({'success': True, 'message': 'Cập nhật thành công', 'id': id})
    return jsonify({'error': 'Unauthorized'}), 401

# --- User_Subjects ---
@app.route('/user_subjects', methods=['GET', 'POST'])
def user_subjects_list():
    permission_check = require_menu_permission('user_subject')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:        
        # Get sort parameters from both GET and POST requests  
        sort_by = request.form.get('sort_by') or request.args.get('sort_by', 'registered_date')
        sort_order = request.form.get('sort_order') or request.args.get('sort_order', 'asc')
        
        # Debug logging for AJAX requests
        if request.form.get('ajax') == '1' or request.args.get('ajax') == '1':
            print(f"AJAX Request - sort_by: {sort_by}, sort_order: {sort_order}")

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
        
        # Special handling for user_name sorting (sort by first name)
        sort_by_first_name = (sort_by == 'user_name')

        # Get filtered data based on role permissions
        users = get_filtered_users_by_role()
        groups = get_filtered_groups_by_role()
        subjects = get_filtered_subjects_by_role()
        criteria = get_filtered_criteria_by_role()
        
        # Sort users by first name using Vietnamese normalization
        users.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=True))
        groups.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
        subjects.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
        criteria.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
        
        # Modal users same as filtered users for consistency
        modal_users = users.copy()

        # Tính toán ngày mặc định: Thứ 2 của tuần hiện tại
        today = datetime.today()
        days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
        nearest_monday = today - timedelta(days=days_since_monday)
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=6)).strftime('%Y-%m-%d')  # Chủ Nhật của tuần

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
        
        # Base query with role-based filtering
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
        
        # Add role-based filtering for users
        if users:
            user_id = [user['id'] for user in users]
            query += " AND us.user_id IN ({})".format(','.join('?' * len(user_id)))
            params.extend(user_id)
        else:
            # If no users allowed, return empty result
            query += " AND 1 = 0"
        
        # Add role-based filtering for subjects
        if subjects:
            subject_ids = [subject['id'] for subject in subjects]
            query += " AND us.subject_id IN ({})".format(','.join('?' * len(subject_ids)))
            params.extend(subject_ids)
        else:
            # If no subjects allowed, return empty result
            query += " AND 1 = 0"
        
        # Add role-based filtering for groups
        if groups:
            group_ids = [group['id'] for group in groups]
            query += " AND u.group_id IN ({})".format(','.join('?' * len(group_ids)))
            params.extend(group_ids)
        else:
            # If no groups allowed, return empty result
            query += " AND 1 = 0"

        # Additional filtering based on search criteria
        if select_all_users:
            # Already filtered by role permissions above, no additional filter needed
            pass
        elif selected_users:
            # Intersect with role-allowed users
            allowed_user_id = [user['id'] for user in users]
            filtered_selected_users = [uid for uid in selected_users if int(uid) in allowed_user_id]
            if filtered_selected_users:
                query += " AND us.user_id IN ({})".format(','.join('?' * len(filtered_selected_users)))
                params.extend(filtered_selected_users)
            else:
                query += " AND 1 = 0"

        if date_from:
            query += " AND us.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND us.registered_date <= ?"
            params.append(date_to)

        if select_all_subjects:
            # Already filtered by role permissions above, no additional filter needed
            pass
        elif selected_subjects:
            # Intersect with role-allowed subjects
            allowed_subject_ids = [subject['id'] for subject in subjects]
            filtered_selected_subjects = [sid for sid in selected_subjects if int(sid) in allowed_subject_ids]
            if filtered_selected_subjects:
                query += " AND us.subject_id IN ({})".format(','.join('?' * len(filtered_selected_subjects)))
                params.extend(filtered_selected_subjects)
            else:
                query += " AND 1 = 0"

        if select_all_groups:
            # Already filtered by role permissions above, no additional filter needed
            pass
        elif selected_groups:
            # Intersect with role-allowed groups
            allowed_group_ids = [group['id'] for group in groups]
            filtered_selected_groups = [gid for gid in selected_groups if int(gid) in allowed_group_ids]
            if filtered_selected_groups:
                query += " AND u.group_id IN ({})".format(','.join('?' * len(filtered_selected_groups)))
                params.extend(filtered_selected_groups)
            else:
                query += " AND 1 = 0"

        query += f" ORDER BY {sort_column} {sort_direction}"
        cursor.execute(query, params)
        db_rows = cursor.fetchall()
        
        # If sorting by user_name, apply Vietnamese first name sorting
        if sort_by_first_name:
            db_rows = sorted(db_rows, 
                           key=lambda r: vietnamese_sort_key(r[1], sort_by_first_name=True),
                           reverse=(sort_order == 'desc'))
        
        conn.close()
        
        records = []
        for row in db_rows:
            # row[3] là trường ngày (registered_date)
            formatted_date = format_date_ddmmyyyy(row[4])
            # Tạo tuple mới với ngày đã format
            record = (row[0], row[1], row[2], row[3], formatted_date, row[5], row[6], row[7])
            records.append(record)
            
        # Check if this is an AJAX request
        if request.form.get('ajax') == '1' or request.args.get('ajax') == '1':
            # Generate table HTML for AJAX response
            table_html = "<tbody>"
            for record in records:
                edit_button = ""
                delete_button = ""
                
                edit_button = f'<button class="btn btn-sm btn-info me-1" onclick="openEditModal({record[0]})">Sửa</button>'
            
                delete_url = url_for('user_subjects_delete', id=record[0], sort_by=sort_by, sort_order=sort_order, 
                                    date_from=date_from, date_to=date_to, users=selected_users, 
                                    subjects=selected_subjects, groups=selected_groups)
                delete_button = f'<button class="btn btn-sm btn-danger" data-delete-url="{delete_url}" onclick="confirmDeleteRecord(this)">Xóa</button>'
            
                criteria_text = record[3] if record[3] else 'None'
                table_html += f'<tr data-id="{record[0]}"><td>{record[1]}</td><td>{record[2]}</td><td>{criteria_text}</td><td>{record[7]}</td><td style="display: none;">{record[5]}</td><td>{record[4]}</td><td>{record[6]}</td><td class="text-nowrap">{edit_button}{delete_button}</td></tr>'
            
            table_html += "</tbody>"
            return jsonify({'html': table_html})

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
                               role_name=session.get('role_name'),
                               is_gvcn=is_user_gvcn())
    else:
        return redirect(url_for('login'))


@app.route('/user_subjects/create', methods=['GET', 'POST'])
def user_subjects_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
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
    """Old route - redirect to secure version"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate secure token
    token = generate_action_token('edit', id, 'user_subjects', expiry_hours=2)
    
    # Redirect to secure route
    return redirect(url_for('secure_action_handler', action='edit', table='user_subjects', token=token))

def user_subjects_edit_secure(id, token):
    permission_check = require_menu_permission('user_conduct')
    if permission_check:
        return permission_check
    
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
        
        flash('Cập nhật học tập thành công', 'success')
        return redirect(url_for('user_subjects_list'))

    record = read_record_by_id('User_Subjects', id,
                               ['id', 'user_id', 'subject_id', 'criteria_id', 'registered_date', 'total_points', 'entered_by'])
    if not record:
        flash('Không tìm thấy bản ghi', 'error')
        return redirect(url_for('user_subjects_list'))
    
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
                           is_gvcn=is_user_gvcn(),
                           token=token)



@app.route('/user_subjects/delete/<int:id>')
def user_subjects_delete(id):
    """Old route - redirect to secure version"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Generate secure token
    token = generate_action_token('delete', id, 'user_subjects', expiry_hours=1)
    
    # Redirect to secure route
    return redirect(url_for('secure_action_handler', action='delete', table='user_subjects', token=token))

def user_subjects_delete_secure(id, token):
    """Secure user subjects delete function"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Verify record exists
    record = read_record_by_id('User_Subjects', id)
    if not record:
        flash('Không tìm thấy bản ghi', 'error')
        return redirect(url_for('user_subjects_list'))
    
    delete_record('User_Subjects', id)
    flash('Xóa bản ghi thành công', 'success')
    return redirect(url_for('user_subjects_list'))


@app.route('/group_summary', methods=['GET', 'POST'])
def group_summary():
    # Kiểm tra quyền truy cập
    permission_check = require_menu_permission('group_summary')
    if permission_check:
        return permission_check
    
    if 'user_id' not in session:
        return  # Hoặc trả về lỗi phù hợp

    # Tính toán ngày mặc định (Thứ Hai đến Chủ Nhật)
    today = datetime.today()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    default_date_from = monday.strftime('%Y-%m-%d')
    default_date_to = sunday.strftime('%Y-%m-%d')

    # Lấy tham số từ request (GET hoặc POST)
    if request.method == 'POST':
        sort_by = request.form.get('sort_by', 'group_name')
        sort_order = request.form.get('sort_order', 'asc')
        date_from = request.form.get('date_from') or default_date_from
        date_to = request.form.get('date_to') or default_date_to
        period_type = request.form.get('period_type', 'week')
    else:
        sort_by = request.args.get('sort_by', 'group_name')
        sort_order = request.args.get('sort_order', 'asc')
        date_from = request.args.get('date_from') or default_date_from
        date_to = request.args.get('date_to') or default_date_to
        period_type = request.args.get('period_type', 'week')
    data_source = 'all'  # Luôn sử dụng tất cả nguồn dữ liệu

    # Danh sách cột hợp lệ để sắp xếp
    valid_columns = {
        'group_name': 'group_name',
        'prev_total': 'prev_total',
        'prev_study': 'prev_study', 
        'prev_conduct': 'prev_conduct',
        'now_total': 'now_total',
        'now_study': 'now_study',
        'now_conduct': 'now_conduct',
        'progress': 'progress'
    }

    # Khởi tạo kết nối database
    conn = connect_db()
    cursor = conn.cursor()

    # Lấy role_id của GVCN, Master và group_id của "Giáo viên"
    cursor.execute("SELECT id FROM Roles WHERE name = 'GVCN'")
    result = cursor.fetchone()
    gvcn_role_id = result[0] if result else None
    cursor.execute("SELECT id FROM Roles WHERE name = 'Master'")
    result = cursor.fetchone()
    master_role_id = result[0] if result else None
    cursor.execute("SELECT id FROM Groups WHERE name = 'Giáo viên'")
    result = cursor.fetchone()
    teacher_group_id = result[0] if result else None

    # Lấy danh sách groups (loại bỏ "Giáo viên")
    if teacher_group_id is not None:
        cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0 AND id != ?", (teacher_group_id,))
    else:
        cursor.execute("SELECT id, name FROM Groups WHERE is_deleted = 0")
    
    # Lấy danh sách users (loại bỏ GVCN và Master)
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

    # Lấy danh sách groups dựa trên quyền
    groups = get_filtered_groups_by_role()
    all_group_ids = [group['id'] for group in groups]

    # Xây dựng truy vấn tổng điểm (User_Conduct và User_Subjects)
    queries = []
    for table, points_column in [('User_Conduct', 'conduct_points'), ('User_Subjects', 'study_points')]:
        query = f"""
            SELECT g.name AS group_name, SUM(t.total_points) AS {points_column}
            FROM {table} t
            JOIN Users u ON t.user_id = u.id
            JOIN Groups g ON u.group_id = g.id
            WHERE t.is_deleted = 0
        """
        params = []
        
        # Thêm điều kiện lọc vai trò, nhóm, và ngày
        if excluded_roles:
            placeholders = ','.join('?' * len(excluded_roles))
            query += f" AND u.role_id NOT IN ({placeholders})"
            params.extend(excluded_roles)
        
        if all_group_ids:
            query += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
            params.extend(all_group_ids)
        
        if date_from:
            query += " AND t.registered_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND t.registered_date <= ?"
            params.append(date_to)
        
        query += " GROUP BY g.id, g.name"
        queries.append((query, params))

    # Thực thi truy vấn và tổng hợp kết quả
    records = {}
    for query, params in queries:
        cursor.execute(query, params)
        for group_name, total_points in cursor.fetchall():
            records[group_name] = records.get(group_name, 0) + (total_points or 0)

    # Tính ngày kỳ trước
    date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
    date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
    period_days = (date_to_dt - date_from_dt).days + 1
    prev_date_to_dt = date_from_dt - timedelta(days=1)
    prev_date_from_dt = prev_date_to_dt - timedelta(days=period_days-1)
    prev_date_from = prev_date_from_dt.strftime('%Y-%m-%d')
    prev_date_to = prev_date_to_dt.strftime('%Y-%m-%d')

    # Truy vấn điểm kỳ trước và kỳ này
    points_data = {}
    for period, start_date, end_date in [('prev', prev_date_from, prev_date_to), ('now', date_from, date_to)]:
        points_data[period] = {'conduct': {}, 'study': {}}
        for table, points_type in [('User_Conduct', 'conduct'), ('User_Subjects', 'study')]:
            query = f"""
                SELECT g.name AS group_name, SUM(t.total_points) AS {points_type}_points
                FROM {table} t
                JOIN Users u ON t.user_id = u.id
                JOIN Groups g ON u.group_id = g.id
                WHERE t.is_deleted = 0 AND t.registered_date >= ? AND t.registered_date <= ?
            """
            params = [start_date, end_date]
            
            if excluded_roles:
                placeholders = ','.join('?' * len(excluded_roles))
                query += f" AND u.role_id NOT IN ({placeholders})"
                params.extend(excluded_roles)
            
            if all_group_ids:
                query += " AND u.group_id IN ({})".format(','.join('?' * len(all_group_ids)))
                params.extend(all_group_ids)
            
            query += " GROUP BY g.id, g.name"
            cursor.execute(query, params)
            points_data[period][points_type] = {row[0]: row[1] or 0 for row in cursor.fetchall()}

    conn.close()

    # Tạo danh sách kết quả
    records_list = []
    for group in groups:
        name = group['name']
        prev_conduct = points_data['prev']['conduct'].get(name, 0)
        prev_study = points_data['prev']['study'].get(name, 0)
        prev_total = prev_conduct + prev_study
        now_conduct = points_data['now']['conduct'].get(name, 0)
        now_study = points_data['now']['study'].get(name, 0)
        now_total = now_conduct + now_study
        progress = now_total - prev_total
        
        records_list.append([
            name, prev_total, prev_study, prev_conduct,
            now_total, now_study, now_conduct, progress
        ])

    # Sắp xếp kết quả
    if sort_by in valid_columns:
        index = {
            'group_name': 0, 'prev_total': 1, 'prev_study': 2, 'prev_conduct': 3,
            'now_total': 4, 'now_study': 5, 'now_conduct': 6, 'progress': 7
        }[sort_by]
        if sort_by == 'group_name':
            records_list.sort(key=lambda x: vietnamese_sort_key(x[0], sort_by_first_name=False), reverse=(sort_order == 'desc'))
        else:
            records_list.sort(key=lambda x: x[index], reverse=(sort_order == 'desc'))


        # Kiểm tra xem có phải AJAX request không
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Render chỉ phần table HTML
            table_html = render_template_string("""
<div class="table-responsive">
    <table class="table table-bordered table-striped">
        <thead>
            <tr>
                <th rowspan="2" class="text-nowrap">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="group_name" data-order="{{ 'desc' if sort_by == 'group_name' and sort_order == 'asc' else 'asc' }}">
                        Nhóm
                        {% if sort_by == 'group_name' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th colspan="3" class="text-center">Kỳ Trước</th>
                <th colspan="3" class="text-center">Kỳ Này</th>
                <th rowspan="2" class="text-nowrap">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="progress" data-order="{{ 'desc' if sort_by == 'progress' and sort_order == 'asc' else 'asc' }}">
                        Tiến bộ↓↑
                        {% if sort_by == 'progress' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
            </tr>
            <tr>
                <th class="text-center">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="prev_study" data-order="{{ 'desc' if sort_by == 'prev_study' and sort_order == 'asc' else 'asc' }}">
                        Học tập
                        {% if sort_by == 'prev_study' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="prev_conduct" data-order="{{ 'desc' if sort_by == 'prev_conduct' and sort_order == 'asc' else 'asc' }}">
                        Hạnh kiểm
                        {% if sort_by == 'prev_conduct' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="prev_total" data-order="{{ 'desc' if sort_by == 'prev_total' and sort_order == 'asc' else 'asc' }}">
                        Tổng
                        {% if sort_by == 'prev_total' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="now_study" data-order="{{ 'desc' if sort_by == 'now_study' and sort_order == 'asc' else 'asc' }}">
                        Học tập
                        {% if sort_by == 'now_study' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="now_conduct" data-order="{{ 'desc' if sort_by == 'now_conduct' and sort_order == 'asc' else 'asc' }}">
                        Hạnh kiểm
                        {% if sort_by == 'now_conduct' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="now_total" data-order="{{ 'desc' if sort_by == 'now_total' and sort_order == 'asc' else 'asc' }}">
                        Tổng
                        {% if sort_by == 'now_total' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            {% for record in records %}
            <tr>
                <td>{{ record[0] }}</td>
                <td class="text-center">{{ record[2] }}</td>
                <td class="text-center">{{ record[3] }}</td>
                <td class="text-center">{{ record[1] }}</td>
                <td class="text-center">{{ record[5] }}</td>
                <td class="text-center">{{ record[6] }}</td>
                <td class="text-center">{{ record[4] }}</td>
                <td class="text-center">
                    {% if record[7] > 0 %}
                        <span class="text-success">+{{ record[7] }}</span>
                    {% elif record[7] < 0 %}
                        <span class="text-danger">{{ record[7] }}</span>
                    {% else %}
                        <span class="text-muted">{{ record[7] }}</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
            """, records=records_list, sort_by=sort_by, sort_order=sort_order)
            
            return jsonify({
                'success': True,
                'html': table_html
            })

        return render_template_with_permissions('group_summary.html',
                               records=records_list,
                               groups=groups,
                               date_from=date_from,
                               date_to=date_to,
                               period_type=period_type,  # Thêm period_type
                               data_source=data_source,  # Luôn là 'all'
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


@app.route('/user_summary', methods=['GET', 'POST'])
def user_summary():
    permission_check = require_menu_permission('user_summary')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        
        # Get sort parameters from both GET and POST
        if request.method == 'POST':
            sort_by = request.form.get('sort_by', request.args.get('sort_by', 'user_name'))
            sort_order = request.form.get('sort_order', request.args.get('sort_order', 'asc'))
        else:
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


        # Filter users and groups based on permissions  
        filtered_users = get_filtered_users_by_role()
        groups = get_filtered_groups_by_role()
        
        filtered_users.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=True))
        groups.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))

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
        period_type = 'week'  # Thêm period_type
        select_all_users = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            period_type = request.form.get('period_type', 'week')  # Lấy period_type từ form
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            period_type = request.args.get('period_type', 'week')  # Lấy period_type từ args

        conn = connect_db()
        cursor = conn.cursor()

        # Base user query with permission filtering
        user_query = """
                SELECT id, name
                FROM Users
                WHERE is_deleted = 0
            """
        user_params = []
        
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
            filtered_user_id = [user[0] for user in filtered_users]
            if filtered_user_id:
                user_query += " AND id IN ({})".format(','.join('?' * len(filtered_user_id)))
                user_params.extend(filtered_user_id)
        elif selected_users:
            user_query += " AND id IN ({})".format(','.join('?' * len(selected_users)))
            user_params.extend(selected_users)
        if select_all_groups:
            group_ids = [group['id'] for group in groups]
            if group_ids:
                user_query += " AND group_id IN ({})".format(','.join('?' * len(group_ids)))
                user_params.extend(group_ids)
        elif selected_groups:
            user_query += " AND group_id IN ({})".format(','.join('?' * len(selected_groups)))
            user_params.extend(selected_groups)

        cursor.execute(user_query, user_params)
        users = cursor.fetchall()
        users.sort(key=lambda u: vietnamese_sort_key(u[1], sort_by_first_name=True))
        
        records = []
        for user_id, user_name in users:
            conduct_points = 0
            academic_points = 0

            # Điểm rèn luyện (User_Conduct)
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
                conduct_points = uc_points

            # Điểm học tập (User_Subjects)
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
                academic_points = us_points

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
            prev_conduct_points = 0
            prev_academic_points = 0
            
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
                    
                    # Điểm hạnh kiểm kỳ trước
                    cursor.execute('''
                        SELECT SUM(total_points) FROM User_Conduct
                        WHERE user_id = ? AND is_deleted = 0 
                        AND registered_date >= ? AND registered_date <= ?
                    ''', (user_id, prev_date_from, prev_date_to))
                    prev_uc = cursor.fetchone()[0]
                    if prev_uc:
                        prev_conduct_points = prev_uc
                    
                    # Điểm học tập kỳ trước
                    cursor.execute('''
                        SELECT SUM(total_points) FROM User_Subjects
                        WHERE user_id = ? AND is_deleted = 0 
                        AND registered_date >= ? AND registered_date <= ?
                    ''', (user_id, prev_date_from, prev_date_to))
                    prev_us = cursor.fetchone()[0]
                    if prev_us:
                        prev_academic_points = prev_us
                    
                    # Tính sự thay đổi cho từng loại điểm
                    current_academic_points = academic_points if academic_points else 0
                    current_conduct_points = conduct_points if conduct_points else 0
                    
                    academic_difference = current_academic_points - prev_academic_points
                    conduct_difference = current_conduct_points - prev_conduct_points
                    total_point = current_academic_points + current_conduct_points
                    
                    logging.info(f"User ID: {user_id}, Academic Diff: {current_academic_points}, Conduct Diff: {current_conduct_points}, Total: {total_point}")
                    
                    auto_comment = get_auto_comment(academic_difference, conduct_difference)
                    auto_ranking = get_auto_comment_for_category(total_point, "ranking")
                    if auto_ranking is None:
                        auto_ranking = ""
                    if auto_comment is None:
                        auto_comment = ""
                    
                except:
                    pass
            
            
            # Kiểm tra tiêu chuẩn
            standard = ""
            # Kiểm tra User_Subjects
            cursor.execute("""
                SELECT COUNT(*) FROM User_Subjects
                WHERE user_id = ? AND is_deleted = 0
                AND registered_date >= ? AND registered_date <= ?
            """, (user_id, date_from, date_to))
            us_count = cursor.fetchone()[0]

            # Kiểm tra User_Conduct
            cursor.execute("""
                SELECT COUNT(*) FROM User_Conduct
                WHERE user_id = ? AND is_deleted = 0
                AND registered_date >= ? AND registered_date <= ?
            """, (user_id, date_from, date_to))
            uc_count = cursor.fetchone()[0]

            
            if us_count == 0 and uc_count == 0:
                standard = "HT/HK"
            elif us_count == 0:
                standard = "HT"
            elif uc_count == 0:
                standard = "HK"
            else:
                standard = ""

            # Thêm vào tuple record
            records.append((user_name, academic_points if academic_points else 0, conduct_points if conduct_points else 0, standard, user_id, current_comment, auto_comment, prev_academic_points, prev_conduct_points, auto_ranking))

        if sort_by == 'user_name':
            records.sort(key=lambda x: vietnamese_sort_key(x[0], sort_by_first_name=True) if x[0] else '', reverse=(sort_order == 'desc'))
        elif sort_by == 'academic_points':
            records.sort(key=lambda x: x[1], reverse=(sort_order == 'desc'))
        elif sort_by == 'conduct_points':
            records.sort(key=lambda x: x[2], reverse=(sort_order == 'desc'))
        elif sort_by == 'prev_academic_points':
            records.sort(key=lambda x: x[7], reverse=(sort_order == 'desc'))  # index 7 is prev_academic_points
        elif sort_by == 'prev_conduct_points':
            records.sort(key=lambda x: x[8], reverse=(sort_order == 'desc'))   # index 8 is prev_conduct_points
        elif sort_by == 'academic_progress':
            records.sort(key=lambda x: x[1] - x[7], reverse=(sort_order == 'desc'))  # current - previous
        elif sort_by == 'conduct_progress':
            records.sort(key=lambda x: x[2] - x[8], reverse=(sort_order == 'desc'))  # current - previous
        elif sort_by == 'total_points':
            records.sort(key=lambda x: x[1] + x[2], reverse=(sort_order == 'desc'))
        elif sort_by == 'standard':
            # Sắp xếp theo tiêu chuẩn: HT/HK > HT > HK > ''
            def standard_sort_key(val):
                order_map = {'HT/HK': 0, 'HT': 1, 'HK': 2, '': 3}
                return order_map.get(val[3], 99)
            records.sort(key=standard_sort_key, reverse=(sort_order == 'desc'))

        conn.close()

        role_name=session.get('role_name', '')
        
        # Kiểm tra xem có phải AJAX request không
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            
            # Render chỉ phần table HTML
            table_html = render_template_string("""
<div class="table-responsive">
    <table class="table table-striped table-hover">
        <thead>
            <tr>
                <th rowspan="2" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="standard" data-order="{{ 'desc' if sort_by == 'standard' and sort_order == 'asc' else 'asc' }}">
                        Đạt
                        {% if sort_by == 'standard' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th rowspan="2" style="width: 220px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="user_name" data-order="{{ 'desc' if sort_by == 'user_name' and sort_order == 'asc' else 'asc' }}">
                        Họ Tên
                        {% if sort_by == 'user_name' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th colspan="3" class="text-center">Học Tập</th>
                <th colspan="3" class="text-center">Hạnh Kiểm</th>
                {% if role_name == 'GVCN' or role_name == 'Master' %}
                <th rowspan="2" class="comment-col">Xếp loại</th>
                <th rowspan="2" class="comment-col">Nhận xét</th>
                {% endif %}
            </tr>
            <tr>
                <th class="text-center" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="prev_academic_points" data-order="{{ 'desc' if sort_by == 'prev_academic_points' and sort_order == 'asc' else 'asc' }}">
                        Trước
                        {% if sort_by == 'prev_academic_points' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="academic_points" data-order="{{ 'desc' if sort_by == 'academic_points' and sort_order == 'asc' else 'asc' }}">
                        Sau
                        {% if sort_by == 'academic_points' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="academic_progress" data-order="{{ 'desc' if sort_by == 'academic_progress' and sort_order == 'asc' else 'asc' }}">
                        ↑↓
                        {% if sort_by == 'academic_progress' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="prev_conduct_points" data-order="{{ 'desc' if sort_by == 'prev_conduct_points' and sort_order == 'asc' else 'asc' }}">
                        Trước
                        {% if sort_by == 'prev_conduct_points' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="conduct_points" data-order="{{ 'desc' if sort_by == 'conduct_points' and sort_order == 'asc' else 'asc' }}">
                        Sau
                        {% if sort_by == 'conduct_points' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                <th class="text-center" style="width: 90px;">
                    <a href="#" class="sort-link text-decoration-none text-dark" data-sort="conduct_progress" data-order="{{ 'desc' if sort_by == 'conduct_progress' and sort_order == 'asc' else 'asc' }}">
                        ↑↓
                        {% if sort_by == 'conduct_progress' %}
                            {% if sort_order == 'asc' %}▲{% else %}▼{% endif %}
                        {% else %}
                            <i class="fas fa-sort"></i>
                        {% endif %}
                    </a>
                </th>
                
            </tr>
        </thead>
        <tbody>
            {% for record in records %}
                <tr>
                    <td>
                        {{ record[3] }}
                    </td>
                    <td>
                        <span class="user-name-clickable" 
                              data-user-id="{{ record[4] }}" 
                              data-date-from="{{ date_from or '' }}" 
                              data-date-to="{{ date_to or '' }}"
                              style="cursor: pointer; color: #007bff; text-decoration: underline;"
                              title="Click để copy link báo cáo">
                            {{ record[0] }}
                            <i class="fas fa-external-link-alt ms-1"></i>
                        </span>
                    </td>
                    <td class="text-center">{{ record[7] if record|length > 7 else 0 }}</td>
                    <td class="text-center">{{ record[1] }}</td>
                    <td class="text-center">
                        {% set academic_progress = (record[1] - (record[7] if record|length > 7 else 0)) %}
                        <span class="{% if academic_progress > 0 %}text-success{% elif academic_progress < 0 %}text-danger{% else %}text-muted{% endif %}">
                            {% if academic_progress > 0 %}+{% endif %}{{ academic_progress }}
                        </span>
                    </td>
                    <td class="text-center">{{ record[8] if record|length > 8 else 0 }}</td>
                    <td class="text-center">{{ record[2] }}</td>
                    <td class="text-center">
                        {% set conduct_progress = (record[2] - (record[8] if record|length > 8 else 0)) %}
                        <span class="{% if conduct_progress > 0 %}text-success{% elif conduct_progress < 0 %}text-danger{% else %}text-muted{% endif %}">
                            {% if conduct_progress > 0 %}+{% endif %}{{ conduct_progress }}
                        </span>
                    </td>
                    {% if role_name == 'GVCN' or role_name == 'Master' %}
                    <td>                        
                        <div class="d-flex align-items-center">
                            <span class="comment-text">{{record[9]}}</span>
                        </div>                        
                    </td>
                    <td class="comment-col">                        
                        <div class="d-flex align-items-center">
                            <textarea class="form-control me-2 auto-save-comment" id="comment_{{ record[4] }}" data-user-id="{{ record[4] }}" rows="2">{{ (record[5] if record[5] else record[6]) if record|length > 5 else '' }}</textarea>
                            <span class="save-status text-muted small" id="status_{{ record[4] }}"></span>
                        </div>                        
                    </td>
                    {% endif %}
                </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% if not records %}
    <div class="alert alert-info text-center">
        <i class="fas fa-info-circle"></i> Không có dữ liệu phù hợp với điều kiện tìm kiếm.
    </div>
{% endif %}
            """, 
                                       records=records,
                                       date_from=date_from,
                                       date_to=date_to,
                                       sort_by=sort_by,
                                       sort_order=sort_order,
                                       selected_users=selected_users,
                                       selected_groups=selected_groups,
                                       role_name=role_name,
                                       period_type=period_type)
            
            return jsonify({
                'success': True,
                'html': table_html
            })
        
        return render_template_with_permissions('user_summary.html',
                               records=records,
                               users=users,
                               groups=groups,
                               date_from=date_from,
                               date_to=date_to,
                               period_type=period_type,  # Thêm period_type
                               selected_users=selected_users,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_groups=select_all_groups,
                               sort_by=sort_by,
                               sort_order=sort_order,
                               role_name=role_name,
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
        
        # First try normal username/password login
        user = read_all_records('Users', condition=f"username = '{username}' AND password = '{password}'")
        
        # If normal login fails, try role_username/role_password login
        if not user:
            user = read_all_records('Users', condition=f"role_username = '{username}' AND role_password = '{password}'")
            
        if user:
            user_id = user[0][0]
            user_data = user[0]  # [id, name, username, password, class_id, group_id, role_id, role_username, role_password]
            
            # Determine which login method was used and set appropriate role permissions
            # Check if it was role_username/role_password login
            role_login = read_all_records('Users', condition=f"role_username = '{username}' AND role_password = '{password}' AND id = {user_id}")
            
            session['user_id'] = user_id
            
            if role_login:
                # Role login - use the user's actual role
                session['login_type'] = 'role_login'
                session['role_id'] = user_data[6]  # role_id from Users table
                
                # Get role name
                if user_data[6]:
                    role_data = read_record_by_id('Roles', user_data[6], ['id', 'name'])
                    session['role_name'] = role_data[1] if role_data else None
                else:
                    session['role_name'] = None
            else:
                # Normal login - force role ID 9 permissions (student role)
                session['login_type'] = 'normal_login'
                session['force_role_id'] = 9
                session['role_id'] = 9
                session['role_name'] = 'Học sinh'
                session['login_type'] = 'normal_login'
                session['force_role_id'] = 9
            
            # Kiểm tra nếu user không phải master thì check ngày hiệu lực
            if not is_master_user(user_id):
                if check_system_expiry():
                    error = 'Hệ thống đã hết hiệu lực. Vui lòng liên hệ quản trị viên.'
                    return render_template('login.html', error=error, class_name=class_name, permissions={})
            
            # Lưu lịch sử đăng nhập (ngày giờ local hoặc client)
            client_time = request.form.get('client_time')
            if client_time:
                try:
                    # Tách thành ngày và giờ, chuyển về đúng format
                    dt = client_time.strip().replace('T', ' ').replace('/', '-')
                    # Hỗ trợ cả dạng 'YYYY-MM-DD HH:MM:SS' hoặc 'YYYY-MM-DD HH:MM'
                    parts = dt.split(' ')
                    if len(parts) == 2:
                        date_part = parts[0]
                        time_part = parts[1]
                        # Nếu time thiếu giây, thêm ':00'
                        if len(time_part.split(':')) == 2:
                            time_part += ':00'
                        # Chuyển về đúng format
                        login_date = datetime.strptime(date_part, '%Y-%m-%d').strftime('%Y-%m-%d')
                        login_time = datetime.strptime(time_part, '%H:%M:%S').strftime('%H:%M:%S')
                        
                    else:
                        # Nếu format không đúng, dùng giờ server
                        login_date = datetime.now().strftime('%Y-%m-%d')
                        login_time = datetime.now().strftime('%H:%M:%S')
                except Exception:
                    login_date = datetime.now().strftime('%Y-%m-%d')
                    login_time = datetime.now().strftime('%H:%M:%S')
            else:
                login_date = datetime.now().strftime('%Y-%m-%d')
                login_time = datetime.now().strftime('%H:%M:%S')

            # Lưu vào bảng Login_History
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Login_History (user_id, login_date, login_time)
                VALUES (?, ?, ?)
            """, (user_id, login_date, login_time))
            conn.commit()
            conn.close()
            
            return redirect(url_for('home'))
        else:
            error = 'Invalid username or password'

    return render_template('login.html', error=error, class_name=class_name, permissions={})

@app.route('/home')
def home():
    if 'user_id' in session:
        # Tự động tìm ảnh background trong folder upload
        background_image = get_background_image()
        
        return render_template_with_permissions('home.html', background_image=background_image)
    else:
        return redirect(url_for('login'))

@app.route('/background/<filename>')
def serve_background(filename):
    """Serve background images"""
    try:
        app_root = os.path.dirname(os.path.abspath(__file__))
        backgrounds_dir = os.path.join(app_root, 'static', 'uploads', 'backgrounds')
        return send_from_directory(backgrounds_dir, filename)
    except:
        # Nếu không tìm thấy file, trả về 404
        abort(404)

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Xóa user_id khỏi session
    session.pop('login_type', None)  # Xóa login_type khỏi session
    session.pop('force_role_id', None)  # Xóa force_role_id khỏi session
    return redirect(url_for('login'))

# --- Settings Page ---
@app.route('/settings')
def settings():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:        
        # Tự động tìm ảnh background trong folder upload
        current_background = get_background_image()
        
        # Load system config for expiry date
        system_config = load_system_config()
        system_expiry_date = system_config.get('system_expiry_date', '')
        current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        return render_template_with_permissions('settings.html', 
                                               current_background=current_background,
                                               system_expiry_date=system_expiry_date,
                                               current_date=current_date)
    else:
        return redirect(url_for('login'))

@app.route('/settings/update_background', methods=['POST'])
def settings_update_background():    
    if 'background_image' not in request.files:
        flash('Không có file được chọn', 'error')
        return redirect(url_for('settings'))
    
    file = request.files['background_image']
    if file.filename == '':
        flash('Không có file được chọn', 'error')
        return redirect(url_for('settings'))
    
    if file and allowed_file(file.filename):
        try:
            # Xóa tất cả ảnh background cũ
            clear_all_background_images()
            
            # Lưu file mới
            upload_folder = os.path.join('static', 'uploads', 'backgrounds')
            filename = save_uploaded_file(file, upload_folder)
            
            if filename:
                flash('Cập nhật hình nền thành công!', 'success')
            else:
                flash('Lỗi khi lưu file', 'error')
        except Exception as e:
            flash(f'Lỗi: {str(e)}', 'error')
    else:
        flash('File không hợp lệ. Chỉ hỗ trợ PNG, JPG, JPEG, GIF, WEBP', 'error')
    
    return redirect(url_for('settings'))

@app.route('/settings/remove_background')
def settings_remove_background():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Xóa tất cả ảnh background
        clear_all_background_images()
        flash('Đã xóa hình nền', 'success')
    except Exception as e:
        flash(f'Lỗi: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/save_system_config', methods=['POST'])
def save_system_config():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    
    try:
        data = request.get_json()
        expiry_date = data.get('system_expiry_date')
        
        # Load current config
        config = load_system_config()
        config['system_expiry_date'] = expiry_date
        
        # Save to file
        if save_system_config_to_file(config):
            return jsonify({'success': True, 'message': 'Cấu hình đã được lưu thành công'})
        else:
            return jsonify({'success': False, 'error': 'Không thể lưu cấu hình'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- Reset Data Page ---
@app.route('/reset')
def reset_page():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:        
        # Danh sách các table và mô tả theo thứ tự xóa
        tables = [
            {'name': 'User_Conduct', 'description': 'Dữ liệu hạnh kiểm học sinh'},
            {'name': 'User_Subjects', 'description': 'Dữ liệu học tập học sinh'},
            {'name': 'Criteria', 'description': 'Dữ liệu tiêu chí đánh giá'},
            {'name': 'Subjects', 'description': 'Dữ liệu môn học'},
            {'name': 'Conduct', 'description': 'Dữ liệu hạnh kiểm'},
            {'name': 'Groups', 'description': 'Dữ liệu nhóm'},
            {'name': 'Role_Permissions', 'description': 'Dữ liệu phân quyền'},
            {'name': 'Roles', 'description': 'Dữ liệu chức vụ'},
            {'name': 'Classes', 'description': 'Dữ liệu lớp học'},
            {'name': 'Users', 'description': 'Dữ liệu người dùng'}
        ]
        
        return render_template_with_permissions('reset.html', tables=tables)
    else:
        return redirect(url_for('login'))

@app.route('/reset/table/<table_name>', methods=['POST'])
def reset_table(table_name):
    
    if 'user_id' in session:
        
        # Danh sách table được phép xóa theo thứ tự
        allowed_tables = ['User_Conduct', 'User_Subjects', 'Criteria', 'Subjects', 'Conduct', 
                         'Groups', 'Role_Permissions', 'Roles', 'Classes', 'Users', 'User_Comments' ]
        
        if table_name not in allowed_tables:
            return jsonify({'error': 'Table không hợp lệ'}), 400
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Xóa dữ liệu với điều kiện đặc biệt
            if table_name == 'Role_Permissions':
                system_roles = [5, 9, 15]
                tables = [
                    'Role_Permissions',
                    'Role_Menu_Permissions',
                    'Role_Subject_Permissions',
                    'Role_Criteria_Permissions',
                    'Role_User_Permissions',
                    'Role_Conduct_Permissions'
                ]
                for table in tables:
                    query = f"DELETE FROM {table} WHERE role_id NOT IN ({','.join(str(r) for r in system_roles)})"
                    cursor.execute(query)
                
                cursor.execute("DELETE FROM Role_User_Permissions")
            elif table_name == 'Roles':
                # Không xóa role Master, GVCN và role ID = 9
                cursor.execute("DELETE FROM Roles WHERE name NOT IN ('Master', 'GVCN') AND id != 9")
                
            elif table_name == 'Users':
                # Không xóa user có role Master, GVCN
                cursor.execute("DELETE FROM Login_history")
                
                cursor.execute("""
                    DELETE FROM Users 
                    WHERE role_id NOT IN (
                        SELECT id FROM Roles WHERE name IN ('Master', 'GVCN')
                    )
                """)
            else:
          
                # Xóa toàn bộ dữ liệu các bảng khác
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        
        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Lấy danh sách mẫu nhận xét
            cursor.execute('''
                SELECT id, comment_category, comment_type, score_range_min, score_range_max, comment_text, created_date
                FROM Comment_Templates 
                WHERE is_active = 1
                ORDER BY comment_category, comment_type, score_range_min
            ''')
            templates = cursor.fetchall()
            logging.info(f"Loaded {templates} comment templates")
            conn.close()
            
            return render_template_with_permissions('comment_management.html', templates=templates)
        except Exception as e:
            flash(f'Lỗi khi tải dữ liệu: {str(e)}', 'error')
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

@app.route('/comment_template/create', methods=['GET', 'POST'])
def comment_template_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        
        if request.method == 'POST':
            try:
                comment_category = request.form['comment_category']  # 'academic' hoặc 'conduct'
                comment_type = request.form['comment_type']  # 'encouragement' hoặc 'reminder'
                score_range_min = int(request.form['score_range_min'])
                score_range_max = int(request.form['score_range_max'])
                comment_text = request.form['comment_text']
                color = request.form.get('color', '#2e800b')  # Màu mặc định
                
                conn = connect_db()
                cursor = conn.cursor()
                
                logging.info(f"Creating comment template: category={comment_category}, type={comment_type}, range=({score_range_min}-{score_range_max}), color={color}")
                cursor.execute('''
                    INSERT INTO Comment_Templates (comment_category, comment_type, score_range_min, score_range_max, comment_text, color)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (comment_category, comment_type, score_range_min, score_range_max, comment_text, color))
                
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
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
      
        conn = connect_db()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            try:
                comment_category = request.form['comment_category']
                comment_type = request.form['comment_type']
                score_range_min = int(request.form['score_range_min'])
                score_range_max = int(request.form['score_range_max'])
                comment_text = request.form['comment_text']
                
                cursor.execute('''
                    UPDATE Comment_Templates 
                    SET comment_category=?, comment_type=?, score_range_min=?, score_range_max=?, comment_text=?
                    WHERE id=? AND is_active=1
                ''', (comment_category, comment_type, score_range_min, score_range_max, comment_text, template_id))
                
                conn.commit()
                conn.close()
                
                flash('Đã cập nhật mẫu nhận xét thành công!', 'success')
                return redirect(url_for('comment_management'))
            except Exception as e:
                flash(f'Lỗi khi cập nhật mẫu nhận xét: {str(e)}', 'error')
        
        # Lấy thông tin mẫu nhận xét
        cursor.execute('SELECT * FROM Comment_Templates WHERE id=? AND is_active=1', (template_id,))
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
            
            cursor.execute('UPDATE Comment_Templates SET is_active=0 WHERE id=?', (template_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Đã xóa mẫu nhận xét thành công!'})
        except Exception as e:
            return jsonify({'error': f'Lỗi khi xóa mẫu nhận xét: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Chưa đăng nhập'}), 401

# API routes for Comment Templates
@app.route('/api/comment_template/create', methods=['POST'])
def api_comment_template_create():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    try:        
        comment_category = request.form['comment_category']
        comment_type = request.form['comment_type']
        logging.info(f"API Received comment_type: {comment_type}")
        score_range_min = int(request.form['score_range_min'])
        score_range_max = int(request.form['score_range_max'])
        comment_text = request.form['comment_text']
        
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO Comment_Templates (comment_category, comment_type, score_range_min, score_range_max, comment_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (comment_category, comment_type, score_range_min, score_range_max, comment_text))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Đã thêm mẫu nhận xét thành công!'})
    except Exception as e:
        return jsonify({'error': f'Lỗi khi thêm mẫu nhận xét: {str(e)}'}), 500

@app.route('/api/comment_template/<int:template_id>', methods=['GET'])
def api_get_comment_template(template_id):
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, comment_category, comment_type, score_range_min, score_range_max, 
                   comment_text, is_active, color
            FROM Comment_Templates 
            WHERE id = ?
        ''', (template_id,))

        result = cursor.fetchone()
        conn.close()
        
        logging.info(f"Fetched comment template: {result}")
        if result:
            template = {
                'id': result[0],
                'comment_category': result[1],
                'comment_type': result[2],
                'score_range_min': result[3],
                'score_range_max': result[4],
                'comment_text': result[5],
                'is_active': bool(result[6]),
                'color': result[7]
            }
            return jsonify({'success': True, 'template': template})
        else:
            return jsonify({'error': 'Không tìm thấy mẫu nhận xét'}), 404
    except Exception as e:
        return jsonify({'error': f'Lỗi khi lấy thông tin mẫu nhận xét: {str(e)}'}), 500

@app.route('/api/comment_template/edit', methods=['POST'])
def api_comment_template_edit():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    try:
        template_id = request.form['template_id']
        comment_category = request.form['comment_category']
        comment_type = request.form['comment_type']
        score_range_min = int(request.form['score_range_min'])
        score_range_max = int(request.form['score_range_max'])
        comment_text = request.form['comment_text']
        color = request.form.get('color', '#2e800b')  # Màu mặc định
        
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE Comment_Templates 
            SET comment_category=?, comment_type=?, score_range_min=?, score_range_max=?, comment_text=?, color=?
            WHERE id=? AND is_active=1
        ''', (comment_category, comment_type, score_range_min, score_range_max, comment_text, color, template_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Đã cập nhật mẫu nhận xét thành công!'})
    except Exception as e:
        return jsonify({'error': f'Lỗi khi cập nhật mẫu nhận xét: {str(e)}'}), 500

def get_auto_comment_for_category(score_difference, category):
    """Lấy nhận xét tự động dựa trên sự thay đổi điểm số cho từng danh mục"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        abs_diff = abs(score_difference)
        comment_type = 'encouragement' if score_difference >= 0 else 'reminder'
        
        cursor.execute('''
            SELECT comment_text FROM Comment_Templates 
            WHERE comment_category = ? AND comment_type = ? 
            AND ? BETWEEN score_range_min AND score_range_max 
            AND is_active = 1
            ORDER BY score_range_min LIMIT 1
        ''', (category, comment_type, abs_diff))
        
        logging.info(f"Fetching auto comment for category={category}, type={comment_type}, abs_diff={abs_diff}")    
        
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logging.error(f"Error in get_auto_comment_for_category: {str(e)}")
        return None

def get_ranking_info(total_points):
    """Lấy thông tin xếp loại và màu từ database"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT comment_text, color FROM Comment_Templates 
            WHERE comment_category = 'ranking' 
            AND ? BETWEEN score_range_min AND score_range_max 
            AND is_active = 1
            ORDER BY score_range_min LIMIT 1
        ''', (total_points,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0], result[1]  # ranking_text, color
        else:
            return "GVCN liên lạc sau", "#6c757d"  # Default
            
    except Exception as e:
        logging.error(f"Error in get_ranking_info: {str(e)}")
        return "GVCN liên lạc sau", "#6c757d"  # Default
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    except:
        return None

def get_auto_comment(academic_diff, conduct_diff):
    """Lấy nhận xét tự động cho cả học tập và hạnh kiểm"""
    academic_comment = get_auto_comment_for_category(academic_diff, 'academic') if academic_diff != 0 else None
    conduct_comment = get_auto_comment_for_category(conduct_diff, 'conduct') if conduct_diff != 0 else None
    
    comments = []
    if academic_comment:
        comments.append(f"Học tập: {academic_comment}")
    if conduct_comment:
        comments.append(f"Hạnh kiểm: {conduct_comment}")
    
    return "; ".join(comments) if comments else None

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


# @app.route('/save_user_ranking', methods=['POST'])
# def save_user_ranking():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Chưa đăng nhập'}), 401
    
#     try:
#         data = request.get_json()
#         user_id = data['user_id']
#         ranking = data['ranking']
#         period_start = data['period_start']
#         period_end = data['period_end']
        
#         conn = connect_db()
#         cursor = conn.cursor()
        
#         # Kiểm tra xem đã có nhận xét cho kỳ này chưa
#         cursor.execute('''
#             SELECT id FROM User_Comments 
#             WHERE user_id = ? AND period_start = ? AND period_end = ?
#         ''', (user_id, period_start, period_end))
#         existing = cursor.fetchone()
        
#         if existing:
#             # Cập nhật ranking hiện tại
#             cursor.execute('''
#                 UPDATE User_Comments 
#                 SET ranking = ?, updated_date = CURRENT_TIMESTAMP
#                 WHERE user_id = ? AND period_start = ? AND period_end = ?
#             ''', (ranking, user_id, period_start, period_end))
#         else:
#             # Thêm bản ghi mới với ranking
#             cursor.execute('''
#                 INSERT INTO User_Comments 
#                 (user_id, period_start, period_end, ranking, is_auto_generated)
#                 VALUES (?, ?, ?, ?, 1)
#             ''', (user_id, period_start, period_end, ranking))
        
#         conn.commit()
#         conn.close()
        
#         return jsonify({'success': True, 'message': 'Đã lưu xếp loại thành công!'})
#     except Exception as e:
#         return jsonify({'error': f'Lỗi khi lưu xếp loại: {str(e)}'}), 500


@app.route('/user_report/<int:user_id>')
def user_report_old(user_id):
    """Old route - redirect to generate secure token"""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Generate secure token
    token = generate_report_token(user_id, date_from, date_to, expiry_hours=168)  # 3 days expiry
    
    # Redirect to secure route
    return redirect(url_for('user_report_secure', token=token))

@app.route('/report/<token>')
def user_report_secure(token):   
    """Secure user report route with encrypted token"""
    payload = verify_report_token(token)
    if not payload:
        return "Link đã hết hạn hoặc không hợp lệ", 403
    
    user_id = payload.get('user_id')
    date_from = payload.get('date_from')
    date_to = payload.get('date_to')
    
    try:     
        student = get_user_by_id(user_id)
        if not student:
            error_html = '<div class="alert alert-danger">Không tìm thấy thông tin học sinh</div>'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'html': error_html})
            return error_html
        
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
                SELECT u.name 
                FROM Users u 
                JOIN Roles r ON u.role_id = r.id 
                WHERE r.name = 'GVCN' AND u.is_deleted = 0
                LIMIT 1
            """)
        teacher_info = cursor.fetchone()
        teacher_name = teacher_info[0] if teacher_info else "Chưa phân công"
        conn.close()
        
        report_html = generate_student_report_html(user_id, date_from, date_to, student, teacher_name)
        
        # Nếu là truy cập trực tiếp thì trả về HTML đầy đủ
        return render_template('user_report.html', report_html=report_html, hide_navbar=True)
        
    except Exception as e:
        error_html = f'<div class="alert alert-danger">Có lỗi xảy ra: {str(e)}</div>'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'html': error_html})
        return error_html

@app.route('/generate_report_link', methods=['POST'])
def generate_report_link():
    """Generate secure report link for authenticated users"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        target_user_id = data.get('user_id')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        expiry_hours = data.get('expiry_hours', 72)  # Default 3 days
        
        if not target_user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        # Generate token
        token = generate_report_token(target_user_id, date_from, date_to, expiry_hours)
        
        # Generate full URL
        report_url = url_for('user_report_secure', token=token, _external=True)
        
        return jsonify({
            'success': True,
            'url': report_url,
            'token': token,
            'expires_in_hours': expiry_hours
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Placeholder functions for remaining secure routes (to be implemented)
def class_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('classes'))

def class_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('classes'))

def group_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('groups'))

def group_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('groups'))

def role_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('roles'))

def role_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('roles'))

def conduct_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('conducts'))

def conduct_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('conducts'))

def subject_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('subjects'))

def subject_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('subjects'))

def criteria_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('criteria'))

def criteria_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('criteria'))

def comment_template_edit_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('comment_management'))

def comment_template_delete_secure(id, token):
    flash('Chức năng đang được phát triển', 'info')
    return redirect(url_for('comment_management'))


@app.route('/student_report', methods=['GET', 'POST'])
def student_report():
    """Báo cáo kết quả học sinh"""
    # Check permissions
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    
    # Get current user info
    current_user = get_user_by_id(session['user_id'])
    if not current_user:
        flash('Không tìm thấy thông tin người dùng', 'error')
        return redirect(url_for('login'))
    
    # Students can only view their own reports, masters can view all
    if request.method == 'GET':
        # Get list of users for master users
        users = []
        if session.get('role_name') == 'Master' or session.get('role_name') == 'GVCN':
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.name FROM Users u
                LEFT JOIN Roles r ON u.role_id = r.id
                WHERE u.is_deleted = 0 
                AND (r.name IS NULL OR r.name NOT IN ('GVCN', 'Master', 'Quản trị viên'))
            """)
            users = cursor.fetchall()
            conn.close()
            
            # Sort users by Vietnamese first name like user_summary
            users = sorted(users, key=lambda u: vietnamese_sort_key(u[1], sort_by_first_name=True))
        
        return render_template_with_permissions('student_report.html',
                             current_user_info=current_user,
                             users=users,
                             role_name=session.get('role_name'))
    
    # Handle POST request (search for report data)
    if request.method == 'POST':
        try:
            user_id = request.form.get('user_id')
            date_from = request.form.get('date_from')
            date_to = request.form.get('date_to')
            
            # Validation
            if not user_id:
                return jsonify({'success': False, 'error': 'Vui lòng chọn học sinh'})
            
            if not date_from or not date_to:
                return jsonify({'success': False, 'error': 'Vui lòng chọn khoảng thời gian'})
            
            
            # Get student info
            student = get_user_by_id(user_id)
            if not student:
                return jsonify({'success': False, 'error': 'Không tìm thấy thông tin học sinh'})
            
            # Get teacher info (homeroom teacher)
            conn = connect_db()
            cursor = conn.cursor()
            try:
                # Make sure student has class_id
                cursor.execute("""
                        SELECT u.name 
                        FROM Users u 
                        JOIN Roles r ON u.role_id = r.id 
                        WHERE r.name = 'GVCN' AND u.is_deleted = 0
                        LIMIT 1
                    """)
                teacher_info = cursor.fetchone()
                teacher_name = teacher_info[0] if teacher_info else "Chưa phân công"
            except Exception as e:
                teacher_name = "Chưa phân công"
            finally:
                conn.close()
            
            # Generate report HTML
            report_html = generate_student_report_html(user_id, date_from, date_to, student, teacher_name)
            
            return jsonify({'success': True, 'html': report_html})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


def generate_student_report_html(user_id, date_from, date_to, student, teacher_info):
    """Generate HTML content for student report"""
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Parse dates
        from_date = datetime.strptime(date_from, '%Y-%m-%d')
        to_date = datetime.strptime(date_to, '%Y-%m-%d')
        
        # Determine period display
        if (to_date - from_date).days == 6:  # Weekly report
            period_text = f"Tuần từ {from_date.strftime('%d/%m/%Y')} đến {to_date.strftime('%d/%m/%Y')}"
            period_type = 'Tuần'
        else:  # Monthly report
            period_text = f"Tháng {from_date.strftime('%m/%Y')}"
            period_type = 'Tháng'
        
        # Get subjects data
        cursor.execute("""
            SELECT s.name, COALESCE(c.name, 'Chưa đánh giá') as result, us.total_points, us.registered_date
            FROM User_Subjects us
            JOIN Subjects s ON us.subject_id = s.id
            LEFT JOIN Criteria c ON us.criteria_id = c.id
            WHERE us.user_id = ? AND us.is_deleted = 0 AND us.registered_date >= ? AND us.registered_date <= ?
            ORDER BY us.registered_date, s.name
        """, (user_id, date_from, date_to))
        subjects_data = cursor.fetchall()
        
        # Get conduct data
        cursor.execute("""
            SELECT c.name, uc.total_points, uc.registered_date, c.conduct_type
            FROM User_Conduct uc
            JOIN Conduct c ON uc.conduct_id = c.id
            WHERE uc.user_id = ? AND uc.is_deleted = 0
            AND uc.registered_date >= ? AND uc.registered_date <= ?
            ORDER BY uc.registered_date, c.name
        """, (user_id, date_from, date_to))
        conduct_data = cursor.fetchall()
        
        # Get teacher comments for the period - exact match with search period
        cursor.execute("""
            SELECT uc.comment_text, uc.created_date, uc.period_start, uc.period_end
            FROM User_Comments uc
            WHERE uc.user_id = ? 
            AND uc.period_start = ? AND uc.period_end = ?
            ORDER BY uc.created_date DESC
        """, (user_id, date_from, date_to))
        comments_data = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM Classes WHERE is_deleted = 0 ORDER BY name")
        classes = cursor.fetchall()
        classnames = classes[0][1] if classes else "Chưa phân lớp"
        
        # Calculate statistics
        total_conduct_points = sum([row[1] for row in conduct_data])
        
        # Additional statistics for enhanced report
        total_academic_points = 0  # Will be calculated properly below
        prev_academic_points = 0
        prev_conduct_points = 0
        
        # Calculate total academic points from subjects_data if available
        try:
            cursor.execute("""
                SELECT SUM(total_points) FROM User_Subjects
                WHERE user_id = ? AND is_deleted = 0 
                AND registered_date >= ? AND registered_date <= ?
            """, (user_id, date_from, date_to))
            total_academic_points = cursor.fetchone()[0] or 0
        except:
            total_academic_points = 0
        
        # Calculate previous period points for comparison
        try:
            from_date_obj = datetime.strptime(date_from, '%Y-%m-%d')
            to_date_obj = datetime.strptime(date_to, '%Y-%m-%d')
            period_duration = (to_date_obj - from_date_obj).days
            prev_period_end = from_date_obj - timedelta(days=1)
            prev_period_start = prev_period_end - timedelta(days=period_duration)
            prev_date_from_str = prev_period_start.strftime('%Y-%m-%d')
            prev_date_to_str = prev_period_end.strftime('%Y-%m-%d')
            
            # Previous academic points
            cursor.execute("""
                SELECT SUM(total_points) FROM User_Subjects
                WHERE user_id = ? AND is_deleted = 0 
                AND registered_date >= ? AND registered_date <= ?
            """, (user_id, prev_date_from_str, prev_date_to_str))
            prev_academic_points = cursor.fetchone()[0] or 0
            
            # Previous conduct points
            cursor.execute("""
                SELECT SUM(total_points) FROM User_Conduct
                WHERE user_id = ? AND is_deleted = 0 
                AND registered_date >= ? AND registered_date <= ?
            """, (user_id, prev_date_from_str, prev_date_to_str))
            prev_conduct_points = cursor.fetchone()[0] or 0
        except:
            prev_academic_points = 0
            prev_conduct_points = 0
        
        # Calculate progress
        academic_progress = total_academic_points - prev_academic_points
        conduct_progress = total_conduct_points - prev_conduct_points
        
        # Calculate ranking
        total_points = total_academic_points + total_conduct_points
        ranking, ranking_color = get_ranking_info(total_points)
        logging.info(f"Calculated total_points: {total_points}, ranking: {ranking}, color: {ranking_color}")
        
        # Progress indicators
        def get_progress_class(progress):
            if progress > 0:
                return "text-success", "fa-arrow-up", f"+{progress}"
            elif progress < 0:
                return "text-danger", "fa-arrow-down", str(progress)
            else:
                return "text-muted", "fa-minus", "0"
        
        academic_class, academic_icon, academic_text = get_progress_class(academic_progress)
        conduct_class, conduct_icon, conduct_text = get_progress_class(conduct_progress)
        
        # Group subjects by result
        subjects_by_result = {}
        for subject, result, points, date in subjects_data:
            if result not in subjects_by_result:
                subjects_by_result[result] = []
            subjects_by_result[result].append((subject, points, date))
        
        # Group conduct by week
        conduct_by_week = {}
        for conduct, points, registered_date, conduct_type in conduct_data:
            if registered_date not in conduct_by_week:
                conduct_by_week[registered_date] = []
            conduct_by_week[registered_date].append((conduct, points, conduct_type))
        
        # Generate HTML with proper CSS classes
        html = f"""
        <div class="position-relative">
            
            
            <div class="report-header" style="
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 30px 20px;
                border-radius: 10px 10px 0 0;
                margin-bottom: 0;
            ">
                <h1 class="text-center mb-3" style="color: white; font-weight: bold; font-size: 1.8rem;">KẾT QUẢ RÈN LUYỆN LỚP {classnames}</h1>
                <div class="student-teacher-row d-flex justify-content-between align-items-center">
                    <div class="student-name fw-bold" style="color: #ecf0f1; font-size: 1.1rem;">Học sinh: {student['name']}</div>
                    <div class="period-info text-center" style="color: #bdc3c7; font-size: 1rem; font-weight: 500;">{period_text}</div>
                    <div class="teacher-name fw-bold" style="color: #ecf0f1; font-size: 1.1rem;">GVCN: {teacher_info}</div>
                </div>
            </div>
            
            <div class="report-body p-4">
                <!-- Summary Cards -->
                <div class="summary-cards row g-3 mb-4">                    
                    <div class="col-md-3">
                        <div class="summary-card conduct-card h-100 p-3 text-center" style="background: #b4b4b4; color: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
                            <h3 class="mb-2" style="font-size: 2rem; font-weight: bold;">{total_conduct_points}</h3>
                            <p class="mb-2" style="font-size: 1.1rem;">Điểm rèn luyện</p>
                            <small class="mt-1 d-block">
                                <i class="fas {conduct_icon} {conduct_class}"></i>
                                <span class="{conduct_class}">{conduct_text} điểm</span>
                            </small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="summary-card study-card h-100 p-3 text-center" style="background: #7cc1ffe8; color: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
                            <h3 class="mb-2" style="font-size: 2rem; font-weight: bold;">{total_academic_points}</h3>
                            <p class="mb-2" style="font-size: 1.1rem;">Điểm học tập</p>
                            <small class="mt-1 d-block">
                                <i class="fas {academic_icon} {academic_class}"></i>
                                <span class="{academic_class}">{academic_text} điểm</span>
                            </small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="summary-card total-card h-100 p-3 text-center" style="background: #075e6770; color: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
                            <h3 class="mb-2" style="font-size: 2rem; font-weight: bold;">{total_academic_points + total_conduct_points}</h3>
                            <p class="mb-2" style="font-size: 1.1rem;">Tổng điểm</p>
                            <small class="mt-1 d-block" style="color: rgba(255,255,255,0.9);">
                                {period_type} trước: {prev_academic_points + prev_conduct_points} điểm
                            </small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="summary-card ranking-card h-100 p-3 text-center" style="background: {ranking_color}; color: white; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);">
                            <h3 class="mb-2" style="font-size: 1.8rem; font-weight: bold;">{ranking}</h3>
                            <p class="mb-2" style="font-size: 1.1rem;">Xếp loại</p>
                            <small class="mt-1 d-block" style="color: rgba(255,255,255,0.9);">
                                Dựa trên tổng {total_points} điểm
                            </small>
                        </div>
                    </div>
                </div>
                
                <!-- Subjects Detail -->
                <div class="details-section mb-4 p-4" style="background: #fdfdfd; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); border: 1px solid #e8e8e8;">
                    <h3 class="mb-3" style="color: #000000; border-bottom: 3px solid #3498db; padding-bottom: 10px; font-weight: 600;">
                        <i class="fas fa-book me-2" style="color: #3498db;"></i>Kết quả Học tập
                    </h3>
                    <div class="table-responsive">
                        <table class="table table-striped table-hover mb-0">
                            <thead style="background: linear-gradient(135deg, #000000 0%, #34495e 100%); color: white;">
                                <tr>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Môn học</th>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Kết quả</th>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Điểm</th>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Ngày</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        # Add subjects data
        for subject, result, points, date in subjects_data:
            # Format date
            try:
                formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                formatted_date = date
                
            # Format points with color
            points_class = ""
            if points > 0:
                points_class = "text-success fw-bold"
                points_display = f"+{points}"
            elif points < 0:
                points_class = "text-danger fw-bold"
                points_display = str(points)
            else:
                points_class = "text-muted"
                points_display = "0"
                
            html += f"""
                                <tr style="border-bottom: 1px solid #f1f2f6; background: white;">
                                    <td style="padding: 15px; font-weight: 500; color: #000000;">{subject}</td>
                                    <td style="padding: 15px;"><span class="{points_class}">{result}</span></td>
                                    <td style="padding: 15px;"><span class="{points_class}">{points_display}</span></td>
                                    <td style="padding: 15px; color: #000000; font-size: 0.95rem;">{formatted_date}</td>
                                </tr>
            """
        
        if not subjects_data:
            html += """
                                <tr>
                                    <td colspan="4" class="text-center text-muted" style="padding: 20px;">Chưa có dữ liệu học tập</td>
                                </tr>
            """
        
        html += """
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Conduct Detail -->
                <div class="details-section mb-4 p-4" style="background: #fdfdfd; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); border: 1px solid #e8e8e8;">
                    <h3 class="mb-3" style="color: #000000; border-bottom: 3px solid #b4b4b4; padding-bottom: 10px; font-weight: 600;">
                        <i class="fas fa-star me-2" style="color: #b4b4b4;"></i>Kết quả Hạnh kiểm
                    </h3>
                    <div class="table-responsive">
                        <table class="table table-striped table-hover mb-0">
                            <thead style="background: linear-gradient(135deg, #000000 0%, #34495e 100%); color: white;">
                                <tr>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Tiêu chí</th>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Loại Hạnh kiểm</th>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Điểm</th>
                                    <th style="border: none; padding: 15px; font-weight: 500;">Ngày</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        # Add conduct data
        for conduct, points, registered_date, conduct_type in conduct_data:
            points_class = ""
            if points >= 0:
                points_class = "text-success fw-bold"
            else:
                points_class = "text-danger fw-bold"
            
            points_display = f"+{points}" if points > 0 else str(points)
            
            # Format date
            try:
                formatted_date = datetime.strptime(registered_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                formatted_date = registered_date
                
            html += f"""
                                <tr style="border-bottom: 1px solid #f1f2f6; background: white;">
                                    <td style="padding: 15px; font-weight: 500;"><span class="{points_class}">{conduct}</span></td>
                                    <td style="padding: 15px;"><span class="{points_class}">{conduct_type}</span></td>
                                    <td style="padding: 15px;"><span class="{points_class}">{points_display}</span></td>
                                    <td style="padding: 15px; color: #000000; font-size: 0.95rem;">{formatted_date}</td>
                                </tr>
            """
        
        if not conduct_data:
            html += """
                                <tr>
                                    <td colspan="3" class="text-center text-muted" style="padding: 20px;">Chưa có dữ liệu hạnh kiểm</td>
                                </tr>
            """
        
        html += """
                            </tbody>
                        </table>
                    </div>
                </div>
        """
        
        # Add teacher comments section if there are any comments
        if comments_data:
            html += """
                <!-- Teacher Comments -->
                <div class="details-section mb-4 p-4" style="background: #fdfdfd; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); border: 1px solid #e8e8e8;">
                    <h3 class="mb-3" style="color: #000000; border-bottom: 3px solid #f39c12; padding-bottom: 10px; font-weight: 600;">
                        <i class="fas fa-comment me-2" style="color: #f39c12;"></i>Nhận xét của giáo viên
                    </h3>
            """
            
            for comment_text, created_date, period_start, period_end in comments_data:
                try:
                    formatted_date = datetime.strptime(created_date, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
                except:
                    try:
                        formatted_date = datetime.strptime(created_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except:
                        formatted_date = created_date
                
                # Format period display
                try:
                    period_from = datetime.strptime(period_start, '%Y-%m-%d').strftime('%d/%m/%Y')
                    period_to = datetime.strptime(period_end, '%Y-%m-%d').strftime('%d/%m/%Y')
                    period_display = f"({period_from} - {period_to})"
                except:
                    period_display = ""
                
                # Escape HTML in comment content
                safe_comment = str(comment_text).replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
                
                if safe_comment and safe_comment != "None":
                    html += f"""
                        <div class=\"comment-item mb-3 p-3\" style=\"background: #f8f9fa; border-left: 4px solid #f39c12; border-radius: 5px;\">
                            <div class=\"comment-content\" style=\"color: #34495e; line-height: 1.6;\">
                                {safe_comment}
                            </div>
                        </div>
                    """
            
            html += """
                </div>
            """
        
        html += """
            </div>
        </div>
        """
        
        return html
        
    except Exception as e:
        return f'<div class="alert alert-danger">Có lỗi xảy ra: {str(e)}</div>'
    finally:
        conn.close()

def get_all_mondays_in_year(year):
    """Lấy tất cả ngày thứ 2 trong năm"""
    mondays = []
    current_date = datetime(year, 1, 1)
    
    # Tìm thứ 2 đầu tiên trong năm
    while current_date.weekday() != 0:  # 0 = Monday
        current_date += timedelta(days=1)
    
    # Lấy tất cả thứ 2 trong năm
    while current_date.year == year:
        mondays.append(current_date)
        current_date += timedelta(weeks=1)
    
    return mondays

@app.route('/settings/weeks')
def settings_weeks():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check

    if 'user_id' in session:
        # Lấy dữ liệu tuần đã lưu (nếu có)
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT week_number, from_date, to_date FROM Week_Settings")
        saved_weeks = {row[0]: {'from_date': row[1], 'to_date': row[2]} for row in cursor.fetchall()}
        conn.close()

        # Tạo danh sách 52 tuần
        week_data = []
        for i in range(1, 53):
            week_info = saved_weeks.get(i, {})
            week_data.append({
                'week_number': i,
                'from_date': week_info.get('from_date', ''),
                'to_date': week_info.get('to_date', '')
            })

        return render_template('settings_weeks.html', week_data=week_data)
    else:
        return redirect(url_for('login'))

@app.route('/api/settings/weeks/save', methods=['POST'])
def save_week_settings():
    if 'user_id' in session:
        data = request.json
        week_settings = data.get('week_settings', [])

        conn = connect_db()
        cursor = conn.cursor()

        try:
            # Lấy tất cả tuần hiện có trong DB
            cursor.execute("SELECT week_number FROM Week_Settings")
            existing_weeks = {row[0] for row in cursor.fetchall()}

            # Cập nhật hoặc thêm mới các tuần gửi lên
            sent_weeks = set()
            for setting in week_settings:
                week_number = setting['week_number']
                from_date = setting['from']
                to_date = setting['to']
                sent_weeks.add(week_number)
                cursor.execute("SELECT id FROM Week_Settings WHERE week_number = ?", (week_number,))
                row = cursor.fetchone()
                if row:
                    # Update
                    cursor.execute("UPDATE Week_Settings SET from_date=?, to_date=? WHERE week_number=?", (from_date, to_date, week_number))
                else:
                    # Insert
                    cursor.execute("INSERT INTO Week_Settings (week_number, from_date, to_date) VALUES (?, ?, ?)", (week_number, from_date, to_date))

            # Xóa các tuần không còn trong danh sách gửi lên
            weeks_to_delete = existing_weeks - sent_weeks
            for week_number in weeks_to_delete:
                cursor.execute("DELETE FROM Week_Settings WHERE week_number=?", (week_number,))

            conn.commit()
            return jsonify({'success': True, 'message': 'Lưu cài đặt tuần thành công'})
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/week_by_date')
def api_week_by_date():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Thiếu ngày'}), 400

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({'error': 'Sai định dạng ngày'}), 400

    conn = connect_db()
    cursor = conn.cursor()
    # Lấy tất cả tuần có from_date <= date <= to_date
    cursor.execute("""
        SELECT week_number, from_date, to_date 
        FROM Week_Settings 
        WHERE from_date IS NOT NULL AND to_date IS NOT NULL
          AND from_date <= ? AND to_date >= ?
        ORDER BY week_number ASC
    """, (date_str, date_str))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        # Nếu có nhiều tuần, lấy tuần nhỏ nhất
        week_number, from_date, to_date = rows[0]
        return jsonify({
            'week_number': week_number,
            'from_date': from_date,
            'to_date': to_date
        })
    else:
        # Nếu không có, phán đoán tuần theo thứ 2 và chủ nhật
        monday = date_obj - timedelta(days=date_obj.weekday())
        sunday = monday + timedelta(days=6)
        week_number = int(monday.strftime("%U")) + 1
        return jsonify({
            'week_number': week_number,
            'from_date': monday.strftime("%Y-%m-%d"),
            'to_date': sunday.strftime("%Y-%m-%d")
        })

@app.route('/api/week_by_number')
def api_week_by_number():
    week_number = request.args.get('week_number', type=int)

    if week_number is not None and week_number >= 1 and week_number <= 52:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT week_number, from_date, to_date 
            FROM Week_Settings 
            WHERE week_number = ?
        """, (week_number,))
        row = cursor.fetchone()
        conn.close()

        if row and row[1] and row[2]:
            return jsonify({
                'week_number': row[0],
                'from_date': row[1],
                'to_date': row[2]
            })
        else:
            return jsonify({'error': f'Tuần {week_number} chưa được đăng ký'}), 400
    else:
        return jsonify({'error': 'Số tuần không hợp lệ (1-52)'}), 400 

@app.route('/api/get_week_number')
def get_week_number_api():
    """API lấy số tuần dựa trên ngày thứ 2"""
    monday_date = request.args.get('monday_date')
    if not monday_date:
        return jsonify({'week_number': None})
    
    try:
        # Parse năm từ monday_date
        year = datetime.strptime(monday_date, '%Y-%m-%d').year
        
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT week_number FROM Week_Settings 
            WHERE year = ? AND monday_date = ?
        """, (year, monday_date))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({'week_number': result[0]})
        else:
            return jsonify({'week_number': 'X'})
    except Exception as e:
        return jsonify({'week_number': None, 'error': str(e)})

@app.route('/api/conducts/grouped', methods=['GET'])
def get_grouped_conducts_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, conduct_type FROM Conduct WHERE is_deleted = 0 ORDER BY conduct_type, name")
    rows = cursor.fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        conduct_type = row[2] or 'Khác'
        if conduct_type not in grouped:
            grouped[conduct_type] = []
        grouped[conduct_type].append({'id': row[0], 'name': row[1]})
    
    return jsonify(grouped)

@app.route('/api/criteria/grouped', methods=['GET'])
def get_grouped_criteria_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, criterion_type FROM Criteria WHERE is_deleted = 0 ORDER BY criterion_type, name")
    rows = cursor.fetchall()
    conn.close()

    
    grouped = {}
    for row in rows:    
        if row[2] is not None:
            if row[2] == 1:
                criterion_type = 'điểm cộng'
            else:
                criterion_type = 'điểm trừ'
        else:
            criterion_type = 'Khác'
        if criterion_type not in grouped:
            grouped[criterion_type] = []
        grouped[criterion_type].append({'id': row[0], 'name': row[1]})
    
    
    return jsonify(grouped)


@app.route('/login_history', methods=['GET', 'POST'])
def login_history():
    permission_check = require_menu_permission('master')
    if permission_check:
        return permission_check
    
    if 'user_id' in session:
        
        # Get sort parameters from both GET and POST requests
        sort_by = request.form.get('sort_by')
        sort_order = request.form.get('sort_order') or request.args.get('sort_order', 'asc')

        valid_columns = {
            'user_name': 'u.name',
            'login_date': 'lh.login_date',
            'login_time': 'lh.login_time'
        }
        sort_column = valid_columns.get(sort_by, 'u.name')
        sort_direction = 'DESC' if sort_order == 'desc' else 'ASC'
        
        # Special handling for user_name sorting (sort by first name)
        sort_by_first_name = (sort_by == 'user_name')

        # Get filtered data based on role permissions
        
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM Users WHERE is_deleted = 0 AND role_id IN (SELECT id FROM Roles WHERE is_deleted = 0 AND name NOT IN ('Master')) ORDER BY name")
        results = cursor.fetchall()
        users = [{'id': r[0], 'name': r[1]} for r in results]
        conn.close()
        
        groups = get_filtered_groups_by_role()
        
        # Sort users by first name using Vietnamese normalization
        users.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=True))
        groups.sort(key=lambda u: vietnamese_sort_key(u['name'], sort_by_first_name=False))
        
        # Modal users same as filtered users for consistency

        # Tính toán ngày mặc định: Thứ 2 của tuần hiện tại
        today = datetime.today()
        days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
        nearest_monday = today - timedelta(days=days_since_monday)
        default_date_from = nearest_monday.strftime('%Y-%m-%d')
        default_date_to = (nearest_monday + timedelta(days=6)).strftime('%Y-%m-%d')  # Chủ Nhật của tuần

        selected_users = []
        date_from = default_date_from
        date_to = default_date_to
        selected_groups = []
        select_all_users = False
        select_all_groups = False

        if request.method == 'POST':
            select_all_users = request.form.get('select_all_users') == 'on'
            selected_users = request.form.getlist('users')
            date_from = request.form.get('date_from') or default_date_from
            date_to = request.form.get('date_to') or default_date_to
            select_all_groups = request.form.get('select_all_groups') == 'on'
            selected_groups = request.form.getlist('groups')
        else:
            select_all_users = request.args.get('select_all_users') == 'on'
            selected_users = request.args.getlist('users')
            date_from = request.args.get('date_from') or default_date_from
            date_to = request.args.get('date_to') or default_date_to
            select_all_groups = request.args.get('select_all_groups') == 'on'
            selected_groups = request.args.getlist('groups')

        conn = connect_db()
        cursor = conn.cursor()
        
        base_query = """
            FROM Login_History lh
            JOIN Users u ON lh.user_id = u.id
            LEFT JOIN Roles r ON u.role_id = r.id
            WHERE lh.login_date BETWEEN ? AND ?
            AND r.name NOT IN ('Master')
            AND u.is_deleted = 0
        """
        params = [date_from, date_to]

        if selected_users:
            placeholders = ','.join(['?' for _ in selected_users])
            base_query += f" AND u.id IN ({placeholders})"
            params.extend(selected_users)

        if selected_groups:
            placeholders = ','.join(['?' for _ in selected_groups])
            base_query += f" AND u.group_id IN ({placeholders})"
            params.extend(selected_groups)

        # Lấy toàn bộ record, không phân trang
        data_query = f"""
            SELECT u.id, u.name, lh.login_date, lh.login_time
            {base_query}
            ORDER BY {sort_column} {sort_direction}
        """
 
        cursor.execute(data_query, params)
        records = cursor.fetchall()
        
        # If sorting by user_name, apply Vietnamese first name sorting
        if sort_by_first_name:
            records = sorted(records, 
                           key=lambda r: vietnamese_sort_key(r[1], sort_by_first_name=True),
                           reverse=(sort_order == 'desc'))
        
        conn.close()

        # Check if this is an AJAX request
        if request.form.get('ajax') == '1' or request.args.get('ajax') == '1':
            # Generate table HTML for AJAX response
            table_html = "<tbody>"
            for record in records:                
                table_html += f'<tr data-id="{record[0]}"><td>{record[1]}</td><td>{record[2]}</td><td>{record[3]}</td></tr>'
            
            table_html += "</tbody>"
            return jsonify({'html': table_html})


        return render_template_with_permissions('login_history.html',
                               records=records,
                               users=users,  # Use filtered users for both filter and modal
                               groups=groups,
                               all_users=users,  # Use filtered users for modal
                               sort_by=sort_by,
                               sort_order=sort_order,
                               date_from=date_from,
                               date_to=date_to,
                               selected_users=selected_users,
                               selected_groups=selected_groups,
                               select_all_users=select_all_users,
                               select_all_groups=select_all_groups,
                               is_gvcn=is_user_gvcn(),
                               role_name=session.get('role_name'))
    else:
        return redirect(url_for('login'))

def encode_user_id(user_id):
    return base64.urlsafe_b64encode(str(user_id).encode()).decode()

def decode_user_id(encoded):
    try:
        # Thêm padding nếu thiếu
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += '=' * (4 - missing_padding)
        return int(base64.urlsafe_b64decode(encoded.encode()).decode())
    except Exception:
        return None
    
@app.route('/user_account_encoded/<encoded_id>')
def user_account_encoded(encoded_id):
    user_id = decode_user_id(encoded_id)
    if not user_id:
        return "<h3>Link không hợp lệ!</h3>", 400
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.name, u.username, u.password, r.name as role_name, u.role_username, u.role_password
        FROM Users u
        LEFT JOIN Roles r ON u.role_id = r.id
        WHERE u.id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    class_data = read_record_by_id('Classes', id, ['id', 'name'])
    
    if not user:
        return "<h3>Không tìm thấy user!</h3>", 404
    
    logging.info(f"Accessed user account for user_id: {class_data}")
    
    return render_template(
        'user_account.html',
        name=user[0],
        username=user[1],
        password=user[2],
        role_name=user[3],
        role_username=user[4],
        role_password=user[5],
        class_name=class_data['name'] if class_data else "Chưa phân lớp"
    )


if __name__ == '__main__':
    setup_sample_data()
    app.run(debug=True, port=5001)