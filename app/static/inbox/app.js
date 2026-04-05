const apiPrefix = "/api/v1";

const state = {
  token: localStorage.getItem("ufpb_token") || "",
  user: JSON.parse(localStorage.getItem("ufpb_user") || "null"),
  selectedConversationId: null,
  conversations: [],
  messageSignaturesByConversation: {},
  selectedMessageIds: new Set(),
  pendingMessageRefresh: null,
  passwordForced: false,
  loginChallengeId: null,
  recordKind: null,
  activeRecorder: null,
  activeStream: null,
  discardRecordedMedia: false,
  messagePollTimer: null,
  conversationPollTimer: null,
  exportContext: null,
};

const els = {
  loginOverlay: document.getElementById("loginOverlay"),
  loginForm: document.getElementById("loginForm"),
  loginEmail: document.getElementById("loginEmail"),
  loginPassword: document.getElementById("loginPassword"),
  loginError: document.getElementById("loginError"),
  challengeQuestion: document.getElementById("challengeQuestion"),
  challengeAnswer: document.getElementById("challengeAnswer"),
  refreshChallengeBtn: document.getElementById("refreshChallengeBtn"),
  passwordOverlay: document.getElementById("passwordOverlay"),
  passwordForm: document.getElementById("passwordForm"),
  passwordTitle: document.getElementById("passwordTitle"),
  passwordHelp: document.getElementById("passwordHelp"),
  closePasswordModalBtn: document.getElementById("closePasswordModalBtn"),
  currentPassword: document.getElementById("currentPassword"),
  newPassword: document.getElementById("newPassword"),
  passwordError: document.getElementById("passwordError"),
  currentUserName: document.getElementById("currentUserName"),
  currentUserEmail: document.getElementById("currentUserEmail"),
  openPasswordBtn: document.getElementById("openPasswordBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  adminSection: document.getElementById("adminSection"),
  refreshUsersBtn: document.getElementById("refreshUsersBtn"),
  activeUsersOnly: document.getElementById("activeUsersOnly"),
  adminUsersTableBody: document.getElementById("adminUsersTableBody"),
  newUserName: document.getElementById("newUserName"),
  newUserEmail: document.getElementById("newUserEmail"),
  newUserPassword: document.getElementById("newUserPassword"),
  createUserBtn: document.getElementById("createUserBtn"),
  refreshConversationsBtn: document.getElementById("refreshConversationsBtn"),
  conversationList: document.getElementById("conversationList"),
  chatTitle: document.getElementById("chatTitle"),
  chatSubtitle: document.getElementById("chatSubtitle"),
  messageCountBadge: document.getElementById("messageCountBadge"),
  adminMessageTools: document.getElementById("adminMessageTools"),
  selectAllMessagesCheckbox: document.getElementById("selectAllMessagesCheckbox"),
  selectedMessagesCount: document.getElementById("selectedMessagesCount"),
  deleteCurrentConversationMessagesBtn: document.getElementById("deleteCurrentConversationMessagesBtn"),
  deleteSelectedMessagesBtn: document.getElementById("deleteSelectedMessagesBtn"),
  deleteAllMessagesBtn: document.getElementById("deleteAllMessagesBtn"),
  messages: document.getElementById("messages"),
  messageType: document.getElementById("messageType"),
  textRow: document.getElementById("textRow"),
  textContent: document.getElementById("textContent"),
  mediaUrlRow: document.getElementById("mediaUrlRow"),
  mediaUrl: document.getElementById("mediaUrl"),
  mediaCaptionRow: document.getElementById("mediaCaptionRow"),
  mediaCaption: document.getElementById("mediaCaption"),
  mediaMimeTypeRow: document.getElementById("mediaMimeTypeRow"),
  mediaMimeType: document.getElementById("mediaMimeType"),
  mediaActionsRow: document.getElementById("mediaActionsRow"),
  imageFileInput: document.getElementById("imageFileInput"),
  uploadImageBtn: document.getElementById("uploadImageBtn"),
  recordAudioBtn: document.getElementById("recordAudioBtn"),
  recordVideoBtn: document.getElementById("recordVideoBtn"),
  sendMessageBtn: document.getElementById("sendMessageBtn"),
  recordOverlay: document.getElementById("recordOverlay"),
  recordTitle: document.getElementById("recordTitle"),
  recordHelp: document.getElementById("recordHelp"),
  recordPreview: document.getElementById("recordPreview"),
  recordError: document.getElementById("recordError"),
  cancelRecordBtn: document.getElementById("cancelRecordBtn"),
  startRecordBtn: document.getElementById("startRecordBtn"),
  stopRecordBtn: document.getElementById("stopRecordBtn"),
  exportOverlay: document.getElementById("exportOverlay"),
  exportDate: document.getElementById("exportDate"),
  exportStartTime: document.getElementById("exportStartTime"),
  exportEndTime: document.getElementById("exportEndTime"),
  exportProfile: document.getElementById("exportProfile"),
  exportError: document.getElementById("exportError"),
  closeExportBtn: document.getElementById("closeExportBtn"),
  downloadHtmlBtn: document.getElementById("downloadHtmlBtn"),
  downloadPdfBtn: document.getElementById("downloadPdfBtn"),
  toast: document.getElementById("toast"),
};

function setSession(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("ufpb_token", token);
  localStorage.setItem("ufpb_user", JSON.stringify(user));
}

function clearSession() {
  state.token = "";
  state.user = null;
  state.selectedConversationId = null;
  state.conversations = [];
  state.messageSignaturesByConversation = {};
  state.selectedMessageIds = new Set();
  state.pendingMessageRefresh = null;
  state.loginChallengeId = null;
  localStorage.removeItem("ufpb_token");
  localStorage.removeItem("ufpb_user");
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  setTimeout(() => els.toast.classList.add("hidden"), 2800);
}

function escapeHtml(raw) {
  if (!raw) {
    return "";
  }
  return String(raw)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function updateUserHeader() {
  if (!state.user) {
    els.currentUserName.textContent = "-";
    els.currentUserEmail.textContent = "-";
    els.adminSection.classList.add("hidden");
    els.adminMessageTools.classList.add("hidden");
    return;
  }
  els.currentUserName.textContent = state.user.name;
  els.currentUserEmail.textContent = state.user.email;
  els.adminSection.classList.toggle("hidden", !state.user.is_admin);
  refreshAdminMessageTools();
}

function updateSelectedMessagesLabel() {
  const count = state.selectedMessageIds.size;
  els.selectedMessagesCount.textContent = `${count} selecionadas`;
  els.deleteSelectedMessagesBtn.disabled = count === 0;
}

function clearSelectedMessages() {
  state.selectedMessageIds = new Set();
  els.selectAllMessagesCheckbox.checked = false;
  updateSelectedMessagesLabel();
}

function refreshAdminMessageTools() {
  const showTools = Boolean(state.user?.is_admin && state.selectedConversationId);
  els.adminMessageTools.classList.toggle("hidden", !showTools);
  els.deleteCurrentConversationMessagesBtn.disabled = !showTools;
  if (!showTools) {
    clearSelectedMessages();
    return;
  }
  updateSelectedMessagesLabel();
}

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const isFormData = options.body instanceof FormData;
  if (!isFormData && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(`${apiPrefix}${path}`, { ...options, headers });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = {};
    }
  }

  if (response.status === 401) {
    await logout(false);
    const authError = new Error(data.detail || "Sessão expirada. Faça login novamente.");
    authError.status = 401;
    throw authError;
  }
  if (!response.ok) {
    const requestError = new Error(data.detail || "Erro na requisição.");
    requestError.status = response.status;
    throw requestError;
  }
  return data;
}

