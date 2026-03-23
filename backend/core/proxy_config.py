"""
Proxy Configuration Module

Manages proxy settings for external API requests, supporting multiple proxy types
and bypass configurations for corporate environments.
"""
from typing import Dict, Optional, Literal, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ProxyType = Literal["socks5", "http", "https", "none"]


class ProxyConfig(BaseSettings):
    """
    Proxy configuration for external API requests.
    
    Supports:
    - SOCKS5 proxy (via SSH tunnel or dedicated SOCKS server)
    - HTTP/HTTPS proxy
    - No proxy (bypass)
    - Domain-based bypass rules
    """
    
    use_proxy: bool = Field(
        default=False,
        description="Enable/disable proxy usage"
    )
    
    proxy_type: ProxyType = Field(
        default="socks5",
        description="Type of proxy: socks5, http, https, or none"
    )
    
    proxy_host: str = Field(
        default="localhost",
        description="Proxy server hostname or IP"
    )
    
    proxy_port: int = Field(
        default=1080,
        description="Proxy server port"
    )
    
    proxy_username: Optional[str] = Field(
        default=None,
        description="Proxy authentication username (optional)"
    )
    
    proxy_password: Optional[str] = Field(
        default=None,
        description="Proxy authentication password (optional)"
    )
    
    no_proxy_domains: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of domains that should bypass proxy"
    )
    
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates (set to False as last resort)"
    )
    
    def get_proxies_dict(self) -> Optional[Dict[str, str]]:
        """
        Get proxy configuration in requests library format.
        
        Returns:
            Dict with 'http' and 'https' proxy URLs, or None if proxy disabled
        """
        if not self.use_proxy or self.proxy_type == "none":
            return None
        
        # Build proxy URL with authentication if provided
        auth_part = ""
        if self.proxy_username and self.proxy_password:
            auth_part = f"{self.proxy_username}:{self.proxy_password}@"
        
        # Build proxy URL based on type
        if self.proxy_type == "socks5":
            proxy_url = f"socks5://{auth_part}{self.proxy_host}:{self.proxy_port}"
        elif self.proxy_type == "http":
            proxy_url = f"http://{auth_part}{self.proxy_host}:{self.proxy_port}"
        elif self.proxy_type == "https":
            proxy_url = f"https://{auth_part}{self.proxy_host}:{self.proxy_port}"
        else:
            return None
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    
    def should_bypass_proxy(self, url: str) -> bool:
        """
        Check if a URL should bypass the proxy based on no_proxy_domains.
        
        Args:
            url: The URL to check
            
        Returns:
            True if URL should bypass proxy, False otherwise
        """
        if not self.use_proxy:
            return True
        
        # Parse no_proxy domains
        bypass_domains = [d.strip() for d in self.no_proxy_domains.split(",")]
        
        # Check if URL contains any bypass domain
        for domain in bypass_domains:
            if domain and domain in url:
                return True
        
        return False
    
    def get_session_kwargs(self, url: str) -> Dict[str, Any]:
        """
        Get kwargs for requests.Session configuration.
        
        Args:
            url: Target URL (for bypass checking)
            
        Returns:
            Dict with 'proxies' and 'verify' keys
        """
        kwargs: Dict[str, Any] = {
            "verify": self.verify_ssl
        }
        
        if not self.should_bypass_proxy(url):
            proxies = self.get_proxies_dict()
            if proxies:
                kwargs["proxies"] = proxies
        
        return kwargs
    
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False
    )


def create_proxy_config(
    use_proxy: bool = False,
    proxy_type: ProxyType = "socks5",
    proxy_host: str = "localhost",
    proxy_port: int = 1080,
    proxy_username: Optional[str] = None,
    proxy_password: Optional[str] = None,
    no_proxy_domains: str = "localhost,127.0.0.1",
    verify_ssl: bool = True
) -> ProxyConfig:
    """
    Factory function to create ProxyConfig instance.
    
    Args:
        use_proxy: Enable proxy
        proxy_type: Type of proxy (socks5, http, https, none)
        proxy_host: Proxy server host
        proxy_port: Proxy server port
        proxy_username: Optional authentication username
        proxy_password: Optional authentication password
        no_proxy_domains: Comma-separated bypass domains
        verify_ssl: Verify SSL certificates
        
    Returns:
        ProxyConfig instance
    """
    return ProxyConfig(
        use_proxy=use_proxy,
        proxy_type=proxy_type,
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
        no_proxy_domains=no_proxy_domains,
        verify_ssl=verify_ssl
    )
