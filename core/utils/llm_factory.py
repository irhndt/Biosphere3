from langchain_openai import ChatOpenAI, AzureChatOpenAI
from collections import defaultdict
from typing import Dict, DefaultDict, Literal
from dotenv import load_dotenv
import os
from langchain.callbacks.base import BaseCallbackHandler
from core.db.api_client import game_api
from httpx import AsyncClient, Client

load_dotenv()

ModelType = Literal["PLAN", "CHAT"]

openai_api_keys = [os.getenv(f"OPENAI_API_KEY_{i}") for i in range(1, 11)]
deepseek_api_keys = [os.getenv(f"DEEPSEEK_API_KEY_{i}") for i in range(1, 6)]
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai_request_count = 0
deepseek_request_count = 0


def get_api_key(model_name: str) -> str:
    api_key = ""
    global openai_request_count
    global deepseek_request_count
    if model_name.startswith("gpt"):
        api_key = openai_api_keys[openai_request_count % len(openai_api_keys)]
        openai_request_count += 1
    elif model_name.startswith("deepseek"):
        api_key = deepseek_api_keys[deepseek_request_count % len(deepseek_api_keys)]
        deepseek_request_count += 1
    return api_key


class LLMSelector:
    token_usage: DefaultDict[str, Dict[str, int]] = defaultdict(
        lambda: {"prompt": 0, "completion": 0, "total": 0},
        {
            "gpt-4o-mini": {"prompt": 0, "completion": 0, "total": 0},
            "gpt-4o": {"prompt": 0, "completion": 0, "total": 0},
            "deepseek-chat": {"prompt": 0, "completion": 0, "total": 0},
        },
    )

    @classmethod
    def initialize_token_usage(cls):
        modelToken = game_api.request_sync(
            method="GET", endpoint="/modelToken/getLatestModelToken"
        )
        for item in modelToken:
            if not item:
                continue
            model_type = item.get("modelType")
            cls.token_usage[model_type] = {
                "prompt": item.get("prompt", 0),
                "completion": item.get("completion", 0),
                "total": item.get("total", 0),
            }

    @classmethod
    def get_token_usage(cls) -> Dict[str, Dict[str, int]]:
        return dict(cls.token_usage)

    @classmethod
    def _update_token_usage(cls, model_name: str, usage_data: dict):
        if "token_usage" in usage_data:
            token_data = usage_data["token_usage"]
            cls.token_usage[model_name]["prompt"] += token_data.get("prompt_tokens", 0)
            cls.token_usage[model_name]["completion"] += token_data.get(
                "completion_tokens", 0
            )
            cls.token_usage[model_name]["total"] += token_data.get("total_tokens", 0)

    @classmethod
    def get_llm(cls, model_name: str, temperature: float = 0.7, retry=False):
        callbacks = [TokenUsageHandler(model_name)]
        # !!!Temporary change deepseek to gpt-4o-mini!!!
        if model_name.startswith("deepseek"):
            model_name = "gpt-4o-mini"
        api_key = get_api_key(model_name)
        # print(model_name)
        if model_name.startswith("gpt"):
            if retry:
                return ChatOpenAI(
                    base_url="https://api.aiproxy.io/v1",
                    api_key=api_key,
                    model=model_name,
                    temperature=temperature,
                    callbacks=callbacks,
                    streaming=False,
                )
            else:
                return AzureChatOpenAI(
                    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
                    api_key=azure_api_key,
                    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
                    temperature=temperature,
                    callbacks=callbacks,
                    model="gpt-4o-mini",
                    streaming=False,
                )
        elif model_name.startswith("deepseek"):
            return ChatOpenAI(
                base_url="https://api.deepseek.com/v1",
                api_key=api_key,
                model=model_name,
                temperature=temperature,
                callbacks=callbacks,
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}")


class LLM:
    def __init__(self, prompt_template, model_name, output_type, temperature=0.7):
        self.model_name = model_name
        self.temperature = temperature
        self.prompt_template = prompt_template
        self.output_type = output_type
        self.retry = False
        self.llm = self.prompt_template | LLMSelector.get_llm(
            model_name=model_name, temperature=temperature
        ).with_structured_output(output_type)

    async def ai_invoke(self, payload: Dict[str, str]):
        return await self.llm.ainvoke(payload)

    def set_retry(self):
        self.retry = not self.retry
        self.llm = self.prompt_template | LLMSelector.get_llm(
            model_name=self.model_name,
            temperature=self.temperature,
            retry=self.retry,
        ).with_structured_output(self.output_type)
        
    def temperature_down(self):
        self.temperature = max(0.1, self.temperature - 0.1)
        self.llm = self.prompt_template | LLMSelector.get_llm(
            model_name=self.model_name,
            temperature=self.temperature,
            retry=self.retry,
        ).with_structured_output(self.output_type)


class TokenUsageHandler(BaseCallbackHandler):
    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__()

    def on_llm_end(self, response, **kwargs):
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            usage_data = {"token_usage": token_usage}
            LLMSelector._update_token_usage(self.model_name, usage_data)


llm_selector = LLMSelector()
llm_selector.initialize_token_usage()
