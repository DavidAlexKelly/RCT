from typing import Dict, Any
from config import config

class LLMHandler:
    """Simplified LLM handler with basic validation."""
    
    def __init__(self, model_config=None, debug=False):
        """Initialize LLM handler."""
        self.debug = debug
        self.model_config = model_config or {"name": "llama3:8b", "temperature": 0.1}
        
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
            print(f"LLM Handler: Initialized with {self.model_config['name']}")
    
    def invoke(self, prompt: str) -> str:
        """Direct LLM invocation with basic validation."""
        assert prompt and prompt.strip(), "Empty prompt"
        assert len(prompt) <= config.max_prompt_length, f"Prompt too long: {len(prompt)}"
        
        if self.debug:
            print(f"\n=== LLM INVOCATION DEBUG ===")
            print(f"Model: {self.model_config['name']}")
            print(f"Prompt length: {len(prompt)}")
            print(f"Temperature: {self.model_config.get('temperature', 0.1)}")
            print("=" * 40)
        
        try:
            response = self.llm.invoke(prompt)
            
            if not response:
                raise RuntimeError("LLM returned empty response")
            
            response = response.strip()
            
            if self.debug:
                print(f"\n=== LLM RESPONSE DEBUG ===")
                print(f"Response length: {len(response)}")
                if len(response) <= 300:
                    print(f"Full response: '{response}'")
                else:
                    print(f"Response preview: '{response[:150]}...{response[-150:]}'")
                print("=" * 40)
            
            return response
            
        except Exception as e:
            error_msg = f"LLM invocation failed: {e}"
            if self.debug:
                print(f"\n=== LLM ERROR DEBUG ===")
                print(f"Error: {error_msg}")
                print(f"Model: {self.model_config['name']}")
                print("=" * 40)
            raise RuntimeError(error_msg)