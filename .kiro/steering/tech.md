# SPRINT Technical Stack

## Core Framework

- **Flask** - Python web framework for handling GitHub webhooks
- **Python 3.x** - Primary programming language

## Machine Learning Stack

- **PyTorch** - Deep learning framework for model inference
- **Transformers** - Hugging Face library for NLP models
- **PEFT** - Parameter-Efficient Fine-Tuning for model customization
- **BitsAndBytes** - Model quantization for GPU optimization

## Key Dependencies

- **Accelerate** - Distributed training and inference
- **Datasets** - Data processing and management
- **Pandas/NumPy** - Data manipulation
- **Requests** - HTTP client for GitHub API calls

## Infrastructure

- **ngrok** - Secure tunneling for local development
- **SQLite** (implied) - Local database for issue storage
- **GitHub API** - Repository integration and webhook handling

## Hardware Requirements

- **GPU**: Ampere family GPU required for bug localization model (Llama-7b)
- **Storage**: ~20GB for models and project files
- **Memory**: Sufficient RAM for concurrent model loading

## Common Commands

### Setup and Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Download models from Google Drive (manual step)
# Update .env file with model paths
```

### Running the Application

```bash
# Terminal 1: Start ngrok tunnel
ngrok http 5000

# Terminal 2: Start Flask application
python main.py
# or
python -m main
```

### Environment Configuration

Required `.env` variables:

- `GITHUB_PRIVATE_KEY` - GitHub App private key
- `GITHUB_APP_ID` - GitHub App ID
- `CLIENT_ID` - GitHub App client ID
- `DUPLICATE_BR_MODEL_PATH` - Path to duplicate detection model
- `SEVERITY_PREDICTION_MODEL_PATH` - Path to severity prediction model
- `BUGLOCALIZATION_MODEL_PATH` - Path to bug localization model
- `POOL_PROCESSOR_MAX_WORKERS` - Multiprocessing worker count (default: 4)

## Development Notes

- Uses multiprocessing with 'spawn' method on Windows/Linux with CUDA
- ThreadPoolExecutor for concurrent webhook processing
- Modular architecture with separate components for each feature
