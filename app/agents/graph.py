import asyncio
import uuid
from typing import Union

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agents.context import ContextRepoInfo
from app.agents.state import PRState
import logging
import mlflow

from app.config import settings

logger = logging.getLogger(__name__)

class WorkflowAgent:

    def __init__(self, graph):
        self.graph = graph

    @staticmethod
    async def build_state_graph():
        logger.info("building state graph")
        agent_builder = StateGraph(PRState)
        from app.agents.nodes.data_retriever_node import data_retriever_node, data_retriever_error_handler
        from app.agents.nodes.file_reviewer_node import file_reviewer_node, file_reviewer_error_handler
        from app.agents.nodes.chunker_node import chunker_node
        from app.agents.nodes.triage_node import triage_node
        from app.agents.nodes.synthesizer_node import synthesizer_node

        # Add nodes
        agent_builder.add_node("data_retriever_node", data_retriever_node, error_handler=data_retriever_error_handler)
        agent_builder.add_node("triage_node", triage_node)
        agent_builder.add_node("chunker_node", chunker_node)
        agent_builder.add_node("file_reviewer_node", file_reviewer_node, error_handler=file_reviewer_error_handler)
        agent_builder.add_node("synthesizer_node", synthesizer_node)

        # Add edges to connect nodes
        agent_builder.add_edge(START, "data_retriever_node")
        agent_builder.add_edge("data_retriever_node", "triage_node")
        agent_builder.add_edge("triage_node", "chunker_node")
        agent_builder.add_edge("chunker_node", "file_reviewer_node")
        agent_builder.add_edge("synthesizer_node", END)

        if settings.postgres.url:
            async with AsyncPostgresSaver.from_conn_string(settings.postgres.url) as checkpointer:
                await checkpointer.setup()
                return agent_builder.compile(checkpointer=checkpointer)
        else:
            return agent_builder.compile(checkpointer=MemorySaver())

    @staticmethod
    async def activate_mlflow():
        if not settings.mlflow.tracking_uri:
            return
        # 1. Configure MLflow
        mlflow.set_tracking_uri( settings.mlflow.tracking_uri)  # Or your tracking server
        mlflow.set_experiment(settings.mlflow.experiment)

        # 2. Enable Auto-Tracing - This is the core of the integration
        mlflow.langchain.autolog()

    async def astream_pr_files(self, context:  Union[ContextRepoInfo, dict]):
        if isinstance(context, dict):
            context = ContextRepoInfo(**context)
        logger.info(f"starting to stream pr files Github PR: {context}")
        config = {
            "configurable": {
                "thread_id":  str(uuid.uuid4())
            }
        }
        async for part in self.graph.astream({},
            stream_mode=["updates"],
            context=context , version="v2", config=config):
            for node_name, state in part["data"].items():
                if state and "error" in state:
                    yield {
                        "error": state["error"]
                    }
                elif ("file_reviewer_node" in node_name) and state and "file_reviews" in state and len(state["file_reviews"]) > 0:
                    yield {
                        "file_name" : state["file_reviews"][0]["file"],
                        "issues" : state["file_reviews"][0]["review"]["issues"],
                        "summary" : state["file_reviews"][0]["review"]["summary"],
                        "error": state["file_reviews"][0]["review"]["error"],
                        "new_data": state["file_reviews"][1]["review"]["dataaaa"]
                    }



def build_context_data():
    return ContextRepoInfo(user_name="ykhanbabaei", repository="url-shortener", pull_number=2)



async def get_workflow_agent():
    global _workflow_agent
    if _workflow_agent is None:
        _g = await WorkflowAgent.build_state_graph()
        WorkflowAgent.activate_mlflow()
        _workflow_agent = WorkflowAgent(_g)
    return _workflow_agent

_workflow_agent = None
