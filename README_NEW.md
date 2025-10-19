# 📄 Mistral OCR - Document Classifier

Automatically classify and split PDF documents into categories using Mistral OCR and Google Gemini AI.

## Features

- 🔍 **OCR Processing**: Extract text from PDFs using Mistral's advanced OCR
- 🏷️ **Smart Classification**: Automatically categorize pages (passport, marksheets, resumes, etc.)
- ✂️ **PDF Splitting**: Split multi-page PDFs into separate files by category
- 📥 **Easy Downloads**: Download categorized PDFs individually
- ☁️ **Cloud Ready**: Deploy to Streamlit Cloud or run locally

## Supported Document Categories

- Academic certificates (10th/12th marksheets, degrees, transcripts)
- Identity documents (passport, Aadhaar card)
- Language proficiency tests (TOEFL, IELTS, PTE, Duolingo)
- Proficiency tests (GRE, GMAT)
- Professional documents (resume, work experience letters)
- Application materials (SOP, LORs)

## Quick Start

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/gauravkhati/multi-doc-tagging.git
cd multi-doc-tagging
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**

Create a `.env` file:
```env
MISTRAL_API_KEY=your_mistral_api_key
GOOGLE_API_KEY=your_google_ai_studio_key
```

Or for Vertex AI with service account:
```env
MISTRAL_API_KEY=your_mistral_api_key
GOOGLE_APPLICATION_CREDENTIALS=storage.json
```

4. **Run the app:**
```bash
streamlit run app.py
```

5. **Open browser:** http://localhost:8501

### Docker Deployment

1. **Build and run with Docker Compose:**
```bash
docker compose up --build
```

2. **Access the app:** http://localhost:8501

3. **View logs:**
```bash
docker compose logs -f app
```

4. **Stop the app:**
```bash
docker compose down
```

## Streamlit Cloud Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick steps:**
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Create new app pointing to your repo
4. Add secrets in app settings
5. Deploy!

## Project Structure

```
mistral_ocr_app/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image configuration
├── docker-compose.yml     # Docker Compose setup
├── .dockerignore          # Files to exclude from Docker
├── .gitignore             # Files to exclude from Git
├── .env.example           # Environment variables template
├── DEPLOYMENT.md          # Deployment guide
└── README.md              # This file
```

## Environment Variables

### Required
- `MISTRAL_API_KEY`: Your Mistral API key

### Authentication (choose one)
- `GOOGLE_API_KEY`: Google AI Studio API key (simpler)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to GCP service account JSON (for Vertex AI)

## API Keys

### Mistral API
Get your API key from [Mistral Console](https://console.mistral.ai/)

### Google Gemini
**Option A: Google AI Studio** (Recommended)
- Get free API key: https://makersuite.google.com/app/apikey
- Set `GOOGLE_API_KEY` environment variable

**Option B: Vertex AI with Service Account**
- Create GCP project with Vertex AI enabled
- Create service account and download JSON
- Set `GOOGLE_APPLICATION_CREDENTIALS` to JSON path

## Technologies Used

- **[Streamlit](https://streamlit.io/)**: Web application framework
- **[Mistral AI](https://mistral.ai/)**: OCR processing
- **[Google Gemini](https://ai.google.dev/)**: Document classification
- **[PyPDF2](https://pypdf2.readthedocs.io/)**: PDF manipulation
- **[Docker](https://www.docker.com/)**: Containerization

## Usage

1. Upload a multi-page PDF document
2. Click "Process Document"
3. View OCR results and classification
4. Download split PDFs by category

## Development

### Local with live reload:
```bash
streamlit run app.py --server.runOnSave true
```

### Docker with source mounted:
```bash
# Already configured in docker-compose.yml
docker compose up
# Edit files locally, changes reflect in container
```

### Run tests:
```bash
# Add your tests here
pytest tests/
```

## Troubleshooting

### Import errors
```bash
pip install -r requirements.txt
```

### API authentication errors
- Verify API keys are correct
- Check `.env` file exists and is loaded
- For Streamlit Cloud, verify secrets are configured

### Docker issues
```bash
# Rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up
```

### Memory issues on Streamlit Cloud
- Free tier has 1GB RAM limit
- Process smaller PDFs (< 10 pages)
- Consider upgrading to paid tier

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: [GitHub Issues](https://github.com/gauravkhati/multi-doc-tagging/issues)
- **Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## Acknowledgments

- Mistral AI for OCR capabilities
- Google for Gemini AI model
- Streamlit for the amazing framework

---

Built with ❤️ using Mistral OCR & Gemini AI
