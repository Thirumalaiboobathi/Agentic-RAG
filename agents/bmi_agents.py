import asyncio
import logging
import re
import time

from langchain_core.prompts import ChatPromptTemplate

from graph.state import AgentState
from tools.bmi_tool import calculate_bmi
from tools.llm import get_llm

logger = logging.getLogger(__name__)

_BMI_PROMPT = """
You are a professional healthcare assistant.

Using the BMI data below, explain in a patient-friendly way.

BMI Data:
{bmi_data}

Provide:

- BMI Value
- BMI Category
- What it means
- Possible health risks
- Exercise recommendation
- Diet recommendation
- Ideal weight range
"""

async def bmi_agent_node(state: AgentState):
    start = time.time()
    
    
    emit = state.get("emit")
    query = state["user_query"]
    
    if emit:
        await emit(
            "agent_progress",
            "bmi",
            "Calculating BMI"
        )
    height_match = re.search(r'(\d+(?:\.\d+)?)\s*cm', query, re.IGNORECASE)
    weight_match = re.search(r'(\d+(?:\.\d+)?)\s*kg', query, re.IGNORECASE)
    
    if not height_match or not weight_match:
        return {
            "agent_result": {
                "agent": "bmi",
                "content": (
                    "Please provide both height (cm) and weight (kg).\n\n"
                    "Example:\n"
                    "Height: 170 cm\n"
                    "Weight: 72 kg"
                ),
                "sources": [],
                "raw": {}
            }
        }

    height = float(height_match.group(1))
    weight = float(weight_match.group(1))

    bmi_data = await asyncio.to_thread(
        calculate_bmi,
        weight,
        height
    )

    if emit:
        await emit(
            "agent_progress",
            "bmi",
            "Generating health recommendation..."
        )

    prompt = ChatPromptTemplate.from_template(_BMI_PROMPT)

    chain = prompt | get_llm()

    response = await asyncio.to_thread(
        chain.invoke,
        {
            "bmi_data": bmi_data
        }
    )

    latency = int((time.time() - start) * 1000)

    return {
        "bmi_result": bmi_data,
        "agent_result": {
            "agent": "bmi",
            "content": response.content,
            "sources": ["BMI Calculator"],
            "raw": bmi_data,
        },
        "latency_ms": {
            **state.get("latency_ms", {}),
            "bmi": latency,
        },
    }
