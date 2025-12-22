from crewai import BaseLLM
from typing import Any, Dict, List, Optional, Union
import requests

class CustomLLM(BaseLLM):
    def __init__(
        self,
        model: str,
        api_key: str,
        endpoint: str,
        temperature: Optional[float] = None,
    ):
        super().__init__(model=model, temperature=temperature)
        self.api_key = api_key
        self.endpoint = endpoint

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs,  # ✅ 关键：兼容 from_task
    ) -> Union[str, Any]:

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        if tools and self.supports_function_calling():
            payload["tools"] = tools

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def supports_function_calling(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return 8192
