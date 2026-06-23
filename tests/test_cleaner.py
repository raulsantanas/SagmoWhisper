from src.cleaner import SYSTEM_PROMPT, Cleaner


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeCompletion(self._content)


class _FakeChat:
    def __init__(self, content):
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content):
        self.chat = _FakeChat(content)


def test_clean_returns_cleaned_text():
    client = _FakeClient("Olá, mundo.")

    cleaner = Cleaner(client, "llama-3.1-8b-instant")
    result = cleaner.clean("é, tipo, olá mundo né")

    assert result == "Olá, mundo."


def test_clean_strips_whitespace():
    client = _FakeClient("  texto limpo  ")

    cleaner = Cleaner(client, "llama-3.1-8b-instant")
    result = cleaner.clean("texto cru")

    assert result == "texto limpo"


def test_clean_uses_system_prompt_and_low_temperature():
    client = _FakeClient("ok")

    cleaner = Cleaner(client, "llama-3.1-8b-instant")
    cleaner.clean("entrada")

    call = client.chat.completions.calls[0]
    assert call["model"] == "llama-3.1-8b-instant"
    assert call["temperature"] == 0.2
    messages = call["messages"]
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1] == {"role": "user", "content": "entrada"}
