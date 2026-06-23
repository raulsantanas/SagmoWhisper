SYSTEM_PROMPT = (
    "Você corrige transcrições de fala em português do Brasil. "
    "Remova hesitações (é, tipo, né), corrija pontuação e ortografia, "
    "mantenha exatamente o sentido e o tom. "
    "Responda APENAS com o texto corrigido, sem comentários nem aspas."
)


class Cleaner:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def clean(self, text: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return completion.choices[0].message.content.strip()
