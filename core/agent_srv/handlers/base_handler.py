from loguru import logger
from json import JSONDecodeError
from pydantic import ValidationError
from core.utils.llm_factory import llm_selector, LLM
from core.agent_srv.prompts import correct_format_prompt
from core.db.api_client import game_api, agent_api
from core.agent_srv.node_model import BaseModel, RunningState
from azure.core.exceptions import HttpResponseError
from langchain_core.exceptions import OutputParserException
import traceback
import time


class BaseHandler:
    MAX_RETRIES = 3

    @classmethod
    def create_planner(self, prompt_template, model_name, output_type, temperature=0.5):
        return LLM(prompt_template, model_name, output_type, temperature)

    @classmethod
    async def api_retry(
        self,
        llm: LLM,
        payload: dict,
        state: RunningState,
        node_model: BaseModel,
    ):
        retry_count = 0
        response = None
        while retry_count < self.MAX_RETRIES:
            try:
                response = await llm.ai_invoke(payload)
                # logger.info("Raw output: " + str(response))
                break
            except OutputParserException as e:
                logger.error(f"⛔ OutputParserException in api_retry: {e}")
                if "JSONDecodeError" in str(e):
                    logger.error(f"⛔ JSON parsing related error in api_retry: {e}")
                    print(traceback.format_exc())
                    retry_count += 1
                    if retry_count == self.MAX_RETRIES and hasattr(e, "doc"):
                        return self.correct_format_error(state, e.doc, node_model)
                    continue
                else:
                    raise e
            except ConnectionError as e:
                logger.error(f"⛔ ConnectionError in api_retry: {e}")
                llm.set_retry()
                print(traceback.format_exc())
                retry_count += 1
                time.sleep(2**retry_count)
                continue
            except TimeoutError as e:
                logger.error(f"⛔ TimeoutError in api_retry: {e}")
                llm.set_retry()
                print(traceback.format_exc())
                retry_count += 1
                time.sleep(2**retry_count)
                continue
            except ValidationError as e:
                logger.error(
                    f"⛔ ValidationError in validate {node_model.__name__}: {e}"
                )
                retry_count += 1
                if retry_count == self.MAX_RETRIES and e.errors() is not None:
                    return self.correct_format_error(state, e.errors(), node_model)
                continue
            except HttpResponseError as e:
                logger.error(f"⛔ HttpResponseError in api_retry: {e}")
                print(traceback.format_exc())
                llm.set_retry()
                retry_count += 1
                continue
            except Exception as e:
                logger.error(f"⛔ Error in api_retry: {e}")
                print(traceback.format_exc())
                retry_count += 1
                if retry_count == self.MAX_RETRIES and response is not None:
                    return self.correct_format_error(state, response, node_model)
                continue

        return response

    @classmethod
    async def send_message(self, state, message_name, message_code, data):
        if not state.get("instance"):
            logger.warning(f"⚠️ User {state['userid']}: Instance not found.")
            return
        response = {
            "characterId": state["userid"],
            "messageName": message_name,
            "messageCode": message_code,
            "data": data,
        }
        await state["instance"].send_message(response)
        return response

    async def correct_format_error(self, state, raw_response, node_model):
        correcter = self.create_planner(
            correct_format_prompt,
            state.get("character_stats", {}).get("model_type"),
            node_model,
            0.4,
        )
        try:
            corrected_response = await correcter.ainvoke({"raw_response": raw_response})
            logger.info(f"🔍 Corrected response: {corrected_response}")
        except Exception as e:
            logger.error(f"⛔ Error in correct_format_error: {e}")
            print(traceback.format_exc())
            corrected_response = raw_response

        return corrected_response
