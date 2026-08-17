"""
Legacy Supabase Auth Integration using deprecated v1 sign_in method.
"""
from supabase import create_client

SUPABASE_URL = "https://xyzcompany.supabase.co"
SUPABASE_KEY = "public-anon-key"

def login_user(email_addr: str, pass_word: str):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Deprecated in Supabase v2 (Should be sign_in_with_password)
    user_session = supabase.auth.sign_in(email=email_addr, password=pass_word)
    return user_session

if __name__ == "__main__":
    session = login_user("dev@example.com", "secretpass123")
    print("Logged in successfully:", session)
