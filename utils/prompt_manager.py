import os
import sys
import importlib.util
from pathlib import Path

class PromptManager:
    """Simplified prompt manager that loads framework handlers."""
    
    def __init__(self, regulation_framework=None):
        """Initialize prompt manager and load framework handler."""
        
        if not regulation_framework:
            raise ValueError("regulation_framework is required")
        
        self.regulation_framework = regulation_framework.strip()
        
        # Load regulation handler
        self.handler = self._load_regulation_handler(self.regulation_framework)
        if not self.handler:
            raise RuntimeError(f"Failed to load handler for {self.regulation_framework}")
    
    def _load_regulation_handler(self, regulation_framework: str):
        """Load framework-specific handler module using proper import paths."""
        
        # Construct paths relative to project root
        project_root = Path(__file__).parent.parent
        handler_path = project_root / "knowledge_base" / regulation_framework / "handler.py"
        
        if not handler_path.exists():
            raise FileNotFoundError(f"Handler not found: {handler_path}")
        
        if handler_path.stat().st_size == 0:
            raise ValueError(f"Empty handler file: {handler_path}")
        
        try:
            # Create module spec for dynamic import
            module_name = f"knowledge_base.{regulation_framework}.handler"
            
            # Remove if already loaded to avoid conflicts
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            if not spec or not spec.loader:
                raise ImportError(f"Failed to create spec for {handler_path}")
            
            # Load the module
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules before executing to handle circular imports
            sys.modules[module_name] = module
            
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                # Clean up sys.modules if execution fails
                if module_name in sys.modules:
                    del sys.modules[module_name]
                raise
            
            # Get handler class
            if not hasattr(module, 'RegulationHandler'):
                raise AttributeError(f"No RegulationHandler class in {handler_path}")
            
            handler_class = getattr(module, 'RegulationHandler')
            if not isinstance(handler_class, type):
                raise TypeError("RegulationHandler must be a class")
            
            # Initialize handler
            return handler_class(debug=False)
            
        except ImportError as e:
            # Handle import errors specifically
            if "utils.regulation_handler_base" in str(e):
                raise ImportError(
                    f"Cannot import base handler. Try running: pip install -e .\n"
                    f"Original error: {e}"
                )
            else:
                raise ImportError(f"Failed to import handler for {regulation_framework}: {e}")
                
        except Exception as e:
            raise RuntimeError(f"Failed to load handler for {regulation_framework}: {e}")