function formatDate(dateText) {
  if (!dateText) {
    return "-";
  }
  try {
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(dateText));
  } catch {
    return dateText;
  }
}

function formatDateRecife(dateText) {
  if (!dateText) {
    return "-";
  }
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
      timeZone: "America/Recife",
    }).format(new Date(dateText));
  } catch {
    return dateText;
  }
}

function hasActiveMediaPlayback() {
  const mediaElements = els.messages.querySelectorAll("audio, video");
  for (const mediaElement of mediaElements) {
    if (!mediaElement.paused && !mediaElement.ended) {
      return true;
    }
  }
  return false;
}

function buildMessageSignature(messages) {
  return messages
    .map((message) =>
      [
        message.id,
        message.delivery_status || "",
        message.text_content || "",
        message.media_url || "",
        message.media_mime_type || "",
        message.media_caption || "",
      ].join("|")
    )
    .join("||");
}

function setComposerVisibility() {
  const type = els.messageType.value;
  const isText = type === "text";
  els.textRow.classList.toggle("hidden", !isText);
  els.mediaUrlRow.classList.toggle("hidden", isText);
  els.mediaCaptionRow.classList.toggle("hidden", isText);
  els.mediaMimeTypeRow.classList.toggle("hidden", isText);
  els.mediaActionsRow.classList.toggle("hidden", isText);
  els.uploadImageBtn.classList.toggle("hidden", type !== "image");
  els.recordAudioBtn.classList.toggle("hidden", type !== "audio");
  els.recordVideoBtn.classList.toggle("hidden", type !== "video");
}

function resetComposer() {
  els.messageType.value = "text";
  els.textContent.value = "";
  els.mediaUrl.value = "";
  els.mediaCaption.value = "";
  els.mediaMimeType.value = "";
  setComposerVisibility();
}

function clearPolls() {
  if (state.messagePollTimer) {
    clearInterval(state.messagePollTimer);
    state.messagePollTimer = null;
  }
  if (state.conversationPollTimer) {
    clearInterval(state.conversationPollTimer);
    state.conversationPollTimer = null;
  }
}

async function fetchLoginChallenge() {
  try {
    const response = await fetch(`${apiPrefix}/auth/challenge?ts=${Date.now()}`, {
      method: "GET",
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache",
        Pragma: "no-cache",
      },
    });
    if (!response.ok) {
      throw new Error("Falha ao obter charada.");
    }
    const challenge = await response.json();
    state.loginChallengeId = challenge.challenge_id;
    els.challengeQuestion.textContent = `${challenge.question} (expira em ${challenge.expires_in_seconds}s)`;
  } catch {
    state.loginChallengeId = null;
    els.challengeQuestion.textContent = "Não foi possível carregar charada. Atualize a página.";
  }
}

function openPasswordModal(forced = false) {
  state.passwordForced = forced;
  els.passwordTitle.textContent = forced ? "Troca obrigatória de senha" : "Alterar senha";
  els.passwordHelp.textContent = forced ? "No primeiro acesso você precisa trocar a senha." : "Digite a senha atual e a nova senha.";
  els.closePasswordModalBtn.classList.toggle("hidden", forced);
  els.passwordError.textContent = "";
  els.passwordOverlay.classList.remove("hidden");
}

