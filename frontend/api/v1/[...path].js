export default async function handler(req, res) {
    const { path = [] } = req.query;
    const qs = req.url.includes('?') ? '?' + req.url.split('?')[1] : '';
    const upstream = `http://apt-scanner.us-east-1.elasticbeanstalk.com/api/v1/${path.join('/')}${qs}`;
  
    const { host, connection, ...headers } = req.headers;
  
    const init = {
      method: req.method,
      headers,
      body: ['GET','HEAD'].includes(req.method) ? undefined : req,
    };
  
    try {
      const r = await fetch(upstream, init);
  
      // Return status and body
      res.status(r.status);
  
      // If JSON → return as JSON
      const contentType = r.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await r.json();
        return res.json(data);
      }
  
      // Otherwise text
      const text = await r.text();
      return res.send(text);
  
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: "Proxy error", details: err.message });
    }
  }
  
  // Without bodyParser – allows passing the body as is
  export const config = { api: { bodyParser: false } };
  