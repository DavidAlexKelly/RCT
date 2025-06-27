# Regulatory Compliance Analyzer

> AI-powered document analysis tool for regulatory compliance checking across multiple frameworks (GDPR, HIPAA, CCPA, etc.)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai) for local LLM execution

### Installation

```bash
# 1. Clone and install dependencies
git clone <repository-url>
cd compliance-analyzer
pip install -r requirements.txt

# 2. Install and start Ollama
# Visit https://ollama.ai for installation instructions
ollama pull llama3:8b  # Download the default model

# 3. Test the installation
python compliance_analyzer.py models  # Show available models
python compliance_analyzer.py frameworks  # Show available regulations
```

### Basic Usage

**Command Line:**

```bash
# Analyze a document with default settings
python compliance_analyzer.py analyze --file document.pdf

# Use different presets and options
python compliance_analyzer.py analyze \
  --file contract.pdf \
  --regulation-framework gdpr \
  --preset accuracy \
  --chunking-method smart \
  --export report.txt
```

**Web Interface:**

```bash
# Launch the web UI
cd ui
python launch.py
# or
streamlit run app.py

# Open http://localhost:8501 in your browser
```

## 📋 Features

- **Multi-Format Support**: PDF, TXT, Markdown documents
- **Smart Document Processing**: Intelligent chunking that respects document structure
- **Progressive Analysis**: Focuses on high-risk sections to save time and cost
- **Multiple Frameworks**: GDPR included, extensible to other regulations
- **Flexible Interfaces**: Both command-line and web-based interfaces
- **Detailed Reporting**: Comprehensive reports with citations and explanations

## ⚙️ Configuration

### Performance Presets

- **`balanced`** _(default)_: Good speed and accuracy for most documents
- **`speed`**: Fastest analysis, suitable for quick scans
- **`accuracy`**: Best quality results, slower processing
- **`comprehensive`**: Analyzes every section thoroughly

### Document Chunking Methods

- **`smart`** _(recommended)_: Automatically detects document structure
- **`paragraph`**: Groups content by paragraphs
- **`sentence`**: Fine-grained sentence-level grouping
- **`simple`**: Basic character-based splitting

### Model Options

- **`small`**: llama3:8b - Fast, suitable for most analyses
- **`medium`**: llama3:70b-instruct-q4_0 - Better accuracy, requires more RAM
- **`large`**: llama3:70b-instruct - Highest accuracy, requires 32GB+ RAM

## 📁 Project Structure

```
compliance_analyzer/
├── compliance_analyzer.py      # Main CLI entry point
├── config.py                   # Configuration system
├── ui/                         # Web interface
│   ├── app.py                  # Streamlit main app
│   ├── components/             # UI components
│   ├── ui_utils/              # UI utilities
│   └── launch.py              # Cross-platform launcher
├── utils/                      # Core processing modules
│   ├── document_processor.py  # Document chunking & processing
│   ├── llm_handler.py         # LLM integration
│   ├── embeddings_handler.py  # Vector embeddings & RAG
│   ├── progressive_analyzer.py # Risk-based analysis
│   └── report_generator.py    # Report generation
├── knowledge_base/            # Regulation frameworks
│   └── gdpr/                  # GDPR compliance rules
│       ├── articles.txt       # Regulation articles
│       ├── context.txt        # Background information
│       ├── common_patterns.txt # Violation patterns
│       └── handler.py         # Framework-specific logic
└── sample_docs/              # Example documents for testing
```

## 🔧 Advanced Usage

### Custom Analysis

```bash
# Test different chunking strategies
python compliance_analyzer.py test-chunking --file document.pdf --method smart --size 1000

# View current configuration
python compliance_analyzer.py config

# Apply performance presets
python compliance_analyzer.py preset accuracy
```

### Adding New Regulation Frameworks

1. Create directory: `knowledge_base/new_framework/`
2. Add required files:
   - `articles.txt` - Regulation text for analysis
   - `context.txt` - Background information (optional)
   - `common_patterns.txt` - Common violation patterns (optional)
   - `handler.py` - Custom processing logic (optional)
3. Update `knowledge_base/regulation_index.json`

### Programmatic Usage

```python
from utils.document_processor import DocumentProcessor
from utils.llm_handler import LLMHandler
from config import apply_preset

# Apply configuration preset
config = apply_preset('balanced')

# Process document
processor = DocumentProcessor()
doc_info = processor.process_document('document.pdf')

# Analyze with LLM
llm = LLMHandler()
results = llm.analyze_compliance(doc_info['chunks'])
```

## 🐛 Troubleshooting

### Common Issues

**"Ollama not found"**

- Install Ollama from https://ollama.ai
- Ensure `ollama` command is in your PATH
- Start Ollama service: `ollama serve`

**"No models available"**

- Pull a model: `ollama pull llama3:8b`
- List models: `ollama list`

**"Knowledge base not found"**

- Ensure `knowledge_base/gdpr/articles.txt` exists
- Check file permissions
- Validate framework: `python compliance_analyzer.py validate gdpr`

**Memory issues with large models**

- Use smaller model: `--model small`
- Reduce chunk size in config
- Use `speed` preset for lower memory usage

### Performance Tuning

**For faster analysis:**

- Use `--preset speed`
- Use `--model small`
- Use `--chunking-method simple`

**For better accuracy:**

- Use `--preset accuracy`
- Use `--model large` (if you have enough RAM)
- Use `--chunking-method smart`

## 📊 Output Formats

### JSON Output (CLI)

```json
{
  "document": "privacy_policy.pdf",
  "regulation_framework": "gdpr",
  "findings": [
    {
      "issue": "Data stored indefinitely without justification",
      "regulation": "Article 5(1)(e)",
      "citation": "\"customer data retained permanently\"",
      "section": "Data Retention Policy"
    }
  ],
  "summary": "Found 3 potential compliance issues"
}
```

### Detailed Reports

- Human-readable text format
- Section-by-section analysis
- Issue summaries and recommendations
- Export via `--export report.txt`

### Web Dashboard

- Interactive visualizations
- Real-time progress tracking
- Multiple export formats
- Shareable results

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Validate knowledge base
python validate_knowledge_base.py gdpr
```

### Code Style

- Use type hints for all public functions
- Follow PEP 8 naming conventions
- Add docstrings to classes and methods
- Keep functions under 50 lines when possible

## 📄 License

[Add your license information here]

## 🆘 Support

- **Issues**: Create GitHub issues for bugs and feature requests
- **Documentation**: Check the `/docs` folder for detailed guides
- **Configuration**: Run `python compliance_analyzer.py config` for current settings

---

**Pro Tip**: Start with the `balanced` preset and `smart` chunking for most documents. Only switch to other options if you need specific performance characteristics.
