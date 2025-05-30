# config/models.py

"""
Model configurations for different LLM sizes and capabilities.
"""

# Model configuration
MODELS = {
    "small": {
        "key": "small",
        "name": "llama3:8b",
        "batch_size": 4,
        "context_window": 4096,
        "temperature": 0.1,
        "description": "Fast model suitable for most analyses"
    },
    "medium": {
        "key": "medium",
        "name": "llama3:70b-instruct-q4_0",  # Using llama3 70B with quantization for better performance/quality balance
        "batch_size": 2, 
        "context_window": 8192,
        "temperature": 0.1,
        "description": "Balanced model with improved accuracy"
    },
    "large": {
        "key": "large",
        "name": "llama3:70b-instruct",
        "batch_size": 1,
        "context_window": 8192,
        "temperature": 0.1,
        "description": "High-accuracy model (requires 32GB+ RAM)"
    }
}

# Default model to use
DEFAULT_MODEL = "small"