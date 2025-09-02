#!/usr/bin/env python3
"""
Quick test for implemented URL encryption routes
"""

def test_implemented_routes():
    """Test the implemented secure routes"""
    try:
        from app import generate_action_token, verify_action_token, app
        
        print("🧪 TESTING IMPLEMENTED SECURE ROUTES")
        print("="*60)
        
        # Test High Priority Routes
        high_priority_tests = [
            {"table": "users", "action": "edit", "id": 1},
            {"table": "users", "action": "delete", "id": 1},
            {"table": "user_conduct", "action": "edit", "id": 1},
            {"table": "user_conduct", "action": "delete", "id": 1},
        ]
        
        print("🚨 HIGH PRIORITY ROUTES:")
        for test in high_priority_tests:
            token = generate_action_token(test["action"], test["id"], test["table"])
            payload = verify_action_token(token, test["action"], test["table"])
            
            if payload:
                print(f"✅ {test['table']}/{test['action']}/{test['id']} -> Token: {token[:30]}...")
            else:
                print(f"❌ {test['table']}/{test['action']}/{test['id']} -> Failed")
        
        # Test URL generation
        print(f"\n🌐 SAMPLE SECURE URLS:")
        with app.app_context():
            from flask import url_for
            
            test_cases = [
                {"action": "edit", "table": "users", "token": "sample_token_here"},
                {"action": "delete", "table": "user_conduct", "token": "sample_token_here"}
            ]
            
            for case in test_cases:
                try:
                    url = url_for('secure_action_handler', 
                                action=case["action"], 
                                table=case["table"], 
                                token=case["token"])
                    print(f"   /{case['action']}/{case['table']}/token -> {url}")
                except Exception as e:
                    print(f"   ❌ URL generation failed: {e}")
        
        # Test Security Features
        print(f"\n🔒 SECURITY TESTS:")
        
        # Test 1: Token expiry
        expired_token = generate_action_token("edit", 1, "users", expiry_hours=-1)
        expired_payload = verify_action_token(expired_token)
        if expired_payload is None:
            print("✅ Expired token correctly rejected")
        else:
            print("❌ Expired token should be rejected")
        
        # Test 2: Action validation
        edit_token = generate_action_token("edit", 1, "users")
        delete_validation = verify_action_token(edit_token, expected_action="delete")
        if delete_validation is None:
            print("✅ Action mismatch correctly rejected")
        else:
            print("❌ Action mismatch should be rejected")
        
        # Test 3: Table validation
        users_token = generate_action_token("edit", 1, "users")
        conduct_validation = verify_action_token(users_token, expected_table="user_conduct")
        if conduct_validation is None:
            print("✅ Table mismatch correctly rejected")
        else:
            print("❌ Table mismatch should be rejected")
        
        print(f"\n🎯 IMPLEMENTATION STATUS:")
        implemented = ["users", "user_conduct"]
        pending = ["user_subjects", "classes", "groups", "roles", "conducts", "subjects", "criteria", "comment_templates"]
        
        print(f"✅ Implemented: {', '.join(implemented)}")
        print(f"⏳ Pending: {', '.join(pending)}")
        
        print(f"\n📋 NEXT STEPS:")
        print("1. Complete user_subjects routes")
        print("2. Implement remaining medium priority routes")
        print("3. Update frontend to use secure URLs")
        print("4. Test all routes end-to-end")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    test_implemented_routes()
