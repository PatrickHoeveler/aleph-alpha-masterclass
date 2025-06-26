from dotenv import load_dotenv
from pharia_skill import ChatParams, Message
from pydantic import BaseModel
from collections.abc import Iterable
from typing import Iterable
from statistics import mean
from uuid import uuid4
import requests
import os
import json

from intelligence_layer.connectors import StudioClient

from intelligence_layer.core import NoOpTracer, Task, TaskSpan

from intelligence_layer.evaluation import (
    Example,
    StudioDatasetRepository,
    AggregationLogic,
    StudioBenchmarkRepository,
    SingleOutputEvaluationLogic,
)

from pharia_skill.testing import DevCsi
import logging
import math

from pharia_skill import TopLogprobs, ChatResponse
from pharia_skill.testing import DevCsi
from jinja2 import Template
from abc import ABC

from qa import custom_rag

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)



from intelligence_layer.evaluation.dataset.domain import Example
from qa import Input, Output
import tqdm

load_dotenv(".env")
PHARIA_STUDIO_PROJECT_NAME = "team-red"

# studio_client = StudioClient(
#     project=PHARIA_STUDIO_PROJECT_NAME,
#     studio_url=os.getenv("PHARIA_STUDIO_ADDRESS"),
#     auth_token=os.getenv("PHARIA_AI_TOKEN"),
#     create_project=False,
# )


class QATask(Task[Input, Output]):
    def __init__(self) -> None:
        self.token = os.getenv("PHARIA_AI_TOKEN")
        self.kernel_url = os.getenv("PHARIA_KERNEL_ADDRESS")
        self.skill_namespace = "team-red"
        self.skill_name = "team-red-skill"

    def do_run(self, input: Input, task_span: TaskSpan) -> Output:
        # try:
        #     headers = {"Authorization": f"Bearer {self.token}"}
        #     url = f"{self.kernel_url}/v1/skills/{self.skill_namespace}/{self.skill_name}/run"
        #     response = requests.post(
        #         url,
        #         json=input.model_dump() if isinstance(input, BaseModel) else input,
        #         headers=headers,
        #     )
        #     response = response.json()
        #     return Output(answer=response["answer"])
        # except Exception as e:
        #     print(e)
        #     return Output(answer=None)


        csi = DevCsi().with_studio("team-red")
        res = custom_rag(csi, Input(question="Please query the number of tables."))
        print("---- result ----")
        print(res.answer)
        return Output(answer=res.answer)

class ExpectedOutput(BaseModel):
    query: str | None


#studio_dataset_repo = StudioDatasetRepository(studio_client=studio_client)

with open("../test-data/examples.json", 'r', encoding='utf-8') as file:
    test_set = json.load(file)

    
