# config/prompts/ccpa_prompts.py

"""
CCPA/CPRA-specific prompt templates.
"""

from .base_prompts import ANALYZE_COMPLIANCE_PROMPT, CONTRADICTION_ANALYSIS_PROMPT

# CCPA-specific compliance analysis prompt
CCPA_ANALYZE_COMPLIANCE_PROMPT = """
You are a California privacy law compliance analyzer. Analyze this section for compliance with CCPA/CPRA requirements.

SECTION: {section}
TEXT: {text}

APPLICABLE REGULATIONS:
{regulations}

CONTENT INDICATORS:
- Contains personal information references: {has_personal_data}
- Contains collection references: {has_data_collection}
- Contains sharing references: {has_data_sharing}
- Contains retention references: {has_retention}
- Contains agreement/consent references: {has_consent}
- Contains rights references: {has_rights}
- Contains automated decision references: {has_automated}
- Contains sensitive data references: {has_sensitive}

ANALYSIS GUIDELINES:
1. Focus on California consumer rights (right to know, delete, correct, limit use of sensitive PI)
2. Check for proper notice at collection requirements
3. Evaluate opt-out mechanisms for sale/sharing of personal information
4. Look for data retention policies and purpose limitations
5. Identify proper handling of sensitive personal information
6. Check for compliant privacy policy disclosures

TASK:
List the 2-3 most important CCPA/CPRA compliance issues in this section, with:
- Clear description of the issue
- The specific CCPA/CPRA provision being violated
- Confidence level (High/Medium/Low)
- Explanation of why this violates California privacy law
- Direct quote from the text showing the violation

Return as JSON:
{{
  "issues": [
    {{
      "issue": "Description of the compliance issue",
      "regulation": "Regulation reference (e.g., 'CCPA § 1798.100')",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation",
      "citation": "Direct quote from text showing the violation"
    }}
  ],
  "topic_tags": ["notice", "opt_out", "consumer_rights", "etc"]
}}

IMPORTANT: Focus on QUALITY over QUANTITY. It is better to identify 1-2 significant issues with strong evidence than many minor or speculative issues.
"""

# CCPA-specific contradiction analysis prompt
CCPA_CONTRADICTION_ANALYSIS_PROMPT = """
Analyze these California privacy law compliance findings and identify contradictions or inconsistencies across document sections.

Look for:
1. CONTRADICTIONS in consumer rights implementation
2. INCONSISTENCIES in sale/sharing opt-out mechanisms
3. GAPS in notice at collection requirements
4. CONTRADICTORY statements about data retention periods
5. INCONSISTENT handling of sensitive personal information

ISSUES FOUND:
{issues}

Identify contradictions and format your answer as a JSON array:
[
  {{
    "issue": "Description of contradiction",
    "section": "Sections involved",
    "confidence": "High/Medium/Low",
    "explanation": "Why this is a California privacy law compliance problem",
    "finding_type": "contradiction"
  }}
]

Return [] if no contradictions found.
"""

def get_analyze_compliance_prompt():
    """Return the CCPA-specific analysis prompt."""
    return CCPA_ANALYZE_COMPLIANCE_PROMPT

def get_contradiction_analysis_prompt():
    """Return the CCPA-specific contradiction analysis prompt."""
    return CCPA_CONTRADICTION_ANALYSIS_PROMPT