// ==========================================================
// Chronos Gaming Hub & Cloud Services - main.js
// Helpers para consumir la API JSON REST (/api/usuarios, /api/licencias)
// desde el frontend, además de las vistas HTML server-rendered.
// ==========================================================

const API_BASE = "";

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.error || `Error HTTP ${response.status}`);
    }

    if (response.status === 204) return null;
    return response.json();
}

// ---------------- Usuarios ----------------
const UsuariosAPI = {
    listar: () => apiRequest("/api/usuarios"),
    obtener: (id) => apiRequest(`/api/usuarios/${id}`),
    crear: (data) => apiRequest("/api/usuarios", { method: "POST", body: JSON.stringify(data) }),
    actualizar: (id, data) => apiRequest(`/api/usuarios/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    eliminar: (id) => apiRequest(`/api/usuarios/${id}`, { method: "DELETE" }),
};

// ---------------- Licencias ----------------
const LicenciasAPI = {
    listar: () => apiRequest("/api/licencias"),
    obtener: (id) => apiRequest(`/api/licencias/${id}`),
    crear: (data) => apiRequest("/api/licencias", { method: "POST", body: JSON.stringify(data) }),
    actualizar: (id, data) => apiRequest(`/api/licencias/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    eliminar: (id) => apiRequest(`/api/licencias/${id}`, { method: "DELETE" }),
};

// Expone las utilidades en la consola del navegador para pruebas rápidas.
window.Chronos = { UsuariosAPI, LicenciasAPI };

document.addEventListener("DOMContentLoaded", () => {
    console.log("%cChronos Gaming Hub & Cloud Services", "color:#00f0ff;font-weight:bold;");
    console.log("API disponible en window.Chronos.UsuariosAPI / window.Chronos.LicenciasAPI");
});
