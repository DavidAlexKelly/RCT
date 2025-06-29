# utils/llm_handler.py - Simplified (329 → 120 lines)

import json
import re
from typing import List, Dict, Any, Optional
from config import config

class LLMHandler:
    def __init__(self, model_config=None, prompt_manager=None, debug=False):
        """Initialize LLM handler."""
        self.debug = debug
        self.model_config = model_config or {"name": "llama3:8b", "temperature": 0.1}
        
        assert prompt_manager, "prompt_manager required"
        self.prompt_manager = prompt_manager
        
        # Initialize Ollama
        try:
            from langchain_ollama import OllamaLLM as Ollama
            self.llm = Ollama(
                model=self.model_config["name"],
                temperature=self.model_config.get("temperature", 0.1)
            )
        except ImportError:
            raise RuntimeError("Install langchain_ollama: pip install langchain_ollama")
        
        if self.debug:
            print(f"Initialized LLM: {self.model_config['name']}")
    
    def get_batch_size(self) -> int:
        """Return recommended batch size."""
        return self.model_config.get("batch_size", 1)
    
    def invoke(self, prompt: str) -> str:
        """Direct LLM invocation."""
        assert prompt and prompt.strip(), "Empty prompt"
        assert len(prompt) <= config.max_prompt_length, f"Prompt too long: {len(prompt)}"
        
        try:
            response = self.llm.invoke(prompt)
            assert response, "Empty response"
            return response
        except Exception as e:
            raise RuntimeError(f"LLM failed: {e}")
    
    def analyze_compliance(self, document_chunk: Dict[str, Any], 
                           regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze document chunk for compliance issues."""
        
        assert document_chunk and regulations, "Missing chunk or regulations"
        
        doc_text = document_chunk.get("text", "")
        assert doc_text.strip(), "Empty document text"
        
        chunk_position = document_chunk.get("position", "Unknown")
        should_analyze = document_chunk.get("should_analyze", True)
        
        if self.debug:
            print(f"Analyzing: {chunk_position}")
        
        # Skip analysis for low-priority chunks
        if not should_analyze:
            return {
                "issues": [],
                "position": chunk_position,
                "text": doc_text,
                "should_analyze": False
            }
        
        # Get content indicators from regulation handler
        content_indicators = {}
        potential_violations = []
        
        handler = getattr(self.prompt_manager, 'regulation_handler', None)
        if handler:
            if hasattr(handler, 'extract_content_indicators'):
                content_indicators = handler.extract_content_indicators(doc_text)
            
            if hasattr(handler, 'extract_potential_violations'):
                potential_violations = handler.extract_potential_violations(doc_text, "")
        
        # Format regulations
        regs_to_use = regulations[:config.rag_articles]
        formatted_regulations = self.prompt_manager.format_regulations(regs_to_use)
        
        # Generate prompt
        prompt = self.prompt_manager.create_analysis_prompt(
            doc_text, chunk_position, formatted_regulations, 
            content_indicators, potential_violations
        )
        
        # Check prompt length
        if len(prompt) > config.max_prompt_length:
            if self.debug:
                print(f"Truncating prompt: {len(prompt)} -> {config.max_prompt_length}")
            # Use fewer regulations
            truncated_regs = regs_to_use[:max(1, len(regs_to_use)//2)]
            formatted_regulations = self.prompt_manager.format_regulations(truncated_regs)
            prompt = self.prompt_manager.create_analysis_prompt(
                doc_text, chunk_position, formatted_regulations,
                content_indicators, potential_violations
            )
        
        # Get LLM response
        response = self.llm.invoke(prompt)
        
        if self.debug:
            print(f"Response: {response[:100]}...")
        
        # Parse response
        result = self._parse_response(response, doc_text)
        
        # Add metadata
        result.update({
            "position": chunk_position,
            "text": doc_text,
            "should_analyze": True
        })
        
        # Add section to issues
        for issue in result.get("issues", []):
            issue["section"] = chunk_position
        
        if self.debug:
            issues = result.get("issues", [])
            print(f"Found {len(issues)} issues")
        
        return result
    
    def _parse_response(self, response: str, doc_text: str = "") -> Dict[str, List[Dict[str, Any]]]:
        """Parse LLM response for violations."""
        
        assert response.strip(), "Empty LLM response"
        
        result = {"issues": []}
        
        try:
            # Extract JSON array
            array_text = self._extract_json_array(response)
            
            if not array_text:
                # Check for explicit "no issues" response
                if any(phrase in response.lower() for phrase in ["no compliance issues", "no violations", "[]"]):
                    return result
                else:
                    raise ValueError("No JSON array found")
            
            # Parse JSON
            violations = json.loads(array_text)
            assert isinstance(violations, list), f"Expected array, got {type(violations)}"
            
            # Convert to standard format
            for violation in violations:
                if (isinstance(violation, list) and len(violation) >= 3 and 
                    len(str(violation[0]).strip()) > 5):
                    
                    issue_desc = str(violation[0]).strip()
                    regulation = str(violation[1]).strip()
                    citation = str(violation[2]).strip()
                    
                    result["issues"].append({
                        "issue": issue_desc,
                        "regulation": regulation,
                        "citation": f'"{citation}"' if citation and not citation.startswith('"') else citation
                    })
            
        except json.JSONDecodeError:
            if self.debug:
                print("JSON parsing failed, trying regex fallback")
            result = self._fallback_parsing(response)
        
        return result
    
    def _extract_json_array(self, response: str) -> str:
        """Extract JSON array from response."""
        start = response.find('[')
        if start == -1:
            return ""
        
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
        
        return response[start:end + 1] if end != -1 else ""
    
    def _fallback_parsing(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback parsing using regex."""
        result = {"issues": []}
        
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