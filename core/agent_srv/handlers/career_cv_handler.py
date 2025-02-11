from .base_handler import BaseHandler
from core.agent_srv.prompts import *
from core.agent_srv.node_model import NewCV, MayorDecision
from core.agent_srv.utils import *
from core.db.api_client import agent_api, game_api
from loguru import logger


class CareerCVHandler(BaseHandler):

    async def generate_cv(self, instance, msg):
        cv_generator = self.create_planner(prompt_for_cv_new, "gpt-4o-mini", NewCV, 0.5)
        userid = msg.get("characterId")
        msg_data = msg.get("data", {})
        health = msg_data.get("health", 0)
        money = instance.state["character_stats"].get("money", 0)
        experience = msg_data.get("studyXp", 0)
        education = instance.state["character_stats"].get("education", "None")
        jobId = instance.state["character_stats"].get("jobId", 0)
        week = msg_data.get("week", 0)
        date = msg_data.get("date", 0)
        character_name = instance.state["character_stats"].get("name", "None")

        character_industry = agent_api.request_sync(
            method="GET", endpoint=f"/industry/{userid}"
        )["industry"]
        cv_data = agent_api.request_sync(
            method="GET", endpoint="/cv/", params={"characterId": userid}
        )
        all_public_jobs = game_api.request_sync(
            method="GET", endpoint="/publicWork/getAll"
        )
        if not cv_data:
            past_work_experience = None
        else:
            past_work_experience = cv_data[0].get("experience", None)
        biography = instance.state["character_stats"].get("personality", "None")
        job_data = game_api.request_sync(
            method="GET", endpoint=f"/publicWork/getById/{jobId}"
        )
        eligible_jobs = filter_jobs(all_public_jobs, education, experience)
        if job_data:
            current_job = {
                job_data["jobName"]: {
                    "id": job_data["id"],
                    "jobType": job_data["jobType"],
                    "jobPlace": job_data["jobPlace"],
                    "dailyWages": job_data["dailyWages"],
                    "education": job_data["education"],
                    "wagePerHour": job_data["wagePerHour"],
                    # "populationRatioCap": job_data["populationRatioCap"],
                }
            }
            current_job_str = (
                f"""# Current Job\n{convert_to_table_string(current_job)}\n"""
            )
        else:
            current_job_str = "# Current Job\nCurrently, you don't have a job.\n"
        if eligible_jobs:
            eligible_jobs_str = f"# Eligible Jobs\nThe following jobs are available for you to choose from, as you meet the requirements:\n{convert_to_table_string(eligible_jobs)}\n"
        else:
            eligible_jobs_str = f"# Eligible Jobs\nCurrently, there are no eligible jobs to choose from.\n"
        industry, industry_goal_for_cv = get_industry_and_goal(character_industry)
        payload = {
            "industry": industry,
            "industry_goal_for_cv": industry_goal_for_cv,
            "characterName": character_name,
            "education": education,
            "money": money,
            "past_work_experience": past_work_experience,
            "biography": biography,
            "current_job_str": current_job_str,
            "eligible_jobs_str": eligible_jobs_str,
        }
        logger.info(prompt_for_cv_new.format(**payload))
        cv = await self.api_retry(
            cv_generator,
            payload,
            state=instance.state,
            node_model=NewCV,
        )
        logger.info(f"📃 CV: {cv}")
        if cv.job_id == 0:
            logger.info("📃 CV: No job selected. Agent want to keep the original job. ")
            return

        decision_job_name = get_job_name(cv.job_id, all_public_jobs)
        cv_request = {
            "jobid": cv.job_id,
            "characterId": userid,
            "CV_content": cv.cv,
            "week": week,
            "health": health,
            "studyxp": experience,
            "date": date,
            "jobName": decision_job_name,
            "election_status": "not_yet",
        }
        agent_api.request_sync("POST", "/cv/", data=cv_request)
        mayor_decision = await self.generate_mayor_decision(
            cv, userid, experience, education, week
        )
        if instance and instance.websocket:
            response = await instance.send_message(
                {
                    "characterId": userid,
                    "messageName": "mayor_decision",
                    "messageCode": 10,
                    "data": {
                        "jobId": cv.job_id,
                        "jobName": decision_job_name,
                        "cv": cv.cv,
                        **mayor_decision,
                    },
                }
            )
            instance.log_message("received", json.dumps(response))

    async def generate_mayor_decision(
        self,
        cv,
        user_id,
        experience,
        education,
        week,
    ):
        mayor_decision_generator = self.create_planner(
            mayor_decision_prompt, "gpt-4o-mini", MayorDecision, 0.7
        )
        public_work_info = game_api.request_sync(
            method="GET", endpoint=f"/publicWork/getById/{cv.job_id}"
        )
        check_result = game_api.request_sync(
            method="POST",
            endpoint="/publicWork/checkWork",
            data={
                "characterId": user_id,
                "newJobId": cv.job_id,
                "experience": experience,
                "education": education,
            },
            return_data=False,
        )
        code = check_result.get("code", 0)
        message = check_result.get("message", "")
        payload = {
            "cv": cv.cv,
            "public_work_info": public_work_info,
            "meet_requirements": {"meet": code == 1, "message": message},
        }
        logger.info(
            f"🧔 Mayor decision prompt: {mayor_decision_prompt.format(**payload)}"
        )
        mayor_decision = await self.api_retry(
            mayor_decision_generator,
            payload,
            state={},
            node_model=MayorDecision,
        )
        logger.info(f"🧔 Mayor decision: {mayor_decision.decision}")
        logger.info(f"🧔 Mayor comments: {mayor_decision.comments}")

        agent_api.request_sync(
            method="PUT",
            endpoint="/cv/election_status",
            data={
                "characterId": user_id,
                "jobid": cv.job_id,
                "week": week,
                "election_status": (
                    "succeeded" if mayor_decision.decision == "yes" else "failed"
                ),
            },
        )

        return {
            "mayor_decision": mayor_decision.decision,
            "mayor_comments": mayor_decision.comments,
        }
