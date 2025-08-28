import os
from openai.version import VERSION as OPENAI_VERSION
from pathlib import Path
import json
from dotenv import load_dotenv
from promptflow.core import tool

# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need

## Ojo que no falte OPENAI api key en env, cargada

# AFTER (good)
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")


import json
from pathlib import Path

LOG_PATH = Path("/tmp/pf_debug_raw_.log")
_log_initialized = False

def debug_log(value, label=None):
    global _log_initialized

    try:
        # Overwrite the file only once per run
        mode = "w" if not _log_initialized else "a"
        with open(LOG_PATH, mode) as f:
            if label:
                f.write(f"\n=== {label} ===\n")
            if isinstance(value, (dict, list)):
                f.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
            else:
                f.write(str(value) + "\n")
        _log_initialized = True
    except Exception as e:
        print("Logging failed:", e)


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
def run_llm_plain_text(
    prompt: str,
    deployment_name: str,
    max_tokens: int = 16000,
    temperature: float = 0.4,
    top_p: float = 1.0,
    n: int = 1,
    stop: list = None,
    presence_penalty: float = 0,
    frequency_penalty: float = 0,
    logit_bias: dict = {},
    user: str = "",
    **kwargs,
) -> str:
    """
    Calls the LLM with the provided prompt and returns the plain text response.

    Args:
        prompt (str): The prompt to send to the LLM.
        deployment_name (str): The deployment name of the model.
        max_tokens (int): Maximum tokens for the response.
        temperature (float): Sampling temperature.
        top_p (float): Nucleus sampling parameter.
        n (int): Number of completions to generate.
        stop (list): Stop sequences.
        presence_penalty (float): Presence penalty.
        frequency_penalty (float): Frequency penalty.
        logit_bias (dict): Logit bias mapping.
        user (str): User identifier for tracing.

    Returns:
        str: The plain text response from the LLM.
    """

    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print("\n=== 🛠 Calling LLM with the following parameters ===")
    print("Model:", deployment_name)
    print("Prompt length (chars):", len(prompt))
    print("Prompt (start):", repr(prompt[:300]))

    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert summarization assistant."},
                {"role": "user", "content": prompt}
            ],
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

        choice = response.choices[0]
        reply_content = choice.message.content.strip()

        # Debug logging
        print("=== 📦 Full Response ===")
        print(reply_content[:1000], "..." if len(reply_content) > 1000 else "")

        return reply_content

    except Exception as e:
        print("\n=== ❗️LLM Call Failed ===")
        print("Type:", type(e).__name__)
        print("Message:", str(e))
        if hasattr(e, 'response'):
            print("Full HTTP response (OpenAI):")
            print(e.response)
        raise e


import inspect
from pprint import pprint

def debug_llm_response(response):
    print("\n=== 📡 RAW RESPONSE ===")
    pprint(response)

    debug_log(response.dict(), "FULL RAW RESPONSE")

    try:
        choice = response.choices[0]
        print("\n=== ✅ CHOICE TYPE ===", type(choice))
        print("=== 📋 CHOICE OBJECT ===")
        pprint(choice)

        msg = choice.message
        print("\n=== 🧾 MESSAGE ===")
        pprint(msg)

        if msg.content:
            print("\n=== 📝 TEXT CONTENT ===")
            print(msg.content)

        if msg.function_call:
            print("\n=== ⚙️ FUNCTION CALL ===")
            print("Function Name:", msg.function_call.name)
            print("Arguments Raw:", msg.function_call.arguments)
            try:
                parsed = json.loads(msg.function_call.arguments)
                print("\n=== ✅ PARSED JSON OUTPUT ===")
                pprint(parsed)
            except Exception as e:
                print("\n=== ❌ PARSE ERROR ===")
                print("Message:", str(e))
                print("Raw Args:", msg.function_call.arguments)
        else:
            print("\n=== ⚠️ No function_call in message ===")

    except Exception as e:
        print("\n=== ❌ ERROR: Invalid response structure ===")
        print(str(e))




# def main(prompt: str, deployment_name: str, schema_path: str) -> dict:
#     # Assume we call OpenAI or similar
#     response_text = call_model(prompt, deployment_name)

#     # Load schema dynamically
#     with open(schema_path, "r") as f:
#         schema = json.load(f)

#     parsed = fun?? (response_text, schema)
#     return {"result": parsed}
