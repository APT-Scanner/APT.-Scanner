// api/v1/[...path].js
export default function handler(req, res) {
    res.status(200).json({
      ok: true,
      matched: req.query.path || [],
      url: req.url,
      note: "catch-all alive"
    });
  }
  export const config = { api: { bodyParser: false } };
  