def read_sql_file(filepath: str) -> str:
    """
    Reads the contents of a SQL file and returns it as a string.

    Parameters:
        filepath (str): The path to the .sql file.

    Returns:
        str: The SQL content as a string.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        return str(sql_content)
    except FileNotFoundError:
        return f"Error: File not found at {filepath}"
    except Exception as e:
        return f"An error occurred: {e}"



# examples = [
#     Example(
#         input=Input(question=example["question"], db_schema=read_sql_file('..\\test-data\database_schemas\\'+ example["db_id"]+".sql")),
#         expected_output=ExpectedOutput(
#             query=example["query"]
#         ),
#     )
#     for example in test_set
# ]

# studio_dataset = studio_dataset_repo.create_dataset(
#     examples=examples, dataset_name="team-red-eval-dataset"
# )

# studio_dataset.id


class Checker(ABC):

    def __init__(self) -> None:
        self.dev_csi = DevCsi().with_studio(PHARIA_STUDIO_PROJECT_NAME)
        self.evaluation_model = "llama-3.3-70b-instruct"
        self.logger = logging.getLogger(__name__)

    def get_metric(
        self, question: str, db_schema: str, expected_answer: str, generated_answer: str
    ) -> ChatResponse:
        system_prompt = self.system_prompt
        user_prompt = self.user_prompt.format(
            question=question,
            db_schema=db_schema,
            expected_answer=expected_answer,
            generated_answer=generated_answer,
        )

        messages = [
            Message.system(system_prompt),
            Message.user(user_prompt),
            Message.assistant("Score: "),
        ]
        params = ChatParams(max_tokens=10, temperature=0.0, logprobs=TopLogprobs(10))
        response = self.dev_csi.chat(
            model=self.evaluation_model, messages=messages, params=params
        )

        content = response.message.content.strip()
        fallback_score = self.parse_score(content)

        probs = getattr(response, "logprobs", None)
        if (
            not probs
            or not hasattr(probs, "__getitem__")
            or len(probs) < 2
            or not hasattr(probs[-2], "top")
        ):
            self.logger.warning("No logprobs found")
            return fallback_score

        logprobs = probs[-2].top
        return self.compute_weighted_score(logprobs, fallback_score)

    @staticmethod
    def parse_score(score_str: str) -> float:
        """Convert score string to float if valid, else return fallback"""
        return (
            float(score_str)
            if score_str.isdigit() and 0 <= float(score_str) <= 10
            else 1
        )

    @staticmethod
    def compute_weighted_score(logprobs, fallback_score: float) -> float:
        """Compute weighted score from token logprobs"""
        digit_probs = {
            float(prob.token): math.exp(prob.logprob)
            for prob in logprobs
            if prob.token.isdigit() and 0 <= float(prob.token) <= 10
        }

        total = sum(digit_probs.values())
        if total == 0:
            return fallback_score

        normalized = {k: v / total for k, v in digit_probs.items()}
        return round(sum(k * v for k, v in normalized.items()), 1)

class AccuracyChecker(Checker):

    def __init__(self) -> None:
        super().__init__()
        self.system_prompt = """
        You are a highly precise evaluation assistant specialized in assessing technical accuracy and correctness.

        Your task is to evaluate how accurately the generated answer reflects the technical approach from the expected answer.

        SCORING RUBRIC (1-10):
        - 9-10: Highly accurate - No technical errors, all SQL would work correctly
        - 7-8: Mostly accurate - Minor factual discrepancies or unclear SQL query
        - 5-6: Moderately accurate - Some technical errors but generally correct direction
        - 3-4: Low accuracy - Multiple technical errors or significant misrepresentations of the data base schema
        - 1-2: Poor accuracy - Major technical errors, contradicts expected SQL approach

        EVALUATION CRITERIA:
        1. Is the SQL queries technical syntactically correct?
        2. Would the SQL query work for the referenced db schema?
        3. Are there any contradictions with the expected answer?
        4. Is the information presented without distortion or misinterpretation?

        Return only a single integer score between 1 and 10. 
        """
        self.user_prompt: Template = """
        TASK: Evaluate the factual accuracy of the generated answer against the expected reference answer.

        QUESTION:
        {question}

        DATABASE SCHEMA:
        {db_schema}

        EXPECTED ANSWER (Reference):
        {expected_answer}

        GENERATED ANSWER (To Evaluate):
        {generated_answer}

        EVALUATION STEPS:
        1. Identify the SQL query approach used in the generated and expected answer
        2. Compare how each query relates to the Database schema
        3. Check for any syntactically incorrect SQL 
        4. Assess whether the SQL query could retrieve the data from the SQL data base.

        IMPORTANT: Respond with ONLY a single integer from 1 to 10. Do not include any explanation or additional text.
        """


class FactualityChecker(Checker):
    def __init__(self) -> None:
        super().__init__()
        self.system_prompt = """
        You are a highly precise evaluation assistant specialized in assessing a SQL query's precision and relevance.

        Your task is to evaluate how well the generated SQL query stays within the bounds of a real SQL query without adding hallucinated or irrelevant content.

        SCORING RUBRIC (1-10):
        - 9-10: Excellent precision - Syntactically correct SQL which retrieves data relevant to the user's question, no hallucinations or fabrications
        - 7-8: Good precision - Mostly relevant and syntactically SQL, minimal irrelevant information or slight difference to the user request
        - 5-6: Fair precision - Some irrelevant and syntactically incorrect SQL or minor SQL errors.
        - 3-4: Poor precision - Significant irrelevant content with little to no resemblens to SQL and irrelevant to the user question.
        - 1-2: Very poor precision - Extensive hallucinations or fabricated information. Not an SQL query.

        EVALUATION CRITERIA:
        1. Does the answer represent an SQL query that is able to retrieve the data the user requested?
        2. Are there any fabricated details, dates, or claims that not part of an SQL query?
        3. Is the SQL query syntactically sound?
        
        Return only a single integer score between 1 and 10. 
        """
        self.user_prompt: Template = """
        TASK: Evaluate the information precision and relevance of the generated answer, focusing on detecting hallucinations or fabricated content.

        QUESTION:
        {question}

        DATABASE SCHEMA:
        {db_schema}
        
        EXPECTED ANSWER (Reference):
        {expected_answer}

        GENERATED ANSWER (To Evaluate):
        {generated_answer}

        EVALUATION STEPS:
        1. Compare the generated answer against the reference to identify whether the queries achieve the same goal.
        2. Check for fabricated variable/column/row names not in the data base schema based on the reference query
        3. Assess whether the answer is only an SQL query.
        4. Check if the query is syntactically sound.

        IMPORTANT: Respond with ONLY a single integer from 1 to 10. Do not include any explanation or additional text.
        """


class EfficiencyChecker(Checker):
    def __init__(self) -> None:
        super().__init__()
        self.system_prompt = """
        You are a highly analytical and precise assistant specialized in evaluating the efficiency of SQL queries.

        Your task is to compare a generated SQL query against a reference (expected) SQL query and assess how efficient the generated query is in achieving the same result, given the same user request and database schema.

        SCORING RUBRIC (1-10):
        9-10: Highly Efficient - Matches or exceeds the reference in performance (e.g., uses indexes, avoids unnecessary joins/subqueries, minimizes data scanned).
        7-8: Efficient - Slightly less optimal than the reference but still performant and scalable.
        5-6: Moderately Efficient - Functionally correct but includes inefficiencies (e.g., redundant operations, non-sargable filters).
        3-4: Inefficient - Contains significant inefficiencies that could impact performance.
        1-2: Very Inefficient - Poorly constructed, likely to cause performance issues or fail to scale.
        
        EVALUATION CRITERIA:
        Query Plan Efficiency - Does the query structure allow for efficient execution (e.g., index usage, join order, filtering)?
        Redundancy - Does the query avoid unnecessary operations (e.g., repeated subqueries, unused columns)?
        Scalability - Will the query perform well on large datasets?
        Equivalence - Does the query return the same result set as the reference?
        Best Practices - Does the query follow SQL optimization best practices?
        
        INSTRUCTIONS:
        Focus only on efficiency, not correctness or completeness of the result.
        Assume both queries are syntactically valid and return the same data.
        Do not explain your reasoning.
        Return only a single integer score from 1 to 10.
        """
        self.user_prompt = """
        TASK: Evaluate how completely the generated answer covers the content from the expected answer.

        QUESTION:
        {question}

        DATABASE SCHEMA:
        {db_schema}

        EXPECTED ANSWER (Reference):
        {expected_answer}

        GENERATED ANSWER (To Evaluate):
        {generated_answer}
        
        INSTRUCTIONS:
        1. Focus only on efficiency, not correctness or completeness of the result.
        2. Assume both queries are syntactically valid and return the same data.
        3. Do not explain your reasoning.
        
        IMPORTANT: Respond with ONLY a single integer from 1 to 10. Do not include any explanation or additional text.
        """


class QaEvaluation(BaseModel):
    efficiency_score: float = 0.0  # Coverage of expected content
    accuracy_score: float = 0.0  # Factual correctness
    factuality_score: float = 0.0  # Absence of hallucinations
    # correct_sources: list[str] = []  # Properly cited sources
    # incorrect_sources: list[str] = []  # Incorrectly cited sources
    # source_accuracy: float = 0.0  # Precision of source citations
    # source_recall: float = 0.0  # Recall of expected sources


class QaEvaluationLogic(
    SingleOutputEvaluationLogic[Input, Output, ExpectedOutput, QaEvaluation]
):

    def __init__(self) -> None:
        super().__init__()
        self.accuracy_checker = AccuracyChecker()
        self.factuality_checker = FactualityChecker()
        self.efficiency_checker = EfficiencyChecker()

    def do_evaluate_single_output(
        self, example: Example[Input, ExpectedOutput], output: Output
    ) -> QaEvaluation:

        efficiency_score = self.efficiency_checker.get_metric(
            question=example.input.question,
            db_schema=example.input.db_schema,
            expected_answer=example.expected_output.query,
            generated_answer=output.answer,
        )

        accuracy_score = self.accuracy_checker.get_metric(
            question=example.input.question,
            db_schema=example.input.db_schema,
            expected_answer=example.expected_output.query,
            generated_answer=output.answer,
        )

        factuality_score = self.factuality_checker.get_metric(
            question=example.input.question,
            db_schema=example.input.db_schema,
            expected_answer=example.expected_output.query,
            generated_answer=output.answer,
        )

        # correct_sources, incorrect_sources = self._check_sources(
        #     expected_sources=example.expected_output.sources,
        #     generated_sources=output.sources,
        # )
        return QaEvaluation(
            efficiency_score=efficiency_score,
            accuracy_score=accuracy_score,
            factuality_score=factuality_score,
            #correct_sources=correct_sources,
            #incorrect_sources=incorrect_sources,
            # source_accuracy=self._calculate_source_accuracy(
            #     expected_sources=example.expected_output.sources,
            #     generated_sources=output.sources,
            # ),
            # source_recall=self._calculate_source_recall(
            #     expected_sources=example.expected_output.sources,
            #     generated_sources=output.sources,
            # ),
        )

    # def _check_sources(
    #     self, expected_sources: list[str], generated_sources: list[str]
    # ) -> tuple[list[str], list[str]]:
    #     if not generated_sources:
    #         return [], []

    #     if not expected_sources:
    #         return [], generated_sources.copy()

    #     expected_set = {source.lower().strip() for source in expected_sources}
    #     generated_set = {source.lower().strip() for source in generated_sources}

    #     correct_sources_lower = expected_set.intersection(generated_set)

    #     correct_sources = []
    #     incorrect_sources = []

    #     for source in generated_sources:
    #         if source.lower().strip() in correct_sources_lower:
    #             correct_sources.append(source)
    #         else:
    #             incorrect_sources.append(source)

    #     return correct_sources, incorrect_sources

    # def _calculate_source_accuracy(
    #     self, expected_sources: list[str], generated_sources: list[str]
    # ) -> float:

    #     if not generated_sources:
    #         return 0.0 if expected_sources else 1.0

    #     correct_sources, _ = self._check_sources(expected_sources, generated_sources)
    #     return len(correct_sources) / len(generated_sources)

    # def _calculate_source_recall(
    #     self, expected_sources: list[str], generated_sources: list[str]
    # ) -> float:
    #     if not expected_sources:
    #         return 1.0

    #     if not generated_sources:
    #         return 0.0

    #     expected_set = {source.lower().strip() for source in expected_sources}
    #     generated_set = {source.lower().strip() for source in generated_sources}

    #     found_expected = expected_set.intersection(generated_set)
    #     return len(found_expected) / len(expected_sources)

test_example = test_set[0]
task = QATask()
input = Input(question=test_example["question"], db_schema=read_sql_file('..\\test-data\database_schemas\\'+ test_example["db_id"]+".sql"))
output = task.run(input, NoOpTracer())

example = Example(
    input=input,
    expected_output=ExpectedOutput(
        query=test_example.get("query")),
)

evaluation_logic = QaEvaluationLogic()
evaluation = evaluation_logic.do_evaluate_single_output(example, output)

print(evaluation)


class QaAggregatedEvaluation(BaseModel):
    average_efficiency_score: float
    average_accuracy_score: float
    average_factuality_score: float


class QaAggregationLogic(
    AggregationLogic[
        QaEvaluation,
        QaAggregatedEvaluation,
    ]
):
    def aggregate(self, evaluations: Iterable[QaEvaluation]) -> QaAggregatedEvaluation:
        evaluation_list = list(evaluations)
        if len(evaluation_list) == 0:
            return QaAggregatedEvaluation(
                average_efficiency_score=0.0,
                average_accuracy_score=0.0,
                average_factuality_score=0.0,
                )

        average_efficiency_score = round(
            mean(eval.efficiency_score for eval in evaluation_list), 2
        )
        average_accuracy_score = round(
            mean(eval.accuracy_score for eval in evaluation_list), 2
        )
        average_factuality_score = round(
            mean(eval.factuality_score for eval in evaluation_list), 2
        )

        return QaAggregatedEvaluation(
            average_efficiency_score=average_efficiency_score,
            average_accuracy_score=average_accuracy_score,
            average_factuality_score=average_factuality_score,
        )
    

test_example2 = test_set[1]
task = QATask()
input2 = Input(question=test_example["question"], db_schema=read_sql_file('..\\test-data\database_schemas\\'+ test_example["db_id"]+".sql"))
output2 = task.run(input, NoOpTracer())

example2 = Example(
    input=input2,
    expected_output=ExpectedOutput(
        query=test_example2.get("query")),
)

aggregation_logic = QaAggregationLogic()
evaluation_logic = QaEvaluationLogic()

evaluation_1 = evaluation_logic.do_evaluate_single_output(example, output)
evaluation_2 = evaluation_logic.do_evaluate_single_output(example2, output2)
aggregation = aggregation_logic.aggregate([evaluation_1, evaluation_2])

print(evaluation_1)
print(evaluation_2)
print(f"Aggregation: {aggregation}")