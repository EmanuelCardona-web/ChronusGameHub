// ==========================================================
// Chronos Gaming Hub & Cloud Services - main.js
// Interacciones de la interfaz (diálogos, confirmaciones, filtros,
// menú lateral) y helpers para consumir la API JSON REST.
// Sin manejadores inline: compatible con la Content-Security-Policy.
// ==========================================================

const API_BASE = "";
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || "";

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        credentials: "same-origin",
        ...options,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": CSRF_TOKEN,
            ...(options.headers || {}),
        },
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

// ---------------- Interfaz ----------------
document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-open-dialog]");
    if (opener) {
        document.getElementById(opener.dataset.openDialog)?.showModal();
        return;
    }

    if (event.target.closest("[data-close-dialog]")) {
        event.target.closest("dialog")?.close();
        return;
    }

    // Clic en el fondo del diálogo lo cierra.
    if (event.target instanceof HTMLDialogElement) {
        event.target.close();
        return;
    }

    const flashClose = event.target.closest("[data-flash-close]");
    if (flashClose) {
        flashClose.closest("[data-flash]")?.remove();
        return;
    }

    if (event.target.closest("[data-sidebar-toggle]")) {
        document.querySelector("[data-app-shell]")?.classList.toggle("sidebar-open");
        return;
    }

    // Cierra el menú de usuario y el lateral al hacer clic fuera.
    document.querySelectorAll(".user-menu[open]").forEach((menu) => {
        if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
    const shell = document.querySelector("[data-app-shell].sidebar-open");
    if (shell && !event.target.closest(".sidebar")) shell.classList.remove("sidebar-open");
});

document.addEventListener("submit", (event) => {
    const message = event.target.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
});

document.addEventListener("input", (event) => {
    const tableId = event.target.dataset.tableFilter;
    if (!tableId) return;
    const term = event.target.value.trim().toLowerCase();
    document.querySelectorAll(`#${tableId} tbody tr`).forEach((row) => {
        row.hidden = term !== "" && !row.textContent.toLowerCase().includes(term);
    });
});

document.addEventListener("DOMContentLoaded", () => {
    // Los avisos de éxito se ocultan solos; los errores permanecen hasta cerrarlos.
    document.querySelectorAll(".flash-success[data-flash]").forEach((flash) => {
        setTimeout(() => {
            flash.classList.add("is-hidden");
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });
});
