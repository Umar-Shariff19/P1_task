"""Synthetic-only tests for predictor alert delivery and sink failures."""
from __future__ import annotations

import json

import numpy as np
import pytest

import ipaddress
import os
import socket
import ssl
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

from iot_ids.features.canonical.flow_builder import CANONICAL_21_FEATURE_NAMES
from iot_ids.inference.predictor import IDSPredictor
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.utils.sinks import (
    AlertDeliveryError,
    AlertDeliveryStatus,
    BaseAlertSink,
    JSONLFileSink,
    MultiAlertSink,
    WebhookAlertSink,
    _PinnedHTTPConnection,
    _PinnedHTTPSConnection,
    _SafeRedirectHandler,
    _is_prohibited_ip,
)


class IdentityPreprocessor:
    def transform(self, frame):
        return frame.to_numpy(dtype=float)


class SyntheticProbabilityModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, features):
        positive = np.full(len(features), 0.8, dtype=float)
        return np.column_stack((1.0 - positive, positive))


class MemorySink(BaseAlertSink):
    def __init__(self):
        self.alerts = []

    def write_alert(self, alert_dict):
        self.alerts.append(dict(alert_dict))


class FailingSink(BaseAlertSink):
    def __init__(self):
        self.calls = 0

    def write_alert(self, alert_dict):
        self.calls += 1
        raise OSError("synthetic sink failure; path details must not leak")


def make_predictor(delivery_target=None):
    pipeline = IDSSystemPipeline(
        model=SyntheticProbabilityModel(),
        preprocessor=IdentityPreprocessor(),
        feature_profile="synthetic_alert_delivery",
        feature_names=list(CANONICAL_21_FEATURE_NAMES),
    )
    return IDSPredictor(pipeline, delivery_target=delivery_target)


def packet(timestamp=10.0, flow=1):
    return {
        "timestamp": timestamp,
        "src_ip": "192.0.2.10",
        "dst_ip": f"198.51.100.{flow}",
        "src_port": 20000 + flow,
        "dst_port": 443,
        "protocol": "tcp",
        "length": 120,
        "syn": 1,
        "label": 0,
        "attack_category": "SYNTHETIC_FIXTURE",
    }


def test_injected_sink_receives_finalized_alert_once():
    sink = MemorySink()
    predictor = make_predictor(sink)

    assert predictor.ingest_packet(packet()).alerts == ()
    first = predictor.finalize_pending_flows()
    second = predictor.finalize_pending_flows()

    assert len(first.alerts) == 1
    assert second.alerts == ()
    assert sink.alerts == list(first.alerts)
    assert predictor.metrics.get_summary().alerts_emitted == 1


def test_flow_completion_and_finalization_deliver_each_flow_only_once():
    sink = MemorySink()
    predictor = make_predictor(sink)

    predictor.ingest_packet(packet(timestamp=10.0, flow=1))
    completed = predictor.ingest_packet(packet(timestamp=30.0, flow=1))
    finalized = predictor.finalize_pending_flows()

    assert len(completed.alerts) == len(finalized.alerts) == 1
    assert len(sink.alerts) == 2
    assert predictor.finalize_pending_flows().alerts == ()
    assert len(sink.alerts) == 2


def test_jsonl_sink_receives_predictor_alert_in_temporary_file(tmp_path):
    output = tmp_path / "synthetic" / "alerts.jsonl"
    predictor = make_predictor(JSONLFileSink(output))
    predictor.ingest_packet(packet())

    predictor.finalize_pending_flows()

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["is_anomaly"] is True
    assert records[0]["prediction_prob"] == pytest.approx(0.8)


def test_single_sink_failure_is_explicit_and_not_counted_as_delivered():
    sink = FailingSink()
    predictor = make_predictor(sink)
    predictor.ingest_packet(packet())

    with pytest.raises(AlertDeliveryError) as caught:
        predictor.finalize_pending_flows()

    assert caught.value.result.status is AlertDeliveryStatus.FAILED
    assert (caught.value.result.delivered_count, caught.value.result.failed_count) == (0, 1)
    assert "path details" not in str(caught.value)
    metrics = predictor.metrics.get_summary()
    assert metrics.errors_encountered == 1
    assert metrics.alerts_emitted == 0


def test_callback_false_result_is_an_explicit_delivery_failure():
    predictor = make_predictor(lambda alert: False)
    predictor.ingest_packet(packet())

    with pytest.raises(AlertDeliveryError) as caught:
        predictor.finalize_pending_flows()

    assert caught.value.result.status is AlertDeliveryStatus.FAILED
    assert caught.value.result.failure_types == ("_DeliveryRejected",)


