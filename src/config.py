import os 
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
CASPIAN_API_KEY = os.getenv("CASPIAN_API_KEY", "")
CASPIAN_BASE_URL = os.getenv("CASPIAN_BASE_URL", "")
DEFAULT_CODE_EXPIRATION_MINUTES = 15
COMMAND_PREFIX = "!relay"