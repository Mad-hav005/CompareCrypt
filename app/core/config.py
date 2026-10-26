"""
Configuration settings for the Private Set Intersection system.
"""

from pydantic import BaseModel


class CryptoConfig(BaseModel):
    """Cryptographic parameters configuration."""
    group_name: str = "RFC3526_MODP_2048"
    hash_algorithm: str = "sha256"


class Settings(BaseModel):
    """Application level settings."""
    app_name: str = "CompareCrypt - Secure Private Matching"
    app_version: str = "0.1.0"
    crypto: CryptoConfig = CryptoConfig()


settings = Settings()