def test_multi_sink_failure_reports_partial_delivery_and_attempts_all_sinks():
    good = MemorySink()
    bad = FailingSink()
    predictor = make_predictor(MultiAlertSink([good, bad]))
    predictor.ingest_packet(packet())

    with pytest.raises(AlertDeliveryError) as caught:
        predictor.finalize_pending_flows()

    result = caught.value.result
    assert result.status is AlertDeliveryStatus.PARTIAL
    assert (result.delivered_count, result.failed_count) == (1, 1)
    assert len(good.alerts) == 1
    assert bad.calls == 1
    assert predictor.metrics.get_summary().errors_encountered == 1


def test_finite_stream_callback_failure_is_not_silent_or_counted_twice():
    predictor = make_predictor()
    predictor.ingest_packet(packet())

    def fail_callback(alert):
        raise RuntimeError("synthetic callback failure")

    # The callback is exercised on a flow finalized after stream exhaustion.
    with pytest.raises(AlertDeliveryError) as caught:
        predictor.process_packet_stream([], on_alert=fail_callback)

    assert caught.value.result.status is AlertDeliveryStatus.FAILED
    assert predictor.metrics.get_summary().errors_encountered == 1


def test_webhook_scheme_and_ssrf_validation():
    # Insecure HTTP blocked by default
    with pytest.raises(ValueError, match="Insecure HTTP"):
        WebhookAlertSink("http://example.com/alerts")

    # Private IP / loopback blocked by default (SSRF prevention)
    with pytest.raises(ValueError, match="SSRF protection"):
        WebhookAlertSink("https://127.0.0.1:8443/alerts", allow_local=False)

    with pytest.raises(ValueError, match="SSRF protection"):
        WebhookAlertSink("http://192.168.1.1:8080/alerts", allow_insecure_http=True, allow_local=False)


def test_webhook_delivery_with_mock():
    from unittest.mock import MagicMock, patch
    import io

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.code = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        sink = WebhookAlertSink(
            "http://127.0.0.1:8080/api/v1/alerts",
            auth_header="Bearer super-secret-key-42",
            allow_insecure_http=True,
            allow_local=True,
        )
        test_alert = {"flow_id": "flow-101", "is_anomaly": True, "risk_score": 0.85}
        sink.write_alert(test_alert)

        assert mock_urlopen.call_count == 1
        call_req = mock_urlopen.call_args[0][0]
        assert call_req.full_url == "http://127.0.0.1:8080/api/v1/alerts"
        assert call_req.headers.get("Authorization") == "Bearer super-secret-key-42"
        assert json.loads(call_req.data.decode("utf-8"))["flow_id"] == "flow-101"


def test_webhook_4xx_error_fails_fast_and_redacts_secrets():
    from unittest.mock import patch
    import io
    import urllib.error

    secret_token = "Bearer top-secret-token-xyz"
    http_err = urllib.error.HTTPError(
        url=f"http://127.0.0.1:8080/forbidden?token={secret_token}",
        code=403,
        msg="Forbidden",
        hdrs={},
        fp=io.BytesIO(b"Forbidden"),
    )

    with patch("urllib.request.urlopen", side_effect=http_err) as mock_urlopen:
        sink = WebhookAlertSink(
            "http://127.0.0.1:8080/forbidden",
            auth_header=secret_token,
            allow_insecure_http=True,
            allow_local=True,
            max_retries=3,
        )
        with pytest.raises(RuntimeError) as exc_info:
            sink.write_alert({"flow_id": "test"})

        # Must fail immediately without retries (call count 1)
        assert mock_urlopen.call_count == 1
        err_str = str(exc_info.value)
        assert "403" in err_str
        assert secret_token not in err_str
        assert "non-retryable" in err_str


def test_webhook_5xx_retries_and_exhausts():
    from unittest.mock import patch
    import io
    import urllib.error

    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:8080/server-error",
        code=503,
        msg="Service Unavailable",
        hdrs={},
        fp=io.BytesIO(b"Unavailable"),
    )

    with patch("urllib.request.urlopen", side_effect=http_err) as mock_urlopen:
        sink = WebhookAlertSink(
            "http://127.0.0.1:8080/server-error",
            allow_insecure_http=True,
            allow_local=True,
            max_retries=2,
            backoff_factor=0.01,
        )
        with pytest.raises(RuntimeError) as exc_info:
            sink.write_alert({"flow_id": "test"})

        # Initial attempt + 2 retries = 3 total attempts
        assert mock_urlopen.call_count == 3
        assert "Webhook delivery failed after 3 attempts" in str(exc_info.value)


def test_webhook_payload_size_limit():
    sink = WebhookAlertSink(
        "http://127.0.0.1:8080/alerts",
        allow_insecure_http=True,
        allow_local=True,
    )
    # Huge payload exceeding 5MB
    huge_alert = {"data": "X" * (5 * 1024 * 1024 + 100)}
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        sink.write_alert(huge_alert)


