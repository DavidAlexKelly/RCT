"""
Example Framework Regulation Handler

This is a complete example showing how to create a framework handler.
Use this as a template for creating your own regulatory frameworks.

This example uses "House Rules" as a fun, relatable theme that everyone
can understand, while demonstrating all the same technical concepts
as complex legal frameworks.

Key components:
1. Load classification rules from classification.yaml
2. Implement framework-specific logic
3. Create AI prompts tailored to your regulation
4. Map violations to specific regulation articles
"""

import yaml
from typing import Dict, Any, List
from pathlib import Path

# Import base handler using absolute import
from utils.regulation_handler_base import RegulationHandlerBase

class RegulationHandler(RegulationHandlerBase):
    """House Rules handler - demonstrates best practices using relatable examples."""
    
    def __init__(self, debug=False):
        """Initialize the handler and load framework configuration."""
        super().__init__(debug)
        self.name = "House Rules"
        self.framework_dir = Path(__file__).parent
        
        # Load regulated topics from classification file
        try:
            with open(self.framework_dir / "classification.yaml", 'r') as f:
                self.classification = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Classification file not found: {self.framework_dir / 'classification.yaml'}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in classification file: {e}")
        
        self.regulated_topics = self.classification.get('regulated_topics', {})
        self.analysis_threshold = self.classification.get('analysis_threshold', 2)
        
        if not self.regulated_topics:
            raise ValueError("No regulated topics found in classification file")
        
        if self.debug:
            print(f"House Rules Handler: Loaded {len(self.regulated_topics)} topic categories")
            print(f"Analysis threshold: {self.analysis_threshold}")
    
    def _infer_regulation_from_issue(self, issue: str) -> str:
        """
        Map violation descriptions to specific house rules.
        
        This method takes an issue description and returns the most relevant
        house rule. This shows how to map violations to regulations in any domain.
        """
        issue_lower = issue.lower()
        
        # CUSTOMIZE THESE PATTERNS for your framework
        # Map keywords in violations to specific rules
        patterns = {
            # Cleaning-related violations
            "dishes": "Rule 1.1 - Kitchen and Cooking Areas",
            "dirty": "Rule 1.1 - Kitchen and Cooking Areas", 
            "mess": "Rule 1.2 - Common Areas and Living Spaces",
            "clean": "Rule 1.3 - Bathroom Cleanliness and Etiquette",
            "trash": "Rule 5.2 - Trash and Recycling Management",
            "chore": "Rule 5.1 - Chores and Cleaning Schedule",
            
            # Noise-related violations
            "loud": "Rule 2.1 - Noise and Quiet Hours",
            "music": "Rule 2.2 - Music and Entertainment Systems",
            "quiet": "Rule 2.1 - Noise and Quiet Hours",
            "noise": "Rule 2.1 - Noise and Quiet Hours",
            "phone": "Rule 2.3 - Phone Calls and Video Chats",
            
            # Guest-related violations
            "guest": "Rule 3.1 - Guest and Visitor Policies",
            "party": "Rule 3.2 - Parties and Social Gatherings",
            "overnight": "Rule 3.1 - Guest and Visitor Policies",
            "visitor": "Rule 3.1 - Guest and Visitor Policies",
            
            # Money-related violations
            "bill": "Rule 4.1 - Bills and Financial Responsibilities",
            "rent": "Rule 4.1 - Bills and Financial Responsibilities",
            "money": "Rule 4.1 - Bills and Financial Responsibilities",
            "expense": "Rule 4.2 - Shared Supplies and Household Items",
            "pay": "Rule 4.1 - Bills and Financial Responsibilities",
            
            # Property violations
            "food": "Rule 4.3 - Personal Property and Belongings",
            "borrow": "Rule 4.3 - Personal Property and Belongings",
            "take": "Rule 4.3 - Personal Property and Belongings",
            "steal": "Rule 4.3 - Personal Property and Belongings",
            
            # Communication violations
            "rude": "Rule 6.2 - Respect and Consideration Guidelines",
            "argument": "Rule 6.1 - Communication and Conflict Resolution",
            "meeting": "Rule 6.3 - House Meeting and Decision Making",
            "respect": "Rule 6.2 - Respect and Consideration Guidelines",
            
            # Security violations
            "lock": "Rule 3.3 - Security and Key Management",
            "key": "Rule 3.3 - Security and Key Management",
            "door": "Rule 3.3 - Security and Key Management",
            
            # Add more patterns for your specific domain
        }
        
        # Find the first matching pattern
        for keyword, rule in patterns.items():
            if keyword in issue_lower:
                return rule
        
        # Default fallback if no specific pattern matches
        return "Relevant House Rule"
    
    def create_prompt(self, text: str, section: str, regulations: List[Dict[str, Any]]) -> str:
        """
        Create framework-specific analysis prompt.
        
        This is the core of your framework - it tells the AI what to look for
        and how to analyse the document text against your specific rules.
        
        This example uses house rules to make it relatable and easy to understand.
        """
        
        # Format regulations for the prompt
        formatted_regs = []
        for reg in regulations:
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", "Unknown")
            # Truncate very long regulations to fit in prompt
            if len(reg_text) > 400:
                reg_text = reg_text[:400] + "..."
            formatted_regs.append(f"{reg_id}:\n{reg_text}")
        
        regulations_text = "\n\n".join(formatted_regs)
        
        # CUSTOMIZE THIS PROMPT for your framework
        # Include specific violation patterns that your rules care about
        return f"""You are a {self.name} expert analysing a roommate agreement or house policy document. Find clear violations of reasonable house rules.

DOCUMENT SECTION: {section}

DOCUMENT TEXT:
{text}

RELEVANT HOUSE RULES:
{regulations_text}

INSTRUCTIONS:
Find clear house rule violations in the document text. Look for these violation patterns:

CLEANING AND CHORE VIOLATIONS (Rules 1.1-1.3, 5.1-5.3):
- No cleaning requirements: "roommates not required to clean", "no cleaning duties"
- Unfair chore distribution: "one person does all cleaning", "no shared responsibilities"
- Poor hygiene standards: "dishes can sit for weeks", "bathroom never needs cleaning"
- No consequences for mess: "leave messes indefinitely", "no cleanup required"

NOISE VIOLATIONS (Rules 2.1-2.3):
- No quiet hours: "no noise restrictions", "loud music anytime", "24/7 parties allowed"
- Unreasonable noise levels: "maximum volume always", "ignore neighbors completely"
- No consideration: "disturb others freely", "wake people up intentionally"

GUEST POLICY VIOLATIONS (Rules 3.1-3.3):
- Unlimited guests: "invite anyone anytime", "no guest limits", "permanent guests allowed"
- No advance notice: "surprise overnight guests", "no warning required"
- Guest rule exemptions: "guests don't follow house rules", "visitors do whatever they want"
- Security risks: "give keys to anyone", "prop doors open", "no security measures"

FINANCIAL VIOLATIONS (Rules 4.1-4.3):
- Unfair bill splitting: "some roommates pay nothing", "unequal expense sharing"
- No payment deadlines: "pay bills whenever", "no consequences for late payment"
- Taking others' property: "use anyone's food", "borrow without asking", "keep borrowed items"
- No shared responsibility: "one person pays for everything"

COMMUNICATION VIOLATIONS (Rules 6.1-6.3):
- No conflict resolution: "ignore all problems", "no discussion allowed"
- Disrespectful behavior: "insult roommates freely", "discriminate against others"
- No house meetings: "never discuss house issues", "decisions made by one person"
- Poor communication: "leave passive aggressive notes", "never talk directly"

RESPONSE FORMAT (CRITICAL):
Respond ONLY in this JSON format with no additional text:

{{
    "violations": [
        {{
            "issue": "Clear description of the house rule violation found",
            "regulation": "House rule reference",
            "quote": "Relevant text from the document showing the issue"
        }}
    ]
}}

GUIDELINES:
- Focus on finding rules that would make living together difficult or unfair
- Look for policies that are unreasonable or inconsiderate to roommates
- Use common sense - what would cause problems in a shared living situation?
- Quote should be representative of the issue (doesn't need to be word-perfect)
- If you find violations, include them even if quotes aren't exact matches
- Only skip violations if the rules seem reasonable and fair

If no violations found: {{"violations": []}}

Remember: Response must start with {{ and end with }}. No other text."""
    
    # OPTIONAL: Override other methods for framework-specific behavior
    
    def calculate_risk_score(self, text: str) -> float:
        """
        Calculate risk score for a text section.
        
        You can override this if you want custom risk calculation logic.
        The default implementation counts topic categories which works well.
        """
        # Use the default implementation from base class
        # It counts how many regulated topic categories are found
        return super().calculate_risk_score(text)
    
    def should_analyse(self, text: str) -> bool:
        """
        Determine if a text section should be analysed.
        
        You can override this for custom filtering logic.
        The default checks if topic count >= threshold which works well.
        """
        # Use the default implementation from base class
        # It compares topic count to analysis_threshold
        return super().should_analyse(text)
    
    def parse_response(self, response: str, document_text: str = "") -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract violations.
        
        You can override this if you need custom parsing logic.
        The default implementation handles JSON parsing with fallbacks.
        """
        # Use the default implementation from base class
        # It handles JSON parsing, validation, and cleanup
        return super().parse_response(response, document_text)

# CUSTOMIZATION CHECKLIST for creating your own framework:
#
# 1. Change self.name to your framework name (e.g., "Workplace Rules", "Game Rules")
# 2. Update _infer_regulation_from_issue() patterns for your domain
# 3. Customize create_prompt() with your specific violation patterns
# 4. Update articles.txt with your regulation/rule text
# 5. Update context.yaml with your framework metadata
# 6. Update classification.yaml with your domain keywords
# 7. Test with sample documents
# 8. Set example_only: false in context.yaml to make it appear in UI
#
# EXAMPLES FOR OTHER DOMAINS:
#
# WORKPLACE RULES:
# - Dress code violations, attendance issues, harassment
# - Keywords: "employee", "manager", "dress", "uniform", "tardiness"
#
# SCHOOL RULES:
# - Academic honesty, attendance, behavior violations
# - Keywords: "student", "homework", "cheat", "attendance", "discipline"
#
# GAME RULES:
# - Cheating, unfair play, rule violations
# - Keywords: "player", "cheat", "fair", "turn", "score", "rules"
#
# RESTAURANT RULES:
# - Food safety, hygiene, service standards
# - Keywords: "food", "hygiene", "clean", "customer", "service"
#
# TESTING YOUR FRAMEWORK:
#
# 1. Create a test document with obvious violations:
#    "Roommates can leave dirty dishes for months and play loud music at 3 AM"
# 2. Run: python launch.py
# 3. Upload your test document
# 4. Select your framework from dropdown
# 5. Check if violations are found and make sense
# 6. Adjust keywords/patterns if needed
#
# WHY HOUSE RULES WORK AS AN EXAMPLE:
#
# - Everyone understands living with roommates
# - Rule violations are obvious (dirty dishes, loud noise, etc.)
# - Shows same technical concepts without legal complexity  
# - Easy to see when something violates common sense
# - Fun and engaging while still educational
# - Demonstrates compliance analysis in familiar context
#
# The same patterns work for any domain - just change the keywords and rules!