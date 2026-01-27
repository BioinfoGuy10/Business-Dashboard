import os
from openai import OpenAI
import json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

prompt = """
Find the official Merck KGaA (merckgroup.com) press release URLs for the following events:
1. Surface Solutions divestment (July 2024)
2. Mirus Bio acquisition (May/June 2024)
3. Annual Report 2023 (March 2024)
4. Belen Garijo re-appointed (November 2023)
5. Fiscal 2022 Results (March 2023)
6. Ireland expansion (December 2022)
7. China expansion (September 2022)

Return a JSON mapping of event to URL. Use only official merckgroup.com links if possible.
"""

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}],
    response_format={ "type": "json_object" }
)

print(response.choices[0].message.content)
