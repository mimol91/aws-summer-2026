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
    import re
    # The AgentCore starter toolkit writes .bedrock_agentcore.yaml; the Node CLI writes deployed-state.json.
    candidates = [
        os.path.join(PROJECT, "app", "GovEaseAgent", ".bedrock_agentcore.yaml"),
        os.path.join(PROJECT, "agentcore", ".cli", "deployed-state.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        match = re.search(r"arn:aws:bedrock-agentcore:[^\s\"']+:runtime/[^\s\"']+", text)
        if match:
            return match.group(0)
    return ""


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
    st.session_state["token"] = resp.get("AuthenticationResult", {}).get("AccessToken")
    st.session_state["actor_id"] = email.split("@")[0]
    st.session_state["session_id"] = f"web-{uuid.uuid4()}-{uuid.uuid4()}"
    return True


def invoke_agent(config: dict, prompt: str) -> str:
    """Invoke the deployed AgentCore Runtime with the signed-in user's Cognito access token.

    The runtime is configured with a Cognito JWT authorizer, so the call is a plain HTTPS
    request with a Bearer token rather than a SigV4-signed SDK call.
    """
    import urllib.parse
    import urllib.request

    url = (
        f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/"
        f"{urllib.parse.quote(config['runtime_arn'], safe='')}/invocations?qualifier=DEFAULT"
    )
    payload = json.dumps({"prompt": prompt, "actor_id": st.session_state["actor_id"]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {st.session_state['token']}",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": st.session_state["session_id"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read().decode("utf-8")
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return f"Error {exc.code}: {exc.read().decode('utf-8', 'ignore')[:300]}"
    if "text/event-stream" in content_type:
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
