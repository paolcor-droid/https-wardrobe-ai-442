// metro.config.js
const { getDefaultConfig } = require("expo/metro-config");
const path = require('path');
const { FileStore } = require('metro-cache');

const config = getDefaultConfig(__dirname);

// Use a stable on-disk store (shared across web/android)
const root = process.env.METRO_CACHE_ROOT || path.join(__dirname, '.metro-cache');
config.cacheStores = [
  new FileStore({ root: path.join(root, 'cache') }),
];


// // Exclude unnecessary directories from file watching
// config.watchFolders = [__dirname];
// config.resolver.blacklistRE = /(.*)\/(__tests__|android|ios|build|dist|.git|node_modules\/.*\/android|node_modules\/.*\/ios|node_modules\/.*\/windows|node_modules\/.*\/macos)(\/.*)?$/;

// // Alternative: use a more aggressive exclusion pattern
// config.resolver.blacklistRE = /node_modules\/.*\/(android|ios|windows|macos|__tests__|\.git|.*\.android\.js|.*\.ios\.js)$/;

// Reduce the number of workers to decrease resource usage
config.maxWorkers = 2;

// Codespaces web preview: proxy same-origin /api requests to local FastAPI.
// This avoids cross-origin requests to a separately authenticated private port.
const http = require("http");
const originalEnhanceMiddleware = config.server?.enhanceMiddleware;

config.server = {
  ...config.server,
  enhanceMiddleware(middleware, server) {
    const downstream = originalEnhanceMiddleware
      ? originalEnhanceMiddleware(middleware, server)
      : middleware;
    return (req, res, next) => {
      if (!req.url || !/^\/api(?:\/|\?|$)/.test(req.url)) {
        return downstream(req, res, next);
      }
      const headers = { ...req.headers, host: "127.0.0.1:8000" };
      delete headers.connection;
      const upstream = http.request(
        {
          hostname: "127.0.0.1",
          port: 8000,
          method: req.method,
          path: req.url,
          headers,
        },
        (upstreamResponse) => {
          res.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
          upstreamResponse.pipe(res);
        },
      );
      upstream.on("error", () => {
        if (!res.headersSent) {
          res.writeHead(502, { "Content-Type": "application/json" });
        }
        res.end(JSON.stringify({ detail: "Local FastAPI backend is unavailable" }));
      });
      req.pipe(upstream);
    };
  },
};

module.exports = config;
