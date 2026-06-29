import pytest

from nanoagent.permissions import PermissionManager, PermissionMode, PermissionRule


class TestPermissionManager:
    def test_default_mode_allow(self):
        pm = PermissionManager(default_mode="allow")
        assert pm.check("any_tool") == PermissionMode.ALLOW

    def test_default_mode_deny(self):
        pm = PermissionManager(default_mode="deny")
        assert pm.check("any_tool") == PermissionMode.DENY

    def test_deny_mode(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="run_shell", match_type="prefix", pattern="rm", mode=PermissionMode.DENY,
        ))
        assert pm.check("run_shell", "rm -rf /") == PermissionMode.DENY

    def test_ask_mode(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="run_shell", match_type="prefix", pattern="sudo", mode=PermissionMode.ASK,
        ))
        result = pm.check("run_shell", "sudo rm -rf /")
        assert result == PermissionMode.ASK

    def test_exact_matching(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="run_shell", match_type="exact", pattern="rm -rf /", mode=PermissionMode.DENY,
        ))
        assert pm.check("run_shell", "rm -rf /") == PermissionMode.DENY
        assert pm.check("run_shell", "rm -rf /home") == PermissionMode.ALLOW

    def test_prefix_matching(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="run_shell", match_type="prefix", pattern="rm", mode=PermissionMode.DENY,
        ))
        assert pm.check("run_shell", "rm file.txt") == PermissionMode.DENY
        assert pm.check("run_shell", "echo hello") == PermissionMode.ALLOW

    def test_regex_matching(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="run_shell", match_type="regex", pattern=r"chmod\s+777", mode=PermissionMode.DENY,
        ))
        assert pm.check("run_shell", "chmod 777 file") == PermissionMode.DENY
        assert pm.check("run_shell", "chmod 755 file") == PermissionMode.ALLOW

    def test_no_matching_rule_falls_back(self):
        pm = PermissionManager(default_mode="deny")
        assert pm.check("run_shell", "anything") == PermissionMode.DENY

    def test_wildcard_tool_name(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="*", match_type="prefix", pattern="danger", mode=PermissionMode.DENY,
        ))
        assert pm.check("run_shell", "danger") == PermissionMode.DENY
        assert pm.check("read_file", "danger") == PermissionMode.DENY

    def test_most_specific_wins(self):
        pm = PermissionManager(default_mode="allow")
        pm.add_rule(PermissionRule(
            tool_name="*", match_type="prefix", pattern="rm", mode=PermissionMode.ASK,
        ))
        pm.add_rule(PermissionRule(
            tool_name="run_shell", match_type="prefix", pattern="rm", mode=PermissionMode.DENY,
        ))
        result = pm.check("run_shell", "rm file")
        assert result == PermissionMode.DENY

    def test_load_from_config(self):
        config = {
            "default_mode": "deny",
            "rules": {
                "allow_echo": {
                    "tool": "run_shell",
                    "type": "prefix",
                    "pattern": "echo",
                    "mode": "allow",
                },
            },
        }
        pm = PermissionManager.load_from_config(config)
        assert pm.default_mode == PermissionMode.DENY
        assert pm.check("run_shell", "echo hello") == PermissionMode.ALLOW
        assert pm.check("run_shell", "rm file") == PermissionMode.DENY

    def test_load_from_config_empty(self):
        pm = PermissionManager.load_from_config(None)
        assert pm.default_mode == PermissionMode.ALLOW

    def test_invalid_default_mode_raises(self):
        with pytest.raises(ValueError):
            PermissionManager(default_mode="invalid")
