const apiPrefix = "/api/v1";

const state = {
  token: localStorage.getItem("ufpb_token") || "",
  user: JSON.parse(localStorage.getItem("ufpb_user") || "null"),
  selectedConversationId: null,
  conversations: [],
  messageSignaturesByConversation: {},
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
  // Infinite scroll state
  messagesByConversation: {},
  messageOffsets: {},
  isLoadingMessages: false,
  hasMoreMessages: {},
  messagesPerPage: 50,
  // Audio visualizer state
  audioContext: null,
  analyser: null,
  microphone: null,
  animationId: null,
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
  chatHeaderAvatar: document.getElementById("chatHeaderAvatar"),
  chatTitle: document.getElementById("chatTitle"),
  chatSubtitle: document.getElementById("chatSubtitle"),
  exportCurrentDayBtn: document.getElementById("exportCurrentDayBtn"),
  messageCountBadge: document.getElementById("messageCountBadge"),
  messages: document.getElementById("messages"),
  messageType: document.getElementById("messageType"),
  typeIconsContainer: document.getElementById("typeIconsContainer"),
  typeIcons: document.querySelectorAll(".btn-icon[data-type]"),
  textRow: document.getElementById("textRow"),
  textContent: document.getElementById("textContent"),
  mediaUrl: document.getElementById("mediaUrl"),
  mediaCaptionRow: document.getElementById("mediaCaptionRow"),
  mediaCaption: document.getElementById("mediaCaption"),
  mediaMimeType: document.getElementById("mediaMimeType"),
  mediaActionsRow: document.getElementById("mediaActionsRow"),
  imageFileInput: document.getElementById("imageFileInput"),
  uploadImageBtn: document.getElementById("uploadImageBtn"),
  recordAudioBtn: document.getElementById("recordAudioBtn"),
    sendMessageBtn: document.getElementById("sendMessageBtn"),
  recordOverlay: document.getElementById("recordOverlay"),
  recordTitle: document.getElementById("recordTitle"),
  recordHelp: document.getElementById("recordHelp"),
  recordPreview: document.getElementById("recordPreview"),
  recordError: document.getElementById("recordError"),
  cancelRecordBtn: document.getElementById("cancelRecordBtn"),
  startRecordBtn: document.getElementById("startRecordBtn"),
  stopRecordBtn: document.getElementById("stopRecordBtn"),
  audioVisualizer: document.getElementById("audioVisualizer"),
  audioCanvas: document.getElementById("audioCanvas"),
  audioPreview: document.getElementById("audioPreview"),
  audioPlayer: document.getElementById("audioPlayer"),
  exportOverlay: document.getElementById("exportOverlay"),
  exportDate: document.getElementById("exportDate"),
  exportStartTime: document.getElementById("exportStartTime"),
  exportEndTime: document.getElementById("exportEndTime"),
  exportProfile: document.getElementById("exportProfile"),
  exportError: document.getElementById("exportError"),
  closeExportBtn: document.getElementById("closeExportBtn"),
  downloadHtmlBtn: document.getElementById("downloadHtmlBtn"),
  downloadPdfBtn: document.getElementById("downloadPdfBtn"),
  cleanupSystemBtn: document.getElementById("cleanupSystemBtn"),
  cleanupContactsBtn: document.getElementById("cleanupContactsBtn"),
  appResizer: document.getElementById("appResizer"),
  leftPane: document.querySelector(".left-pane"),
  addContactBtn: document.getElementById("addContactBtn"),
  newContactOverlay: document.getElementById("newContactOverlay"),
  newContactForm: document.getElementById("newContactForm"),
  newContactName: document.getElementById("newContactName"),
  newContactPhone: document.getElementById("newContactPhone"),
  newContactError: document.getElementById("newContactError"),
  closeNewContactBtn: document.getElementById("closeNewContactBtn"),
  catalogBtn: document.getElementById("catalogBtn"),
  catalogOverlay: document.getElementById("catalogOverlay"),
  closeCatalogBtn: document.getElementById("closeCatalogBtn"),
  catalogSearch: document.getElementById("catalogSearch"),
  catalogList: document.getElementById("catalogList"),
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
  state.catalogContacts = [];
  state.messageSignaturesByConversation = {};
  state.pendingMessageRefresh = null;
  state.loginChallengeId = null;
  localStorage.removeItem("ufpb_token");
  localStorage.removeItem("ufpb_user");
}

function showToast(message, type = 'error', duration = 8000) {
  els.toast.textContent = message;
  els.toast.className = `toast toast-${type}`;
  els.toast.classList.remove("hidden");
  
  // Limpa timeout anterior se existir
  if (window.toastTimeout) {
    clearTimeout(window.toastTimeout);
  }
  
  // Remove toast após o tempo especificado
  window.toastTimeout = setTimeout(() => {
    els.toast.classList.add("hidden");
    window.toastTimeout = null;
  }, duration);
}

function showErrorToast(message) {
  showToast(message, 'error', 10000); // Erros ficam 10 segundos
}

function showSuccessToast(message) {
  showToast(message, 'success', 5000);
}

function showInfoToast(message) {
  showToast(message, 'info', 6000);
}

function showLoadingIndicator() {
  const loadingDiv = document.createElement('div');
  loadingDiv.id = 'messagesLoading';
  loadingDiv.className = 'messages-loading';
  loadingDiv.innerHTML = '<div class="loading-spinner"></div><span>Carregando mais mensagens...</span>';
  els.messages.appendChild(loadingDiv);
}

