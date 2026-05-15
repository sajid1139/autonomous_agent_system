from models.goal import Goal
from models.task import Task
from orchestrator.planner import plan
from utils.stream import notify
from helpers.retry import with_retry
import agents.research as research
import agents.summarize as summarize
import agents.critic as critic
import agents.validate as validate
import agents.execute as execute
import agents.report as report_agent

agent_map = {
    "research": research,
    "summarize": summarize,
    "critic": critic,
    "validate": validate,
    "execute": execute,
    "report": report_agent,
}

async def run(goal_id: str):
    try:
        goal = await Goal.get(id=goal_id)
        task_defs = await plan(goal.text)

        db_tasks = {}
        for i, t in enumerate(task_defs):
            rec = await Task.create(
                goal=goal,
                name=t["name"],
                agent=t["agent"],
                status="pending",
                order=i,
            )
            db_tasks[t["name"]] = {"rec": rec, "def": t}

        done = {}

        async def ready(t_def):
            return all(dep in done for dep in t_def.get("depends_on", []))

        remaining = list(task_defs)
        while remaining:
            ran = []
            for t in remaining:
                if await ready(t):
                    ctx = dict(done)
                    rec = db_tasks[t["name"]]["rec"]
                    agent = agent_map.get(t["agent"])
                    result = await with_retry(agent.run, rec, ctx)
                    rec.status = "done"
                    rec.result = str(result)
                    await rec.save()
                    done[t["name"]] = result
                    await notify(goal_id, t["name"] + " done")
                    ran.append(t)
            if not ran:
                break
            for t in ran:
                remaining.remove(t)

        goal.status = "done"
        await goal.save()
        await notify(goal_id, "workflow complete")

    except Exception as e:
        print("AGENT ERROR [engine]:", str(e))
        goal = await Goal.get_or_none(id=goal_id)
        if goal:
            goal.status = "failed"
            await goal.save()
        await notify(goal_id, "failed")
