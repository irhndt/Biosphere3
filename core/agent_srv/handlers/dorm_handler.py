from .base_handler import BaseHandler
from core.agent_srv.prompts import *
from core.agent_srv.node_model import AccommodationDecision
from core.agent_srv.utils import *
from core.db.api_client import agent_api, game_api
from loguru import logger


class AccommodationHandler(BaseHandler):
    async def generate_accommodation_decision(self, state):
        accommodation_decision_generator = self.create_planner(
            accommodation_decision_prompt,
            state.get("character_stats", {}).get("model_type"),
            AccommodationDecision,
            0.5,
        )
        current_accommodation_data = game_api.request_sync(
            method="GET",
            endpoint=f"/characterDormitory/getByCharacterIdNew/{state['userid']}",
        )

        current_accommodation = {"id": 1, "type": "Shelter"}
        if current_accommodation_data:
            current_accommodation["id"] = current_accommodation_data.get("id", 1)
            current_accommodation["type"] = current_accommodation_data.get(
                "type", "Shelter"
            )

        financial_status = {"money": state["character_stats"].get("money", 0)}

        accommodations_response = game_api.request_sync(
            method="GET", endpoint="/dormitory/getAll"
        )
        necessary_fields = [
            "id",
            "type",
            "weeklyRent",
            "energyRecovery",
            "maxEnergy",
            "maxHealth",
            "maxHungry",
        ]
        available_accommodations = [
            {key: accommodation[key] for key in necessary_fields}
            for accommodation in accommodations_response
        ]

        for acc in available_accommodations:
            weekly_rent = acc["weeklyRent"]
            if weekly_rent == 0:
                acc["affordable_weeks"] = 4
            else:
                affordable_weeks = financial_status["money"] // weekly_rent
                affordable_weeks = min(affordable_weeks, 4)
                acc["affordable_weeks"] = int(affordable_weeks)

        failure_reasons = []

        max_retries = 5
        retries = 0

        while retries < max_retries:
            payload = {
                "character_stats": format_character_data(state["character_stats"]),
                "current_accommodation": current_accommodation,
                "available_accommodations": available_accommodations,
                "financial_status": financial_status,
                "failure_reasons": failure_reasons,
            }
            accommodation_decision = await self.api_retry(
                accommodation_decision_generator.ainvoke,
                payload,
                state,
                AccommodationDecision,
            )

            logger.info(f"🏠 Attempt {retries + 1}:")
            logger.info(
                f"🏠 Accommodation ID: {accommodation_decision.accommodation_id}"
            )
            logger.info(f"🏠 Lease Weeks: {accommodation_decision.lease_weeks}")
            logger.info(f"🏠 Comments: {accommodation_decision.comments}")

            selected_accommodation = next(
                (
                    acc
                    for acc in available_accommodations
                    if acc["id"] == accommodation_decision.accommodation_id
                ),
                None,
            )

            if not selected_accommodation:
                failure_message = (
                    f"Attempt {retries + 1}: Selected accommodation ID {accommodation_decision.accommodation_id} "
                    f"does not exist. Please choose a valid accommodation."
                )

                failure_reasons.append(failure_message)
                logger.warning(f"🏠 {failure_message}")
                retries += 1
                continue

            lease_weeks = accommodation_decision.lease_weeks

            if not (1 <= lease_weeks <= 4):
                failure_message = (
                    f"Attempt {retries + 1}: Lease weeks {lease_weeks} is out of allowed range (1-4). "
                    f"Please choose a valid number of weeks."
                )

                failure_reasons.append(failure_message)
                logger.warning(f"🏠 {failure_message}")
                retries += 1
                continue

            weekly_rent = selected_accommodation["weeklyRent"]
            total_rent = weekly_rent * lease_weeks

            if total_rent > financial_status["money"]:
                failure_message = (
                    f"Attempt {retries + 1}: Cannot afford total rent of {total_rent} for accommodation ID "
                    f"{accommodation_decision.accommodation_id} over {lease_weeks} weeks. "
                    f"Available money: {financial_status['money']}."
                )

                failure_reasons.append(failure_message)
                logger.warning(f"🏠 {failure_message}")
                retries += 1
                continue
            else:
                rent_data = {
                    "characterId": state["userid"],
                    "money": financial_status["money"],
                    "dormitoryId": accommodation_decision.accommodation_id,
                    "leaseWeeks": lease_weeks,
                }
                print("rent_data: ", rent_data)
                logger.info(f"🏠 Successfully rented accommodation.")
                break

        else:
            logger.error(
                f"🏠 Could not find an affordable accommodation after {max_retries} attempts."
            )
            return {
                "decision": {
                    "accommodation_id": None,
                    "lease_weeks": None,
                    "accommodation_comments": "Could not find an affordable accommodation.",
                }
            }

        response = await self.send_message(
            state,
            "accommodationChange",
            8,
            {
                "accommodationId": accommodation_decision.accommodation_id,
                "leaseWeeks": lease_weeks,
                "comments": accommodation_decision.comments,
            },
        )
        if state.get("instance"):
            state["instance"].log_message("received", response)

        return {"current_pointer": "Accommodation_Decision"}
