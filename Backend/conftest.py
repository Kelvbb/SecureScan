# Backend/conftest.py
import sys
from pathlib import Path

# Ajoute Backend/ au PYTHONPATH pour que 'app' soit trouvable
sys.path.insert(0, str(Path(__file__).parent))
