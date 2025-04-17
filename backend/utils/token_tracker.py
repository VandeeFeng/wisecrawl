import logging
from typing import Dict

logger = logging.getLogger(__name__)

class TokenTracker:
    def __init__(self):
        self._token_usage = {}  # model -> {prompt_tokens, completion_tokens, total_tokens}
        
    def add_usage(self, model: str, prompt_tokens: int, completion_tokens: int):
        """Add token usage for a model."""
        if model not in self._token_usage:
            self._token_usage[model] = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
            
        self._token_usage[model]['prompt_tokens'] += prompt_tokens
        self._token_usage[model]['completion_tokens'] += completion_tokens
        self._token_usage[model]['total_tokens'] += (prompt_tokens + completion_tokens)
    
    def get_usage(self) -> Dict:
        """Get the current token usage statistics."""
        return self._token_usage
    
    def print_summary(self):
        """Print a summary of token usage."""
        if not self._token_usage:
            logger.info("No token usage recorded.")
            return
            
        logger.info("\n=== Token Usage Summary ===")
        for model, usage in self._token_usage.items():
            logger.info(f"\nModel: {model}")
            logger.info(f"Prompt tokens: {usage['prompt_tokens']}")
            logger.info(f"Completion tokens: {usage['completion_tokens']}")
            logger.info(f"Total tokens: {usage['total_tokens']}")
        logger.info("\n" + "="*24)

# Global token tracker instance
token_tracker = TokenTracker()