function closePasswordModal() {
  if (state.passwordForced) {
    return;
  }
  els.passwordOverlay.classList.add("hidden");
  els.currentPassword.value = "";
  els.newPassword.value = "";
}

function stopActiveStream() {
  if (!state.activeStream) {
    return;
  }
  for (const track of state.activeStream.getTracks()) {
    track.stop();
  }
  state.activeStream = null;
}

function closeRecordModal() {
  stopActiveStream();
  if (els.recordPreview.srcObject) {
    els.recordPreview.srcObject = null;
  }
  state.activeRecorder = null;
  state.recordKind = null;
  els.recordOverlay.classList.add("hidden");
  els.startRecordBtn.classList.remove("hidden");
  els.stopRecordBtn.classList.add("hidden");
}

function mapMediaError(error, kind) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return "Seu navegador não suporta gravação de mídia.";
  }
  if (error?.name === "NotAllowedError" || error?.name === "PermissionDeniedError") {
    return "Permissão negada. Autorize acesso ao microfone/webcam no navegador.";
  }
  if (error?.name === "NotFoundError" || error?.name === "DevicesNotFoundError") {
    return kind === "audio" ? "Nenhum microfone foi encontrado. Verifique seu dispositivo." : "Nenhuma webcam foi encontrada. Verifique seu dispositivo.";
  }
  if (error?.name === "NotReadableError") {
    return "Dispositivo ocupado por outro aplicativo. Feche o outro app e tente novamente.";
  }
  return "Não foi possível iniciar a gravação no momento.";
}

function openRecordModal(kind) {
  state.recordKind = kind;
  els.recordError.textContent = "";
  els.recordOverlay.classList.remove("hidden");
  els.startRecordBtn.classList.remove("hidden");
  els.stopRecordBtn.classList.add("hidden");

  if (kind === "audio") {
    els.recordTitle.textContent = "Gravar áudio";
    els.recordHelp.textContent = "Clique em iniciar e permita acesso ao microfone.";
    els.recordPreview.classList.add("hidden");
    els.recordPreview.srcObject = null;
  } else {
    els.recordTitle.textContent = "Gravar vídeo";
    els.recordHelp.textContent = "Clique em iniciar e permita acesso à webcam/microfone.";
    els.recordPreview.classList.remove("hidden");
    els.recordPreview.srcObject = null;
  }
}

