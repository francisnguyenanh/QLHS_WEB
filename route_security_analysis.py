#!/usr/bin/env python3
"""
Route Security Analysis Script
Analyze all routes and determine which ones need URL encryption
"""

import re

def analyze_routes():
    """Analyze all routes in the application for security requirements"""
    
    print("🔍 ROUTE SECURITY ANALYSIS")
    print("="*80)
    
    # Routes that are already encrypted or don't need encryption
    secure_routes = []
    
    # Routes that need encryption (public access with sensitive data)
    need_encryption = []
    
    # Routes that are already protected (login required)
    login_protected = []
    
    # API routes (usually for internal use)
    api_routes = []
    
    # Routes with analysis
    routes_analysis = [
        # Authentication & Navigation
        {"route": "/", "type": "login_protected", "reason": "Login page, no sensitive data"},
        {"route": "/login", "type": "login_protected", "reason": "Public login form, no sensitive data"},
        {"route": "/home", "type": "login_protected", "reason": "Requires login session"},
        {"route": "/logout", "type": "login_protected", "reason": "Requires login session"},
        
        # Settings & Configuration
        {"route": "/settings", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/settings/update_background", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/settings/remove_background", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/save_system_config", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/reset", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/reset/table/<table_name>", "type": "login_protected", "reason": "Admin only, session protected"},
        
        # User Management
        {"route": "/users", "type": "login_protected", "reason": "Requires login, permission-based filtering"},
        {"route": "/users/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/users/edit/<int:id>", "type": "need_encryption", "reason": "Contains user ID in URL, could expose user enumeration"},
        {"route": "/users/delete/<int:id>", "type": "need_encryption", "reason": "Contains user ID, critical operation"},
        
        # Classes Management
        {"route": "/classes", "type": "login_protected", "reason": "Requires login, no sensitive IDs exposed"},
        {"route": "/classes/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/classes/edit/<int:id>", "type": "need_encryption", "reason": "Contains class ID in URL"},
        {"route": "/classes/delete/<int:id>", "type": "need_encryption", "reason": "Contains class ID, critical operation"},
        
        # Groups Management
        {"route": "/groups", "type": "login_protected", "reason": "Requires login, no sensitive IDs exposed"},
        {"route": "/groups/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/groups/edit/<int:id>", "type": "need_encryption", "reason": "Contains group ID in URL"},
        {"route": "/groups/delete/<int:id>", "type": "need_encryption", "reason": "Contains group ID, critical operation"},
        
        # Roles Management
        {"route": "/roles", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/roles/create", "type": "login_protected", "reason": "Admin only, session protected"},
        {"route": "/roles/edit/<int:id>", "type": "need_encryption", "reason": "Contains role ID, admin function"},
        {"route": "/roles/delete/<int:id>", "type": "need_encryption", "reason": "Contains role ID, critical operation"},
        
        # Conduct Management
        {"route": "/conducts", "type": "login_protected", "reason": "Requires login, no sensitive IDs exposed"},
        {"route": "/conducts/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/conducts/edit/<int:id>", "type": "need_encryption", "reason": "Contains conduct ID in URL"},
        {"route": "/conducts/delete/<int:id>", "type": "need_encryption", "reason": "Contains conduct ID, critical operation"},
        
        # Subjects Management
        {"route": "/subjects", "type": "login_protected", "reason": "Requires login, no sensitive IDs exposed"},
        {"route": "/subjects/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/subjects/edit/<int:id>", "type": "need_encryption", "reason": "Contains subject ID in URL"},
        {"route": "/subjects/delete/<int:id>", "type": "need_encryption", "reason": "Contains subject ID, critical operation"},
        
        # Criteria Management
        {"route": "/criteria", "type": "login_protected", "reason": "Requires login, no sensitive IDs exposed"},
        {"route": "/criteria/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/criteria/edit/<int:id>", "type": "need_encryption", "reason": "Contains criteria ID in URL"},
        {"route": "/criteria/delete/<int:id>", "type": "need_encryption", "reason": "Contains criteria ID, critical operation"},
        
        # User Conduct Management
        {"route": "/user_conduct", "type": "login_protected", "reason": "Requires login, permission-based filtering"},
        {"route": "/user_conduct/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/user_conduct/edit/<int:id>", "type": "need_encryption", "reason": "Contains record ID, student data"},
        {"route": "/user_conduct/delete/<int:id>", "type": "need_encryption", "reason": "Contains record ID, critical operation"},
        
        # User Subjects Management
        {"route": "/user_subjects", "type": "login_protected", "reason": "Requires login, permission-based filtering"},
        {"route": "/user_subjects/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/user_subjects/edit/<int:id>", "type": "need_encryption", "reason": "Contains record ID, student data"},
        {"route": "/user_subjects/delete/<int:id>", "type": "need_encryption", "reason": "Contains record ID, critical operation"},
        
        # Reports & Summaries
        {"route": "/group_summary", "type": "login_protected", "reason": "Requires login, uses query parameters"},
        {"route": "/user_summary", "type": "login_protected", "reason": "Requires login, uses query parameters"},
        {"route": "/print_users", "type": "login_protected", "reason": "POST method, requires login"},
        {"route": "/user_report/<int:user_id>", "type": "secure_routes", "reason": "Already encrypted with token system"},
        {"route": "/report/<token>", "type": "secure_routes", "reason": "Encrypted token-based access"},
        
        # Comment Management
        {"route": "/comment_management", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/comment_template/create", "type": "login_protected", "reason": "Requires login and permissions"},
        {"route": "/comment_template/edit/<int:template_id>", "type": "need_encryption", "reason": "Contains template ID"},
        {"route": "/comment_template/delete/<int:template_id>", "type": "need_encryption", "reason": "Contains template ID, critical operation"},
        {"route": "/save_user_comment", "type": "login_protected", "reason": "POST method, requires login"},
        
        # API Routes (Internal Use)
        {"route": "/api/classes/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/classes", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/groups/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/groups", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/roles/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/roles", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/conducts/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/conducts", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/subjects/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/subjects", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/criteria/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/criteria", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/users/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/users", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/user_conduct/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/user_conduct", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/user_subjects/<int:id>", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/api/user_subjects", "type": "api_routes", "reason": "Internal API, requires login"},
        {"route": "/generate_report_link", "type": "api_routes", "reason": "Internal API for token generation"},
        
        # Utility Routes
        {"route": "/get_conduct_points/<int:conduct_id>", "type": "api_routes", "reason": "Internal utility, requires login"},
        {"route": "/user_conduct_total_points", "type": "api_routes", "reason": "Internal utility, requires login"},
        {"route": "/get_criteria_points/<int:criteria_id>", "type": "api_routes", "reason": "Internal utility, requires login"},
        {"route": "/user_subjects_total_points", "type": "api_routes", "reason": "Internal utility, requires login"},
    ]
    
    # Categorize routes
    for route in routes_analysis:
        if route["type"] == "need_encryption":
            need_encryption.append(route)
        elif route["type"] == "login_protected":
            login_protected.append(route)
        elif route["type"] == "secure_routes":
            secure_routes.append(route)
        elif route["type"] == "api_routes":
            api_routes.append(route)
    
    # Print analysis results
    print("📊 ANALYSIS RESULTS:")
    print(f"   🔒 Already Secure: {len(secure_routes)} routes")
    print(f"   🔐 Need Encryption: {len(need_encryption)} routes")
    print(f"   🔑 Login Protected: {len(login_protected)} routes")
    print(f"   ⚙️ API Routes: {len(api_routes)} routes")
    
    print("\n🔐 ROUTES THAT NEED ENCRYPTION:")
    print("-" * 60)
    for route in need_encryption:
        print(f"   ❌ {route['route']}")
        print(f"      Reason: {route['reason']}")
        print()
    
    print("🔒 ALREADY SECURE ROUTES:")
    print("-" * 60)
    for route in secure_routes:
        print(f"   ✅ {route['route']}")
        print(f"      Status: {route['reason']}")
        print()
    
    print("🔑 LOGIN PROTECTED ROUTES (OK):")
    print("-" * 60)
    print(f"   {len(login_protected)} routes are protected by login session")
    print("   These don't need URL encryption as they require authentication")
    
    print("\n⚙️ API ROUTES (OK):")
    print("-" * 60)
    print(f"   {len(api_routes)} internal API routes")
    print("   These are for internal use and require authentication")
    
    print("\n" + "="*80)
    print("🎯 RECOMMENDATION SUMMARY:")
    print("="*80)
    
    priority_routes = [
        "/users/edit/<int:id>",
        "/users/delete/<int:id>",
        "/user_conduct/edit/<int:id>",
        "/user_conduct/delete/<int:id>",
        "/user_subjects/edit/<int:id>",
        "/user_subjects/delete/<int:id>"
    ]
    
    print("🚨 HIGH PRIORITY (Student Data):")
    for route in priority_routes:
        print(f"   • {route}")
    
    print("\n⚠️ MEDIUM PRIORITY (System Data):")
    medium_routes = [r for r in need_encryption if r["route"] not in priority_routes]
    for route in medium_routes:
        print(f"   • {route['route']}")
    
    print("\n💡 IMPLEMENTATION STRATEGY:")
    print("   1. Implement encryption for HIGH PRIORITY routes first")
    print("   2. Use token-based system similar to user_report")
    print("   3. Generate encrypted tokens for edit/delete operations")
    print("   4. Set appropriate expiry times (shorter for critical operations)")
    print("   5. Add token verification middleware")
    
    return need_encryption

if __name__ == "__main__":
    routes_to_encrypt = analyze_routes()
    
    print(f"\n📋 FINAL COUNT: {len(routes_to_encrypt)} routes need URL encryption")
    print("🔐 Ready to implement secure URL encryption system!")
