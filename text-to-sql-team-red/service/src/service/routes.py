from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from service.db_service import init_db_connection, query
from service.dependencies import get_token, with_kernel
from service.kernel import Json, Kernel, KernelException, Skill
from service.models import HealthResponse

router: APIRouter = APIRouter()


class Output(BaseModel):
    sql_statement: str | None
    sql_harmless: bool
    explanation: str | None = None


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/qa")
async def qa(
    request: Request,
    token: str = Depends(get_token),
    kernel: Kernel = Depends(with_kernel),
) -> Json:
    skill_generator = Skill(
        namespace="customer-playground", name="team-red-skill-generator"
    )
    skill_refiner = Skill(
        namespace="customer-playground", name="team-red-skill-refiner"
    )
    skill_checker = Skill(
        namespace="customer-playground", name="team-red-skill-checker"
    )
    try:
        answer = await kernel.run(skill_generator, token, await request.json())
        refined_answer = await kernel.run(
            skill_refiner, token, {"sql_statement": answer.answer}
        )
        sql_check = await kernel.run(
            skill_checker, token, {"sql_statement": refined_answer.sql_statement}
        )
        output = Output(
            sql_statement=(
                refined_answer.sql_statement if sql_check.sql_harmless else None
            ),
            sql_harmless=sql_check.sql_harmless,
            explanation=sql_check.explanation,
        )

        return output

    except KernelException as exp:
        error_message = ",".join(exp.args)
        if error_message.startswith(
            "Sorry, We could not find the skill you requested in its namespace"
        ):
            error_message += "\n\nPlease check https://docs.aleph-alpha.com/products/pharia-ai/pharia-studio/tutorial/pharia-applications-quick-start/#phariaai-application-skill for instructions on deploying the skill"
        print(error_message)
        raise HTTPException(exp.status_code, error_message) from exp


@router.post("/execute-sql")
async def execute_sql(request: Request) -> Json:
    try:
        # Initialize database connection
        db_connection = init_db_connection()

        # Get the SQL statement from the request body
        request_data = await request.json()
        sql_statement = request_data.get("sql_statement")

        if not sql_statement:
            raise HTTPException(status_code=400, detail="SQL statement is required")

        # Execute the SQL statement
        result = query(db_connection, sql_statement)

        return {"status": "success", "result": result}

    except Exception as exp:
        error_message = str(exp)
        print(error_message)
        raise HTTPException(status_code=500, detail="Failed to execute SQL statement")