async function uploadMediaFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiPrefix}/uploads/media`, {
    method: "POST",
    headers: { Authorization: `Bearer ${state.token}` },
    body: formData,
  });

  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = {};
    }
  }
  if (!response.ok) {
    throw new Error(data.detail || "Falha no upload.");
  }
  return data;
}

async function startRecording() {
  const kind = state.recordKind;
  if (!kind) {
    return;
  }

  const confirmed = window.confirm(
    kind === "audio" ? "Deseja autorizar a gravação de áudio?" : "Deseja autorizar a gravação de vídeo?"
  );
  if (!confirmed) {
    return;
  }

  try {
    const constraints = kind === "audio" ? { audio: true, video: false } : { audio: true, video: true };
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    state.activeStream = stream;
    if (kind === "video") {
      els.recordPreview.srcObject = stream;
    }

    const preferredMime = kind === "audio" ? "audio/webm" : "video/webm";
    const options = MediaRecorder.isTypeSupported(preferredMime) ? { mimeType: preferredMime } : {};
    const recorder = new MediaRecorder(stream, options);
    const chunks = [];
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunks.push(event.data);
      }
    };
    recorder.onstop = () => {
      void (async () => {
        const discard = state.discardRecordedMedia;
        state.discardRecordedMedia = false;
        stopActiveStream();
        if (discard || !chunks.length) {
          closeRecordModal();
          return;
        }
        try {
          const mimeType = options.mimeType || (kind === "audio" ? "audio/webm" : "video/webm");
          const blob = new Blob(chunks, { type: mimeType });
          const file = new File([blob], `${kind}-${Date.now()}.webm`, { type: mimeType });
          const uploaded = await uploadMediaFile(file);
          els.messageType.value = kind;
          setComposerVisibility();
          els.mediaUrl.value = uploaded.media_url;
          els.mediaMimeType.value = uploaded.mime_type || mimeType;
          showToast(`${kind === "audio" ? "Áudio" : "Vídeo"} anexado com sucesso.`);
        } catch (error) {
          showToast(error.message || "Falha ao anexar gravação.");
        } finally {
          closeRecordModal();
        }
      })();
    };

    state.activeRecorder = recorder;
    recorder.start();
    els.startRecordBtn.classList.add("hidden");
    els.stopRecordBtn.classList.remove("hidden");
  } catch (error) {
    els.recordError.textContent = mapMediaError(error, kind);
    stopActiveStream();
  }
}

function stopRecordingAndAttach() {
  if (!state.activeRecorder) {
    return;
  }
  state.discardRecordedMedia = false;
  state.activeRecorder.stop();
}

function cancelRecording() {
  if (state.activeRecorder) {
    state.discardRecordedMedia = true;
    state.activeRecorder.stop();
    return;
  }
  closeRecordModal();
}

async function uploadImageFromLocal(file) {
  if (!file) {
    return;
  }
  try {
    const uploaded = await uploadMediaFile(file);
    els.messageType.value = "image";
    setComposerVisibility();
    els.mediaUrl.value = uploaded.media_url;
    els.mediaMimeType.value = uploaded.mime_type || "image/*";
    showToast("Imagem anexada.");
  } catch (error) {
    showToast(error.message || "Falha ao enviar imagem.");
  } finally {
    els.imageFileInput.value = "";
  }
}

function buildUserRow(user) {
  const canManage = user.id !== state.user.id;
  return `
    <tr>
      <td>
        <strong>${escapeHtml(user.name)}</strong><br>
        <span class="muted">${escapeHtml(user.email)}</span>
      </td>
      <td>${user.is_active ? "Ativo" : "Inativo"}</td>
      <td>${formatDateRecife(user.last_login_at)}</td>
      <td>${formatDateRecife(user.last_logout_at)}</td>
      <td>
        <div class="table-actions">
          <button class="btn btn-outline btn-small" data-action="toggle-status" data-id="${user.id}" ${canManage ? "" : "disabled"}>${user.is_active ? "Desativar" : "Ativar"}</button>
          <button class="btn btn-outline btn-small" data-action="reset-password" data-id="${user.id}" ${canManage ? "" : "disabled"}>Reset senha</button>
          <button class="btn btn-outline btn-small" data-action="delete-user" data-id="${user.id}" ${canManage ? "" : "disabled"}>Excluir</button>
        </div>
      </td>
    </tr>
  `;
}

async function loadAdminUsers() {
  if (!state.user?.is_admin) {
    return;
  }
  const users = await apiRequest(`/users?active_only=${els.activeUsersOnly.checked ? "true" : "false"}`);
  els.adminUsersTableBody.innerHTML = users.length
    ? users.map(buildUserRow).join("")
    : `<tr><td colspan="5">Nenhum usuário encontrado.</td></tr>`;
}

async function createUserFromAdmin() {
  const name = els.newUserName.value.trim();
  const email = els.newUserEmail.value.trim();
  const password = els.newUserPassword.value;
  if (!name || !email || !password) {
    showToast("Preencha nome, e-mail e senha do novo usuário.");
    return;
  }
  await apiRequest("/users", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
  els.newUserName.value = "";
  els.newUserEmail.value = "";
  els.newUserPassword.value = "";
  await loadAdminUsers();
  showToast("Usuário criado.");
}

async function handleAdminUserAction(action, userId) {
  if (action === "toggle-status") {
    const rowButton = document.querySelector(`[data-action="toggle-status"][data-id="${userId}"]`);
    const activate = rowButton?.textContent?.trim() === "Ativar";
    await apiRequest(`/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: activate }),
    });
    await loadAdminUsers();
    showToast(activate ? "Usuário ativado." : "Usuário desativado.");
    return;
  }
  if (action === "reset-password") {
    const newPassword = window.prompt("Digite a nova senha temporária (mínimo 8 caracteres):");
    if (!newPassword) {
      return;
    }
    if (newPassword.length < 8) {
      showToast("A senha precisa ter pelo menos 8 caracteres.");
      return;
    }
    await apiRequest(`/users/${userId}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword }),
    });
    showToast("Senha resetada. O usuário trocará no próximo login.");
    await loadAdminUsers();
    return;
  }
  if (action === "delete-user") {
    if (!window.confirm("Confirma exclusão do usuário?")) {
      return;
    }
    await apiRequest(`/users/${userId}`, { method: "DELETE" });
    await loadAdminUsers();
    showToast("Usuário excluído.");
  }
}

function renderConversations() {
  if (!state.conversations.length) {
    els.conversationList.innerHTML = `<li class="conversation-item">Nenhuma conversa ainda.</li>`;
    return;
  }
  els.conversationList.innerHTML = state.conversations
    .map((conversation) => {
      const activeClass = conversation.id === state.selectedConversationId ? "active" : "";
      return `
        <li class="conversation-item ${activeClass}" data-id="${conversation.id}">
          <div class="conversation-name">${escapeHtml(conversation.contact_name || "Contato sem nome")}</div>
          <div class="conversation-phone">${escapeHtml(conversation.contact_phone)}</div>
          <div class="conversation-phone">Atualizado: ${formatDate(conversation.last_message_at)}</div>
        </li>
      `;
    })
    .join("");

  for (const item of document.querySelectorAll(".conversation-item[data-id]")) {
    item.addEventListener("click", async () => {
      await selectConversation(Number(item.dataset.id));
    });
  }
}

function buildMessageBody(message) {
  const safeText = escapeHtml(message.text_content || "");
  const safeCaption = escapeHtml(message.media_caption || "");
  const safeUrl = escapeHtml(message.media_url || "");
  if (message.message_type === "image" && message.media_url) {
    return `${safeCaption ? `<p>${safeCaption}</p>` : ""}<img class="message-media" src="${safeUrl}" alt="Imagem enviada">`;
  }
  if (message.message_type === "audio" && message.media_url) {
    const encryptedHint = String(message.media_url).includes(".enc")
      ? `<p class="muted">Áudio criptografado do WhatsApp. Para reprodução no navegador, envie base64 no webhook de entrada.</p>`
      : "";
    return `${safeCaption ? `<p>${safeCaption}</p>` : ""}<audio class="message-audio" controls src="${safeUrl}"></audio>${encryptedHint}`;
  }
  if (message.message_type === "video" && message.media_url) {
    return `${safeCaption ? `<p>${safeCaption}</p>` : ""}<video class="message-video" controls src="${safeUrl}"></video>`;
  }
  return `<p>${safeText || "[mensagem sem conteúdo textual]"}</p>`;
}

function openExportModal(referenceTimestamp) {
  const baseDate = referenceTimestamp ? new Date(referenceTimestamp) : new Date();
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Recife",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(baseDate);
  const y = parts.find((item) => item.type === "year")?.value || "1970";
  const m = parts.find((item) => item.type === "month")?.value || "01";
  const d = parts.find((item) => item.type === "day")?.value || "01";
  els.exportDate.value = `${y}-${m}-${d}`;
  els.exportStartTime.value = "00:00";
  els.exportEndTime.value = "23:59";
  els.exportProfile.value = "indefinido";
  els.exportError.textContent = "";
  state.exportContext = { conversationId: state.selectedConversationId };
  els.exportOverlay.classList.remove("hidden");
}

function closeExportModal() {
  els.exportOverlay.classList.add("hidden");
  state.exportContext = null;
}

function buildExportQuery() {
  const dateValue = els.exportDate.value;
  const startValue = els.exportStartTime.value || "00:00";
  const endValue = els.exportEndTime.value || "23:59";
  if (!dateValue) {
    throw new Error("Selecione a data para exportar.");
  }
  if (endValue < startValue) {
    throw new Error("Hora final não pode ser menor que hora inicial.");
  }
  const query = new URLSearchParams({
    export_date: dateValue,
    start_time: startValue,
    end_time: endValue,
    contact_profile: els.exportProfile.value,
  });
  return { query: query.toString(), date: dateValue, startTime: startValue, endTime: endValue };
}

function downloadBlob(content, filename, mimeType) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

function buildExportHtmlDocument(data) {
  const lines = data.entries
    .map((entry) => {
      const imageTag = entry.embedded_image_data_url
        ? `<div style="margin-top:6px;"><img src="${entry.embedded_image_data_url}" alt="Imagem da conversa" style="max-width:420px;border-radius:6px;border:1px solid #cfded7;"></div>`
        : "";
      const media = entry.media_url && !entry.embedded_image_data_url
        ? `<div><strong>Mídia:</strong> ${escapeHtml(entry.media_url)}</div>`
        : "";
      return `<article style="border:1px solid #d2dfd9;border-radius:8px;padding:8px;margin:8px 0;background:#fff;">
        <div style="font-size:12px;color:#4e6c62;margin-bottom:4px;">${escapeHtml(entry.timestamp_recife)} | ${escapeHtml(entry.author_name)} (${escapeHtml(entry.author_role)})</div>
        <div>${escapeHtml(entry.content)}</div>${imageTag}${media}</article>`;
    })
    .join("");

  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Conversa ${data.conversation_id}</title></head>
  <body style="font-family:Segoe UI,Arial,sans-serif;background:#f5faf7;padding:16px;color:#102b24;">
  <h1 style="margin:0 0 10px;">Relatório de Conversa</h1>
  <p><strong>Cliente:</strong> ${escapeHtml(data.contact_name)} | <strong>Perfil:</strong> ${escapeHtml(data.contact_profile)} | <strong>Telefone:</strong> ${escapeHtml(data.contact_phone)}</p>
  <p><strong>Intervalo:</strong> ${escapeHtml(data.date)} de ${escapeHtml(data.start_time)} até ${escapeHtml(data.end_time)}</p>
  <hr>${lines || "<p>Sem mensagens no intervalo selecionado.</p>"}</body></html>`;
}

async function downloadExportHtml() {
  if (!state.exportContext?.conversationId) {
    throw new Error("Nenhuma conversa selecionada.");
  }
  const { query, date, startTime, endTime } = buildExportQuery();
  const data = await apiRequest(`/conversations/${state.exportContext.conversationId}/export?${query}`);
  const filename = `conversa_${state.exportContext.conversationId}_${date}_${startTime.replace(":", "")}_${endTime.replace(":", "")}.html`;
  downloadBlob(buildExportHtmlDocument(data), filename, "text/html;charset=utf-8");
}

async function downloadExportPdf() {
  if (!state.exportContext?.conversationId) {
    throw new Error("Nenhuma conversa selecionada.");
  }
  const { query, date, startTime, endTime } = buildExportQuery();
  const response = await fetch(`${apiPrefix}/conversations/${state.exportContext.conversationId}/export/pdf?${query}`, {
    headers: { Authorization: `Bearer ${state.token}` },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Falha ao gerar PDF.");
  }
  const filename = `conversa_${state.exportContext.conversationId}_${date}_${startTime.replace(":", "")}_${endTime.replace(":", "")}.pdf`;
  downloadBlob(await response.blob(), filename, "application/pdf");
}

function renderMessages(messages) {
  els.messageCountBadge.textContent = `${messages.length} mensagens`;
  const visibleIds = new Set(messages.map((message) => message.id));
  for (const selectedId of Array.from(state.selectedMessageIds)) {
    if (!visibleIds.has(selectedId)) {
      state.selectedMessageIds.delete(selectedId);
    }
  }

  if (!messages.length) {
    els.messages.innerHTML = "<p>Nenhuma mensagem nesta conversa.</p>";
    refreshAdminMessageTools();
    return;
  }
  els.messages.innerHTML = messages
    .map((message) => {
      const klass = message.direction === "outbound" ? "outbound" : "inbound";
      const sender = message.direction === "outbound" ? (message.sender_name || state.user?.name || "Funcionário") : (message.sender_name || "Cliente");
      const adminSelect = state.user?.is_admin
        ? `<div class="message-select-row"><label><input type="checkbox" data-action="select-message" data-id="${message.id}" ${state.selectedMessageIds.has(message.id) ? "checked" : ""}> Selecionar</label></div>`
        : "";
      return `<article class="message-item ${klass}">
          ${adminSelect}
          <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span>${escapeHtml(message.delivery_status)}</span></div>
          ${buildMessageBody(message)}
          <div class="message-actions"><button class="btn btn-outline btn-small" data-action="export-message" data-created="${message.created_at}">Exportar dia desta mensagem</button></div>
        </article>`;
    })
    .join("");
  refreshAdminMessageTools();
  if (state.user?.is_admin) {
    const selectableCount = els.messages.querySelectorAll('[data-action="select-message"]').length;
    const selectedCount = els.messages.querySelectorAll('[data-action="select-message"]:checked').length;
    els.selectAllMessagesCheckbox.checked = selectableCount > 0 && selectedCount === selectableCount;
  }
  updateSelectedMessagesLabel();

  for (const checkbox of els.messages.querySelectorAll('[data-action="select-message"]')) {
    checkbox.addEventListener("change", () => {
      const messageId = Number(checkbox.dataset.id);
      if (!Number.isFinite(messageId) || messageId <= 0) {
        return;
      }
      if (checkbox.checked) {
        state.selectedMessageIds.add(messageId);
      } else {
        state.selectedMessageIds.delete(messageId);
      }
      const allCheckboxes = els.messages.querySelectorAll('[data-action="select-message"]');
      const selectedCheckboxes = els.messages.querySelectorAll('[data-action="select-message"]:checked');
      els.selectAllMessagesCheckbox.checked = allCheckboxes.length > 0 && allCheckboxes.length === selectedCheckboxes.length;
      updateSelectedMessagesLabel();
    });
  }

  for (const button of document.querySelectorAll('[data-action="export-message"]')) {
    button.addEventListener("click", () => openExportModal(button.dataset.created));
  }
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function loadConversations(preserveSelection = true) {
  const conversations = await apiRequest("/conversations?limit=100");
  state.conversations = conversations;
  const previousSelection = state.selectedConversationId;
  if (!preserveSelection || !state.selectedConversationId) {
    state.selectedConversationId = conversations[0]?.id || null;
  } else if (!conversations.some((item) => item.id === state.selectedConversationId)) {
    state.selectedConversationId = conversations[0]?.id || null;
  }
  const selectionChanged = previousSelection !== state.selectedConversationId;
  if (selectionChanged) {
    clearSelectedMessages();
  }
  renderConversations();
  refreshAdminMessageTools();
  if (state.selectedConversationId) {
    const selected = conversations.find((item) => item.id === state.selectedConversationId);
    els.chatTitle.textContent = selected?.contact_name || "Contato sem nome";
    els.chatSubtitle.textContent = selected?.contact_phone || "-";
    await loadMessages({ forceRender: selectionChanged });
  } else {
    els.chatTitle.textContent = "Selecione uma conversa";
    els.chatSubtitle.textContent = "Aguardando seleção";
    renderMessages([]);
  }
}

async function loadMessages(options = {}) {
  const forceRender = Boolean(options.forceRender);
  if (!state.selectedConversationId) {
    renderMessages([]);
    return;
  }
  const conversationId = state.selectedConversationId;
  const messages = await apiRequest(`/conversations/${conversationId}/messages?limit=200`);
  const signature = buildMessageSignature(messages);
  const previousSignature = state.messageSignaturesByConversation[conversationId];

  if (!forceRender && signature === previousSignature) {
    return;
  }

  if (!forceRender && hasActiveMediaPlayback()) {
    state.pendingMessageRefresh = { conversationId, signature };
    return;
  }

  renderMessages(messages);
  state.messageSignaturesByConversation[conversationId] = signature;
  if (state.pendingMessageRefresh?.conversationId === conversationId) {
    state.pendingMessageRefresh = null;
  }
}

async function selectConversation(id) {
  if (state.selectedConversationId !== id) {
    clearSelectedMessages();
  }
  state.selectedConversationId = id;
  renderConversations();
  refreshAdminMessageTools();
  const selected = state.conversations.find((item) => item.id === id);
  els.chatTitle.textContent = selected?.contact_name || "Contato sem nome";
  els.chatSubtitle.textContent = selected?.contact_phone || "-";
  await loadMessages({ forceRender: true });
}

async function sendMessage() {
  if (!state.selectedConversationId) {
    showToast("Selecione uma conversa antes de enviar.");
    return;
  }
  const messageType = els.messageType.value;
  const payload = {
    message_type: messageType,
    text_content: null,
    media_url: null,
    media_mime_type: null,
    media_caption: null,
  };
  if (messageType === "text") {
    if (!els.textContent.value.trim()) {
      showToast("Digite a mensagem de texto.");
      return;
    }
    payload.text_content = els.textContent.value.trim();
  } else {
    if (!els.mediaUrl.value.trim()) {
      showToast("Informe a URL da mídia.");
      return;
    }
    payload.media_url = els.mediaUrl.value.trim();
    payload.media_caption = els.mediaCaption.value.trim() || null;
    payload.media_mime_type = els.mediaMimeType.value.trim() || null;
    if (els.textContent.value.trim()) {
      payload.text_content = els.textContent.value.trim();
    }
  }
  await apiRequest(`/conversations/${state.selectedConversationId}/messages`, { method: "POST", body: JSON.stringify(payload) });
  resetComposer();
  await loadMessages();
  await loadConversations(true);
}

async function deleteSelectedMessagesFromConversation() {
  if (!state.user?.is_admin) {
    showToast("Apenas administrador pode apagar mensagens.");
    return;
  }
  if (!state.selectedConversationId) {
    showToast("Selecione uma conversa.");
    return;
  }
  const selectedIds = Array.from(state.selectedMessageIds);
  if (!selectedIds.length) {
    showToast("Selecione ao menos uma mensagem.");
    return;
  }
  if (!window.confirm(`Confirma apagar ${selectedIds.length} mensagem(ns) selecionada(s)?`)) {
    return;
  }

  const result = await apiRequest(`/conversations/${state.selectedConversationId}/messages/delete-selected`, {
    method: "POST",
    body: JSON.stringify({ message_ids: selectedIds }),
  });

  clearSelectedMessages();
  delete state.messageSignaturesByConversation[state.selectedConversationId];
  await loadConversations(true);
  showToast(`${result.deleted_count || selectedIds.length} mensagem(ns) apagada(s).`);
}

async function deleteAllMessagesFromCurrentConversation() {
  if (!state.user?.is_admin) {
    showToast("Apenas administrador pode apagar mensagens.");
    return;
  }
  if (!state.selectedConversationId) {
    showToast("Selecione uma conversa.");
    return;
  }

  const confirmed = window.confirm(
    "Isso vai apagar todas as mensagens da conversa selecionada. Deseja continuar?"
  );
  if (!confirmed) {
    return;
  }

  const result = await apiRequest(`/conversations/${state.selectedConversationId}/messages/all`, {
    method: "DELETE",
  });

  clearSelectedMessages();
  delete state.messageSignaturesByConversation[state.selectedConversationId];
  await loadConversations(true);
  showToast(`${result.deleted_count || 0} mensagem(ns) apagada(s) desta conversa.`);
}

async function deleteAllMessagesForTesting() {
  if (!state.user?.is_admin) {
    showToast("Apenas administrador pode apagar mensagens.");
    return;
  }
  const confirmed = window.confirm(
    "Isso vai apagar TODAS as mensagens do sistema (todas as conversas). Deseja continuar?"
  );
  if (!confirmed) {
    return;
  }

  const result = await apiRequest("/conversations/messages/all", { method: "DELETE" });
  clearSelectedMessages();
  state.messageSignaturesByConversation = {};
  await loadConversations(true);
  showToast(`${result.deleted_count || 0} mensagem(ns) apagada(s) no total.`);
}

async function login(email, password) {
  if (!state.loginChallengeId) {
    await fetchLoginChallenge();
  }
  const challengeAnswer = els.challengeAnswer.value.trim();
  if (!challengeAnswer) {
    throw new Error("Responda a charada antes de entrar.");
  }
  const result = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      challenge_id: state.loginChallengeId,
      challenge_answer: challengeAnswer,
    }),
  });
  setSession(result.access_token, result.user);
  updateUserHeader();
  els.loginOverlay.classList.add("hidden");
  els.loginPassword.value = "";
  els.challengeAnswer.value = "";
  if (result.must_change_password) {
    openPasswordModal(true);
  } else {
    await initializeInbox();
  }
}

