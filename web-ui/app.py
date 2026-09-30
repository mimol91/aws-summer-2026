"""
Bilingual (English / Arabic), right-to-left aware chat interface for a
Future Vision hackathon agent. Participants point it at their deployed
AgentCore Runtime and sign in with Cognito.

Configuration is read from environment variables, or from cognito_config.json
and the AgentCore project config. The one integration point you complete with
Kiro is invoke_agent(), which calls your AgentCore Runtime.

Run locally:
    pip install streamlit boto3
    streamlit run app.py --server.port 8501
"""

import json
import os
import uuid

import boto3
import streamlit as st

REGION = os.environ.get("AWS_REGION", "us-west-2")

STRINGS = {
    "en": {
        "title": "GovEase - Dubai Government Services Assistant",
        "welcome": "Hello. Tell me which government service you need and I will handle the rest.",
        "input": "Type your message",
        "signin": "Sign in",
        "email": "Email",
        "password": "Password",
        "logout": "Sign out",
    },
    "ar": {
        "title": "GovEase - مساعد الخدمات الحكومية في دبي",
        "welcome": "مرحباً. أخبرني بالخدمة الحكومية التي تحتاجها وسأتولى الباقي.",
        "input": "اكتب رسالتك",
        "signin": "تسجيل الدخول",
        "email": "البريد الإلكتروني",
        "password": "كلمة المرور",
        "logout": "تسجيل الخروج",
    },
}


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.join(HERE, "..", "GovEase")


def _runtime_arn_from_project() -> str:
    """Read the deployed runtime ARN written by `agentcore deploy` so nothing is hardcoded."""
    path = os.path.join(PROJECT, "agentcore", ".cli", "deployed-state.json")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as handle:
        state = json.load(handle)
    text = json.dumps(state)
    # Any runtime ARN in the deployed state belongs to this single-runtime project.
    import re
    match = re.search(r"arn:aws:bedrock-agentcore:[^\"]+:runtime/[^\"]+", text)
    return match.group(0) if match else ""


def load_config() -> dict:
    """Load Cognito and runtime configuration from the project's cognito_config.json."""
    config = {}
    path = os.environ.get("COGNITO_CONFIG", os.path.join(PROJECT, "cognito_config.json"))
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    # The web sign-in uses the public app client, not the machine-to-machine one.
    config["client_id"] = os.environ.get("COGNITO_CLIENT_ID") or config.get("web_client_id") or config.get("client_id", "")
    config["runtime_arn"] = os.environ.get("AGENT_RUNTIME_ARN") or _runtime_arn_from_project()
    return config


def apply_direction(lang: str) -> None:
    """Apply right-to-left layout for Arabic."""
    if lang == "ar":
        st.markdown(
            "<style>.stApp { direction: rtl; text-align: right; }</style>",
            unsafe_allow_html=True,
        )


def sign_in(config: dict, email: str, password: str) -> bool:
    client = boto3.client("cognito-idp", region_name=REGION)
    try:
        resp = client.initiate_auth(
            ClientId=config["client_id"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))
        return False
    st.session_state["token"] = resp.get("AuthenticationResult", {}).get("IdToken")
    st.session_state["actor_id"] = email.split("@")[0]
    st.session_state["session_id"] = str(uuid.uuid4())
    return True


def invoke_agent(config: dict, prompt: str) -> str:
    """Invoke the deployed AgentCore Runtime.

    Complete this with Kiro so it matches your runtime. Look up the current
    AgentCore Runtime invoke API with the MCP documentation tools. The call
    passes the prompt, the actor_id, and a stable session_id so memory works.
    """
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    payload = json.dumps({"prompt": prompt, "actor_id": st.session_state["actor_id"]}).encode("utf-8")
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=config["runtime_arn"],
        runtimeSessionId=st.session_state["session_id"],
        runtimeUserId=st.session_state["actor_id"],
        payload=payload,
    )
    body = resp["response"].read().decode("utf-8")
    if "text/event-stream" in resp.get("contentType", ""):
        return _collect_stream(body)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def _collect_stream(body: str) -> str:
    """Join the streamed Bedrock events into the assistant's final text and list the tools it called."""
    text, tools = [], []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        inner = event.get("event", {}) if isinstance(event, dict) else {}
        start = inner.get("contentBlockStart", {}).get("start", {})
        if start.get("toolUse"):
            tools.append(start["toolUse"].get("name", ""))
        delta = inner.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            text.append(delta["text"])
    reply = "".join(text).strip() or body
    if tools:
        st.session_state["last_tools"] = tools
    return reply


def main() -> None:
    config = load_config()
    lang = st.sidebar.selectbox("Language / اللغة", ["en", "ar"], index=0)
    apply_direction(lang)
    text = STRINGS[lang]

    st.title(text["title"])

    if "token" not in st.session_state:
        st.subheader(text["signin"])
        email = st.text_input(text["email"])
        password = st.text_input(text["password"], type="password")
        if st.button(text["signin"]) and email and password:
            if sign_in(config, email, password):
                st.rerun()
        return

    if st.sidebar.button(text["logout"]):
        st.session_state.clear()
        st.rerun()

    if "history" not in st.session_state:
        st.session_state["history"] = [("assistant", text["welcome"])]

    for role, message in st.session_state["history"]:
        with st.chat_message(role):
            st.write(message)

    prompt = st.chat_input(text["input"])
    if prompt:
        st.session_state["history"].append(("user", prompt))
        with st.chat_message("user"):
            st.write(prompt)
        with st.spinner("..."):
            reply = invoke_agent(config, prompt)
        st.session_state["history"].append(("assistant", reply))
        with st.chat_message("assistant"):
            st.write(reply)
        tools = st.session_state.pop("last_tools", None)
        if tools:
            st.caption("Tools called: " + " -> ".join(tools))


if __name__ == "__main__":
    main()
