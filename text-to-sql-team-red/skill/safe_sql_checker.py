from pharia_skill import ChatParams, Csi, IndexPath, Message, skill
from pydantic import BaseModel

NAMESPACE = "Studio"
COLLECTION = "team-red-collection"
INDEX = "team-red-index"

# Read the database schema from schema.txt
DB_SCHEMA = """=== DATABASE STRUCTURE ===
CREATE TABLE Categories (
    CategoryID    INTEGER,
    PRIMARY KEY (CategoryID),
    CategoryName  TEXT,
    Description   TEXT,
    Picture       BLOB   
);
... (truncated for brevity) ...
"""


class Input(BaseModel):
    sql_statement: str


class Output(BaseModel):
    answer: str | None


@skill
def safe_sql_checker(csi: Csi, input: Input) -> Output:
    # Validate the provided SQL statement
    if not input.sql_statement.lower().startswith("select"):
        return Output(answer="Error: Only SELECT statements are allowed.")

    # Check if the SQL statement is harmful
    content = f"""Analyze the following SQL statement and determine if it is harmful or could potentially cause damage to the database or its data. Provide a clear response indicating whether the statement is safe or harmful, and explain why.

    SQL Statement:
    {input.sql_statement}
"""
    message = Message.user(content)
    params = ChatParams(max_tokens=512)
    response = csi.chat("llama-3.1-8b-instruct", [message], params)

    return Output(answer=response.message.content)


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()
    res = safe_sql_checker(
        csi,
        Input(sql_statement="SELECT * FROM Customers;"),
    )
    print("---- result ----")
    print(res.answer)
