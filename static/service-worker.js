const CACHE_NAME = "restaurante-cache-v1";
const urlsToCache = [
  "/",
  "/static/img/logo.png",
  "/static/manifest.json",
  "/static/service-worker.js",
  "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
];

// Instalar el service worker y cachear archivos
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    }).catch((error) => {
      console.error("❌ Error al cachear durante install:", error);
    })
  );
});

// Interceptar solicitudes
self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Retorna del caché o hace fetch de la red
      return response || fetch(event.request).catch(() => {
        // Puedes retornar una página de error personalizada aquí si quieres
        return new Response("Sin conexión y recurso no encontrado en caché", {
          status: 404,
          statusText: "Offline / Not cached"
        });
      });
    })
  );
});

// Activar y limpiar caché viejo
self.addEventListener("activate", (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((cacheName) => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      )
    )
  );
});
