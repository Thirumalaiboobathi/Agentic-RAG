import asyncio
import logging
import time
import re

from langchain_core.prompts import ChatPromptTemplate
from tools.weather_tool import get_weather
from tools.llm import get_llm
from graph.state import AgentState

logger = logging.getLogger(__name__)

_WEATHER_PROMPT = """
You are a Weather Assistant.

Answer ONLY using the weather data below.

Weather Data:
{weather}

User Question:
{question}

Provide:
- Current temperature
- Feels like temperature
- Weather condition
- Humidity
- Wind speed
- Visibility
- UV Index
- Short recommendation
"""

async def weather_agent_node(state: AgentState):
    
    start = time.time()
    
    emit= state.get("emit")
    query = state["user_query"]
    match = re.search(
        r"(?:in|at|for)\s+([a-zA-Z\s]+)\??",
        query,
        re.IGNORECASE
    )

    if match:
        city = match.group(1).strip()
    else:
        city = "Madurai"
    
    if emit:
        await emit(
            'agent_progress',
            "weather",
            f"Fetching live weather for {city}..."
        )
    try:
       weather = await asyncio.to_thread(get_weather, city)
    
    except Exception as e:
        logger.exception(e)
        
        return{
            "agent_result":{
                "agent": "weather",
                "content": "Unable to retrieve weather information.",
                "sources": [],
                "raw": {"error": str(e)}
            }
        }
    if emit:
        await emit(
            "agent_progress",
            "weather",
            "Weather data received. Generating reaponse"
        )
        
    prompt = ChatPromptTemplate.from_template(_WEATHER_PROMPT)
    
    chain = prompt | get_llm()
    
    response = await asyncio.to_thread(
        chain.invoke,
        {
            "weather": weather,
            "question": query
        }
    )
    
    latency = int((time.time() - start) * 1000)
    
    return{
        "weather_output": weather,
        "agent_result": {
            "agent": "weather",
            "content": response.content,
            "sources": ["wttr.in"],
            "raw": weather
        },
        "latency_ms":{
            **state.get("latency_ms",{}),
            "weather": latency,
        }
    }
       
        