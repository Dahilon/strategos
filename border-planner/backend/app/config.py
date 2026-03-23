import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'border-planner-dev')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o')
    LLM_TIMEOUT_SECONDS = float(os.environ.get('LLM_TIMEOUT_SECONDS', '45'))
    LLM_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', '1'))
    SIM_ALLOW_LOCAL_FALLBACK = os.environ.get('SIM_ALLOW_LOCAL_FALLBACK', 'true').lower() == 'true'
    SIM_FORCE_LOCAL_DECISIONS = os.environ.get('SIM_FORCE_LOCAL_DECISIONS', 'false').lower() == 'true'

    CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../config')
    RESULTS_DIR = os.path.join(os.path.dirname(__file__), '../results')

    @classmethod
    def validate(cls):
        errors = []
        if not cls.LLM_API_KEY or cls.LLM_API_KEY == 'your_api_key_here':
            errors.append("LLM_API_KEY not configured — edit backend/.env")
        return errors

    @classmethod
    def llm_ready(cls):
        return cls.LLM_API_KEY and cls.LLM_API_KEY != 'your_api_key_here'
