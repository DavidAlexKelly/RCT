# config/prompts/base_prompts.py

"""
Base regulation-agnostic prompt templates.
"""

# Generic compliance analysis prompt
ANALYZE_COMPLIANCE_PROMPT = """
You are a regulatory compliance analyzer. Analyze this text for compliance issues with the provided regulations.

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
1. Focus on the MOST SIGNIFICANT compliance issues (2-3 issues maximum)
2. Only identify clear violations with strong evidence in the text
3. Provide specific regulation references when possible
4. Include direct quotes from the text as evidence
5. Rate your confidence in each finding (High/Medium/Low)

TASK:
List the most important compliance issues in this section, with:
- Clear description of the issue
- The specific regulation it violates
- Confidence level (High/Medium/Low)
- Explanation of why this is a compliance concern
- Direct quote from the text showing the violation

Return as JSON:
{{
  "issues": [
    {{
      "issue": "Description of the compliance issue",
      "regulation": "Regulation reference",
      "confidence": "High/Medium/Low",
      "explanation": "Why this violates the regulation",
      "citation": "Direct quote from text showing the violation"
    }}
  ],
  "topic_tags": ["data_processing", "retention", "sharing", "etc"]
}}

IMPORTANT: Focus on QUALITY over QUANTITY. It is better to identify 1-2 significant issues with strong evidence than many minor or speculative issues.
"""

# Generic contradiction analysis prompt
CONTRADICTION_ANALYSIS_PROMPT = """
Analyze these compliance findings and identify contradictions or inconsistencies across document sections.

Look for:
1. CONTRADICTIONS: Where different sections have contradictory statements
   Example: One section says data is stored indefinitely but another mentions a retention period

2. UNRESOLVED ISSUES: Where one section raises an issue that another section should address but doesn't
   Example: Section A describes collecting data but no section mentions safeguards

3. IMPLEMENTATION GAPS: Where a promised measure isn't properly implemented
   Example: Section A promises withdrawal options but no section describes how this works

4. SCOPE INCONSISTENCIES: Where the scope of a policy varies
   Example: One section applies a policy to "all data" but another limits it

ISSUES FOUND:
{issues}

Identify contradictions and format your answer as a JSON array:
[
  {{
    "issue": "Description of contradiction",
    "section": "Sections involved",
    "confidence": "High/Medium/Low",
    "explanation": "Why this is a problem",
    "finding_type": "contradiction"
  }}
]

Return [] if no contradictions found.
"""