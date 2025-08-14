import aiohttp
import asyncio
from typing import Dict, Any, Optional
from config import GROQ_URL, PERPLEXITY_URL, JOKE_API_URL, EIGHTBALL_API_URL

class APIClient:
    def __init__(self, groq_key: str, perplexity_key: str):
        self.groq_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {groq_key}"
        }
        self.perplexity_headers = {
            "Authorization": f"Bearer {perplexity_key}",
            "Content-Type": "application/json"
        }
    
    async def make_groq_request(self, messages: list, model: str = "openai/gpt-oss-120b") -> Optional[str]:
        """Make async request to Groq API."""
        data = {
            "model": model,
            "messages": messages,
            "temperature": 1,
            "max_completion_tokens": 8192,
            "top_p": 1,
            "reasoning_effort": "medium",
            "stream": False,
            "stop": None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GROQ_URL, headers=self.groq_headers, json=data, timeout=30) as response:
                    response.raise_for_status()
                    response_json = await response.json()
                    return response_json['choices'][0]['message']['content']
        except (aiohttp.ClientError, KeyError, asyncio.TimeoutError) as e:
            print(f"Groq API Error: {e}")
            return None
    
    async def make_perplexity_request(self, messages: list) -> Optional[str]:
        """Make async request to Perplexity API."""
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.2,
            "top_p": 0.9,
            "return_citations": False,
            "search_domain_filter": ["perplexity.ai"],
            "return_images": False,
            "return_related_questions": False,
            "search_recency_filter": "month",
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(PERPLEXITY_URL, headers=self.perplexity_headers, json=payload, timeout=60) as response:
                    response.raise_for_status()
                    response_json = await response.json()
                    return response_json['choices'][0]['message']['content']
        except (aiohttp.ClientError, KeyError, asyncio.TimeoutError) as e:
            print(f"Perplexity API Error: {e}")
            return None
    
    async def get_joke(self) -> str:
        """Get a joke from the joke API."""
        headers = {"Accept": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(JOKE_API_URL, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        joke_data = await response.json()
                        return joke_data['joke']
                    else:
                        return f"Error: Failed to fetch joke. Status code: {response.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Joke API Error: {e}")
            return "Sorry, couldn't fetch a joke right now."
    
    async def get_eight_ball_response(self, question: str) -> str:
        """Get an 8-ball response."""
        params = {"question": question}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(EIGHTBALL_API_URL, params=params, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('reading', 'Magic 8-ball is unclear')
                    else:
                        return f"Error: {response.status}"
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"8-ball API Error: {e}")
            return "The magic 8-ball is not responding."