import openai
import stripe
from pydantic import BaseModel

openai.api_key = 'sk-test-key'

def ask_chatgpt(question: str) -> str:
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': question}]
    )
    return response['choices'][0]['message']['content']

def generate_embedding(text: str):
    result = openai.Embedding.create(input=text, model='text-embedding-ada-002')
    return result['data'][0]['embedding']

class UserConfig(BaseModel):
    name: str
    age: int
    class Config:
        orm_mode = True

class AppSettings(BaseModel):
    debug: bool = False
    class Config:
        env_file = '.env'

stripe.api_key = 'sk_test_legacy'

def charge_customer(amount_cents: int, customer_id: str, description: str):
    charge = stripe.Charge.create(
        amount=amount_cents, currency='usd',
        customer=customer_id, description=description,
    )
    return charge
