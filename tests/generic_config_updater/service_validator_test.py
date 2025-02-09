import copy
import json
import jsondiff
import os
import unittest
from collections import defaultdict
from unittest.mock import patch

from generic_config_updater.services_validator import vlan_validator, rsyslog_validator
import generic_config_updater.gu_common


# Mimics os.system call
#
os_system_calls = []
os_system_call_index = 0
msg = ""

def mock_os_system_call(cmd):
    global os_system_calls, os_system_call_index

    assert os_system_call_index < len(os_system_calls)
    entry = os_system_calls[os_system_call_index]
    os_system_call_index += 1

    assert cmd == entry["cmd"], msg
    return entry["rc"]


test_data = [
        { "old": {}, "upd": {}, "cmd": "" },
        {
            "old": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.10" ] } } },
            "upd": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.10" ] } } },
            "cmd": ""
        },
        {
            "old": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.10" ] } } },
            "upd": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.11" ] } } },
            "cmd": "systemctl restart dhcp_relay"
        },
        {
            "old": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.10" ] } } },
            "upd": { "VLAN": {
                "XXX": { "dhcp_servers": [ "10.10.10.10" ] },
                "YYY": { "dhcp_servers": [ ] } } },
            "cmd": ""
        },
        {
            "old": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.10" ] } } },
            "upd": { "VLAN": {
                "XXX": { "dhcp_servers": [ "10.10.10.10" ] },
                "YYY": { "dhcp_servers": [ "10.12.12.1" ] } } },
            "cmd": "systemctl restart dhcp_relay"
        },
        {
            "old": { "VLAN": { "XXX": { "dhcp_servers": [ "10.10.10.10" ] } } },
            "upd": {},
            "cmd": "systemctl restart dhcp_relay"
        }
    ]

test_rsyslog_fail = [
        # Fail the calls, to get the entire fail path calls invoked
        #
        { "cmd": "/usr/bin/rsyslog-config.sh", "rc": 1 },        # config update; fails
        { "cmd": "systemctl restart rsyslog", "rc": 1 },         # rsyslog restart; fails
        { "cmd": "systemctl reset-failed rsyslog", "rc": 1 },    # reset; failure here just logs
        { "cmd": "systemctl restart rsyslog", "rc": 1 },         # restart again; fails
        { "cmd": "systemctl restart rsyslog", "rc": 1 },         # restart again; fails
    ]


class TestServiceValidator(unittest.TestCase):

    @patch("generic_config_updater.change_applier.os.system")
    def test_change_apply(self, mock_os_sys):
        global os_system_expected_cmd
        global os_system_calls, os_system_call_index

        mock_os_sys.side_effect = mock_os_system_call

        i = 0
        for entry in test_data:
            if entry["cmd"]:
                os_system_calls.append({"cmd": entry["cmd"], "rc": 0 })
            msg = "case failed: {}".format(str(entry))

            vlan_validator(entry["old"], entry["upd"], None)


        # Test failure case
        #
        os_system_calls = test_rsyslog_fail
        os_system_call_index = 0

        rc = rsyslog_validator("", "", "")
        assert not rc, "rsyslog_validator expected to fail"

