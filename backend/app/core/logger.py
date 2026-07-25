"""
LARISKA AI
Centralized Logger Configuration
"""

import logging
import sys
from app.core.config import settings

def setup_logger(name: str = "lariska") -> logging.Logger:
    _logger = logging.getLogger(name)
    
    # Mencegah duplikasi handler jika logger dipanggil berkali-kali
    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
        
        # Set level berdasarkan config.py
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        _logger.setLevel(log_level)
        
        # Jangan propagasi ke root logger untuk menghindari double print
        _logger.propagate = False

    return _logger

logger = setup_logger()