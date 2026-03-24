# IncluSpeech - Microsoft Innovation March Challenge 2026
### Multimodal AI communication hub for inclusive, real-time collaboration

IncluSpeech bridges the communication gap between Deaf, hard-of-hearing, and hearing individuals by combining real-time speech-to-text transcription, bidirectional sign language translation, and automated accessible meeting summaries — all powered by Azure AI and delivered through a seamless, privacy-conscious experience.

## What it does

IncluSpeech aims to deliver high-accuracy transcription streamed directly to participants in real time, alongside bidirectional communication between spoken language and sign language through video-based gesture recognition. Automated meeting summarization converts live conversations into accessible, structured notes on the fly — ensuring no participant is left behind.

## Azure services

- **Azure AI Speech** — real-time transcription, speaker diarization, and bilingual language detection (EN/ES)
- **Azure OpenAI Service (GPT-4o)** — dynamic per-utterance translation between English and Spanish
- **Azure Custom Vision** — ASL sign language recognition from webcam video frames

### Future roadmap

- **Azure Computer Vision** — supplement Custom Vision with general gesture detection
- **Azure Video Indexer** — post-session accessibility review of recorded conversations
- **Azure Communication Services** — remote multi-user sessions beyond local single-device use

## How to run

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure AI Speech resource (key + region)
- Azure OpenAI resource (optional — needed for translation)
- Azure Custom Vision resource (optional — needed for sign language recognition)

### 1. Clone and enter the repo

```bash
git clone <repo-url>
cd inclu-speech
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and fill in your Azure credentials:
#   AZURE_SPEECH_KEY=...
#   AZURE_SPEECH_REGION=...       e.g. eastus
#   AZURE_OPENAI_KEY=...          (optional)
#   AZURE_OPENAI_ENDPOINT=...     (optional)
#   AZURE_OPENAI_DEPLOYMENT=...   (optional)
#   AZURE_CUSTOM_VISION_ENDPOINT=...        (optional — for sign language)
#   AZURE_CUSTOM_VISION_PREDICTION_KEY=...   (optional — for sign language)
#   AZURE_CUSTOM_VISION_PROJECT_ID=...       (optional — for sign language)
#   AZURE_CUSTOM_VISION_ITERATION_NAME=...   (optional — for sign language)

uvicorn app.main:app --port 8000 --reload
```

### 3. Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

The Vite dev server proxies WebSocket connections (`/ws/*`) to the backend on port 8000 automatically.

### 4. Run backend tests

```bash
cd backend
source .venv/bin/activate
pytest
```

## Responsible AI

IncluSpeech is built with privacy at its core. Video and audio streams are processed ephemerally and never stored without explicit user consent. Azure AI Content Safety ensures safe and inclusive communication channels, while transparency features surface AI decisions clearly to users. The platform is co-designed with Deaf and hard-of-hearing stakeholders to ensure genuine, lasting accessibility impact.