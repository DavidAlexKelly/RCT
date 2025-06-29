import os
import sys
import importlib.util
from typing import Dict, Any, List, Optional
from pathlib import Path

class PromptManager:
    """Prompt manager for independent regulation handlers."""
    
    def __init__(self, regulation_framework=None, regulation_context=None, regulation_patterns=None):
        """Initialize prompt manager."""
        
        assert regulation_framework, "regulation_framework required"
        
        self.regulation_framework = regulation_framework.strip()
        self.regulation_context = regulation_context or ""
        self.regulation_patterns = regulation_patterns or ""
        
        # Load regulation handler
        self.regulation_handler = self._load_regulation_handler(self.regulation_framework)
        assert self.regulation_handler, f"Failed to load handler for {self.regulation_framework}"
        
        # Validate handler has required methods
        required_methods = ['create_analysis_prompt', 'format_regulations', 'get_classification_terms']
        missing = [m for m in required_methods if not hasattr(self.regulation_handler, m)]
        assert not missing, f"Handler missing methods: {missing}"
    
    def _load_regulation_handler(self, regulation_framework: str):
        """Load independent regulation handler module."""
        
        # Construct paths
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        handler_path = os.path.join(script_dir, "knowledge_base", regulation_framework, "handler.py")
        
        assert os.path.exists(handler_path), f"Handler not found: {handler_path}"
        assert os.path.getsize(handler_path) > 0, f"Empty handler file: {handler_path}"
        
        try:
            # Import handler module
            module_name = f"knowledge_base.{regulation_framework}.handler"
            
            # Remove if already loaded to avoid conflicts
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            assert spec and spec.loader, f"Failed to create spec for {handler_path}"
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get handler class
            assert hasattr(module, 'RegulationHandler'), f"No RegulationHandler class in {handler_path}"
            
            handler_class = getattr(module, 'RegulationHandler')
            assert isinstance(handler_class, type), "RegulationHandler must be a class"
            
            # Initialize handler
            return handler_class(debug=False)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load handler for {regulation_framework}: {e}")
    
    def create_analysis_prompt(self, text: str, section: str, regulations: str, 
                             content_indicators: Optional[Dict] = None, 
                             potential_violations: Optional[List] = None,
                             risk_level: str = "unknown") -> str:
        """Create analysis prompt using handler-specific logic."""
        
        assert text and text.strip(), "Empty text"
        assert section, "Empty section"
        assert regulations, "Empty regulations"
        assert len(text) <= 50000, f"Text too long: {len(text)}"
        
        try:
            return self.regulation_handler.create_analysis_prompt(
                text, section, regulations, content_indicators,
                potential_violations, self.regulation_framework, risk_level
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create prompt: {e}")
    
    def format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """Format regulations using handler-specific logic."""
        
        assert regulations, "Empty regulations list"
        
        # Validate regulations
        for i, reg in enumerate(regulations):
            assert isinstance(reg, dict), f"Regulation {i+1} must be dict"
            assert reg.get("text", "").strip(), f"Regulation {i+1} missing text"
        
        try:
            # Check if handler has custom format_regulations method
            if hasattr(self.regulation_handler, 'format_regulations'):
                return self.regulation_handler.format_regulations(
                    regulations, self.regulation_context, self.regulation_patterns
                )
            else:
                # Fallback to basic formatting
                return self._basic_format_regulations(regulations)
        except Exception as e:
            raise RuntimeError(f"Failed to format regulations: {e}")
    
    def _basic_format_regulations(self, regulations: List[Dict[str, Any]]) -> str:
        """Basic regulation formatting fallback."""
        formatted_regs = []
        
        if self.regulation_context:
            formatted_regs.append(f"CONTEXT:\n{self.regulation_context[:500]}...")
        
        for i, reg in enumerate(regulations):
            reg_text = reg.get("text", "")
            reg_id = reg.get("id", f"Regulation {i+1}")
            
            # Truncate long texts
            if len(reg_text) > 300:
                reg_text = reg_text[:300] + "..."
            
            formatted_reg = f"{reg_id}:\n{reg_text}"
            formatted_regs.append(formatted_reg)
        
        return "\n\n".join(formatted_regs)
    
    def get_classification_terms(self, term_type: str) -> List[str]:
        """Get classification terms from handler."""
        
        assert term_type, "Empty term_type"
        
        valid_types = ["data_terms", "regulatory_keywords", "high_risk_patterns", "priority_keywords"]
        assert term_type in valid_types, f"Invalid term_type: {term_type}"
        
        try:
            terms = self.regulation_handler.get_classification_terms(term_type)
            assert isinstance(terms, list), f"Expected list, got {type(terms)}"
            
            # Filter valid terms
            valid_terms = [t for t in terms if t and isinstance(t, str) and t.strip()]
            assert valid_terms, f"No valid {term_type} found"
            
            return valid_terms
            
        except Exception as e:
            raise RuntimeError(f"Failed to get {term_type}: {e}")
    
    def parse_llm_response(self, response: str, document_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse LLM response using handler-specific logic."""
        
        try:
            # Check if handler has custom parse_llm_response method
            if hasattr(self.regulation_handler, 'parse_llm_response'):
                return self.regulation_handler.parse_llm_response(response, document_text)
            else:
                # Fallback to basic parsing
                return self._basic_parse_response(response)
        except Exception as e:
            raise RuntimeError(f"Failed to parse LLM response: {e}")
    
    def _basic_parse_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Basic response parsing fallback."""
        import json
        import re
        
        result = {"issues": []}
        
        try:
            # Extract JSON array
            start = response.find('[')
            if start == -1:
                return result
            
            bracket_count = 0
            end = -1
            
            for i in range(start, len(response)):
                if response[i] == '[':
                    bracket_count += 1
                elif response[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end = i
                        break
            
            if end == -1:
                return result
            
            array_text = response[start:end + 1]
            violations = json.loads(array_text)
            
            for violation in violations:
                if (isinstance(violation, list) and len(violation) >= 3 and 
                    len(str(violation[0]).strip()) > 5):
                    
                    result["issues"].append({
                        "issue": str(violation[0]).strip(),
                        "regulation": str(violation[1]).strip(),
                        "citation": f'"{str(violation[2]).strip()}"'
                    })
            
        except (json.JSONDecodeError, Exception):
            # Regex fallback
            patterns = [
                r'\[\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\s*\]',
                r"\[\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\s*\]"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                for match in matches:
                    if len(match) == 3 and len(match[0].strip()) > 5:
                        result["issues"].append({
                            "issue": match[0].strip(),
                            "regulation": match[1].strip(),
                            "citation": f'"{match[2].strip()}"'
                        })
        
        return result
    
    def validate_handler(self) -> Dict[str, Any]:
        """Validate loaded handler."""
        
        result = {
            "framework": self.regulation_framework,
            "handler_loaded": self.regulation_handler is not None,
            "errors": [],
            "warnings": []
        }
        
        if not self.regulation_handler:
            result["errors"].append("No handler loaded")
            return result
        
        # Test classification terms
        term_types = ["data_terms", "regulatory_keywords", "high_risk_patterns", "priority_keywords"]
        
        for term_type in term_types:
            try:
                terms = self.get_classification_terms(term_type)
                if len(terms) < 3:
                    result["warnings"].append(f"Few {term_type}: {len(terms)}")
            except Exception as e:
                result["errors"].append(f"{term_type} failed: {e}")
        
        # Test prompt creation
        try:
            self.create_analysis_prompt("Test text", "Test section", "Test regulation")
        except Exception as e:
            result["errors"].append(f"Prompt test failed: {e}")
        
        return result