function hideLoadingIndicator() {
  const loadingDiv = document.getElementById('messagesLoading');
  if (loadingDiv) {
    loadingDiv.remove();
  }
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
    return;
  }
  els.currentUserName.textContent = state.user.name;
  els.currentUserEmail.textContent = state.user.email;
  els.adminSection.classList.toggle("hidden", !state.user.is_admin);
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
    const errorMsg = data.error?.message || data.detail || "Sessão expirada. Faça login novamente.";
    const authError = new Error(errorMsg);
    authError.status = 401;
    throw authError;
  }

  if (!response.ok) {
    const errorMsg = data.error?.message || data.detail || `Erro da API: ${response.status}`;
    const requestError = new Error(errorMsg);
    requestError.status = response.status;
    requestError.responseData = data;
    requestError.responseText = text;
    console.error('API Error Details:', {
      status: response.status,
      url: `${apiPrefix}${path}`,
      data: data,
      text: text,
      headers: headers
    });
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
  const audioElements = els.messages.querySelectorAll("audio");
  const videoElements = els.messages.querySelectorAll("video");
  
  // Verificar áudios
  for (const mediaElement of audioElements) {
    if (!mediaElement.paused && !mediaElement.ended) {
      return true;
    }
  }
  
  // Verificar vídeos
  for (const mediaElement of videoElements) {
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
  els.mediaCaptionRow.classList.toggle("hidden", isText);
  els.mediaActionsRow.classList.toggle("hidden", isText);
  els.uploadImageBtn.classList.toggle("hidden", type !== "image" && type !== "document");
  els.recordAudioBtn.classList.toggle("hidden", type !== "audio");

  if (type === "document") {
    els.imageFileInput.accept = "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.txt,.csv,.zip,.rar";
    els.uploadImageBtn.textContent = "Anexar arquivo local";
  } else {
    els.imageFileInput.accept = "image/*";
    els.uploadImageBtn.textContent = "Enviar imagem local";
  }
}

function updateTypeIcons() {
  if (!els.typeIcons) return;
  const currentType = els.messageType.value;
  els.typeIcons.forEach(icon => {
    if (icon.dataset.type === currentType) {
      icon.classList.add("active");
    } else {
      icon.classList.remove("active");
    }
  });
}

function resetComposer() {
  els.messageType.value = "text";
  updateTypeIcons();
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

async function fetchLoginChallenge(autoGenerate = false) {
  try {
    console.log('Buscando nova charada... autoGenerate:', autoGenerate);
    
    const response = await fetch(`${apiPrefix}/auth/challenge?ts=${Date.now()}`, {
      method: "GET",
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache",
        Pragma: "no-cache",
      },
    });
    
    console.log('Challenge response status:', response.status);
    
    if (!response.ok) {
      throw new Error(`Falha ao obter charada (${response.status}).`);
    }
    
    const challenge = await response.json();
    console.log('Challenge recebida:', challenge);
    
    if (!challenge.challenge_id || !challenge.question) {
      throw new Error("Resposta da charada inválida.");
    }
    
    state.loginChallengeId = challenge.challenge_id;
    els.challengeQuestion.textContent = `${challenge.question} (expira em ${challenge.expires_in_seconds}s)`;
    els.challengeAnswer.value = "";
    els.loginError.textContent = "";
    
    console.log('Charada carregada com sucesso:', {
      id: challenge.challenge_id,
      question: challenge.question,
      expires_in: challenge.expires_in_seconds
    });
    
  } catch (error) {
    console.error('Challenge Error:', error);
    state.loginChallengeId = null;
    els.challengeQuestion.textContent = "Não foi possível carregar charada. Atualize a página.";
    els.loginError.textContent = "Erro ao carregar charada. Tente novamente.";
    
    // Só tenta novamente automaticamente se for erro de conexão E se for chamada automaticamente
    if (autoGenerate && (error.message?.includes('fetch') || error.message?.includes('network'))) {
      setTimeout(() => {
        console.log('Tentando carregar charada novamente...');
        fetchLoginChallenge(true);
      }, 2000);
    }
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
  // Parar visualizador
  stopAudioVisualizer();
  
  // Parar gravação
  state.activeRecorder?.stop();
  state.activeStream?.getTracks().forEach((t) => t.stop());
  state.activeRecorder = null;
  state.recordKind = null;
  
  // Esconder modal
  els.recordOverlay.classList.add("hidden");
  els.startRecordBtn.classList.remove("hidden");
  els.stopRecordBtn.classList.add("hidden");
  els.audioVisualizer.classList.add("hidden");
  els.audioPreview.classList.add("hidden");
}

function startAudioVisualizer() {
  try {
    // Criar contexto de áudio
    state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 256;
    
    // Conectar microfone ao analisador
    const source = state.audioContext.createMediaStreamSource(state.activeStream);
    source.connect(state.analyser);
    
    // Mostrar visualizador
    els.audioVisualizer.classList.remove("hidden");
    
    // Iniciar animação
    drawWaveform();
  } catch (error) {
    console.error('Erro ao iniciar visualizador:', error);
  }
}

function drawWaveform() {
  if (!state.analyser) return;
  
  const canvas = els.audioCanvas;
  const ctx = canvas.getContext('2d');
  const bufferLength = state.analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  
  function draw() {
    state.animationId = requestAnimationFrame(draw);
    
    state.analyser.getByteFrequencyData(dataArray);
    
    // Limpar canvas
    ctx.fillStyle = '#0c1f19';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Desenhar ondas
    const barWidth = (canvas.width / bufferLength) * 2.5;
    let barHeight;
    let x = 0;
    
    for (let i = 0; i < bufferLength; i++) {
      barHeight = (dataArray[i] / 255) * canvas.height * 0.8;
      
      // Cor verde para as ondas
      const r = 34 + (dataArray[i] / 255) * 50;
      const g = 197 + (dataArray[i] / 255) * 58;
      const b = 94 + (dataArray[i] / 255) * 50;
      
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
      ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
      
      x += barWidth + 1;
    }
  }
  
  draw();
}

function stopAudioVisualizer() {
  if (state.animationId) {
    cancelAnimationFrame(state.animationId);
    state.animationId = null;
  }
  
  if (state.audioContext) {
    state.audioContext.close();
    state.audioContext = null;
  }
  
  state.analyser = null;
  state.microphone = null;
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
    els.recordTitle.textContent = "Gravar Áudio";
    els.recordHelp.textContent = "Clique em 'Iniciar Gravação' e permita acesso ao microfone.";
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

  // Atualizar texto para mostrar que estamos solicitando permissão
  els.recordHelp.textContent = "Solicitando permissão do microfone...";

  const confirmed = window.confirm(
    kind === "audio" ? "Deseja autorizar a gravação de áudio?" : "Deseja autorizar a gravação de vídeo?"
  );
  if (!confirmed) {
    els.recordHelp.textContent = "Clique em 'Iniciar Gravação' e permita acesso ao microfone.";
    return;
  }

  try {
    // Only audio recording is supported - video recording removed
    if (kind === "video") {
      els.recordError.textContent = "Video recording is no longer supported. Please use audio only.";
      els.recordError.classList.remove("hidden");
      return;
    }
    
    const constraints = { audio: true, video: false };
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    state.activeStream = stream;

    const preferredMime = "audio/webm";
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
          const mimeType = options.mimeType || "audio/webm";
          const blob = new Blob(chunks, { type: mimeType });
          const file = new File([blob], `audio-${Date.now()}.webm`, { type: mimeType });
          const uploaded = await uploadMediaFile(file);
          els.messageType.value = "audio";
          updateTypeIcons();
          setComposerVisibility();
          els.mediaUrl.value = uploaded.media_url;
          els.mediaMimeType.value = uploaded.mime_type || mimeType;
          showSuccessToast("Áudio anexado com sucesso.");
        } catch (error) {
          showToast(error.message || "Falha ao anexar gravação.");
        } finally {
          closeRecordModal();
        }
      })();
    };

    state.activeRecorder = recorder;
    recorder.start();
    
    // Iniciar visualizador de áudio
    startAudioVisualizer();
    
    // Atualizar UI
    els.startRecordBtn.classList.add("hidden");
    els.stopRecordBtn.classList.remove("hidden");
    els.recordHelp.textContent = "Gravando... clique em 'Parar e Anexar' quando terminar.";
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
  
  const originalBtnText = els.uploadImageBtn.textContent;
  els.uploadImageBtn.disabled = true;
  els.uploadImageBtn.innerHTML = '<span class="loading-spinner-inline"></span> Anexando...';

  try {
    const uploaded = await uploadMediaFile(file);
    const type = file.type.startsWith("image/") ? "image" : "document";
    els.messageType.value = type;
    updateTypeIcons();
    setComposerVisibility();
    els.mediaUrl.value = uploaded.media_url;
    els.mediaMimeType.value = uploaded.mime_type || file.type;
    showSuccessToast("Arquivo anexado.");
  } catch (error) {
    showToast(error.message || "Falha ao enviar arquivo.");
  } finally {
    els.imageFileInput.value = "";
    els.uploadImageBtn.disabled = false;
    els.uploadImageBtn.textContent = originalBtnText;
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
  showSuccessToast("Usuário criado.");
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
    showSuccessToast(activate ? "Usuário ativado." : "Usuário desativado.");
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
    showSuccessToast("Senha resetada. O usuário trocará no próximo login.");
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

async function cleanupContacts() {
  if (!window.confirm("⚠️ CONFIRMAÇÃO NECESSÁRIA\n\nEsta ação IRREVERSÍVEL irá apagar:\n\n• TODOS os perfis de contatos salvos\n• TODAS as conversas (e todas as mensagens vinculadas a elas)\n\nEsta ação NÃO PODE ser desfeita!\n\nDeseja continuar?")) {
    return;
  }
  
  try {
    showInfoToast("Iniciando exclusão de contatos...");
    await apiRequest("/admin/cleanup/contacts", { method: "DELETE" });
    showSuccessToast("✅ Limpeza de contatos e conversas concluída!");
    
    // Reset state
    if (state.selectedConversationId) {
      state.selectedConversationId = null;
      els.messages.innerHTML = "<p>Sistema limpo. Selecione uma conversa.</p>";
      els.chatTitle.textContent = "Sistema Limpo";
      els.chatSubtitle.textContent = "Todas as mensagens foram removidas";
    }
    
    // Atualizar UI
    await loadConversations(true);
    await loadCatalog();
  } catch (error) {
    throw error;
  }
}

async function cleanupSystem() {
  if (!window.confirm("⚠️ CONFIRMAÇÃO NECESSÁRIA\n\nEsta ação IRREVERSIVEL irá apagar:\n\n• TODAS as mensagens do sistema\n• TODOS os arquivos da pasta uploads\n\nEsta ação NÃO PODE ser desfeita!\n\nDeseja continuar?")) {
    return;
  }
  
  try {
    showInfoToast("Iniciando limpeza do sistema...");
    
    // Apagar todas as mensagens
    await apiRequest("/admin/cleanup/messages", { method: "DELETE" });
    showSuccessToast("Todas as mensagens foram apagadas.");
    
    // Aguardar um pouco antes de apagar os arquivos
    setTimeout(async () => {
      try {
        showInfoToast("Apagando arquivos de upload...");
        
        // Apagar todos os arquivos de upload
        await apiRequest("/admin/cleanup/uploads", { method: "DELETE" });
        showSuccessToast("Todos os arquivos de upload foram apagados.");
        
        showSuccessToast("✅ Limpeza do sistema concluída com sucesso!");
        
        // Limpar interface
        if (state.selectedConversationId) {
          state.selectedConversationId = null;
          els.messages.innerHTML = "<p>Sistema limpo. Selecione uma conversa.</p>";
          els.chatTitle.textContent = "Sistema Limpo";
          els.chatSubtitle.textContent = "Todas as mensagens foram removidas";
        }
        
        // Limpar conversas
        await loadConversations(true);
        
      } catch (error) {
        console.error('Erro ao apagar arquivos:', error);
        showErrorToast("Erro ao apagar arquivos: " + (error.message || "Erro desconhecido"));
      }
    }, 2000);
    
  } catch (error) {
    console.error('Erro ao apagar mensagens:', error);
    showErrorToast("Erro ao apagar mensagens: " + (error.message || "Erro desconhecido"));
  }
}

function getInitials(name) {
  if (!name || name === "Contato sem nome") return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return parts[0][0].toUpperCase();
}

function stringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h = Math.abs(hash) % 360;
  return `hsl(${h}, 65%, 45%)`;
}

