"""
Legacy LangChain Application using deprecated v0.1 LLMChain pattern.
"""
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

def generate_summary(text_input: str) -> str:
    prompt = PromptTemplate(
        input_variables=["text"],
        template="Summarize the following text concisely: {text}"
    )
    llm = OpenAI(temperature=0.7)
    
    # Deprecated in LangChain v0.2+ (Should be migrated to LCEL: prompt | llm)
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.predict(text=text_input)
    return response

if __name__ == "__main__":
    print(generate_summary("ApiPatch is an autonomous agent for fixing broken APIs."))