def test_webhook_redirect_disallowed():
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.code = 200
    mock_resp.geturl.return_value = "http://attacker.example.com/stolen"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        sink = WebhookAlertSink(
            "http://127.0.0.1:8080/alerts",
            allow_insecure_http=True,
            allow_local=True,
            max_retries=1,
            backoff_factor=0.01,
        )
        with pytest.raises(RuntimeError) as exc_info:
            sink.write_alert({"flow_id": "test"})
        assert "disallowed for security" in str(exc_info.value)


def test_webhook_dns_rebinding_connection_time_enforcement():
    """Validates that a DNS rebinding / TOCTOU race is eliminated at connection time.

    If DNS initially resolves to a benign public IP during configuration and pre-check,
    but rebinds to an internal loopback IP during socket connection, the connection-time
    enforcer in _PinnedHTTPConnection strictly fails closed before any connection is made.
    """
    lookup_count = 0

    def mock_getaddrinfo(host, port, *args, **kwargs):
        nonlocal lookup_count
        lookup_count += 1
        # Call 1 (init validation) & Call 2 (write_alert pre-check): returns public IP
        # Call 3 (connection-time inside _PinnedHTTPConnection.connect): rebinds to loopback IP!
        if lookup_count < 3:
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]
        else:
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", port))]

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo):
        sink = WebhookAlertSink(
            "http://rebinding-victim.example.com/alerts",
            allow_insecure_http=True,
            allow_local=False,
            max_retries=0,
        )

        with pytest.raises(ValueError, match="SSRF protection blocked webhook delivery"):
            sink.write_alert({"flow_id": "flow-rebinding-test"})


@pytest.mark.parametrize(
    "ip_str,is_blocked",
    [
        ("127.0.0.1", True),
        ("127.255.255.254", True),
        ("10.0.0.1", True),
        ("172.16.0.1", True),
        ("192.168.1.1", True),
        ("169.254.169.254", True),
        ("0.0.0.0", True),
        ("224.0.0.1", True),
        ("240.0.0.1", True),
        ("100.64.0.1", True),
        ("198.51.100.1", True),
        ("::1", True),
        ("::", True),
        ("fe80::1", True),
        ("fc00::1", True),
        ("fd12:3456:789a::1", True),
        ("::ffff:127.0.0.1", True),
        ("::ffff:169.254.169.254", True),
        ("::ffff:10.0.0.1", True),
        ("::127.0.0.1", True),
        ("93.184.216.34", False),
        ("8.8.8.8", False),
        ("2606:2800:220:1:248:1893:25c8:1946", False),
        ("::ffff:93.184.216.34", False),
    ],
)
def test_prohibited_ip_classification(ip_str, is_blocked):
    """Verifies complete address filtering across IPv4, IPv6, and mapped IPv6 variants."""
    ip_obj = ipaddress.ip_address(ip_str)
    assert _is_prohibited_ip(ip_obj) is is_blocked


def test_webhook_multi_homed_dns_with_prohibited_ip_fails_closed():
    """Verifies that multi-homed DNS resolutions containing ANY restricted IP fail closed."""
    def mock_getaddrinfo(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.1", port)),
        ]

    with patch("socket.getaddrinfo", side_effect=mock_getaddrinfo):
        with pytest.raises(ValueError, match="SSRF protection blocked webhook delivery"):
            WebhookAlertSink("https://multihomed.example.com/alerts", allow_local=False)


def test_webhook_tls_sni_and_cert_verification():
    """Verifies that _PinnedHTTPSConnection connects to the pinned IP while preserving TLS SNI and cert check."""
    mock_sock = MagicMock(spec=socket.socket)
    mock_ssl_sock = MagicMock()
    mock_ssl_context = MagicMock(spec=ssl.SSLContext)
    mock_ssl_context.wrap_socket.return_value = mock_ssl_sock

    with patch("socket.socket", return_value=mock_sock), \
         patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]):

        conn = _PinnedHTTPSConnection("api.trusted-domain.com", 443, allow_local=False, context=mock_ssl_context)
        conn.connect()

        # The underlying TCP socket was connected to the pinned IP
        mock_sock.connect.assert_called_once_with(("93.184.216.34", 443))

        # wrap_socket received the original domain name as server_hostname (for SNI and SAN verification)
        mock_ssl_context.wrap_socket.assert_called_once_with(
            mock_sock, server_hostname="api.trusted-domain.com"
        )


