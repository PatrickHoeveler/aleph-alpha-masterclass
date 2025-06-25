import json
import uuid
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from intelligence_layer.connectors import (
    CollectionPath,
    DocumentContents,
    DocumentIndexClient,
    DocumentIndexRetriever,
    DocumentPath,
    IndexConfiguration,
    IndexPath,
    InstructableEmbed,
    LimitedConcurrencyClient,
    ResourceNotFound,
    SemanticEmbed,
)
from intelligence_layer.core import InMemoryTracer, LuminousControlModel
from intelligence_layer.examples import MultipleChunkRetrieverQa, RetrieverBasedQaInput

load_dotenv()

NAMESPACE = "Studio"

document_index = DocumentIndexClient(
    token=getenv("AA_TOKEN"),
    base_document_index_url=getenv("DOCUMENT_INDEX_URL"),
)

# change this value if you want to use a collection of a different name
COLLECTION = "team-red"

collection_path = CollectionPath(namespace=NAMESPACE, collection=COLLECTION)

INDEX = "team-red-index"

index_path = IndexPath(namespace=NAMESPACE, index=INDEX)


examples_path = Path("data/examples.json")
if examples_path.exists():
    with open(examples_path, "r", encoding="utf-8") as file:
        examples = json.load(file)
        for example in examples:
            document_path = DocumentPath(
                collection_path=collection_path, document_name=str(uuid.uuid4())
            )
            document_index.add_document(
                document_path,
                contents=DocumentContents._from_modalities_json(
                    {
                        "contents": [{"modality": "text", "text": example["question"]}],
                        "metadata": {"query": example["query"]},
                    }
                ),
            )

else:
    print(f"File {examples_path} does not exist.")
