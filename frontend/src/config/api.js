// API configuration that adapts to environment
const getAPIBase = () => {
  // In development, use the proxy configured in vite.config.js
  if (import.meta.env.DEV) {
    return '';  // Empty string uses current host with proxy
  }
  
  // In production, check if we're on the unified deployment or separate domains
  const currentHost = window.location.hostname;
  
  if (currentHost.includes('elasticbeanstalk.com') || 
      currentHost.includes('duckdns.org') || 
      currentHost === 'localhost' ||
      currentHost.includes('127.0.0.1')) {
    // Unified deployment - API is served from same domain
    return '';
  }
  
  // Fallback to the configured API endpoint for separate deployments
  return "https://aptscanner.duckdns.org";
};

const API_BASE = getAPIBase();

export default API_BASE;
