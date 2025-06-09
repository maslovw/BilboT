#!/usr/bin/env python3
"""
Patching script for db_manager.py to fix in-memory database issues with tests
"""

import os
import sys
import re

# Get the absolute path to db_manager.py
db_manager_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bilbot", "database", "db_manager.py")

with open(db_manager_path, 'r') as f:
    content = f.read()

# Add the global conn variable at the top of the file
content = content.replace(
    'logger = logging.getLogger(__name__)',
    'logger = logging.getLogger(__name__)\n\n# Global connection for testing\nconn = None'
)

# Replace the init_database function with the modified version
content = re.sub(
    r'def init_database\(\):(.*?)try:(.*?)db_path = get_database_path\(\)(.*?)conn = sqlite3\.connect\(db_path\)(.*?)cursor = conn\.cursor\(\)',
    'def init_database():\\1try:\\2# If a connection was set by the tests, use it\\2global conn\\2if "conn" in globals() and conn is not None:\\3c = conn.cursor()\\2else:\\3# Normal operation - create a new connection\\3db_path = get_database_path()\\3conn = sqlite3.connect(db_path)\\3c = conn.cursor()',
    content, 
    flags=re.DOTALL
)

# Replace all instances of cursor.execute with c.execute in the init_database function
init_database_section = re.search(r'def init_database\(\):(.*?)finally:', content, re.DOTALL).group(0)
modified_section = init_database_section.replace('cursor.execute', 'c.execute')
content = content.replace(init_database_section, modified_section)

# Replace the CRUD functions to use the global connection in tests
functions_to_modify = ['save_user', 'save_chat', 'save_receipt', 'get_user_receipts']

for func in functions_to_modify:
    pattern = rf'def {func}\((.*?)\):(.*?)try:(.*?)db_path = get_database_path\(\)(.*?)conn = sqlite3\.connect\(db_path\)'
    replacement = f'def {func}(\\1):\\2try:\\3global conn\\3if "conn" in globals() and conn is not None:\\4# Use the existing connection for testing\\4pass\\3else:\\4db_path = get_database_path()\\4conn = sqlite3.connect(db_path)'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Save the modified file
with open(db_manager_path, 'w') as f:
    f.write(content)

print(f"Successfully patched {db_manager_path}")
