# Stack Tecnológica

## Linguagem Principal

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Python     | 3.8+   | Linguagem única do projeto |

---

## Dependências Python

| Biblioteca            | Versão  | Propósito                                        |
|-----------------------|---------|--------------------------------------------------|
| `google-generativeai` | latest  | Cliente para Gemini API (narrativa com IA)       |
| `google-cloud-texttospeech` | latest | TTS neural em pt-BR (voz principal)       |
| `pygame`              | latest  | Engine de reprodução de áudio (SFX + TTS MP3)   |
| `SpeechRecognition`   | latest  | Reconhecimento de voz (entrada por microfone)    |
| `pyaudio`             | latest  | Interface com dispositivos de áudio              |
| `requests`            | latest  | HTTP client (ElevenLabs API)                     |
| `python-dotenv`       | latest  | Gerenciamento de variáveis de ambiente (.env)    |
| `pyttsx3`             | latest  | TTS local offline (fallback gratuito)            |

---

## APIs Externas

### Google Gemini 1.5-Flash (OBRIGATÓRIO)
- **Custo**: Pay-per-use (tokens)
- **Uso no projeto**:
  - Mestre do Jogo (RPG): geração de narrativa open-world
  - Mestre dos Contos: adaptação literária estruturada
  - Archivista: extração e atualização de estado
- **Parâmetros usados**:
  - Temperature: 0.75
  - Max output tokens: 1024
  - Safety filters: BLOCK_NONE (permitir temas dramáticos)
- **Configuração**: `GEMINI_API_KEY` no `.env`

### Google Cloud TTS (RECOMENDADO)
- **Custo**: ~$4 por 1 milhão de caracteres
- **Vozes**:
  - Narradora: `pt-BR-Neural2-A` (feminina)
  - Mestre: `pt-BR-Neural2-B` (masculina)
- **Formato saída**: MP3 / Linear16
- **Taxa de amostragem**: 22.050 Hz
- **Velocidade**: 1.5x (mais dinâmica)
- **Configuração**: `GOOGLE_APPLICATION_CREDENTIALS` (JSON do service account)

### ElevenLabs (OPCIONAL)
- **Custo**: ~$22 por 1 milhão de caracteres
- **Voice ID padrão**: `21m00Tcm4TlvDq8ikWAM` (Rachel)
- **Configuração**: `ELEVENLABS_API_KEY` no `.env`

### Google Speech Recognition (incluído em SpeechRecognition)
- **Custo**: Gratuito (quota generosa)
- **Idioma configurado**: `pt-BR`
- **Uso**: Entrada de voz do jogador

---

## Cadeia de Prioridade TTS

```
1. Google Cloud TTS  ──► disponível? → usa (melhor qualidade)
        │ não
        ▼
2. pyttsx3 (local)   ──► disponível? → usa (offline, gratuito)
        │ não
        ▼
3. ElevenLabs        ──► disponível? → usa (premium)
        │ não
        ▼
4. Sem áudio         ──► só exibe texto no terminal
```

---

## Formato dos Dados

| Formato | Uso                                                        |
|---------|------------------------------------------------------------|
| JSON    | Configuração (`config.json`), estado (`estado_do_mundo.json`), campanhas (NPCs, locais, itens, eventos) |
| Markdown| Documentação das campanhas (`campanha.md`)                 |
| TXT     | Texto original dos contos literários                       |
| MP3     | Efeitos sonoros e narração em cache                        |
| .env    | Variáveis de ambiente (chaves API, paths)                  |

---

## Ambiente de Execução

```
Terminal / Console
    ↑ stdin  ↓ stdout

Microfone → pyaudio → SpeechRecognition → Google STT API
                                              ↓
                                          texto

Caixa de som ← pygame ← MP3 ← Google Cloud TTS / pyttsx3
```

---

## Variáveis de Ambiente

```env
# Obrigatório
GEMINI_API_KEY=AIza...

# Google Cloud TTS (recomendado)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=meu-projeto-id

# ElevenLabs (opcional)
ELEVENLABS_API_KEY=sk_...
```