def test_safe_redirect_handler_blocks_all_redirect_codes():
    """Verifies that _SafeRedirectHandler halts on 3xx codes without issuing redirect requests."""
    import io

    handler = _SafeRedirectHandler()
    req = urllib.request.Request("https://api.example.com/alerts")

    for code in (301, 302, 303, 307, 308):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            handler.redirect_request(
                req,
                io.BytesIO(),
                code,
                "Redirect",
                {"Location": "http://169.254.169.254/secret"},
                "http://169.254.169.254/secret",
            )
        assert exc_info.value.code == code
        assert "disallowed for security" in str(exc_info.value)


def test_webhook_proxy_policy():
    """Verifies proxy handling: ambient proxy neutralization, explicit proxy, and opt-in environment proxy."""
    with patch.dict(os.environ, {"http_proxy": "http://env-proxy.local:8080", "https_proxy": "https://env-proxy.local:8080"}):
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]):
            # By default (allow_proxy=False), ambient environment proxy is neutralized
            sink_no_proxy = WebhookAlertSink("https://example.com/alerts", allow_proxy=False)
            proxy_handlers = [h for h in sink_no_proxy._opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
            for ph in proxy_handlers:
                assert ph.proxies == {}

            # With allow_proxy=True, environment proxies are read
            sink_env_proxy = WebhookAlertSink("https://example.com/alerts", allow_proxy=True)
            env_proxy_handlers = [h for h in sink_env_proxy._opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
            assert any("env-proxy.local" in str(ph.proxies) for ph in env_proxy_handlers)

            # Explicit proxy_url is set and verified
            sink_explicit_proxy = WebhookAlertSink(
                "https://example.com/alerts",
                proxy_url="http://explicit-proxy.example.com:8080",
                allow_local=True,
            )
            explicit_handlers = [h for h in sink_explicit_proxy._opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
            assert any(ph.proxies.get("http") == "http://explicit-proxy.example.com:8080" for ph in explicit_handlers)


def test_pinned_http_connection_direct_ip_pinning():
    """Verifies that _PinnedHTTPConnection connects directly to the validated IP tuple."""
    mock_sock = MagicMock(spec=socket.socket)

    with patch("socket.socket", return_value=mock_sock), \
         patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]):

        conn = _PinnedHTTPConnection("safe.example.com", 80, allow_local=False)
        conn.connect()

        # Confirms socket connected directly to the pinned IP tuple, avoiding hostname resolution at connect
        mock_sock.connect.assert_called_once_with(("93.184.216.34", 80))


def test_pinned_https_socket_cleanup_on_tls_failure():
    """Verifies that underlying socket is closed and cleaned up if TLS wrap_socket fails."""
    mock_sock = MagicMock(spec=socket.socket)
    mock_ssl_context = MagicMock(spec=ssl.SSLContext)
    mock_ssl_context.wrap_socket.side_effect = ssl.SSLError("Certificate verify failed")

    with patch("socket.socket", return_value=mock_sock), \
         patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]):

        conn = _PinnedHTTPSConnection("api.example.com", 443, allow_local=False, context=mock_ssl_context)
        with pytest.raises(ssl.SSLError, match="Certificate verify failed"):
            conn.connect()

        # Confirms socket was closed and reference cleared on TLS failure
        mock_sock.close.assert_called_once()
        assert conn.sock is None


def test_pinned_http_kernel_peername_check_blocks_prohibited_destination():
    """Verifies that if kernel socket peername reports a prohibited IP, connection fails closed."""
    mock_sock = MagicMock(spec=socket.socket)
    # Simulate an OS socket redirection / transparent proxy returning loopback from kernel getpeername
    mock_sock.getpeername.return_value = ("127.0.0.1", 80)

    with patch("socket.socket", return_value=mock_sock), \
         patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]):

        conn = _PinnedHTTPConnection("redirected.example.com", 80, allow_local=False)
        with pytest.raises(ValueError, match="SSRF protection blocked webhook delivery to restricted connected peer IP"):
            conn.connect()

        mock_sock.close.assert_called()


def test_dns_resolver_malformed_and_empty_records_fail_closed():
    """Verifies that empty or malformed DNS resolver results fail closed safely."""
    # Empty resolver response
    with patch("socket.getaddrinfo", return_value=[]):
        conn_empty = _PinnedHTTPConnection("empty.example.com", 80, allow_local=False)
        with pytest.raises(OSError, match="No address records returned"):
            conn_empty.connect()

    # Malformed resolver response (missing sockaddr)
    with patch("socket.getaddrinfo", return_value=[("not_a_valid_5_tuple",)]):
        conn_malformed = _PinnedHTTPConnection("malformed.example.com", 80, allow_local=False)
        with pytest.raises(ValueError, match="Malformed DNS resolver entry"):
            conn_malformed.connect()