async function changePassword(currentPassword, newPassword) {
  const user = await apiRequest("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  state.user = user;
  localStorage.setItem("ufpb_user", JSON.stringify(user));
  updateUserHeader();
  const wasForced = state.passwordForced;
  state.passwordForced = false;
  els.passwordOverlay.classList.add("hidden");
  els.currentPassword.value = "";
  els.newPassword.value = "";
  showToast("Senha alterada com sucesso.");
  if (wasForced) {
    await initializeInbox();
  } else if (state.user?.is_admin) {
    await loadAdminUsers();
  }
}

async function logout(callApi = true) {
  clearPolls();
  closeRecordModal();
  closeExportModal();
  if (callApi && state.token) {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch {
      // mantém logout local
    }
  }
  clearSession();
  updateUserHeader();
  els.loginOverlay.classList.remove("hidden");
  els.passwordOverlay.classList.add("hidden");
  els.messages.innerHTML = "";
  els.conversationList.innerHTML = "";
  els.chatTitle.textContent = "Selecione uma conversa";
  els.chatSubtitle.textContent = "Aguardando seleção";
  els.adminUsersTableBody.innerHTML = "";
  await fetchLoginChallenge();
}

async function initializeInbox() {
  clearPolls();
  if (state.user?.is_admin) {
    await loadAdminUsers();
  }
  await loadConversations(false);
  state.conversationPollTimer = setInterval(async () => {
    try {
      await loadConversations(true);
    } catch (error) {
      console.error(error);
    }
  }, 12000);
  state.messagePollTimer = setInterval(async () => {
    try {
      await loadMessages();
    } catch (error) {
      console.error(error);
    }
  }, 4000);
}

function bindEvents() {
  els.refreshChallengeBtn.addEventListener("click", async () => {
    await fetchLoginChallenge();
  });
  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    els.loginError.textContent = "";
    try {
      await login(els.loginEmail.value.trim(), els.loginPassword.value);
    } catch (error) {
      els.loginError.textContent = error.message || "Falha no login.";
      await fetchLoginChallenge();
      els.challengeAnswer.value = "";
    }
  });
  els.passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    els.passwordError.textContent = "";
    try {
      await changePassword(els.currentPassword.value, els.newPassword.value);
    } catch (error) {
      els.passwordError.textContent = error.message || "Falha ao alterar senha.";
    }
  });
  els.closePasswordModalBtn.addEventListener("click", closePasswordModal);
  els.openPasswordBtn.addEventListener("click", () => openPasswordModal(false));
  els.logoutBtn.addEventListener("click", async () => {
    await logout(true);
  });
  els.messageType.addEventListener("change", setComposerVisibility);
  els.sendMessageBtn.addEventListener("click", async () => {
    try {
      await sendMessage();
    } catch (error) {
      showToast(error.message || "Erro ao enviar mensagem.");
    }
  });
  els.refreshConversationsBtn.addEventListener("click", async () => {
    try {
      await loadConversations(true);
    } catch (error) {
      showToast(error.message || "Erro ao atualizar conversas.");
    }
  });
  els.selectAllMessagesCheckbox.addEventListener("change", () => {
    const shouldSelect = els.selectAllMessagesCheckbox.checked;
    const checkboxes = els.messages.querySelectorAll('[data-action="select-message"]');
    for (const checkbox of checkboxes) {
      checkbox.checked = shouldSelect;
      const messageId = Number(checkbox.dataset.id);
      if (!Number.isFinite(messageId) || messageId <= 0) {
        continue;
      }
      if (shouldSelect) {
        state.selectedMessageIds.add(messageId);
      } else {
        state.selectedMessageIds.delete(messageId);
      }
    }
    updateSelectedMessagesLabel();
  });
  els.deleteSelectedMessagesBtn.addEventListener("click", async () => {
    try {
      await deleteSelectedMessagesFromConversation();
    } catch (error) {
      showToast(error.message || "Falha ao apagar mensagens selecionadas.");
    }
  });
  els.deleteCurrentConversationMessagesBtn.addEventListener("click", async () => {
    try {
      await deleteAllMessagesFromCurrentConversation();
    } catch (error) {
      showToast(error.message || "Falha ao apagar mensagens da conversa.");
    }
  });
  els.deleteAllMessagesBtn.addEventListener("click", async () => {
    try {
      await deleteAllMessagesForTesting();
    } catch (error) {
      showToast(error.message || "Falha ao apagar todas as mensagens.");
    }
  });
  els.uploadImageBtn.addEventListener("click", () => els.imageFileInput.click());
  els.imageFileInput.addEventListener("change", async () => {
    await uploadImageFromLocal(els.imageFileInput.files?.[0]);
  });
  els.recordAudioBtn.addEventListener("click", () => openRecordModal("audio"));
  els.recordVideoBtn.addEventListener("click", () => openRecordModal("video"));
  els.startRecordBtn.addEventListener("click", async () => {
    await startRecording();
  });
  els.stopRecordBtn.addEventListener("click", stopRecordingAndAttach);
  els.cancelRecordBtn.addEventListener("click", cancelRecording);
  els.refreshUsersBtn.addEventListener("click", async () => {
    try {
      await loadAdminUsers();
    } catch (error) {
      showToast(error.message || "Falha ao carregar usuários.");
    }
  });
  els.activeUsersOnly.addEventListener("change", async () => {
    try {
      await loadAdminUsers();
    } catch (error) {
      showToast(error.message || "Falha ao aplicar filtro.");
    }
  });
  els.createUserBtn.addEventListener("click", async () => {
    try {
      await createUserFromAdmin();
    } catch (error) {
      showToast(error.message || "Falha ao criar usuário.");
    }
  });
  els.adminUsersTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      return;
    }
    try {
      await handleAdminUserAction(button.dataset.action, Number(button.dataset.id));
    } catch (error) {
      showToast(error.message || "Falha na operação de usuário.");
    }
  });
  els.closeExportBtn.addEventListener("click", closeExportModal);
  els.downloadHtmlBtn.addEventListener("click", async () => {
    els.exportError.textContent = "";
    try {
      await downloadExportHtml();
      showToast("HTML exportado.");
    } catch (error) {
      els.exportError.textContent = error.message || "Falha ao exportar HTML.";
    }
  });
  els.downloadPdfBtn.addEventListener("click", async () => {
    els.exportError.textContent = "";
    try {
      await downloadExportPdf();
      showToast("PDF exportado.");
    } catch (error) {
      els.exportError.textContent = error.message || "Falha ao exportar PDF.";
    }
  });
}

async function bootstrap() {
  bindEvents();
  setComposerVisibility();
  resetComposer();
  updateUserHeader();
  await fetchLoginChallenge();
  if (!state.token) {
    els.loginOverlay.classList.remove("hidden");
    return;
  }
  els.loginOverlay.classList.add("hidden");
  let me;
  try {
    me = await apiRequest("/auth/me");
  } catch {
    await logout(false);
    return;
  }

  state.user = me;
  localStorage.setItem("ufpb_user", JSON.stringify(me));
  updateUserHeader();
  if (me.must_change_password) {
    openPasswordModal(true);
    return;
  }

  try {
    await initializeInbox();
  } catch (error) {
    clearPolls();
    showToast(error.message || "Falha ao carregar inbox. Atualize a página.");
  }
}

bootstrap();
