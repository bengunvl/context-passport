const http = require('http');
const fs   = require('fs');
const path = require('path');
const port = process.env.PORT || 3000;

// Every path served is resolved against this and then checked to be inside it.
// realpath so that the comparison holds if the checkout itself sits behind a
// symlink, which would otherwise make every request look like an escape.
const ROOT = fs.realpathSync(__dirname);

// Paths inside the root that are still not part of the published site.
//
// Deliberately a narrow list rather than "reject anything starting with a dot".
// The specification's own examples reference /.well-known/cp-revoked-keys.json
// and /.well-known/did.json, so a blanket rule on dotfiles would block a path
// this site has a stated reason to serve one day.
const DENIED_SEGMENTS = new Set(['.git']);

/**
 * Resolve a request path to a file inside ROOT, or null if it points outside.
 *
 * req.url is the raw request target and Node does not normalize it, so a
 * client writing to the socket directly can send "GET /../../etc/passwd".
 * path.join would happily resolve that to a real file outside the site root,
 * which is an arbitrary file read. Browsers collapse the dot segments before
 * sending, which is why this does not show up in ordinary use.
 *
 * Decoding happens before the containment check, otherwise %2e%2e walks up
 * just as well as "..".
 */
function resolveWithinRoot(urlPath) {
  let decoded;
  try {
    decoded = decodeURIComponent(urlPath);
  } catch {
    return null;   // malformed percent-encoding
  }
  if (decoded.includes('\0')) return null;

  // The leading "." keeps an absolute decoded path from escaping ROOT: resolve
  // would otherwise take "/etc/passwd" as the final, absolute answer.
  const candidate = path.resolve(ROOT, '.' + decoded);
  if (candidate !== ROOT && !candidate.startsWith(ROOT + path.sep)) return null;

  // Checked on the resolved path rather than on the request text, so that
  // spellings like /foo/../.git/config are caught after normalization rather
  // than being compared against as written.
  const relative = path.relative(ROOT, candidate);
  if (relative && relative.split(path.sep).some((segment) => DENIED_SEGMENTS.has(segment))) {
    return null;
  }

  return candidate;
}

const mime = {
  '.html': 'text/html',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.md':   'text/markdown',
  '.png':  'image/png',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/' || urlPath === '') urlPath = '/index.html';

  const tryServe = (candidate, onMiss) => {
    fs.stat(candidate, (statErr, stats) => {
      if (statErr) { onMiss(); return; }
      if (stats.isDirectory()) {
        // Directory request: try <dir>/index.html. Safe to join without a
        // second check, since candidate is already inside ROOT and the
        // appended segment is a constant.
        const indexCandidate = path.join(candidate, 'index.html');
        fs.readFile(indexCandidate, (idxErr, idxData) => {
          if (idxErr) { onMiss(); return; }
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(idxData);
        });
        return;
      }
      fs.readFile(candidate, (readErr, data) => {
        if (readErr) { onMiss(); return; }
        const ext = path.extname(candidate);
        res.writeHead(200, { 'Content-Type': mime[ext] || 'text/plain' });
        res.end(data);
      });
    });
  };

  // A miss is a 404, not the index page.
  //
  // This used to fall through to index.html for SPA-style routing. Nothing on
  // this site routes on the client, so there was no route being rescued: the
  // only internal links are /, /blog/ and a real file under /blog/, and each
  // of those resolves to something on disk. What the fallback did instead was
  // answer every mistyped, renamed or not-yet-deployed path with "200, here
  // is a document".
  //
  // That became expensive when SchemaStore/schemastore#6264 merged, because
  // editors now fetch /schema/*.json on their own without the user asking. A
  // 404 tells a validator the schema is not there. A 200 of HTML tells it the
  // schema arrived, so the JSON parse error surfaces against the user's own
  // document rather than against the URL, and the person seeing it has no
  // path back to the cause.
  //
  // text/plain rather than an HTML error page, so nothing reading the
  // content-type is told it was handed a document to parse.
  const serveNotFound = () => {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Not found\n');
  };

  const filePath = resolveWithinRoot(urlPath);

  // A path pointing outside the root is treated as a miss rather than as its
  // own status code. It gets the byte-for-byte response an unknown path gets,
  // so the reply says nothing about what does or does not exist out there.
  if (filePath === null) { serveNotFound(); return; }

  tryServe(filePath, serveNotFound);
}).listen(port, () => {
  console.log(`Context Passport running on port ${port}`);
});
