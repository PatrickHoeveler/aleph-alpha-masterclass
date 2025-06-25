from pharia_skill import ChatParams, Csi, IndexPath, Message, skill
from pydantic import BaseModel

NAMESPACE = "Studio"
COLLECTION = "team-red-collection"
INDEX = "team-red-index"


class Input(BaseModel):
    question: str
    namespace: str = NAMESPACE
    collection: str = COLLECTION
    index: str = INDEX


class Output(BaseModel):
    answer: str | None


@skill
def custom_rag(csi: Csi, input: Input) -> Output:
    index = IndexPath(
        namespace=input.namespace,
        collection=input.collection,
        index=input.index,
    )

    if not (documents := csi.search(index, input.question, 3, 0.5)):
        return Output(answer=None)

    ranked_queries = []
    for rank, document in enumerate(documents, start=1):
        metadata = csi.document_metadata(document_path=document.document_path)
        query = metadata.get("query", "")
        ranked_queries.append({"rank": rank, "query": query})

    print(f"Ranked Queries: {ranked_queries}")

    # TODO: Prompt Engineering

    context = "\n".join(
        [f"Rank: {q['rank']}, Query: {q['query']}" for q in ranked_queries]
    )

    # Read the database schema from schema.txt
    with open("schema.txt", "r") as schema_file:
        db_schema = schema_file.read()

    content = f"""Using the provided top three SQL queries below, generate a new SQL query that accurately addresses the given question. Ensure the generated query is syntactically correct and optimized for execution. If possible, combine relevant elements from the provided queries to construct the new query. Do not fabricate data or make assumptions beyond the provided information.

    Only answer with the SQL query, without any additional text or explanation so that we can directly use it for execution on the Northwind Sqlite db.

    Top Queries:
    {context}

    DB Schema:
    {db_schema}
        
    Question: {input.question}
"""
    message = Message.user(content)
    params = ChatParams(max_tokens=512)
    response = csi.chat("llama-3.1-8b-instruct", [message], params)
    return Output(answer=response.message.content)


if __name__ == "__main__":
    from pharia_skill.testing import DevCsi

    csi = DevCsi()
    res = custom_rag(csi, Input(question="Please query the number of tables."))
    print("---- result ----")
    print(res.answer)
