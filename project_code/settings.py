import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LIQUIPEDIA_API_KEY")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
BOT_KEY = os.getenv("BOT_API_KEY")
dbname = os.getenv("dbname")
user = os.getenv("user")
host = os.getenv("host")