from core.conversation_srv.conversation_prompts import *
from core.utils.llm_factory import LLMSelector
from core.conversation_srv.conversation_model import *
from core.db.api_client import agent_api

llm_selector = LLMSelector()


def conversation_llm(prompt_template, model_name, output_type, temperature):
    return prompt_template | llm_selector.get_llm(
        model_type="CHAT", model_name=model_name, temperature=temperature
    ).with_structured_output(output_type)


conversation_topic_planner = conversation_llm(
    prompt_template=conversation_topic_planner_prompt,
    model_name="gpt-4o-mini",
    output_type=ConversationTopics,
    temperature=1
)

conversation_generator = conversation_llm(
    prompt_template=conversation_generator_prompt,
    model_name="gpt-4o",
    output_type=ConversationContent,
    temperature=0.5
)

simple_content_generator = conversation_llm(
    prompt_template=simple_content_prompt,
    model_name="gpt-4o",
    output_type=ConversationContent,
    temperature=0.5
)

conversation_check = conversation_llm(
    prompt_template=conversation_check_prompt,
    model_name="gpt-4o-mini",
    output_type=CheckResult,
    temperature=0
)

impression_update = conversation_llm(
    prompt_template=impression_update_prompt,
    model_name="gpt-4o-mini",
    output_type=ImpressionUpdate,
    temperature=1
)

conversation_intimacy_mark = conversation_llm(
    prompt_template=intimacy_mark_prompt,
    model_name="gpt-4o-mini",
    output_type=IntimacyMark,
    temperature=0.5
)


def make_api_request_sync(
    method: str,
    endpoint: str,
    params: dict = None,
    data: dict = None,
):
    response = {}
    retry_count = 0
    while retry_count < 3:
        try:
            response = agent_api.request_sync(method, endpoint, params, data, False)
            break
        except Exception as e:
            print(f"API request error: {e}")
            retry_count += 1
    if response:
        return response
    else:
        return {"data": None}
