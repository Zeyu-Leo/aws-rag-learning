from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).with_name(".env"))
client = OpenAI()

stream = client.responses.create(
    model="openai.gpt-oss-120b",
    input=[
        {"role": "user", "content": "Tell me a short story about a robot."}
    ],
    stream=True
)

for event in stream:
    print(event)