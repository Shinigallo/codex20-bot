const http = require('http');
const port = process.env.PORT || 8080;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Codex20 is alive!\n');
});

server.listen(port, () => {
  console.log(`Health check server running on port ${port}`);
});
