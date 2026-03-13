import os
from openai.version import VERSION as OPENAI_VERSION
from pathlib import Path
import json
from dotenv import load_dotenv
from promptflow.core import tool

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need


def to_bool(value) -> bool:
    return str(value).lower() == "true"


def get_client():
    if OPENAI_VERSION.startswith("0."):
        raise Exception(
            "Please upgrade your OpenAI package to version >= 1.0.0 or using the command: pip install --upgrade openai."
        )
    api_key = os.environ["OPENAI_API_KEY"]
    conn = dict(
        api_key=os.environ["OPENAI_API_KEY"],
    )
    if api_key.startswith("sk-"):
        from openai import OpenAI as Client
    else:
        from openai import AzureOpenAI as Client
        conn.update(
            azure_endpoint=os.environ.get("AZURE_OPENAI_API_BASE", "azure"),
            api_version=os.environ.get("OPENAI_API_VERSION", "2023-07-01-preview"),
        )

    if "OPENAI_API_KEY" not in os.environ or "AZURE_OPENAI_API_BASE" not in os.environ:
        # load environment variables from .env file
        load_dotenv()

    if "OPENAI_API_KEY" not in os.environ:
        raise Exception("Please specify environment variables: OPENAI_API_KEY")

    return Client(**conn)



def load_schema(file_path: str):
    # Load JSON schema from the specified file path
    with open(file_path, 'r') as schema_file:
        return json.load(schema_file)


# Load schema once (relative to this file’s location)
# SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schemas/generate_fixes.json")
# SCHEMA_PATH = "./parsed_message_advanced.json"
# function_schema = load_schema(SCHEMA_PATH)
# function_name = 'parsed_message'



from pathlib import Path

@tool
def run_llm_schema_tool(
    prompt: str,
    # for AOAI, deployment name is customized by user, not model name.
    deployment_name: str,
    schema_path: str,
    function_name: str = "parsed_message",
    suffix: str = None,
    max_tokens: int = 16000,
    temperature: float = .4,
    top_p: float = 1.0,
    n: int = 1,
    echo: bool = False,
    stop: list = None,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
    logit_bias: dict = {},
    user: str = "",
    **kwargs,
) -> dict:


    # TODO: remove below type conversion after client can pass json rather than string.
    echo = to_bool(echo)


    from pathlib import Path

    schema_path = Path(schema_path).expanduser().resolve()
    assert schema_path.exists(), f"Schema path does not exist: {schema_path}"
    schema = load_schema(str(schema_path))
    # schema = load_schema(schema_path)

    if "name" not in schema or schema["name"] != function_name:
        raise ValueError(f"Schema does not match expected name '{function_name}': got {schema}")


    client = get_client()

    print("FUNCTION NAME:", function_name)
    print("FUNCTIONS AVAILABLE:", [schema.get("name")])

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": ""},
            {"role": "user", "content": prompt}
        ],
        functions=[schema],
        function_call={"name": function_name},
        model=deployment_name,
        max_tokens=int(max_tokens),
        temperature=float(temperature),
        top_p=float(top_p),
        n=int(n),
        stop=stop if stop else None,
        presence_penalty=float(presence_penalty),
        frequency_penalty=float(frequency_penalty),
        logit_bias=logit_bias or {},
        user=user,
    )

    raw_args = response.choices[0].message.function_call.arguments

    try:
        parsed = json.loads(raw_args)
    except json.JSONDecodeError as e:
        raise ValueError(f"Function call output is not valid JSON:\n{raw_args}") from e

    # ✅ OPTIONAL: append result to a heap-style file for long-term collection
    heap_path = Path("/home/matias/dev/my-agents/Cities/gpt_chats/flows/gpt_chats2/outputs_heap.jsonl")
    heap_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(heap_path, "a") as f:
        json.dump(parsed, f, ensure_ascii=False)
        f.write("\n")

    return parsed



# def main(prompt: str, deployment_name: str, schema_path: str) -> dict:
#     # Assume we call OpenAI or similar
#     response_text = call_model(prompt, deployment_name)

#     # Load schema dynamically
#     with open(schema_path, "r") as f:
#         schema = json.load(f)

#     parsed = fun?? (response_text, schema)
#     return {"result": parsed}
