import scm_test_base
from scm_test_base import AbstractSCMTest, _add_to_file, ROSINSTALL_CMD
        cmd = [ROSINSTALL_CMD, "ws", "-n"]
        cmd = [ROSINSTALL_CMD, "ws", "--diff"]
        cmd = [ROSINSTALL_CMD, ".", "--diff"]
        cmd = [ROSINSTALL_CMD, ".", "--status"]
        cmd = [ROSINSTALL_CMD, "ws", "--status"]
        cmd = [ROSINSTALL_CMD, "ws", "--status-untracked"]