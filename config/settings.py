# config/settings.py

"""
General settings and defaults for the compliance analysis tool.
"""

# Configuration version
CONFIG_VERSION = "1.0.0"

# Chunk size configuration
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100

# Path configurations
KNOWLEDGE_BASE_DIR = "knowledge_base"

# Progressive analysis settings
PROGRESSIVE_ANALYSIS_ENABLED = True
HIGH_RISK_SCORE_THRESHOLD = 5
MEDIUM_RISK_SCORE_THRESHOLD = 2
RISK_SCORE_WEIGHTS = {
    "high_risk_keyword": 3,
    "pattern_indicator": 2,
    "data_term": 1
}

# Common data terms for all frameworks
DATA_TERMS = [
    "personal data", "email", "address", "phone", "location", 
    "user", "profile", "data", "information", "identifier", 
    "record", "account", "tracking", "customer"
]