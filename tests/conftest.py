import os
import shutil
import tempfile
import pytest


@pytest.fixture
def agent():
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    from nanoagent.agent import Agent
    agent = Agent(db_path=db_path)
    yield agent
    agent.memory.close()
    shutil.rmtree(tmpdir)
