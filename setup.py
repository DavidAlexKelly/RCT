"""
Setup script for Regulatory Compliance Analyzer

This script helps with package installation and dependency management.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith('#') and not line.startswith('-')
        ]

setup(
    name="regulatory-compliance-analyzer",
    version="1.0.0",
    description="AI-powered document analysis tool for regulatory compliance checking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    # Author information
    author="Compliance Analyzer Team",
    author_email="team@compliance-analyzer.com",
    url="https://github.com/your-org/compliance-analyzer",
    
    # Package discovery
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    include_package_data=True,
    
    # Dependencies
    install_requires=requirements,
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0", 
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0"
        ],
        "gpu": [
            "torch>=2.0.0",
            "faiss-gpu>=1.7.4"
        ],
        "ui": [
            "streamlit>=1.28.0",
            "plotly>=5.17.0"
        ]
    },
    
    # Entry points for command line
    entry_points={
        "console_scripts": [
            "compliance-analyzer=compliance_analyzer:cli",
        ],
    },
    
    # Python version requirement  
    python_requires=">=3.8",
    
    # Package data
    package_data={
        "": [
            "knowledge_base/**/*.txt",
            "knowledge_base/**/*.json", 
            "knowledge_base/**/*.py",
            "ui/**/*.py",
            "sample_docs/**/*"
        ]
    },
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Legal Industry",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Office Suites",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    
    # Keywords for discoverability
    keywords="compliance, regulation, gdpr, ai, nlp, document-analysis, legal-tech",
    
    # Project URLs
    project_urls={
        "Documentation": "https://github.com/your-org/compliance-analyzer/docs",
        "Bug Reports": "https://github.com/your-org/compliance-analyzer/issues",
        "Source": "https://github.com/your-org/compliance-analyzer",
    },
)