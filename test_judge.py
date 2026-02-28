import os
from dotenv import load_dotenv
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

class JudicialOpinion(BaseModel):
    judge: Literal["Prosecutor", "Defense", "TechLead"]
    criterion_id: str
    score: int = Field(ge=1, le=5)
    argument: str
    cited_evidence: List[str] = Field(default_factory=list, description="List of evidence IDs or keys cited")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("No GOOGLE_API_KEY")
    exit(1)

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
structured_llm = llm.with_structured_output(JudicialOpinion)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a judge."),
    ("human", "Rubric Dimension: Test\n\nEvidence: Test")
])

chain = prompt | structured_llm

print("Invoking judge chain...")
try:
    result = chain.invoke({"dimension": "test", "evidence": "test"})
    print("Success:")
    print(result)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
