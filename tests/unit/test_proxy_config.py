"""
Unit tests for ProxyConfig module.

Tests proxy configuration for SOCKS5, HTTP, HTTPS, domain bypass, and authentication.
"""
import pytest
from backend.core.proxy_config import ProxyConfig, create_proxy_config


class TestProxyConfig:
    """Test suite for ProxyConfig class."""
    
    def test_proxy_disabled_by_default(self):
        """Test that proxy is disabled by default."""
        config = ProxyConfig()
        assert config.use_proxy is False
        assert config.get_proxies_dict() is None
    
    def test_socks5_proxy_configuration(self):
        """Test SOCKS5 proxy configuration."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="socks5",
            proxy_host="localhost",
            proxy_port=1080
        )
        
        assert config.use_proxy is True
        assert config.proxy_type == "socks5"
        assert config.proxy_host == "localhost"
        assert config.proxy_port == 1080
        
        proxies = config.get_proxies_dict()
        assert proxies is not None
        assert "http" in proxies
        assert "https" in proxies
        assert proxies["http"] == "socks5://localhost:1080"
        assert proxies["https"] == "socks5://localhost:1080"
    
    def test_http_proxy_configuration(self):
        """Test HTTP proxy configuration."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="http",
            proxy_host="proxy.example.com",
            proxy_port=8080
        )
        
        proxies = config.get_proxies_dict()
        assert proxies is not None
        assert proxies["http"] == "http://proxy.example.com:8080"
        assert proxies["https"] == "http://proxy.example.com:8080"
    
    def test_https_proxy_configuration(self):
        """Test HTTPS proxy configuration."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="https",
            proxy_host="secure-proxy.example.com",
            proxy_port=8443
        )
        
        proxies = config.get_proxies_dict()
        assert proxies is not None
        assert proxies["http"] == "https://secure-proxy.example.com:8443"
        assert proxies["https"] == "https://secure-proxy.example.com:8443"
    
    def test_proxy_with_authentication(self):
        """Test proxy configuration with username and password."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="socks5",
            proxy_host="localhost",
            proxy_port=1080,
            proxy_username="testuser",
            proxy_password="testpass"
        )
        
        proxies = config.get_proxies_dict()
        assert proxies is not None
        assert proxies["http"] == "socks5://testuser:testpass@localhost:1080"
        assert proxies["https"] == "socks5://testuser:testpass@localhost:1080"
    
    def test_proxy_none_type(self):
        """Test proxy type 'none' returns no proxies."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="none"
        )
        
        assert config.get_proxies_dict() is None
    
    def test_domain_bypass_single_domain(self):
        """Test that URLs can bypass proxy based on domain."""
        config = create_proxy_config(
            use_proxy=True,
            no_proxy_domains="localhost"
        )
        
        assert config.should_bypass_proxy("http://localhost:8000") is True
        assert config.should_bypass_proxy("https://api.pexels.com") is False
    
    def test_domain_bypass_multiple_domains(self):
        """Test bypass with multiple domains."""
        config = create_proxy_config(
            use_proxy=True,
            no_proxy_domains="localhost,127.0.0.1,.local"
        )
        
        assert config.should_bypass_proxy("http://localhost:8000") is True
        assert config.should_bypass_proxy("http://127.0.0.1:5000") is True
        assert config.should_bypass_proxy("http://service.local") is True
        assert config.should_bypass_proxy("https://api.pexels.com") is False
    
    def test_session_kwargs_with_proxy(self):
        """Test session kwargs generation with proxy enabled."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="socks5",
            proxy_host="localhost",
            proxy_port=1080,
            verify_ssl=True
        )
        
        kwargs = config.get_session_kwargs("https://api.pexels.com")
        
        assert "verify" in kwargs
        assert kwargs["verify"] is True
        assert "proxies" in kwargs
        assert kwargs["proxies"]["http"] == "socks5://localhost:1080"
    
    def test_session_kwargs_with_bypass_domain(self):
        """Test session kwargs when URL should bypass proxy."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="socks5",
            proxy_host="localhost",
            proxy_port=1080,
            no_proxy_domains="localhost"
        )
        
        kwargs = config.get_session_kwargs("http://localhost:8000")
        
        assert "verify" in kwargs
        # Should not include proxies for bypass domains
        assert "proxies" not in kwargs
    
    def test_session_kwargs_without_proxy(self):
        """Test session kwargs when proxy is disabled."""
        config = create_proxy_config(
            use_proxy=False
        )
        
        kwargs = config.get_session_kwargs("https://api.pexels.com")
        
        assert "verify" in kwargs
        assert "proxies" not in kwargs
    
    def test_ssl_verification_disabled(self):
        """Test SSL verification can be disabled."""
        config = create_proxy_config(
            use_proxy=True,
            verify_ssl=False
        )
        
        assert config.verify_ssl is False
        
        kwargs = config.get_session_kwargs("https://api.pexels.com")
        assert kwargs["verify"] is False
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ProxyConfig()
        
        assert config.use_proxy is False
        assert config.proxy_type == "socks5"
        assert config.proxy_host == "localhost"
        assert config.proxy_port == 1080
        assert config.proxy_username is None
        assert config.proxy_password is None
        assert config.no_proxy_domains == "localhost,127.0.0.1"
        assert config.verify_ssl is True
    
    def test_partial_authentication_no_username(self):
        """Test proxy authentication when only password is provided."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="socks5",
            proxy_password="testpass"  # No username
        )
        
        proxies = config.get_proxies_dict()
        assert proxies is not None
        # Should not include auth if username is missing
        assert "testpass" not in proxies["http"]
        assert proxies["http"] == "socks5://localhost:1080"
    
    def test_partial_authentication_no_password(self):
        """Test proxy authentication when only username is provided."""
        config = create_proxy_config(
            use_proxy=True,
            proxy_type="socks5",
            proxy_username="testuser"  # No password
        )
        
        proxies = config.get_proxies_dict()
        assert proxies is not None
        # Should not include auth if password is missing
        assert "testuser" not in proxies["http"]
        assert proxies["http"] == "socks5://localhost:1080"
