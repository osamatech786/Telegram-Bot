import os
import openai
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.agents import tool
from langchain.agents import Tool
from langchain.agents import initialize_agent, AgentType

from serpapi import GoogleSearch
import requests
from dotenv import load_dotenv

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')  # You can set your API key in an environment variable

# Define the Langchain chain
template = "The user has asked: {question}. Generate a detailed response."
prompt = PromptTemplate(input_variables=["question"], template=template)
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
# chain = LLMChain(llm=llm, prompt=prompt)



################
# Tools
################

## Agents as tools:
@tool("Agent 0 - General Queries")
def run_agent_0(query: str) -> str:
    """Handles general queries using Agent 0."""
    logger.info(f"Routing query to Agent 0: {query}")
    return agent_0.run(query)

@tool("Agent 1 - Appointment Queries")
def run_agent_1(query: str) -> str:
    """Handles appointment-related queries using Agent 1."""
    logger.info(f"Routing query to Agent 1: {query}")
    return agent_1.run(query)

## Tools as functions:
@tool("answer_questions")
def answer_questions(query: str) -> str:
    """Uses the LLM to answer user queries."""
    logger.info(f"Executing 'answer_questions' tool with input: {query}")
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
    return llm.predict(query)

@tool("web_search")
def web_search(query: str) -> str:
    """Searches the web for the given query and returns the top result with a snippet."""
    logger.info(f"Executing 'web_search' tool with input: {query}")
    try:
        search = GoogleSearch({"q": query, "api_key": os.getenv("SERPAPI_KEY")})
        results = search.get_dict()
        first_result = results.get("organic_results", [{}])[0]
        link = first_result.get("link", "No link available.")
        snippet = first_result.get("snippet", "No snippet available.")
        result = f"Top result: {snippet}\n{link}"
        logger.info(f"'web_search' result: {result}")
        return result
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return "An error occurred during the web search."

@tool("current_weather")
def current_weather(query: str) -> str:
    """Fetches current weather information for a specified location.
    Example usage: 'current weather in London' or 'current weather New York'.
    """
    logger.info(f"Executing 'current_weather' tool with input: {query}")
    try:
        # Extract location from the query
        location = query.replace("current weather", "").strip() or "London"  # Default to London if no location is provided
        
        # Call the OpenWeatherMap API
        api_key = os.getenv("OPENWEATHER_API_KEY")  # Make sure to set this in your .env file
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            temp = data["main"]["temp"]
            description = data["weather"][0]["description"]
            city = data["name"]
            return f"The current weather in {city} is {temp}°C with {description}."
        else:
            return f"Could not fetch weather for '{location}'. Please check the location name."
    except Exception as e:
        logger.error(f"Weather tool error: {e}")
        return "An error occurred while fetching the weather."

@tool("schedule_appointment")
def schedule_appointment(query: str) -> str:
    """Schedules an appointment based on the user's input."""
    logger.info(f"Executing 'schedule_appointment' tool with input: {query}")
    # Implement appointment scheduling logic
    return f"Appointment scheduled: {query}"

@tool("reschedule_appointment")
def reschedule_appointment(query: str) -> str:
    """Reschedules an existing appointment."""
    logger.info(f"Executing 'reschedule_appointment' tool with input: {query}")
    # Implement rescheduling logic
    return f"Appointment rescheduled: {query}"



################
# Initialize the agent
################

# Sub-Agent 0: General Queries
tools_agent_0 = [
    Tool(name="Answer Questions", func=answer_questions, description="Answer user queries using LLM."),
    Tool(name="Web Search", func=web_search, description="Search the web for the latest information."),
    Tool(name="Current Weather", func=current_weather, description="Fetch the current weather for a specific location.")
]

llm_agent_0 = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
agent_0 = initialize_agent(tools_agent_0, llm_agent_0, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

# Sub-Agent 1: Appointment Queries
tools_agent_1 = [
    Tool(name="Schedule Appointment", func=schedule_appointment, description="Book an appointment for the user."),
    Tool(name="Reschedule Appointment", func=reschedule_appointment, description="Change the timing of an existing appointment.")
]

llm_agent_1 = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
agent_1 = initialize_agent(tools_agent_1, llm_agent_1, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

# def route_query(query: str) -> str:
#     if "appointment" in query.lower():
#         # Route to Agent 1 for appointment-related queries
#         return agent_1.run(query)
#     else:
#         # Route to Agent 0 for general queries
#         return agent.run(query)

# Main Agent (Router Agent)
tools_main_agent = [
    Tool(name="General Queries", func=run_agent_0, description="Handles general queries like answering questions or web search."),
    Tool(name="Appointment Queries", func=run_agent_1, description="Handles appointment scheduling and rescheduling.")
]

llm_main_agent = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7)
main_agent = initialize_agent(tools_main_agent, llm_main_agent, agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)



################
# Bot Start
################

# Start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    logger.info(f"Received start command from user: {update.effective_user.username}")
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\! I\'m a bot powered by OpenAI\. Ask me anything\.'
    )


# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    logger.info(f"Received help command from user: {update.effective_user.username}")
    await update.message.reply_text('Ask me any question, and I\'ll try to answer using AI!')

    
# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    logger.info(f"Received message: {user_message}")
    try:
        response = handle_query(user_message)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("I'm not sure how to help with that. Please try again!")


# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.warning(f'Update "{update}" caused error "{context.error}"')


def handle_query(query: str) -> str:
    """Handle user query by routing through the main agent."""
    try:
        logger.info(f"Handling query: {query}")
        response = main_agent.run(query)
        logger.info(f"Agent response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error in handle_query: {e}")
        return "Sorry, something went wrong."





def main() -> None:
    """Start the bot."""
    # Your Telegram bot token from BotFather
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(token).build()

    # Log that the bot is starting
    logger.info("Telegram bot started. Waiting for user input...")
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Log all errors
    application.add_error_handler(error_handler)

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()



'''
Architecture Overview
Main Agent (Router Agent):
This agent analyzes user queries and determines which sub-agent should handle the task.
Sub-Agents:
Agent 0: General-purpose queries (e.g., answer_questions, web_search, current_weather).
Agent 1: Appointment-related queries (e.g., schedule_appointment, reschedule_appointment).

ZERO_SHOT_REACT_DESCRIPTION:
The agent will analyze the user query, reason step by step, and decide which tool to use based on the provided tool descriptions. It does so without any additional task-specific training.
'''
