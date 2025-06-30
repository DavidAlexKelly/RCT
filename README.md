# Developer Guide - Regulatory Compliance Analyser

A practical guide for developers working on the Regulatory Compliance Analyser.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Adding New Regulatory Frameworks](#adding-new-regulatory-frameworks)
- [Core Components](#core-components)
- [Configuration & Customization](#configuration--customization)
- [Debugging](#debugging)
- [Deployment](#deployment)

## 🚀 Quick Start

### Development Setup

```bash
# 1. Clone and setup
git clone <repository>
cd regulatory-compliance-analyser

# 2. Install in development mode
pip install -e .

# 3. Install and setup Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3:8b

# 4. Run the application
python launch.py
```

### Project Structure

```
regulatory-compliance-analyser/
├── engine.py                 # Main analysis orchestrator
├── config.py                 # Configuration and settings
├── launch.py                 # Application launcher
├── utils/                    # Core analysis components
├── knowledge_base/           # Regulatory frameworks (pluggable)
│   ├── gdpr/                # GDPR compliance framework
│   └── hipaa/               # HIPAA compliance framework
├── ui/                      # Streamlit web interface
└── sample_docs/            # Test documents
```

## 🏗️ How It Works

### The Big Picture

```
User uploads document → Smart chunking → Filter relevant sections →
Find applicable regulations (RAG) → AI analysis → Extract violations → Report
```

### Core Analysis Flow

```python
def analyse_document(file, framework):
    # 1. Break document into logical sections
    chunks = smart_chunking(file)

    # 2. Filter - only analyse sections with multiple regulated topics
    relevant_chunks = [chunk for chunk in chunks if should_analyse(chunk)]

    # 3. For each relevant section:
    for chunk in relevant_chunks:
        # Find most similar regulations from knowledge base
        regulations = vector_search(chunk_text)

        # Ask AI: "Does this text violate these regulations?"
        violations = llm_analyse(chunk_text, regulations)

        # Parse and collect violations
        results.append(violations)

    # 4. Clean up and return results
    return deduplicate_and_format(results)
```

### Key Intelligence Components

1. **Progressive Filter**: Only analyses sections that mention multiple regulated topics (efficient)
2. **RAG Engine**: Finds the most relevant regulations for each section (contextual)
3. **LLM Reasoning**: Uses AI to determine if specific text violates specific regulations (accurate)
4. **Smart Parsing**: Extracts structured violations from AI responses (robust)

## 📜 Adding New Regulatory Frameworks

This is the main thing you'll want to do. Adding a new regulation (like CCPA, SOX, etc.) is straightforward.

### Step 1: Create Framework Directory

```bash
mkdir knowledge_base/your_framework
cd knowledge_base/your_framework
```

### Step 2: Create the 4 Required Files

#### `articles.txt` - The Regulation Text

This becomes your searchable knowledge base. Format it like this:

```text
Section 1.1 - Data Collection Requirements
Organizations must implement appropriate data collection procedures that ensure transparency and user consent. Data collection should be limited to what is necessary for the stated purpose.

Section 1.2 - Data Processing Standards
All data processing activities shall be conducted in accordance with user permissions. Processing must have a clear legal basis and be proportionate to the intended use.

Section 2.1 - Security Measures
Technical and organizational measures must be implemented to ensure data protection. This includes encryption, access controls, and regular security assessments.
```

**Tips:**

- Each regulation starts with a clear identifier
- Include enough context for semantic search to work
- Copy-paste from official regulation documents

#### `context.yaml` - Framework Metadata

```yaml
framework: your_framework
name: "Your Regulation Name"
full_name: "Full Official Name of the Regulation"
effective_date: "2024-01-01"
jurisdiction: "Country/Region"
scope: "What this regulation covers"

description: >
  Brief description of what this regulatory framework covers.

key_principles:
  - principle: "Transparency"
    section: "Section 1.1"
    description: "Organizations must be transparent about data use"

  - principle: "Security"
    section: "Section 2.1"
    description: "Appropriate security measures required"

common_violations:
  - "Inadequate user consent mechanisms"
  - "Insufficient security measures"
  - "Unclear data processing purposes"
```

#### `classification.yaml` - What Topics to Look For

```yaml
framework: your_framework
version: "1.0"

# Keywords that indicate regulated content
regulated_topics:
  data_processing:
    - "personal data"
    - "user data"
    - "collect"
    - "process"
    - "store"

  user_rights:
    - "consent"
    - "permission"
    - "opt out"
    - "delete"
    - "access"

  security:
    - "security"
    - "encryption"
    - "protect"
    - "safeguard"

# Need this many topic categories to analyse a section
analysis_threshold: 2
```

#### `handler.py` - The Analysis Logic

```python
import yaml
from typing import Dict, Any, List
from pathlib import Path
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """Your Framework compliance handler."""

    def __init__(self, debug=False):
        super().__init__(debug)
        self.name = "Your Framework"
        self.framework_dir = Path(__file__).parent

        # Load your topic classification rules
        with open(self.framework_dir / "classification.yaml", 'r') as f:
            self.classification = yaml.safe_load(f)

        self.regulated_topics = self.classification.get('regulated_topics', {})
        self.analysis_threshold = self.classification.get('analysis_threshold', 2)

    def _infer_regulation_from_issue(self, issue: str) -> str:
        """Map violation descriptions to specific regulation sections."""
        issue_lower = issue.lower()

        # Map keywords to your regulation sections
        patterns = {
            "consent": "Section 1.1 - Data Collection Requirements",
            "security": "Section 2.1 - Security Measures",
            "processing": "Section 1.2 - Data Processing Standards",
            # Add more mappings for your framework
        }

        for keyword, regulation in patterns.items():
            if keyword in issue_lower:
                return regulation

        return "Relevant Framework Section"

    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """Create the prompt sent to the AI."""

        # Format the relevant regulations
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")

        regulations_text = "\n\n".join(formatted_regs)

        return f"""You are a {self.name} compliance expert. Analyse this document section for violations.

DOCUMENT SECTION: {section}

DOCUMENT TEXT:
{text}

RELEVANT {self.name.upper()} SECTIONS:
{regulations_text}

INSTRUCTIONS:
Find clear {self.name} violations in the document text. Look for these violation patterns:

DATA COLLECTION VIOLATIONS:
- No consent mechanism: "collect without consent", "automatic collection"
- Unclear purposes: "collect for business purposes", "any purpose"

SECURITY VIOLATIONS:
- Inadequate protection: "basic security", "minimal protection"
- No encryption: "unencrypted", "plain text storage"

PROCESSING VIOLATIONS:
- No legal basis: "process without permission"
- Excessive processing: "process all data", "unlimited processing"

RESPONSE FORMAT (IMPORTANT):
Respond ONLY in this JSON format with no additional text:

{{
    "violations": [
        {{
            "issue": "Clear description of the violation found",
            "regulation": "{self.name} section reference",
            "quote": "Relevant text from the document"
        }}
    ]
}}

If no violations found: {{"violations": []}}

Remember: Response must start with {{ and end with }}. No other text."""
```

### Step 3: Test Your Framework

Just run the program and see if it works:

```bash
# 1. Start the app
python launch.py

# 2. Upload a test document
# 3. Select your new framework from the dropdown
# 4. Run analysis and see if it finds violations

# If it doesn't appear in the dropdown, check:
python -c "from engine import get_available_frameworks; print([f['id'] for f in get_available_frameworks()])"
```

### Quick Validation Checklist

✅ Framework appears in sidebar dropdown  
✅ Can analyse a document without errors  
✅ Finds violations in obvious violation text  
✅ Doesn't find violations in clean text  
✅ Violation descriptions make sense  
✅ Regulation references are correct

## 🔧 Core Components

### Document Processor (`utils/document_processor.py`)

**What it does**: Breaks documents into logical sections instead of random character chunks

**Key method**:

```python
def process_document(file_path) -> Dict:
    # Returns: {"metadata": {...}, "chunks": [{"text": "...", "position": "Section 1"}, ...]}
```

**To customize document handling**, modify `_smart_chunking()` or `_detect_sections()`

### Embeddings Handler (`utils/embeddings_handler.py`)

**What it does**: Creates the RAG vector database from your `articles.txt`

**Key methods**:

```python
def build_knowledge_base(file_path)  # Load articles.txt into vector DB
def find_similar(query, k=5)         # Find most relevant regulations
```

### LLM Handler (`utils/llm_handler.py`)

**What it does**: Talks to Ollama/LLM models

**To use different models**, edit `MODELS` in `config.py`

### Regulation Handler Base (`utils/regulation_handler_base.py`)

**What it does**: Base class that all framework handlers inherit from

**Key methods your handler inherits**:

- `calculate_risk_score()` - Counts regulated topics in text
- `should_analyse()` - Decides if section needs analysis
- `parse_response()` - Extracts violations from LLM JSON

## ⚙️ Configuration & Customization

### Easy Configuration Changes

```python
# config.py - Main settings
DEFAULT_MODEL = "small"  # or "medium", "large"
MAX_FILE_SIZE_MB = 50    # File upload limit

# Analysis presets
PRESETS = {
    'speed': {
        'topic_threshold': 3.0,  # Higher = fewer sections analysed
        'rag_articles': 3,       # Fewer regulations per section
    },
    'thorough': {
        'topic_threshold': 1.0,  # Lower = more sections analysed
        'rag_articles': 8,       # More regulations per section
    }
}
```

### Environment Variables

```bash
export DEFAULT_MODEL="medium"
export STREAMLIT_PORT=8502
export CHUNK_SIZE=1000
export MAX_FILE_SIZE_MB=100
```

### UI Customization

```python
# ui/styles/custom_css.py - Change colors, fonts, etc.
def apply_custom_styles():
    st.markdown("""<style>
    .main-header { color: your-color; }
    </style>""", unsafe_allow_html=True)
```

## 🐛 Debugging

### Debug Mode

```bash
# Enable debug output in UI
# Check "Debug Mode" in Advanced Options sidebar

# Or in code:
analyser = ComplianceAnalyser(debug=True)
```

### Common Issues & Solutions

#### "Framework not found in dropdown"

```bash
# Check if your framework is valid
python -c "
from engine import ComplianceAnalyser
analyser = ComplianceAnalyser()
frameworks = analyser.get_available_frameworks()
print('Available:', [f['id'] for f in frameworks])
"
```

**Fix**: Make sure you have all 4 required files with correct names

#### "No violations found" (but should find some)

```bash
# Test your topic classification
python -c "
from knowledge_base.your_framework.handler import RegulationHandler
handler = RegulationHandler(debug=True)
score = handler.calculate_risk_score('test text with your keywords')
print(f'Topic score: {score}')
print(f'Should analyse: {handler.should_analyse('test text')}')
"
```

**Fix**: Add more keywords to your `classification.yaml`

#### "LLM connection failed"

```bash
# Check Ollama
ollama list
ollama pull llama3:8b
```

#### "Import errors"

```bash
# Reinstall package
pip install -e .
```

### Debug Output Locations

- **Framework loading**: `utils/prompt_manager.py`
- **Topic classification**: Your framework's `handler.py`
- **RAG search**: `utils/embeddings_handler.py`
- **LLM responses**: `utils/llm_handler.py`
- **Violation parsing**: Your framework's `parse_response()` method

### Useful Debug Commands

```bash
# Test specific components
python -c "from utils.embeddings_handler import EmbeddingsHandler; eh = EmbeddingsHandler(); eh.build_knowledge_base('knowledge_base/gdpr/articles.txt')"

# Check configuration
python config.py

# Test framework handler
python -c "from knowledge_base.gdpr.handler import RegulationHandler; rh = RegulationHandler(debug=True)"
```

## 🚀 Deployment

### Simple Deployment

```bash
# 1. Install on server
pip install -e .

# 2. Install Ollama and models
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3:8b

# 3. Run with specific port
STREAMLIT_PORT=8080 python launch.py
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -e .
RUN curl -fsSL https://ollama.ai/install.sh | sh

EXPOSE 8501
CMD ["python", "launch.py"]
```

### Environment Variables for Production

```bash
export ENVIRONMENT=production
export DEFAULT_MODEL=medium
export MAX_FILE_SIZE_MB=100
export STREAMLIT_PORT=80
```

## 📚 Key Files to Understand

1. **`engine.py`** - Start here, main orchestrator
2. **`config.py`** - All settings and model configurations
3. **`knowledge_base/gdpr/handler.py`** - Example framework implementation
4. **`utils/regulation_handler_base.py`** - Base class for frameworks
5. **`ui/app.py`** - Main web interface

## 🎯 Common Tasks

### Adding a New Model

```python
# In config.py
MODELS["your_model"] = {
    "name": "your-ollama-model:latest",
    "temperature": 0.1,
    "description": "Your custom model"
}
```

### Adding New File Types

```python
# In utils/document_processor.py, modify _extract_text()
def _extract_text(self, file_path):
    ext = file_path.suffix.lower()
    if ext == '.your_format':
        return self._read_your_format(file_path)
    # ... existing code
```

### Changing UI Layout

```python
# In ui/app.py, modify the main() function
# Or create new components in ui/components/
```

### Adding Export Formats

```python
# In ui/ui_utils/export_handler.py
# Add new export functions and buttons
```

This guide focuses on practical usage - understanding the system and extending it for real use cases. The best "test" is simply running the application and seeing if it works as expected!
