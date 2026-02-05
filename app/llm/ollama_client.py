"""
Ollama LLM 客户端
"""
import requests
import json
from typing import Generator, Optional
from app.config import settings


class OllamaClient:
    """Ollama API 客户端"""

    def __init__(
            self,
            base_url: str = None,
            model: str = None,
            timeout: int = 120
    ):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout

    def chat(self, prompt: str, model: str = None) -> str:
        """非流式对话"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model or self.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()["response"]

    def chat_stream(self, prompt: str, model: str = None) -> Generator[str, None, None]:
        """流式对话"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model or self.model,
                "prompt": prompt,
                "stream": True
            },
            stream=True,
            timeout=self.timeout
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "response" in data:
                    yield data["response"]
                if data.get("done", False):
                    break


# 全局客户端
llm_client = OllamaClient()