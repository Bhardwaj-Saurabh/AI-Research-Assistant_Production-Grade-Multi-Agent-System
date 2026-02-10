"""Configuration management for AI Research Assistant.

This module handles environment configuration and settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for the research assistant."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # GCP Configuration
        self.project_id = os.getenv("PROJECT_ID", "")
        self.location = os.getenv("LOCATION", "us-central1")
        self.model_name = os.getenv("MODEL", "gemini-2.0-flash")

        # Service Account Authentication
        self.google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account-key.json")

        # Application Settings
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.port = int(os.getenv("PORT", "8000"))
        self.validation_debug = os.getenv("VALIDATION_DEBUG", "false").lower() == "true"

        # Research Settings
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", "3"))
        self.quality_threshold = float(os.getenv("QUALITY_THRESHOLD", "0.8"))

        # Validate required settings
        if not self.project_id:
            print("⚠️  Warning: PROJECT_ID not set in environment")

    def __repr__(self):
        """String representation of config."""
        return (f"Config(project_id='{self.project_id}', "
                f"location='{self.location}', "
                f"model='{self.model_name}', "
                f"debug={self.debug}, "
                f"log_level='{self.log_level}')")


# Global config instance
config = Config()
