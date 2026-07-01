import os
import tempfile

import pytest

from nanoagent.registry import ToolRegistry


class TestFileTools:
    def test_read_file(self):
        from nanoagent.agent.tools.file_tools import read_file

        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=os.getcwd()) as f:
            f.write("test content")
            tmp = f.name
        try:
            result = read_file(path=tmp)
            assert result == "test content"
        finally:
            os.unlink(tmp)

    def test_read_file_not_found(self):
        from nanoagent.agent.tools.file_tools import read_file

        with pytest.raises(FileNotFoundError):
            read_file(path="/nonexistent/path/file.txt")

    def test_write_file(self):
        from nanoagent.agent.tools.file_tools import write_file

        fd, tmp = tempfile.mkstemp(dir=os.getcwd())
        os.close(fd)
        os.unlink(tmp)
        result = write_file(path=tmp, content="new content")
        assert result is not None
        with open(tmp) as f:
            assert f.read() == "new content"
        os.unlink(tmp)

    def test_glob_file(self):
        from nanoagent.agent.tools.file_tools import glob_file

        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "a.py"), "w").close()
            open(os.path.join(tmpdir, "b.py"), "w").close()
            result = glob_file(pattern="*.py", path=tmpdir)
            assert "a.py" in result
            assert "b.py" in result

    def test_grep_file(self):
        from nanoagent.agent.tools.file_tools import grep_file

        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.txt")
            with open(fpath, "w") as f:
                f.write("hello world\nline two\nhello again\n")
            result = grep_file(pattern="hello", path=tmpdir)
            assert "hello world" in result
            assert "hello again" in result

    def test_path_traversal_protection(self):
        from nanoagent.agent.tools.file_tools import write_file

        with pytest.raises(PermissionError):
            write_file(path="/etc/passwd", content="evil")

    def test_binary_content_read(self):
        from nanoagent.agent.tools.file_tools import read_file

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"\xff\xfe\x00\x01")
            tmp = f.name
        try:
            result = read_file(path=tmp)
            assert isinstance(result, str)
        finally:
            os.unlink(tmp)

    def test_registers_in_tool_registry(self):
        from nanoagent.agent.tools.file_tools import (
            read_file,
            write_file,
            glob_file,
            grep_file,
        )

        registry = ToolRegistry()
        registry.register(read_file)
        registry.register(write_file)
        registry.register(glob_file)
        registry.register(grep_file)
        assert registry.get("read_file") is not None
        assert registry.get("write_file") is not None
        assert registry.get("glob_file") is not None
        assert registry.get("grep_file") is not None
