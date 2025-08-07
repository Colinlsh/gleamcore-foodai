# Singapore AI Dietician - Frontend

Streamlit frontend for the Singapore AI Dietician application.

## Features

- **Clean Interface**: User-friendly web interface for dietary analysis
- **Document Upload**: Support for menu PDFs, images, and nutrition documents
- **Real-time Analysis**: Instant dietary recommendations with Singapore guidelines
- **Guidelines Viewer**: Access to official Health Promotion Board guidelines
- **Responsive Design**: Singapore-themed styling and layout

## Setup

1. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with backend URL if different from default
```

4. **Run the frontend:**
```bash
python run.py
# or directly: streamlit run app.py
```

## Configuration

The frontend connects to the backend via the `BACKEND_URL` environment variable:
- Default: `http://localhost:8000`
- For production: Set to your deployed backend URL

## Features

### Menu Analysis
- Input Singapore dishes for comprehensive dietary analysis
- Personal preferences and health conditions consideration
- Real-time backend communication with loading states

### Document Processing
- Upload menu PDFs, images, or nutrition documents
- Powered by RAG-Anything multimodal processing
- Integration with backend document processing pipeline

### Official Guidelines
- Access to Singapore Health Promotion Board guidelines
- My Healthy Plate recommendations
- Age-specific and health condition guidelines

### Food Recommendations
- Natural language queries for food suggestions
- Personalized recommendations based on user input
- Singapore-specific food knowledge integration

## Deployment

### Streamlit Cloud (Recommended)
1. Push to GitHub repository
2. Connect to Streamlit Cloud
3. Set `BACKEND_URL` environment variable
4. Deploy with one click

### Local Development
```bash
# Ensure backend is running first
cd ../backend && python run.py

# In another terminal, run frontend
cd ../frontend && python run.py
```

## Access
- Frontend: `http://localhost:8501`
- Backend health check visible in sidebar