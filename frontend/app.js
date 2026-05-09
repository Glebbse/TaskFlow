const state = {
  authMode: "login",
  accessToken: localStorage.getItem("taskflow.accessToken") || "",
  user: null,
  tasks: [],
  total: 0,
  limit: 10,
  offset: 0,
};

const els = {
  authPanel: document.getElementById("authPanel"),
  workspace: document.getElementById("workspace"),
  sessionLabel: document.getElementById("sessionLabel"),
  statusMessage: document.getElementById("statusMessage"),
  viewTitle: document.getElementById("viewTitle"),
  viewSubtitle: document.getElementById("viewSubtitle"),
  authForm: document.getElementById("authForm"),
  authUsername: document.getElementById("authUsername"),
  authPassword: document.getElementById("authPassword"),
  authSubmit: document.getElementById("authSubmit"),
  taskCreateForm: document.getElementById("taskCreateForm"),
  taskTitle: document.getElementById("taskTitle"),
  taskDescription: document.getElementById("taskDescription"),
  taskList: document.getElementById("taskList"),
  searchInput: document.getElementById("searchInput"),
  doneFilter: document.getElementById("doneFilter"),
  sortBy: document.getElementById("sortBy"),
  sortOrder: document.getElementById("sortOrder"),
  refreshTasksButton: document.getElementById("refreshTasksButton"),
  prevPage: document.getElementById("prevPage"),
  nextPage: document.getElementById("nextPage"),
  pageInfo: document.getElementById("pageInfo"),
  logoutButton: document.getElementById("logoutButton"),
  logoutAllButton: document.getElementById("logoutAllButton"),
  passwordForm: document.getElementById("passwordForm"),
  currentPassword: document.getElementById("currentPassword"),
  newPassword: document.getElementById("newPassword"),
  profileId: document.getElementById("profileId"),
  profileUsername: document.getElementById("profileUsername"),
  profileRole: document.getElementById("profileRole"),
};

function saveTokens(tokens) {
  state.accessToken = tokens.access_token || "";
  localStorage.setItem("taskflow.accessToken", state.accessToken);
}

function clearSession() {
  state.accessToken = "";
  state.user = null;
  state.tasks = [];
  state.total = 0;
  localStorage.removeItem("taskflow.accessToken");
  renderSession();
}

function setStatus(message, type = "") {
  els.statusMessage.textContent = message;
  els.statusMessage.className = `status ${type}`.trim();
}

function errorDetail(data) {
  if (!data) return "Request failed";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((item) => item.msg).join("; ");
  }
  return "Request failed";
}

async function request(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (state.accessToken && options.auth !== false) {
    headers.set("Authorization", `Bearer ${state.accessToken}`);
  }

  const response = await fetch(path, { ...options, headers, credentials: "same-origin" });

  if (response.status === 401 && retry && path !== "/auth/refresh") {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request(path, options, false);
    }
  }

  if (!response.ok) {
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    throw new Error(errorDetail(data));
  }

  if (response.status === 204) return null;
  return response.json();
}

async function refreshAccessToken() {
  try {
    const tokens = await request(
      "/auth/refresh",
      {
        method: "POST",
        auth: false,
      },
      false,
    );
    saveTokens(tokens);
    return true;
  } catch {
    clearSession();
    return false;
  }
}

async function loadMe() {
  state.user = await request("/users/me");
  renderSession();
}

async function loadTasks() {
  const params = new URLSearchParams({
    limit: String(state.limit),
    offset: String(state.offset),
    sort_by: els.sortBy.value,
    order: els.sortOrder.value,
  });

  if (els.searchInput.value.trim()) {
    params.set("search", els.searchInput.value.trim());
  }
  if (els.doneFilter.value) {
    params.set("is_done", els.doneFilter.value);
  }

  const data = await request(`/tasks?${params.toString()}`);
  state.tasks = data.items;
  state.total = data.total;
  renderTasks();
}

function renderSession() {
  const signedIn = Boolean(state.user);
  els.authPanel.classList.toggle("hidden", signedIn);
  els.workspace.classList.toggle("hidden", !signedIn);
  els.sessionLabel.textContent = signedIn ? `${state.user.username} (${state.user.role})` : "Signed out";
  els.profileId.textContent = signedIn ? state.user.id : "-";
  els.profileUsername.textContent = signedIn ? state.user.username : "-";
  els.profileRole.textContent = signedIn ? state.user.role : "-";
  renderTasks();
}

