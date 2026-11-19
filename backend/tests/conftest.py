import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DATABASE_URL"] = "sqlite:///./test_rentvoice.db"
os.environ["DEMO_MODE"] = "true"
os.environ["ADMIN_TOKEN"] = "test-admin"
os.environ["VAPI_WEBHOOK_SECRET"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest  # noqa: E402

from app.database import Base, engine  # noqa: E402
from scripts.seed import main as seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def db_setup():
    Base.metadata.drop_all(bind=engine)
    seed()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("test_rentvoice.db"):
        os.remove("test_rentvoice.db")
