# target_sample.py - Simulated user codebase with deprecated API calls

import os
import openai

def process_customer_support_ticket(ticket_text: str):
    """
    Deprecated OpenAI API usage (Pre v1.0 SDK format).
    This function breaks in modern OpenAI SDK versions.
    """
    print(f"Processing ticket: {ticket_text[:30]}...")
    
    # OLD DEPRECATED CALL:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful customer support bot."},
            {"role": "user", "content": ticket_text}
        ],
        temperature=0.7
    )
    
    return response['choices'][0]['message']['content']

if __name__ == "__main__":
    ticket = "I was double charged for my monthly subscription. Please refund."
    try:
        reply = process_customer_support_ticket(ticket)
        print("Reply:", reply)
    except Exception as e:
        print("API Error:", e)
