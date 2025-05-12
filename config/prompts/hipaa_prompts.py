# config/prompts/hipaa_prompts.py

"""
HIPAA-specific prompt templates.
"""

from .base_prompts import ANALYZE_COMPLIANCE_PROMPT, CONTRADICTION_ANALYSIS_PROMPT

# HIPAA-specific compliance analysis prompt
HIPAA_ANALYZE_COMPLIANCE_PROMPT = """
You are a HIPAA compliance analyzer. Analyze this section for compliance with US healthcare privacy and security regulations.

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
1. Focus on HIPAA Privacy, Security, and Breach Notification Rules
2. Identify issues related to PHI protection and safeguards
3. Check for proper authorization mechanisms 
4. Look for appropriate security measures for PHI
5. Evaluate data retention and disposal policies
6. Identify issues with business associate relationships

TASK:
List the 2-3 most important HIPAA compliance issues in this section, with:
- Clear description of the issue
- The specific HIPAA provision being violated
- Confidence level (High/Medium/Low)
- Explanation of why this violates HIPAA
- Direct quote from the text showing the violation

Return as JSON:
{{
  "issues": [
    {{
      "issue": "Description of the compliance issue",
      "regulation": "Regulation reference (e.g., 'HIPAA Privacy Rule § 164.502')",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation",
      "citation": "Direct quote from text showing the violation"
    }}
  ],
  "topic_tags": ["phi_protection", "authorization", "security_safeguards", "etc"]
}}

IMPORTANT: Focus on QUALITY over QUANTITY. It is better to identify 1-2 significant issues with strong evidence than many minor or speculative issues.
"""

# HIPAA-specific contradiction analysis prompt
HIPAA_CONTRADICTION_ANALYSIS_PROMPT = """
Analyze these HIPAA compliance findings and identify contradictions or inconsistencies across document sections.

Look for:
1. CONTRADICTIONS in PHI handling practices
2. INCONSISTENCIES in security safeguards across sections
3. GAPS in authorization and consent mechanisms
4. CONTRADICTORY statements about data retention and disposal
5. INCONSISTENT business associate policies

ISSUES FOUND:
{issues}

Identify contradictions and format your answer as a JSON array:
[
  {{
    "issue": "Description of contradiction",
    "section": "Sections involved",
    "confidence": "High/Medium/Low",
    "explanation": "Why this is a HIPAA compliance problem",
    "finding_type": "contradiction"
  }}
]

Return [] if no contradictions found.
"""

def get_analyze_compliance_prompt():
    """Return the HIPAA-specific analysis prompt."""
    return HIPAA_ANALYZE_COMPLIANCE_PROMPT

def get_contradiction_analysis_prompt():
    """Return the HIPAA-specific contradiction analysis prompt."""
    return HIPAA_CONTRADICTION_ANALYSIS_PROMPT