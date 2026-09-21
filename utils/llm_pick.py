from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()

import os

def pick_llm(level:str):
    """
    Pick the LLM model based on the level of the question.
    
    Args:
        level (str): The level of questions can be "low", "medium","high"
    
    Returns:
        str: The name of the LLM model to be used
    """

    if level.lower() == "low":
        return ChatGroq(model="openai/gpt-oss-120b", groq_api_key=os.getenv("GROQ_API_KEY"))
    elif level.lower() == "medium":
        return ChatGroq(model="openai/gpt-oss-120b", groq_api_key=os.getenv("GROQ_API_KEY"))
    elif level.lower() == "high":
        return ChatGroq(model="openai/gpt-oss-120b", groq_api_key=os.getenv("GROQ_API_KEY"))
    
   