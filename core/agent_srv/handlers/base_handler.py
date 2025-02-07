from loguru import logger
from requests import JSONDecodeError, ConnectionError, TimeoutError
from core.utils.llm_factory import llm_selector
from core.agent_srv.prompts import correct_format_prompt
from core.db.api_client import game_api, agent_api
import traceback
import time


class BaseHandler:
    MAX_RETRIES = 3

    @classmethod
    def create_planner(prompt_template, model_name, output_type, temperature=0.5):
        return prompt_template | llm_selector.get_llm(
            model_name=model_name, temperature=temperature
        ).with_structured_output(output_type)

    @classmethod
    async def api_retry(
        api_call,
        payload,
        state,
        node_model,
    ):
        retry_count = 0
        while retry_count < BaseHandler.MAX_RETRIES:
            try:
                response = await api_call(**payload)
                break
            except JSONDecodeError as e:
                logger.error(f"⛔ JSONDecodeError in api_retry: {e}")
                print(traceback.format_exc())
                retry_count += 1
                if retry_count == BaseHandler.MAX_RETRIES:
                    return BaseHandler.correct_format_error(state, response, node_model)
                continue
            except ConnectionError as e:
                logger.error(f"⛔ ConnectionError in api_retry: {e}")
                print(traceback.format_exc())
                retry_count += 1
                time.sleep(2**retry_count)
                if retry_count == BaseHandler.MAX_RETRIES:
                    return BaseHandler.correct_format_error(state, response, node_model)
                continue
            except TimeoutError as e:
                logger.error(f"⛔ TimeoutError in api_retry: {e}")
                print(traceback.format_exc())
                retry_count += 1
                time.sleep(2**retry_count)
                if retry_count == BaseHandler.MAX_RETRIES:
                    return BaseHandler.correct_format_error(state, response, node_model)
                continue
            except Exception as e:
                logger.error(f"⛔ Error in api_retry: {e}")
                print(traceback.format_exc())
                retry_count += 1
                if retry_count == BaseHandler.MAX_RETRIES:
                    return BaseHandler.correct_format_error(state, response, node_model)
                continue

        return response

    @classmethod
    async def send_message(state, message_name, message_code, data):
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
