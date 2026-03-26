from dotenv import load_dotenv
from pathlib import Path

# Load .env so integration tests can read Azure credentials via os.environ
load_dotenv(Path(__file__).parent.parent / ".env")
