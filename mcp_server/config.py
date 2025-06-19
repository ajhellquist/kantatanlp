"""Shared configuration for MCP server."""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.mavenlink.com/api/v1"
TOKEN = os.getenv("KANTATA_API_TOKEN")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
