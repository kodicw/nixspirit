import pytest
import sys
import os

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

from core_nb_client import NbClient


@pytest.fixture(autouse=True)
def clear_nb_cache():
    """
    Ensure the NbClient cache is cleared before every test to prevent side-effects.
    """
    NbClient.clear_cache()
