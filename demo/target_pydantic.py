"""
Pydantic v1 Legacy Model (Not in rules_registry.py!)
Demonstrates Pure Autonomous LLM Detection without pre-defined rules.
"""
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    user_id: int
    username: str
    email_address: str
    
    # Deprecated in Pydantic v2 (Should be model_config = ConfigDict(from_attributes=True))
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

def get_user():
    data = {"user_id": 101, "username": "morad", "email_address": "morad@example.com"}
    # Deprecated in Pydantic v2 (Should be UserProfile.model_validate(data))
    user = UserProfile.parse_obj(data)
    # Deprecated in Pydantic v2 (Should be user.model_dump_json())
    return user.json()

if __name__ == "__main__":
    print(get_user())
