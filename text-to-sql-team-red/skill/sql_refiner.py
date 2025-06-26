from pharia_skill import ChatParams, Csi, Message, skill
from pydantic import BaseModel


class Input(BaseModel):
    sql_statement: str


class Output(BaseModel):
    refined_sql: str | None


@skill
def sql_refiner(csi: Csi, input: Input) -> Output:
    # Prompt to refine and improve the SQL statement
    content = f"""Refine and improve the following SQL statement in terms of performance and readability. Ensure the optimized query maintains the same functionality and adheres to best practices. 

    SQL Statement:
    {input.sql_statement}
    
    Only answer with the SQL query as plain text, without any additional text, comments, explanations, or markdown annotations. Use common SQL line indentations.
"""
    message = Message.user(content)
    params = ChatParams(max_tokens=512)
    response = csi.chat("llama-3.1-8b-instruct", [message], params)

    return Output(refined_sql=response.message.content)


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()
    res = sql_refiner(
        csi,
        Input(sql_statement="SELECT * FROM Customers WHERE Country = 'Germany';"),
    )
    print("---- refined SQL ----")
    print(res.refined_sql)
