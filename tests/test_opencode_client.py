"""Tests for opencode_client.py."""

from unittest.mock import patch

import pytest
import requests

from opencode_client import OpencodeError, OpencodeServer


class TestEnsureRunning:
    def test_healthy_server_returns_immediately(self):
        server = OpencodeServer(url="http://remote:4096")
        with patch.object(server, "health", return_value=True) as mock_health:
            server.ensure_running()
            mock_health.assert_called_once()

    def test_remote_url_raises_on_unhealthy(self):
        server = OpencodeServer(url="http://192.168.1.100:4096")
        with patch.object(server, "health", return_value=False):
            with pytest.raises(OpencodeError, match="not reachable"):
                server.ensure_running()

    def test_local_url_with_auto_start_disabled_raises(self):
        server = OpencodeServer(url="http://localhost:4096")
        with (
            patch.object(server, "health", return_value=False),
            patch("opencode_client.OPENCODE_AUTO_START", False),
        ):
            with pytest.raises(OpencodeError, match="not running"):
                server.ensure_running()

    def test_localhost_shortcut_raises_remote(self):
        server = OpencodeServer(url="http://localhost:9999")
        with (
            patch.object(server, "health", return_value=False),
            patch("opencode_client.OPENCODE_AUTO_START", False),
        ):
            with pytest.raises(OpencodeError, match="not running"):
                server.ensure_running()


class TestHealth:
    def test_health_returns_true_on_ok(self):
        server = OpencodeServer(url="http://localhost:4096")
        with patch("opencode_client.requests.get") as mock_get:
            mock_get.return_value.ok = True
            assert server.health() is True

    def test_health_returns_false_on_request_error(self):
        server = OpencodeServer(url="http://localhost:4096")
        with patch("opencode_client.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError
            assert server.health() is False
