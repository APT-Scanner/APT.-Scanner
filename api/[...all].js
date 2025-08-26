export default async function handler(req, res) {
    const BACKEND_URL = 'http://apt-scanner.us-east-1.elasticbeanstalk.com';
    
    try {
        // Get the path from the URL
        const { all } = req.query;
        const path = Array.isArray(all) ? all.join('/') : all;
        
        // Build the target URL
        const url = new URL(req.url, `https://${req.headers.host}`);
        const queryString = url.search;
        const targetUrl = `${BACKEND_URL}/${path}${queryString}`;
        
        console.log(`Proxying: ${req.method} /${path} -> ${targetUrl}`);
        
        // Prepare headers
        const headers = {};
        if (req.headers.authorization) {
            headers['Authorization'] = req.headers.authorization;
        }
        if (req.headers['content-type']) {
            headers['Content-Type'] = req.headers['content-type'];
        }
        
        // Prepare request options
        const requestOptions = {
            method: req.method,
            headers: headers,
        };
        
        // Add body for non-GET requests
        if (req.method !== 'GET' && req.method !== 'HEAD') {
            if (req.body) {
                requestOptions.body = typeof req.body === 'string' 
                    ? req.body 
                    : JSON.stringify(req.body);
            }
        }
        
        // Make the request
        const response = await fetch(targetUrl, requestOptions);
        
        // Get response content type
        const contentType = response.headers.get('content-type');
        
        // Forward the response
        res.status(response.status);
        
        if (contentType) {
            res.setHeader('Content-Type', contentType);
        }
        
        // Handle response based on content type
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            res.json(data);
        } else {
            const text = await response.text();
            res.send(text);
        }
        
    } catch (error) {
        console.error('Proxy error:', error);
        res.status(502).json({
            error: 'Proxy request failed',
            message: error.message
        });
    }
}
