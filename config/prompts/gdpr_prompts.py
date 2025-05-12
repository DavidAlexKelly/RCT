# config/prompts/gdpr_prompts.py

"""
GDPR-specific prompt templates with enhanced violation detection capabilities.
"""

from .base_prompts import ANALYZE_COMPLIANCE_PROMPT, CONTRADICTION_ANALYSIS_PROMPT

# Enhanced GDPR-specific compliance analysis prompt
GDPR_ANALYZE_COMPLIANCE_PROMPT = """
You are a GDPR compliance auditor with expertise in identifying non-compliant practices. Your task is to find ALL potential GDPR violations in this text, being thorough and attentive to details.

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

VIOLATION PATTERNS TO LOOK FOR:

1. Indefinite Storage: Look for phrases like "indefinitely", "until no longer needed", "as long as necessary", "permanent storage", "no deletion policy", "retain all data", "stored for extended periods". These violate Article 5(1)(e).

2. Forced Consent: Look for phrases like "required to accept", "must agree", "mandatory consent", "no option to decline", "consent required to use", "no alternative", "can only use if you accept". These violate Article 7(4).

3. No Withdrawal Mechanism: Look for phrases like "irrevocable consent", "absence of withdrawal details", "cannot be withdrawn", "permanent authorization", "no opt-out", "difficult to cancel". These violate Article 7(3).

4. Excessive Data Collection: Look for phrases like "all available information", "comprehensive profile", "full history", "maximum data collection", "collect everything", "complete user data", "entire browsing history". These violate Article 5(1)(c).

5. Unclear Purpose: Look for phrases like "various purposes", "future use", "as needed", "multiple use cases", "any purpose", "unspecified business needs", "potential applications". These violate Article 5(1)(b).

6. Automatic Opt-In: Look for phrases like "by default", "pre-selected", "automatically enrolled", "opt-out system", "automatically enabled", "auto-checked boxes". These violate Article 4(11) and Article 7(1).

7. Bundled Consent: Look for phrases like "consent to all", "agreement covers", "blanket consent", "one consent for all", "full package consent", "all-inclusive consent". These violate Article 7(2).

8. Security-Performance Tradeoff: Look for phrases like "balanced against performance", "cost-effective security", "due to budget constraints", "security features may be deferred", "minimal protection". These violate Article 5(1)(f) and Article 32.

9. Missing Data Subject Rights: Look for phrases suggesting limitations on rights like "no access right", "deletion requests", "processed when resources permit", "exempting derived analytics", "no rectification", "no portability", "restricted rights". These violate Articles 15-20.

10. Automated Decision Making: Look for phrases like "automated decisions", "without human oversight", "AI-driven", "automated qualification", "algorithm determines", "without human intervention". These violate Article 22.

11. Vague Information: Look for unclear, ambiguous or complex explanations such as "legal terminology", "complex language", "long privacy policy", "buried in terms", "unclear explanation". These violate Article 12(1).

12. Special Category Processing: Look for processing sensitive data without explicit safeguards, including "biometric data", "health information", "ethnic", "sexual orientation", "political views", "religious beliefs". These violate Article 9(1) and 9(2)(a).

13. Inadequate Security: Look for insufficient security measures like "no encryption", "basic security", "standard password", "no security audits", "minimal protection". These violate Article 5(1)(f) and Article 32.

14. Cross-Border Transfers: Look for transferring data internationally without proper protection, such as "global storage", "international transfers", "cloud hosting", "worldwide access". These violate Article 44.

15. Deliberate Non-Compliance: Look for language suggesting intentional disregard for compliance like "prioritize capabilities over compliance", "regulatory adaptation handled after", "maximize data value", "compliance details may require refinement". These violate Article 5(2), Article 24, and Article 25.

ANALYSIS INSTRUCTIONS:
1. READ THE TEXT CAREFULLY and identify ANY phrases or statements that match the violation patterns above.
2. For EACH violation found, provide:
   - Clear description of the issue
   - The specific GDPR article violated
   - Confidence level (High/Medium/Low) based on how explicit the violation is
   - Explanation of why it violates GDPR
   - EXACT quote from the text showing the violation

3. BE THOROUGH - even subtle or implied violations should be identified
4. PRIORITIZE FINDING ISSUES - err on the side of identifying potential issues rather than missing them
5. Look beyond just explicit pattern matches - identify issues that have the same meaning but different wording

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

If no issues are found, return an empty issues array: {{ "issues": [] }}
"""

# Enhanced GDPR-specific contradiction analysis prompt
GDPR_CONTRADICTION_ANALYSIS_PROMPT = """
Analyze these GDPR compliance findings and identify contradictions or inconsistencies across document sections that would create compliance risks.

Look specifically for:

1. CONTRADICTORY RETENTION POLICIES: Where different sections have inconsistent data retention statements
   Example: One section says data is stored indefinitely but another mentions a specific retention period
   Violation: Article 5(1)(e) - Storage limitation principle

2. INCONSISTENT CONSENT MECHANISMS: Where consent handling varies across document sections
   Example: One section describes consent as optional while another shows it's mandatory
   Violation: Article 7 - Conditions for consent

3. CONFLICTING RIGHTS IMPLEMENTATION: Where data subject rights are inconsistently implemented
   Example: One section promises data deletion but another section exempts certain data
   Violation: Articles 15-22 - Data subject rights

4. SECURITY APPROACH CONTRADICTIONS: Where security commitments vary across sections
   Example: One section promises high security while another mentions trade-offs with performance
   Violation: Article 32 - Security of processing

5. PURPOSE LIMITATION INCONSISTENCIES: Where stated purposes for data collection conflict
   Example: One section limits purpose to specific uses while another allows unspecified future uses
   Violation: Article 5(1)(b) - Purpose limitation

6. DATA MINIMIZATION CONFLICTS: Where different sections suggest different approaches to data volume
   Example: One section mentions collecting only necessary data while another describes comprehensive collection
   Violation: Article 5(1)(c) - Data minimization

7. TRANSPARENCY CONTRADICTIONS: Where explanations of processing differ across the document
   Example: One section provides clear explanation while another is vague about the same process
   Violation: Article 12 - Transparent information

ISSUES FOUND:
{issues}

Identify ALL contradictions and inconsistencies, focusing on those that create GDPR compliance risks. Provide your response as a JSON array:
[
  {{
    "issue": "Detailed description of the contradiction",
    "section": "Specific sections involved (e.g., 'Section 2.1 vs Section 6.3')",
    "confidence": "High/Medium/Low",
    "explanation": "Thorough explanation of why this contradiction creates a GDPR compliance problem",
    "regulation": "The specific GDPR article(s) affected by this contradiction",
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