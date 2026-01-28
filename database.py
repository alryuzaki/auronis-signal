import sqlite3
import datetime
from typing import List, Optional, Tuple, Dict, Any

class BotDatabase:
    def __init__(self, db_file="bot_data.db"):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ... [Previous Tables] ...
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.executemany('''
            INSERT OR IGNORE INTO roles (name) VALUES (?)
        ''', [('Super Admin',), ('Admin',), ('Member',), ('Viewer',)])

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role_id INTEGER,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL,
                duration_days INTEGER NOT NULL,
                assets TEXT DEFAULT 'all' 
            )
        ''')
        try: cursor.execute('ALTER TABLE packages ADD COLUMN assets TEXT DEFAULT "all"')
        except: pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                details TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                package_id INTEGER,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                status TEXT DEFAULT 'active',
                invite_status TEXT DEFAULT 'pending',
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (package_id) REFERENCES packages (id)
            )
        ''')
        try: cursor.execute('ALTER TABLE subscriptions ADD COLUMN invite_status TEXT DEFAULT "pending"')
        except: pass
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                package_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                proof_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (package_id) REFERENCES packages (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                schedule_time TEXT,
                message TEXT NOT NULL,
                last_sent TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                target_groups TEXT NOT NULL,
                frequency TEXT NOT NULL,
                schedule_time TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_sent TIMESTAMP
            )
        ''')

        # NEW: System Settings Table (Key-Value)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        # Insert Default Settings
        cursor.execute('''
            INSERT OR IGNORE INTO system_settings (key, value) 
            VALUES ('maintenance_mode', '0')
        ''')

        conn.commit()
        conn.close()

    # ... [Keep all previous methods] ...
    # --- User Management ---
    def add_user(self, user_id: int, username: str, role_name: str = "Viewer"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM roles WHERE name = ?', (role_name,))
        role = cursor.fetchone()
        role_id = role['id'] if role else 4 
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, role_id) 
                VALUES (?, ?, ?)
            ''', (user_id, username, role_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.name as role_name 
            FROM users u 
            JOIN roles r ON u.role_id = r.id 
            WHERE u.user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
        
    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.name as role_name 
            FROM users u 
            JOIN roles r ON u.role_id = r.id
        ''')
        users = cursor.fetchall()
        conn.close()
        return users

    # --- Package Management ---
    def create_package(self, name: str, price: float, duration_days: int, assets: str = "all"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO packages (name, price, duration_days, assets) VALUES (?, ?, ?, ?)', 
                       (name, price, duration_days, assets))
        conn.commit()
        conn.close()

    def get_packages(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM packages')
        pkgs = cursor.fetchall()
        conn.close()
        return pkgs
        
    def get_package(self, package_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM packages WHERE id = ?', (package_id,))
        pkg = cursor.fetchone()
        conn.close()
        return pkg

    def delete_package(self, package_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM packages WHERE id = ?', (package_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # --- Payment Method Management ---
    def add_payment_method(self, type: str, name: str, details: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO payment_methods (type, name, details) VALUES (?, ?, ?)',
                       (type, name, details))
        conn.commit()
        conn.close()
        
    def get_payment_methods(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM payment_methods')
        methods = cursor.fetchall()
        conn.close()
        return methods
        
    def delete_payment_method(self, method_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM payment_methods WHERE id = ?', (method_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0

    # --- Transaction Management ---
    def create_transaction(self, user_id: int, package_id: int, amount: float, proof_file_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, package_id, amount, status, proof_file_id)
            VALUES (?, ?, ?, 'pending', ?)
        ''', (user_id, package_id, amount, proof_file_id))
        tx_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tx_id

    def get_transaction(self, tx_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, u.username, p.name as package_name, p.duration_days, p.assets
            FROM transactions t
            JOIN users u ON t.user_id = u.user_id
            JOIN packages p ON t.package_id = p.id
            WHERE t.id = ?
        ''', (tx_id,))
        tx = cursor.fetchone()
        conn.close()
        return tx

    def update_transaction_status(self, tx_id: int, status: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE transactions SET status = ? WHERE id = ?', (status, tx_id))
        conn.commit()
        conn.close()

    # --- Subscription Management ---
    def add_subscription(self, user_id: int, package_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT duration_days FROM packages WHERE id = ?', (package_id,))
        pkg = cursor.fetchone()
        if not pkg:
            conn.close()
            return False
            
        duration = pkg['duration_days']
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=duration)
        
        cursor.execute('''
            INSERT INTO subscriptions (user_id, package_id, start_date, end_date, status, invite_status)
            VALUES (?, ?, ?, ?, 'active', 'pending')
        ''', (user_id, package_id, start_date, end_date))
        
        conn.commit()
        conn.close()
        return True

    def get_user_subscription(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, p.name as package_name, p.assets 
            FROM subscriptions s
            JOIN packages p ON s.package_id = p.id
            WHERE s.user_id = ? AND s.status = 'active'
            ORDER BY s.end_date DESC LIMIT 1
        ''', (user_id,))
        sub = cursor.fetchone()
        conn.close()
        return sub

    def update_invite_status(self, sub_id: int, status: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE subscriptions SET invite_status = ? WHERE id = ?', (status, sub_id))
        conn.commit()
        conn.close()

    def get_uninvited_subscriptions(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, u.username, p.name as package_name, p.assets
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            JOIN packages p ON s.package_id = p.id
            WHERE s.status = 'active' AND s.invite_status = 'pending'
        ''')
        subs = cursor.fetchall()
        conn.close()
        return subs

    def check_expiring_soon(self, days=3):
        conn = self.get_connection()
        cursor = conn.cursor()
        target_date = (datetime.datetime.now() + datetime.timedelta(days=days)).date()
        
        cursor.execute('''
            SELECT s.*, u.username 
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status = 'active' 
            AND date(s.end_date) = ?
        ''', (target_date.isoformat(),))
        
        results = cursor.fetchall()
        conn.close()
        return results

    def check_expired(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.datetime.now()
        
        cursor.execute('''
            SELECT s.*, u.username 
            FROM subscriptions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.status = 'active' 
            AND s.end_date < ?
        ''', (now,))
        
        results = cursor.fetchall()
        conn.close()
        return results

    def expire_subscription(self, sub_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE subscriptions SET status = "expired" WHERE id = ?', (sub_id,))
        conn.commit()
        conn.close()

    # --- Role Management ---
    def create_role(self, name: str):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO roles (name) VALUES (?)', (name,))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    def get_roles(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM roles')
        roles = cursor.fetchall()
        conn.close()
        return roles
        
    def delete_role(self, role_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        if role_id <= 4:
            conn.close()
            return False
        cursor.execute('DELETE FROM roles WHERE id = ?', (role_id,))
        conn.commit()
        conn.close()
        return True

    # --- Scheduled Messages ---
    def add_scheduled_message(self, msg_type, time_str, message):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO scheduled_messages (type, schedule_time, message) VALUES (?, ?, ?)',
                       (msg_type, time_str, message))
        conn.commit()
        conn.close()

    def get_due_scheduled_messages(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scheduled_messages')
        msgs = cursor.fetchall()
        conn.close()
        return msgs

    # --- Custom Notifications ---
    def add_custom_notification(self, message, target_groups, frequency, schedule_time):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO custom_notifications (message, target_groups, frequency, schedule_time) 
            VALUES (?, ?, ?, ?)
        ''', (message, target_groups, frequency, schedule_time))
        conn.commit()
        conn.close()

    def get_custom_notifications(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM custom_notifications WHERE is_active = 1')
        notifs = cursor.fetchall()
        conn.close()
        return notifs

    def delete_custom_notification(self, notif_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM custom_notifications WHERE id = ?', (notif_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def update_last_sent(self, notif_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE custom_notifications SET last_sent = ? WHERE id = ?', 
                       (datetime.datetime.now(), notif_id))
        conn.commit()
        conn.close()

    # --- System Settings (NEW) ---
    def get_setting(self, key: str, default: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row['value'] if row else default

    def set_setting(self, key: str, value: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''', (key, value))
        conn.commit()
        conn.close()
