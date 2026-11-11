import json

import httpx
import pytest

from app.llm import DEFAULT_MODEL, ENV_KEYS, GroqLLM, LLMError, LLMSettings, read_settings
from app.rag import Draft


@pytest.fixture
def clean_environment(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def client_for(handler):
    return GroqLLM(LLMSettings("groq", DEFAULT_MODEL, "fixture-secret"), httpx.MockTransport(handler))


def test_settings_precedence_and_hidden_secret(tmp_path, monkeypatch, clean_environment):
    path = tmp_path / ".env"
    path.write_text('# Comentário\nGROQ_API_KEY="file-fixture"\n', "utf-8")
    monkeypatch.setenv("GROQ_API_KEY", "environment-fixture")
    settings = read_settings(path)
    assert settings.api_key == "environment-fixture"
    assert "fixture" not in repr(settings)
    assert settings.model == DEFAULT_MODEL


@pytest.mark.parametrize("content", [
    "", "GROQ_API_KEY=\n", "GROQ_API_KEY=has space\n", "GROQ_API_KEY=a\nGROQ_API_KEY=b\n",
    "TAXMIND_LLM_PROVIDER=unknown\nGROQ_API_KEY=fixture\n",
])
def test_incomplete_or_invalid_settings(tmp_path, clean_environment, content):
    path = tmp_path / ".env"
    path.write_text(content, "utf-8")
    with pytest.raises(LLMError) as error:
        read_settings(path)
    assert error.value.status_code == 503


def test_structured_request_and_schema_validation():
    def handler(request):
        assert request.url == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer fixture-secret"
        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
        assert body["messages"][0] == {"role": "system", "content": "Instrução de teste"}
        assert body["temperature"] == 0
        assert "tools" not in body
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"decision": "abstain", "claims": []}),
        }}]})

    result = client_for(handler).complete("Instrução de teste", {"question": "Fixture"}, Draft)
    assert result.decision == "abstain"


@pytest.mark.parametrize("status,expected", [(401, 503), (403, 503), (429, 429), (500, 502), (302, 502)])
def test_provider_errors_do_not_expose_response_or_secret(status, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="fixture-secret private upstream message")

    with pytest.raises(LLMError) as error:
        client_for(handler).complete("fixture", {}, Draft)
    assert error.value.status_code == expected
    assert "fixture-secret" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("choice", [
    {"finish_reason": "length", "message": {"content": "{}"}},
    {"finish_reason": "stop", "message": {"content": "not json"}},
    {"finish_reason": "stop", "message": {"content": '{"decision":"answer","claims":[],"extra":1}'}},
    {"finish_reason": "stop", "message": {"content": None}},
    {"finish_reason": "stop", "message": {"refusal": "fixture", "content": "{}"}},
])
def test_invalid_incomplete_or_refused_generation(choice):
    with pytest.raises(LLMError):
        client_for(lambda request: httpx.Response(200, json={"choices": [choice]})).complete("fixture", {}, Draft)


def test_timeout_and_connection_error():
    for exception, expected in [(httpx.ReadTimeout, 504), (httpx.ConnectError, 503)]:
        def handler(request):
            raise exception("fixture-secret", request=request)

        with pytest.raises(LLMError) as error:
            client_for(handler).complete("fixture", {}, Draft)
        assert error.value.status_code == expected
        assert "fixture-secret" not in str(error.value)


def test_health_and_missing_credential_are_local_and_explicit(monkeypatch, tmp_path, clean_environment):
    from fastapi.testclient import TestClient
    import app.main as main

    def absent():
        return read_settings(tmp_path / "absent")

    monkeypatch.setattr(main, "read_settings", absent)
    client = TestClient(main.app)
    assert client.get("/health").json()["rag_status"] == "not_configured"
    response = client.post("/ask", json={"question": "Qual é a CBS?"})
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]
    monkeypatch.setattr(main, "read_settings", lambda: LLMSettings("groq", DEFAULT_MODEL, "fixture-secret"))
    health = client.get("/health")
    assert health.json()["rag_status"] == "configured"
    assert "fixture-secret" not in health.text
