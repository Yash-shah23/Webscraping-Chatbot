# config.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load variables from the .env file
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise EnvironmentError("Supabase URL and Key must be set in the .env file")

# Initialize the Supabase client
supabase: Client = create_client(url, key)