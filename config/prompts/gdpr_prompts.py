# config/prompts/gdpr_prompts.py

"""
GDPR-specific prompt templates.
"""

from .base_prompts import ANALYZE_COMPLIANCE_PROMPT, CONTRADICTION_ANALYSIS_PROMPT

# GDPR-specific compliance analysis prompt
GDPR_ANALYZE_COMPLIANCE_PROMPT = """
You are a GDPR compliance analyzer. Analyze this section for compliance with European data protection regulations.

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
1. Focus on GDPR core principles: lawfulness, fairness, transparency, purpose limitation, data minimization, accuracy, storage limitation, integrity, confidentiality, and accountability
2. Identify issues related to consent mechanisms (must be freely given, specific, informed, unambiguous)
3. Check for proper implementation of data subject rights (access, rectification, erasure, etc.)
4. Look for proper security measures and data protection safeguards
5. Evaluate data retention policies against necessity principle
6. Identify any processing of special categories of data without appropriate safeguards

TASK:
List the 2-3 most important GDPR compliance issues in this section, with:
- Clear description of the issue
- The specific GDPR article being violated
- Confidence level (High/Medium/Low)
- Explanation of why this violates GDPR
- Direct quote from the text showing the violation

Return as JSON:
{{
  "issues": [
    {{
      "issue": "Description of the compliance issue",
      "regulation": "Article reference (e.g., 'Article 5(1)(e)')",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation",
      "citation": "Direct quote from text showing the violation"
    }}
  ],
  "topic_tags": ["data_retention", "consent", "etc"]
}}

IMPORTANT: Focus on QUALITY over QUANTITY. It is better to identify 1-2 significant issues with strong evidence than many minor or speculative issues.
"""

# GDPR-specific contradiction analysis prompt
GDPR_CONTRADICTION_ANALYSIS_PROMPT = """
Analyze these GDPR compliance findings and identify contradictions or inconsistencies across document sections.

Look for:
1. CONTRADICTIONS in data retention policies (e.g., indefinite storage vs. defined retention periods)
2. INCONSISTENCIES in consent mechanisms across sections
3. GAPS in implementing data subject rights (e.g., right to erasure mentioned but no implementation)
4. INCONSISTENT security measures or data protection approaches
5. CONTRADICTORY statements about data sharing or third-party transfers

ISSUES FOUND:
{issues}

Identify contradictions and format your answer as a JSON array:
[
  {{
    "issue": "Description of contradiction",
    "section": "Sections involved",
    "confidence": "High/Medium/Low",
    "explanation": "Why this is a GDPR compliance problem",
    "finding_type": "contradiction"
  }}
]

Return [] if no contradictions found.
"""

def get_analyze_compliance_prompt():
    """Return the GDPR-specific analysis prompt."""
    return GDPR_ANALYZE_COMPLIANCE_PROMPT

def get_contradiction_analysis_prompt():
    """Return the GDPR-specific contradiction analysis prompt."""
    return GDPR_CONTRADICTION_ANALYSIS_PROMPT