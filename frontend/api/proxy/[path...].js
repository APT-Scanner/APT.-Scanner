import { Buffer } from 'buffer';

export default async function handler(req, res) {
    const EB_BASE = 'http://apt-scanner.us-east-1.elasticbeanstalk.com';
  
    try {
      const url = new URL(req.url, 'https://dummy'); 
      const qs = url.search || '';
      const segs = req.query.path || [];
      const path = Array.isArray(segs) ? segs.join('/') : segs || '';
      const target = `${EB_BASE}/${path}${qs}`;
  
      const headers = {};
      if (req.headers.authorization) headers['authorization'] = req.headers.authorization;
      if (req.headers['content-type']) headers['content-type'] = req.headers['content-type'];
  
      const r = await fetch(target, {
        method: req.method,
        headers,
        body: (req.method !== 'GET' && req.method !== 'HEAD') ? req.body : undefined,
      });
  
      const ct = r.headers.get('content-type') || 'text/plain';
      res.status(r.status).setHeader('content-type', ct);
      const buf = Buffer.from(await r.arrayBuffer());
      res.send(buf);
    } catch (e) {
      res.status(502).json({ error: 'Proxy failed', detail: String(e?.message || e) });
    }
  }
  