function formatDeliveryStatus(status) {
  if (!status || status === "null") return "";
  const s = status.toLowerCase();
  if (s === "sent") return "enviada";
  if (s === "received") return "recebida";
  if (s === "failed") return "falhou";
  if (s === "delivered") return "entregue";
  if (s === "read") return "lida";
  if (s === "pending") return "pendente";
  return status;
}

function renderConversations() {
  if (!state.conversations.length) {
    els.conversationList.innerHTML = `<li class="conversation-item">Nenhuma conversa ainda.</li>`;
    return;
  }
  els.conversationList.innerHTML = state.conversations
    .map((conversation) => {
      const activeClass = String(conversation.id) === String(state.selectedConversationId) ? "active" : "";
      const fallbackName = conversation.contact_name || conversation.contact_phone || "Contato sem nome";
      const initials = getInitials(fallbackName);
      const bgColor = stringToColor(conversation.contact_phone || fallbackName);
      const avatarContent = conversation.profile_picture_url 
        ? `<img src="${escapeHtml(conversation.profile_picture_url)}" alt="Avatar">`
        : initials;
      return `
        <li class="conversation-item ${activeClass}" data-id="${conversation.id}">
          <div class="conversation-avatar" style="${conversation.profile_picture_url ? 'background-color: transparent;' : `background-color: ${bgColor};`}">${avatarContent}</div>
          <div class="conversation-info">
            <div class="conversation-name">${escapeHtml(fallbackName)}</div>
            <div class="conversation-phone">${escapeHtml(conversation.contact_phone)}</div>
            <div class="conversation-phone">Atualizado: ${formatDate(conversation.last_message_at)}</div>
          </div>
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
  if (message.message_type === "document") {
    const urlHTML = message.media_url 
      ? `<a href="${safeUrl}" target="_blank" style="color:#0a3b2b;text-decoration:none;font-weight:700;">Baixar / Abrir arquivo</a>`
      : `<span style="color:#666;font-size:12px;font-style:italic;">Arquivo indisponível para download</span>`;
    return `${safeCaption ? `<p>${safeCaption}</p>` : ""}<div style="margin:8px 0;padding:12px;background:rgba(255,255,255,0.7);border-radius:8px;border:1px solid #d2dfd9;display:flex;align-items:center;gap:12px;"><span style="font-size:24px;">📄</span><div><strong>Documento</strong><br>${urlHTML}</div></div>`;
  }
  if (message.message_type === "audio" && message.media_url) {
    const encryptedHint = String(message.media_url).includes(".enc")
      ? `<p class="muted">Áudio criptografado do WhatsApp. Para reprodução no navegador, envie base64 no webhook de entrada.</p>`
      : "";
    return `${safeCaption ? `<p>${safeCaption}</p>` : ""}<audio class="message-audio" controls src="${safeUrl}"></audio>${encryptedHint}`;
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

function renderMessages(messages, options = {}) {
  const append = Boolean(options.append);
  const prepend = Boolean(options.prepend);
  const conversationId = state.selectedConversationId;
  
  // Atualiza contador de mensagens (sem piscamento)
  const allMessages = (append || prepend) ? (state.messagesByConversation[conversationId] || []) : messages;
  const currentCount = els.messageCountBadge.textContent;
  const newCount = `${allMessages.length} mensagens`;
  
  // Só atualiza se o contador mudou
  if (currentCount !== newCount) {
    els.messageCountBadge.textContent = newCount;
  }

  // Show/hide export button based on whether there are messages
  els.exportCurrentDayBtn.classList.toggle("hidden", allMessages.length === 0);

  if (!allMessages.length) {
    if (!append) {
      els.messages.innerHTML = "<p>Nenhuma mensagem nesta conversa.</p>";
    }
    return;
  }

  // Se for append, adiciona as novas mensagens no final com animação suave
  if (append) {
    const newMessagesHtml = messages
      .map((message) => {
        const klass = message.direction === "outbound" ? "outbound" : "inbound";
        const sender = message.direction === "outbound" ? (message.sender_name || state.user?.name || "Funcionário") : (message.sender_name || "Cliente");
        return `<article class="message-item ${klass} message-new">
            <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span>${escapeHtml(formatDeliveryStatus(message.delivery_status))}</span></div>
            ${buildMessageBody(message)}
          </article>`;
      })
      .join("");
    
    // Adiciona ao final existente
    els.messages.insertAdjacentHTML('beforeend', newMessagesHtml);
    
    // Animação suave para novas mensagens
    const newElements = els.messages.querySelectorAll('.message-new');
    newElements.forEach(element => {
      element.classList.add('message-new');
      setTimeout(() => {
        element.classList.remove('message-new');
      }, 500);
    });
    
    // Rola para o final suavemente
    setTimeout(() => {
      els.messages.scrollTo({
        top: els.messages.scrollHeight,
        behavior: 'smooth'
      });
    }, 100);
  } else if (prepend) {
    const oldScrollHeight = els.messages.scrollHeight;
    const newMessagesHtml = messages
      .map((message) => {
        const klass = message.direction === "outbound" ? "outbound" : "inbound";
        const sender = message.direction === "outbound" ? (message.sender_name || state.user?.name || "Funcionário") : (message.sender_name || "Cliente");
        return `<article class="message-item ${klass}">
            <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span>${escapeHtml(formatDeliveryStatus(message.delivery_status))}</span></div>
            ${buildMessageBody(message)}
          </article>`;
      })
      .join("");
      
    // Adiciona ao topo existente
    els.messages.insertAdjacentHTML('afterbegin', newMessagesHtml);
    
    // Ajusta o scroll para não perder a posição original
    els.messages.scrollTop += (els.messages.scrollHeight - oldScrollHeight);
  } else {
    // Renderização completa - usa fragment para evitar piscamento
    const fragment = document.createDocumentFragment();
    const tempDiv = document.createElement('div');
    
    tempDiv.innerHTML = allMessages
      .map((message) => {
        const klass = message.direction === "outbound" ? "outbound" : "inbound";
        const sender = message.direction === "outbound" ? (message.sender_name || state.user?.name || "Funcionário") : (message.sender_name || "Cliente");
        return `<article class="message-item ${klass}">
            <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span>${escapeHtml(formatDeliveryStatus(message.delivery_status))}</span></div>
            ${buildMessageBody(message)}
          </article>`;
      })
      .join("");
    
    // Move elementos para o fragment
    while (tempDiv.firstChild) {
      fragment.appendChild(tempDiv.firstChild);
    }
    
    // Substitui conteúdo de uma vez (sem piscamento)
    els.messages.innerHTML = '';
    els.messages.appendChild(fragment);
    
    // Sempre scroll para o fim no load completo
    els.messages.scrollTop = els.messages.scrollHeight;
  }
  
  // Configurar eventos de mídia
  setupMediaEvents();
}

function setupMediaEvents() {
  // Adicionar eventos a todos os elementos de áudio e vídeo
  const mediaElements = els.messages.querySelectorAll("audio, video");
  
  mediaElements.forEach(mediaElement => {
    // Remover eventos anteriores para evitar duplicação
    mediaElement.removeEventListener('play', handleMediaPlay);
    mediaElement.removeEventListener('pause', handleMediaPause);
    mediaElement.removeEventListener('ended', handleMediaEnded);
    
    // Adicionar novos eventos
    mediaElement.addEventListener('play', handleMediaPlay);
    mediaElement.addEventListener('pause', handleMediaPause);
    mediaElement.addEventListener('ended', handleMediaEnded);
  });
}

function handleMediaPlay() {
  // Mídia começou a reproduzir - polling será pausado automaticamente
}

function handleMediaPause() {
  // Mídia pausada - polling será retomado automaticamente
}

function handleMediaEnded() {
  // Mídia terminou - polling será retomado automaticamente
}

function exportCurrentDay() {
  if (!state.selectedConversationId) {
    showToast("Selecione uma conversa primeiro.");
    return;
  }
  
  // Get today's date in local timezone
  const today = new Date();
  const dateStr = today.toISOString().split('T')[0]; // YYYY-MM-DD format
  
  // Set export modal with today's date and full day range
  els.exportDate.value = dateStr;
  els.exportStartTime.value = "00:00";
  els.exportEndTime.value = "23:59";
  els.exportProfile.value = "indefinido";
  
  // Open export modal
  state.exportContext = { conversationId: state.selectedConversationId };
  els.exportOverlay.classList.remove("hidden");
}

async function loadConversations(preserveSelection = true) {
  const conversations = await apiRequest("/conversations?limit=100");
  
  if (preserveSelection && state.selectedConversationId) {
    const existInNew = conversations.some(c => String(c.id) === String(state.selectedConversationId));
    if (!existInNew) {
      let missingContact = state.conversations?.find(c => String(c.id) === String(state.selectedConversationId));
      if (!missingContact && state.catalogContacts) {
        missingContact = state.catalogContacts.find(c => String(c.id) === String(state.selectedConversationId));
      }
      if (missingContact) {
        conversations.unshift(missingContact);
      } else {
        conversations.unshift({
          id: state.selectedConversationId,
          contact_name: els.chatTitle.textContent !== "Selecione uma conversa" ? els.chatTitle.textContent : null,
          contact_phone: els.chatSubtitle.textContent !== "Aguardando seleção" ? els.chatSubtitle.textContent : "",
          last_message_at: new Date().toISOString()
        });
      }
    }
  }

  state.conversations = conversations;
  const previousSelection = state.selectedConversationId;
  if (!preserveSelection || !state.selectedConversationId) {
    state.selectedConversationId = conversations[0]?.id || null;
  } else if (!conversations.some((item) => String(item.id) === String(state.selectedConversationId))) {
    state.selectedConversationId = conversations[0]?.id || null;
  }
  const selectionChanged = previousSelection !== state.selectedConversationId;
  renderConversations();
  if (state.selectedConversationId) {
    const selected = conversations.find((item) => String(item.id) === String(state.selectedConversationId));
    els.chatTitle.textContent = selected?.contact_name || selected?.contact_phone || "Contato sem nome";
    els.chatSubtitle.textContent = selected?.contact_phone || "-";
    if (selected) {
      const avatarContent = selected.profile_picture_url 
        ? `<img src="${escapeHtml(selected.profile_picture_url)}" alt="Avatar">`
        : escapeHtml(getInitials(els.chatTitle.textContent));
      const bgColor = stringToColor(selected.contact_phone || els.chatTitle.textContent);
      els.chatHeaderAvatar.innerHTML = avatarContent;
      els.chatHeaderAvatar.style.cssText = selected.profile_picture_url ? "background-color: transparent;" : `background-color: ${bgColor};`;
      els.chatHeaderAvatar.classList.remove("hidden");
    }
    await loadMessages({ forceRender: selectionChanged });
  } else {
    els.chatTitle.textContent = "Selecione uma conversa";
    els.chatSubtitle.textContent = "Aguardando seleção";
    els.chatHeaderAvatar.classList.add("hidden");
    renderMessages([]);
  }
}

async function loadMessages(options = {}) {
  const forceRender = Boolean(options.forceRender);
  const loadMore = Boolean(options.loadMore);
  const limit = options.limit || state.messagesPerPage;
  
  if (!state.selectedConversationId) {
    renderMessages([]);
    return;
  }
  
  const conversationId = state.selectedConversationId;
  
  // Se estiver carregando mais mensagens, usa o offset existente
  const offset = loadMore ? (state.messageOffsets[conversationId] || 0) : 0;
  
  // Se já estiver carregando, não faz nada
  if (state.isLoadingMessages && !forceRender) {
    return;
  }
  
  state.isLoadingMessages = true;
  
  try {
    // Mostra indicador de carregamento no final
    if (loadMore) {
      showLoadingIndicator();
    }
    
    const messages = await apiRequest(
      `/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`
    );
    
    // Verifica se há novas mensagens antes de renderizar (otimização para evitar piscamento)
    const currentSignature = state.messageSignaturesByConversation[conversationId];
    const newSignature = buildMessageSignature(messages);
    
    // Se for loadMore, adiciona às mensagens existentes
    if (loadMore && state.messagesByConversation[conversationId]) {
      const existingMessages = state.messagesByConversation[conversationId];
      const allMessages = [...messages, ...existingMessages];
      state.messagesByConversation[conversationId] = allMessages;
      
      // Atualiza offset para próxima carga
      state.messageOffsets[conversationId] = offset + messages.length;
      
      // Verifica se há mais mensagens
      state.hasMoreMessages[conversationId] = messages.length === limit;
      
      renderMessages(messages, { prepend: true });
    } else {
      // Primeira carga ou refresh completo - só renderiza se houver mudanças
      if (!forceRender && currentSignature === newSignature) {
        // Não há novas mensagens, não renderiza para evitar piscamento
        return;
      }
      
      state.messagesByConversation[conversationId] = messages;
      state.messageOffsets[conversationId] = messages.length;
      state.hasMoreMessages[conversationId] = messages.length === limit;
      
      renderMessages(messages);
    }
    
    const signature = buildMessageSignature(messages);
    state.messageSignaturesByConversation[conversationId] = signature;
    
    if (state.pendingMessageRefresh?.conversationId === conversationId) {
      state.pendingMessageRefresh = null;
    }
    
  } catch (error) {
    console.error('Error loading messages:', error);
    showToast('Erro ao carregar mensagens.');
  } finally {
    state.isLoadingMessages = false;
    if (loadMore) {
      hideLoadingIndicator();
    }
  }
}

async function selectConversation(id) {
  state.selectedConversationId = id;
  renderConversations();
  const selected = state.conversations.find((item) => String(item.id) === String(id));
  els.chatTitle.textContent = selected?.contact_name || selected?.contact_phone || "Contato sem nome";
  els.chatSubtitle.textContent = selected?.contact_phone || "-";
  if (selected) {
    const avatarContent = selected.profile_picture_url 
      ? `<img src="${escapeHtml(selected.profile_picture_url)}" alt="Avatar">`
      : escapeHtml(getInitials(els.chatTitle.textContent));
    const bgColor = stringToColor(selected.contact_phone || els.chatTitle.textContent);
    els.chatHeaderAvatar.innerHTML = avatarContent;
    els.chatHeaderAvatar.style.cssText = selected.profile_picture_url ? "background-color: transparent;" : `background-color: ${bgColor};`;
    els.chatHeaderAvatar.classList.remove("hidden");
  }
  
  // Limpa estado do scroll infinito ao trocar de conversa
  state.messagesByConversation[id] = [];
  state.messageOffsets[id] = 0;
  state.hasMoreMessages[id] = true;
  state.isLoadingMessages = false;
  
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

async function login(email, password) {
  // Só gera nova charada se não tiver uma válida
  if (!state.loginChallengeId) {
    console.log('Nenhuma charada carregada, gerando nova...');
    await fetchLoginChallenge(true);
  }
  
  // Validações básicas
  if (!email || !password) {
    throw new Error("E-mail e senha são obrigatórios.");
  }
  
  if (!state.loginChallengeId) {
    throw new Error("Charada não carregada. Aguarde...");
  }
  
  const challengeAnswer = els.challengeAnswer.value.trim();
  if (!challengeAnswer) {
    throw new Error("Responda a charada antes de entrar.");
  }
  
  console.log('Enviando login:', {
    email: email.trim(),
    challenge_id: state.loginChallengeId,
    challenge_answer: challengeAnswer
  });
  
  const result = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: email.trim(),
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
  els.chatHeaderAvatar.classList.add("hidden");
  els.adminUsersTableBody.innerHTML = "";
  await fetchLoginChallenge(true);
}

async function initializeInbox() {
  clearPolls();
  if (state.user?.is_admin) {
    await loadAdminUsers();
  }
  await loadConversations(false);
  
  // Se o usuário fez logout, gera nova charada automaticamente
  if (!state.token) {
    await fetchLoginChallenge(true);
    return;
  }
  
  state.conversationPollTimer = setInterval(async () => {
    try {
      await loadConversations(true);
    } catch (error) {
      console.error(error);
    }
  }, 5000);
  state.messagePollTimer = setInterval(async () => {
    try {
      // Pausar atualização se houver mídia reproduzindo
      if (hasActiveMediaPlayback()) {
        return;
      }
      await loadMessages();
    } catch (error) {
      console.error(error);
    }
  }, 2000);
}

function setupResizer() {
  if (!els.appResizer || !els.leftPane) return;
  const savedWidth = localStorage.getItem("ufpb_left_pane_width");
  if (savedWidth) {
    els.leftPane.style.width = savedWidth;
  }
  let isResizing = false;
  els.appResizer.addEventListener("mousedown", (e) => {
    isResizing = true;
    els.appResizer.classList.add("is-resizing");
    document.body.style.cursor = "col-resize";
  });
  document.addEventListener("mousemove", (e) => {
    if (!isResizing) return;
    const newWidth = Math.max(320, typeof window !== "undefined" ? Math.min(e.clientX, window.innerWidth * 0.5) : e.clientX);
    els.leftPane.style.width = `${newWidth}px`;
  });
  document.addEventListener("mouseup", () => {
    if (isResizing) {
      isResizing = false;
      els.appResizer.classList.remove("is-resizing");
      document.body.style.cursor = "";
      localStorage.setItem("ufpb_left_pane_width", els.leftPane.style.width);
    }
  });
}

function openNewContactModal() {
  els.newContactError.textContent = "";
  els.newContactName.value = "";
  els.newContactPhone.value = "";
  els.newContactOverlay.classList.remove("hidden");
  els.newContactName.focus();
}

function closeNewContactModal() {
  els.newContactOverlay.classList.add("hidden");
}

async function createNewContact(event) {
  event.preventDefault();
  els.newContactError.textContent = "";
  try {
    const payload = {
      contact_phone: els.newContactPhone.value.trim(),
      contact_name: els.newContactName.value.trim() || undefined
    };
    const response = await apiRequest("/conversations", { 
      method: "POST", 
      body: JSON.stringify(payload) 
    });
    closeNewContactModal();
    showToast("Contato criado com sucesso!", "success");
    selectContactFromCatalog(response);
  } catch (error) {
    els.newContactError.textContent = error.message || "Erro ao criar contato.";
  }
}

async function loadCatalog() {
  els.catalogList.innerHTML = '<li style="padding: 12px; text-align: center;">Carregando...</li>';
  els.catalogOverlay.classList.remove("hidden");
  try {
    const contacts = await apiRequest("/conversations/contacts/all");
    state.catalogContacts = contacts;
    renderCatalog(state.catalogContacts);
  } catch (error) {
    els.catalogList.innerHTML = `<li style="padding: 12px; color: red;">Erro ao carregar contatos: ${error.message}</li>`;
  }
}

function renderCatalog(contactsToRender) {
  els.catalogList.innerHTML = "";
  if (contactsToRender.length === 0) {
    els.catalogList.innerHTML = '<li style="padding: 12px; text-align: center; color: var(--muted);">Nenhum contato encontrado.</li>';
    return;
  }
  
  contactsToRender.forEach(contact => {
    const li = document.createElement("li");
    li.className = "catalog-item";
    
    const info = document.createElement("div");
    info.className = "catalog-info";
    
    const name = document.createElement("span");
    name.className = "catalog-name";
    name.textContent = contact.contact_name || "Sem Nome";
    
    const phone = document.createElement("span");
    phone.className = "catalog-phone";
    phone.textContent = contact.contact_phone;
    
    info.appendChild(name);
    info.appendChild(phone);
    
    const actionArea = document.createElement("div");
    const chatBtn = document.createElement("button");
    chatBtn.type = "button";
    chatBtn.className = "btn btn-small";
    chatBtn.textContent = "Conversar";
    
    chatBtn.addEventListener("click", () => selectContactFromCatalog(contact));
    
    actionArea.appendChild(chatBtn);
    
    li.appendChild(info);
    li.appendChild(actionArea);
    
    els.catalogList.appendChild(li);
  });
}

function selectContactFromCatalog(contact) {
  els.catalogOverlay.classList.add("hidden");
  
  // Verify if it's already in the sidebar
  let existingIndex = state.conversations.findIndex(c => c.id === contact.id);
  
  if (existingIndex > -1) {
    // If it exists, move it to the top
    const existingChat = state.conversations.splice(existingIndex, 1)[0];
    state.conversations.unshift(existingChat);
  } else {
    // Otherwise, push it to the sidebar artificially
    state.conversations.unshift(contact);
  }
  
  renderConversations();
  
  const item = Array.from(els.conversationList.children).find(
    (li) => li.dataset.id === String(contact.id)
  );
  if (item) item.click();
}

els.catalogSearch.addEventListener("input", (e) => {
  const query = e.target.value.toLowerCase();
  const filtered = state.catalogContacts.filter(c => 
    (c.contact_name && c.contact_name.toLowerCase().includes(query)) ||
    (c.contact_phone && c.contact_phone.includes(query))
  );
  renderCatalog(filtered);
});

function bindEvents() {
  els.refreshChallengeBtn.addEventListener("click", async () => {
    await fetchLoginChallenge(true);
  });
  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    els.loginError.textContent = "";
    try {
      await login(els.loginEmail.value.trim(), els.loginPassword.value);
    } catch (error) {
      console.error('Login Error:', error);
      console.error('Error Details:', {
        status: error.status,
        message: error.message,
        challengeId: state.loginChallengeId,
        email: els.loginEmail.value.trim(),
        challengeAnswer: els.challengeAnswer.value.trim()
      });
      
      // Mostra erro persistente por mais tempo
      showErrorToast(error.message || "Falha no login.");
      
      // Se for erro de charada inválida (400), gera nova charada automaticamente
      // Mas não gera para erro 401 (senha/email incorretos)
      if (error.status === 400 || error.message?.includes('charada') || error.message?.includes('requisição')) {
        console.log('Gerando nova charada devido ao erro:', error.status, error.message);
        showInfoToast('Gerando nova charada automaticamente...');
        await fetchLoginChallenge(true);
        els.challengeAnswer.value = "";
        els.loginPassword.value = "";
      } else {
        console.log('Erro de autenticação (senha/email incorretos), não gerando nova charada. Erro:', error.status, error.message);
        // Limpa apenas a resposta da charada, mantém a senha
        els.challengeAnswer.value = "";
      }
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
  if (els.typeIcons) {
    els.typeIcons.forEach((icon) => {
      icon.addEventListener("click", () => {
        const type = icon.dataset.type;
        if (icon.classList.contains("active") && type !== "text") {
          els.messageType.value = "text";
        } else {
          els.messageType.value = type;
        }
        updateTypeIcons();
        setComposerVisibility();
      });
    });
  }
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
  els.exportCurrentDayBtn.addEventListener("click", () => exportCurrentDay());
  els.uploadImageBtn.addEventListener("click", () => els.imageFileInput.click());
  els.imageFileInput.addEventListener("change", async () => {
    await uploadImageFromLocal(els.imageFileInput.files?.[0]);
  });
  els.recordAudioBtn.addEventListener("click", () => openRecordModal("audio"));
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
  
  // Infinite scroll event listener
  els.messages.addEventListener("scroll", async () => {
    if (!state.selectedConversationId) return;
    
    const conversationId = state.selectedConversationId;
    const hasMore = state.hasMoreMessages[conversationId];
    const isLoading = state.isLoadingMessages;
    
    // Se estiver perto do topo e houver mais mensagens para carregar
    if (!isLoading && hasMore && els.messages.scrollTop <= 150) {
      await loadMessages({ loadMore: true });
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
  els.cleanupSystemBtn.addEventListener("click", async () => {
    try {
      await cleanupSystem();
    } catch (error) {
      console.error('Erro na limpeza do sistema:', error);
      showErrorToast("Erro na limpeza do sistema: " + (error.message || "Erro desconhecido"));
    }
  });
  els.cleanupContactsBtn.addEventListener("click", async () => {
    try {
      await cleanupContacts();
    } catch (error) {
      console.error('Erro na limpeza de contatos:', error);
      showErrorToast("Erro na limpeza de contatos: " + (error.message || "Erro desconhecido"));
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
  els.addContactBtn.addEventListener("click", openNewContactModal);
  els.closeNewContactBtn.addEventListener("click", closeNewContactModal);
  els.newContactForm.addEventListener("submit", createNewContact);
  
  els.catalogBtn.addEventListener("click", loadCatalog);
  els.closeCatalogBtn.addEventListener("click", () => els.catalogOverlay.classList.add("hidden"));
}

async function bootstrap() {
  setupResizer();
  bindEvents();
  setComposerVisibility();
  resetComposer();
  updateUserHeader();
  
  // Sempre gera nova charada ao iniciar a aplicação
  await fetchLoginChallenge(true);
  
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
