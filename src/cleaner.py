SYSTEM_PROMPT = (
    "Você corrige transcrições de fala em português do Brasil. "
    "Regras: "
    "1) Remova hesitações (é, tipo, né, hm, ah). "
    "2) Corrija pontuação e ortografia. "
    "3) Remova repetições e fragmentos duplicados no final da frase — artefatos comuns do Whisper (ex: 'que em menos' após a frase já ter terminado). "
    "4) Mantenha exatamente o sentido e o tom original. "
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
