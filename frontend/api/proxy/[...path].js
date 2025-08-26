import { Buffer } from 'buffer';

export default async function handler(req, res) {
    const EB_BASE = 'http://apt-scanner.us-east-1.elasticbeanstalk.com';
  
    try {
      // Get path from query parameters or catch-all route
      let path = '';
      
      // Check for explicit path query parameter first (e.g., ?path=api/v1/questionnaire/status)
      const pathParam = req.query.path;
      if (pathParam) {
        path = Array.isArray(pathParam) ? pathParam.join('/') : pathParam;
      }
      
      // Remove 'path=' from query string when constructing target URL
      const url = new URL(req.url, 'https://dummy'); 
      if (url.searchParams.has('path')) {
        url.searchParams.delete('path');
      }
      const qs = url.search || '';
      const target = `${EB_BASE}/${path}${qs}`;
      
      console.log(`Proxying ${req.method} ${req.url} -> ${target}`);
  
      const headers = {};
      if (req.headers.authorization) headers['authorization'] = req.headers.authorization;
      if (req.headers['content-type']) headers['content-type'] = req.headers['content-type'];
      if (req.headers.accept) headers['accept'] = req.headers.accept;
      
      // Handle request body for non-GET requests
      let body = undefined;
      if (req.method !== 'GET' && req.method !== 'HEAD') {
        if (req.body) {
          body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
        }
      }
  
      const r = await fetch(target, {
        method: req.method,
        headers,
        body,
      });
  
      const ct = r.headers.get('content-type') || 'application/json';
      res.status(r.status).setHeader('content-type', ct);
      
      // Handle JSON responses properly
      if (ct.includes('application/json')) {
        const data = await r.json();
        res.json(data);
      } else {
        const buf = Buffer.from(await r.arrayBuffer());
        res.send(buf);
      }
    } catch (e) {
      console.error('Proxy error:', e);
      res.status(502).json({ error: 'Proxy failed', detail: String(e?.message || e) });
    }
  }
  