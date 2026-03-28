# first_automation.py
from tinyfish import TinyFish

from dotenv import load_dotenv
from database import register_csv_as_view


load_dotenv()

client = TinyFish()  # Reads TINYFISH_API_KEY from environment

# Stream the automation and print each event as it arrives
with client.agent.stream(
    url="https://www.expedia.com.sg/",  # Target website to automate
    goal="Extract first 2 flights from Singapore to Denpasar today",  # Natural language instruction
    browser_profile="stealth"
) as stream:
    for event in stream:
        print(event)
