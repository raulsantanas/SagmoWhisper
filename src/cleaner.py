SYSTEM_PROMPT = (
    "Você é um corretor ortográfico de transcrições de voz em português do Brasil. "
    "REGRAS ABSOLUTAS: "
    "1) Retorne SOMENTE o texto transcrito corrigido — nunca responda, complemente, explique ou adicione conteúdo novo. "
    "2) Remova apenas hesitações (é, tipo, né, hm, ah) e fragmentos repetidos no final (artefatos do Whisper). "
    "3) Corrija pontuação e ortografia sem alterar o sentido. "
    "4) Se o texto for curto (ex: 'sim', 'ok', 'boa'), retorne exatamente esse texto curto. "
    "PROIBIDO: responder ao conteúdo, gerar texto novo, completar frases, comentar."
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