function renderTasks() {
  els.viewSubtitle.textContent = `${state.total} tasks`;
  els.pageInfo.textContent = `Page ${Math.floor(state.offset / state.limit) + 1}`;
  els.prevPage.disabled = state.offset === 0;
  els.nextPage.disabled = state.offset + state.limit >= state.total;

  if (!state.user) {
    els.taskList.innerHTML = "";
    return;
  }

  if (!state.tasks.length) {
    els.taskList.innerHTML = '<div class="empty-state">No tasks</div>';
    return;
  }

  els.taskList.innerHTML = state.tasks.map((task) => `
    <article class="task-row ${task.is_done ? "done" : ""}" data-task-id="${task.id}">
      <input class="task-check" type="checkbox" ${task.is_done ? "checked" : ""} aria-label="Toggle task">
      <div>
        <p class="task-title">${escapeHtml(task.title)}</p>
        <p class="task-meta">${escapeHtml(task.description || "No description")} &middot; #${task.position}</p>
      </div>
      <div class="task-actions">
        <button class="button danger task-delete" type="button">Delete</button>
      </div>
    </article>
  `).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const payload = {
    username: els.authUsername.value.trim(),
    password: els.authPassword.value,
  };

  try {
    if (state.authMode === "register") {
      await request("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
        auth: false,
      });
    }

    const tokens = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
      auth: false,
    });
    saveTokens(tokens);
    await loadMe();
    await loadTasks();
    setStatus("Signed in", "ok");
    els.authForm.reset();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleCreateTask(event) {
  event.preventDefault();
  try {
    await request("/tasks", {
      method: "POST",
      body: JSON.stringify({
        title: els.taskTitle.value.trim(),
        description: els.taskDescription.value.trim() || null,
      }),
    });
    els.taskCreateForm.reset();
    state.offset = 0;
    await loadTasks();
    setStatus("Task added", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handleTaskListClick(event) {
  const row = event.target.closest(".task-row");
  if (!row) return;
  const taskId = row.dataset.taskId;

  try {
    if (event.target.classList.contains("task-delete")) {
      await request(`/tasks/${taskId}`, { method: "DELETE" });
      await loadTasks();
      setStatus("Task deleted", "ok");
      return;
    }

    if (event.target.classList.contains("task-check")) {
      await request(`/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_done: event.target.checked }),
      });
      await loadTasks();
    }
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function handlePasswordUpdate(event) {
  event.preventDefault();
  try {
    await request("/users/me/password", {
      method: "PATCH",
      body: JSON.stringify({
        current_password: els.currentPassword.value,
        new_password: els.newPassword.value,
      }),
    });
    els.passwordForm.reset();
    setStatus("Password updated", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function logout() {
  clearSession();
  try {
    await request("/auth/logout", {
      method: "POST",
      auth: false,
    }, false);
  } finally {
    setStatus("Logged out", "ok");
  }
}

async function logoutAll() {
  try {
    await request("/auth/logout-all", { method: "POST" });
    clearSession();
    setStatus("Logged out from all sessions", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

function bindEvents() {
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      state.authMode = button.dataset.authMode;
      document.querySelectorAll("[data-auth-mode]").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      els.authSubmit.textContent = state.authMode === "login" ? "Login" : "Register";
    });
  });

  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-view]").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.querySelectorAll(".view").forEach((view) => view.classList.add("hidden"));
      document.getElementById(button.dataset.view).classList.remove("hidden");
      els.viewTitle.textContent = button.textContent;
    });
  });

  els.authForm.addEventListener("submit", handleAuthSubmit);
  els.taskCreateForm.addEventListener("submit", handleCreateTask);
  els.taskList.addEventListener("click", handleTaskListClick);
  els.passwordForm.addEventListener("submit", handlePasswordUpdate);
  els.logoutButton.addEventListener("click", logout);
  els.logoutAllButton.addEventListener("click", logoutAll);
  els.refreshTasksButton.addEventListener("click", () => loadTasks().catch((error) => setStatus(error.message, "error")));

  [els.searchInput, els.doneFilter, els.sortBy, els.sortOrder].forEach((control) => {
    control.addEventListener("change", () => {
      state.offset = 0;
      loadTasks().catch((error) => setStatus(error.message, "error"));
    });
  });

  els.searchInput.addEventListener("input", debounce(() => {
    state.offset = 0;
    loadTasks().catch((error) => setStatus(error.message, "error"));
  }, 250));

  els.prevPage.addEventListener("click", () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadTasks().catch((error) => setStatus(error.message, "error"));
  });

  els.nextPage.addEventListener("click", () => {
    state.offset += state.limit;
    loadTasks().catch((error) => setStatus(error.message, "error"));
  });
}

function debounce(fn, wait) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), wait);
  };
}

async function boot() {
  bindEvents();
  renderSession();
  if (!state.accessToken) {
    await refreshAccessToken();
  }
  if (state.accessToken) {
    try {
      await loadMe();
      await loadTasks();
    } catch {
      clearSession();
    }
  }
}

boot();
