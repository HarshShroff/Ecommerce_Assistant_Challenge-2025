import os
import requests
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class PerplexityClient:
    """Client for Perplexity AI API integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('PERPLEXITY_API_KEY')
        if not self.api_key:
            logger.warning("No Perplexity API key provided. Some features will be limited.")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    def search(self, query: str, model: str = "sonar-small") -> Dict[str, Any]:
        """
        Perform a search using Perplexity API
        
        Args:
            query: The search query
            model: The model to use (sonar-small, sonar-medium, sonar-pro)
            
        Returns:
            Dict containing the search results and sources
        """
        if not self.api_key:
            logger.error("Perplexity API key is required for search")
            return {"error": "API key not configured"}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful e-commerce assistant. Provide concise, accurate information about products and shopping trends."},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.2,
                "max_tokens": 1024
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}"}
                
            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"],
                "sources": self._extract_sources(result)
            }
            
        except Exception as e:
            logger.error(f"Error in Perplexity search: {str(e)}")
            return {"error": f"Search failed: {str(e)}"}
    
    def _extract_sources(self, result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract sources from the API response if available"""
        try:
            if "sources" in result:
                return result["sources"]
            return []
        except:
            return []
