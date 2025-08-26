export const config = { api: { bodyParser: false } };

export default async function handler(req, res) {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const rest = url.pathname.replace(/^\/api\/v1\/questionnaire\/?/, ''); // '' או 'status/...'
  const upstream = `http://apt-scanner.us-east-1.elasticbeanstalk.com/api/v1/questionnaire/${rest}${url.search}`;

  try {
    const r = await fetch(upstream, {
      method: req.method,
      headers: { ...req.headers, host: undefined, connection: undefined },
      body: ['GET','HEAD'].includes(req.method) ? undefined : req,
    });

    res.status(r.status);
    const ct = r.headers.get('content-type') || '';
    if (r.status === 204) return res.end();
    if (ct.includes('application/json')) return res.json(await r.json());
    return res.send(await r.text());
  } catch (e) {
    res.status(502).json({ error: 'Bad gateway', details: e.message });
  }
}
