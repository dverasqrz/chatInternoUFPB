const apiPrefix = "/api/v1";

const state = {
  token: localStorage.getItem("ufpb_token") || "",
  user: null,
  conversations: [],
  messagesByConversation: {},
  selectedConversationId: null,
  messageSignaturesByConversation: {},
  pendingMessageRefresh: null,
  passwordForced: false,
  loginChallengeId: null,
  recordKind: null,
  activeRecorder: null,
  activeStream: null,
  publicConfig: null, // Configuração pública do backend
  discardRecordedMedia: false,
  messagePollTimer: null,
  conversationPollTimer: null,
  exportContext: null,
  // Infinite scroll state
  messageOffsets: {},
  isLoadingMessages: false,
  hasMoreMessages: {},
  messagesPerPage: 50,
  // Audio visualizer state
  audioContext: null,
  analyser: null,
  microphone: null,
  animationId: null,
  // Mensagens prontas (templates) - carregadas do backend
  messageTemplates: [],
  showTemplates: false,
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
  searchGlobalBtn: document.getElementById("searchGlobalBtn"),
  searchGlobalOverlay: document.getElementById("searchGlobalOverlay"),
  closeSearchGlobalBtn: document.getElementById("closeSearchGlobalBtn"),
  searchGlobalInput: document.getElementById("searchGlobalInput"),
  doSearchGlobalBtn: document.getElementById("doSearchGlobalBtn"),
  searchGlobalStatus: document.getElementById("searchGlobalStatus"),
  searchGlobalResults: document.getElementById("searchGlobalResults"),
  conversationList: document.getElementById("conversationList"),
  chatHeaderAvatar: document.getElementById("chatHeaderAvatar"),
  chatTitle: document.getElementById("chatTitle"),
  chatSubtitle: document.getElementById("chatSubtitle"),
  exportCurrentDayBtn: document.getElementById("exportCurrentDayBtn"),
  messageCountBadge: document.getElementById("messageCountBadge"),
  messages: document.getElementById("messages"),
  // Elements do modal de templates
  templatesOverlay: document.getElementById("templatesOverlay"),
  templatesList: document.getElementById("templatesList"),
  closeTemplatesBtn: document.getElementById("closeTemplatesBtn"),
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
  openTemplatesManagerBtn: document.getElementById("openTemplatesManagerBtn"),
  templatesSummary: document.getElementById("templatesSummary"),
  emojiBtn: document.getElementById("emojiBtn"),
  emojiOverlay: document.getElementById("emojiOverlay"),
  closeEmojiBtn: document.getElementById("closeEmojiBtn"),
  emojiSearch: document.getElementById("emojiSearch"),
  emojiGrid: document.getElementById("emojiGrid"),
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
  aiConsultBtn: document.getElementById("aiConsultBtn"),
  aiConsultOverlay: document.getElementById("aiConsultOverlay"),
  closeAiConsultBtn: document.getElementById("closeAiConsultBtn"),
  copyAiResponseBtn: document.getElementById("copyAiResponseBtn"),
  askAiBtn: document.getElementById("askAiBtn"),
  aiQuestion: document.getElementById("aiQuestion"),
  aiResponse: document.getElementById("aiResponse"),
  clearAiHistoryBtn: document.getElementById("clearAiHistoryBtn"),
  aiHistory: document.getElementById("aiHistory"),
  aiHistoryEmpty: document.getElementById("aiHistoryEmpty"),
  // AI Config (Admin)
  configAiProvider: document.getElementById("configAiProvider"),
  configAiAgentEnabled: document.getElementById("configAiAgentEnabled"),
  saveAiConfigBtn: document.getElementById("saveAiConfigBtn"),
  mobileBackBtn: document.getElementById("mobileBackBtn"),
  mobileComposerBackBtn: document.getElementById("mobileComposerBackBtn"),
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

  // Usa URL completa se tiver domínio público configurado
  const baseUrl = state.publicConfig?.public_domain || '';
  // Remove barra final do baseUrl para evitar // duplo
  const cleanBaseUrl = baseUrl ? baseUrl.replace(/\/$/, '') : '';
  const fullUrl = cleanBaseUrl ? `${cleanBaseUrl}${apiPrefix}${path}` : `${apiPrefix}${path}`;

  // Log detalhado para debugging
  console.log('API Request:', {
    path,
    baseUrl,
    cleanBaseUrl,
    apiPrefix,
    fullUrl,
    method: options.method || 'GET',
    hasToken: !!state.token
  });

  let response;
  try {
    console.log(`Fazendo requisição fetch para: ${fullUrl}`);
    console.log('Headers da requisição:', headers);
    console.log('Opções da requisição:', options);
    
    response = await fetch(fullUrl, { ...options, headers });
    console.log(`Resposta recebida - Status: ${response.status}, OK: ${response.ok}`);
  } catch (fetchError) {
    console.error('=== ERRO DE FETCH (REDE) ===');
    console.error('Erro completo:', fetchError);
    console.error('Nome do erro:', fetchError.name);
    console.error('Mensagem do erro:', fetchError.message);
    console.error('URL tentada:', fullUrl);
    console.error('Método:', options.method || 'GET');
    console.error('Headers enviados:', headers);
    
    // Erros de rede específicos
    let errorMessage = "Erro de conexão com o servidor.";
    
    if (fetchError.name === 'TypeError' && fetchError.message.includes('Failed to fetch')) {
      errorMessage = "Não foi possível conectar ao servidor. Verifique sua conexão com a internet e se o backend está online.";
    } else if (fetchError.name === 'AbortError') {
      errorMessage = "A requisição foi cancelada. Tente novamente.";
    } else if (fetchError.message.includes('NetworkError')) {
      errorMessage = "Erro de rede. Verifique sua conexão com a internet.";
    } else if (fetchError.message.includes('CORS')) {
      errorMessage = "Erro de CORS. O servidor não permite requisições desta origem.";
    }
    
    const networkError = new Error(errorMessage);
    networkError.status = 0; // Indica erro de rede
    networkError.originalError = fetchError;
    networkError.url = fullUrl;
    throw networkError;
  }
  
  const text = await response.text();
  console.log(`Resposta text recebida (${text.length} caracteres):`, text.substring(0, 200) + (text.length > 200 ? '...' : ''));
  
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
      console.log('Resposta JSON parseada com sucesso:', data);
    } catch (parseError) {
      console.error('Erro ao fazer parse do JSON:', parseError);
      console.log('Texto bruto que falhou no parse:', text);
      data = {};
    }
  }

  if (response.status === 401) {
    console.log('Detectado status 401 - Fazendo logout');
    await logout(false);
    const errorMsg = data.error?.message || data.detail || "Sessão expirada. Faça login novamente.";
    const authError = new Error(errorMsg);
    authError.status = 401;
    throw authError;
  }

  if (!response.ok) {
    console.error('=== ERRO DE RESPOSTA DA API ===');
    console.error('Status:', response.status);
    console.error('Status Text:', response.statusText);
    console.error('Headers da resposta:', Object.fromEntries(response.headers.entries()));
    console.error('Dados parseados:', data);
    console.error('Texto bruto:', text);
    
    const errorMsg = data.error?.message || data.detail || data.message || `Erro da API: ${response.status} ${response.statusText}`;
    const requestError = new Error(errorMsg);
    requestError.status = response.status;
    requestError.responseData = data;
    requestError.responseText = text;
    requestError.statusText = response.statusText;
    
    console.error('API Error Details:', {
      status: response.status,
      statusText: response.statusText,
      url: fullUrl,
      data: data,
      text: text,
      headers: headers
    });
    throw requestError;
  }
  
  console.log(`Requisição bem sucedida para ${fullUrl}`);
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

// ===== Sistema de Mensagens Prontas (Templates) =====
function showTemplates() {
  renderTemplates();
  els.templatesOverlay.classList.remove("hidden");
  state.showTemplates = true;
}

function hideTemplates() {
  els.templatesOverlay.classList.add("hidden");
  state.showTemplates = false;
}

function renderTemplates() {
  console.log("=== RENDERIZANDO TEMPLATES ===");
  console.log("Número de templates disponíveis:", state.messageTemplates.length);
  console.log("Usuário é admin:", state.user?.is_admin);
  
  const isAdmin = state.user?.is_admin;
  
  // Limpar botões "Novo Template" antigos (fora da lista) para evitar botões duplicados
  if (els.templatesList && els.templatesList.parentElement) {
    const oldBtns = els.templatesList.parentElement.querySelectorAll(".add-template-btn");
    oldBtns.forEach(btn => {
      if (btn.parentElement === els.templatesList.parentElement) {
        btn.remove();
      }
    });
  }
  
  // Verificar se há templates
  if (!state.messageTemplates || state.messageTemplates.length === 0) {
    console.warn("Nenhum template disponível para renderizar");
    
    if (els.templatesList) {
      els.templatesList.innerHTML = `
        <div class="template-empty-state">
          <p>Nenhum template disponível no momento.</p>
          ${isAdmin ? `
            <p>Como administrador, você pode criar novos templates usando o botão abaixo.</p>
          ` : `
            <p>Entre em contato com o administrador para adicionar templates.</p>
          `}
        </div>
      `;
    }
    
    // Adicionar botão de novo template para admins mesmo sem templates
    if (isAdmin && els.templatesList) {
      const addTemplateBtn = document.createElement("button");
      addTemplateBtn.className = "btn btn-primary add-template-btn";
      addTemplateBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        Criar Primeiro Template
      `;
      addTemplateBtn.addEventListener("click", () => showTemplateEditor());
      els.templatesList.appendChild(addTemplateBtn);
    }
    
    return;
  }
  
  console.log("Renderizando templates:", state.messageTemplates.map(t => t.title));
  
  try {
    const templatesHtml = state.messageTemplates.map(template => {
      console.log(`Renderizando template: ${template.title} (ID: ${template.id})`);
      
      return `
        <div class="template-item" data-template-id="${template.id}">
          <div class="template-header">
            <h3 class="template-title">${escapeHtml(template.title)}</h3>
            <div class="template-meta">
              <span class="template-category">${escapeHtml(template.category)}</span>
              ${template.is_system ? '<span class="template-system-badge">Sistema</span>' : ''}
            </div>
          </div>
          <p class="template-content">${escapeHtml(template.content)}</p>
          ${isAdmin ? `
            <div class="template-actions">
              <button class="btn-small btn-outline edit-template-btn" data-template-id="${template.id}" title="Editar">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </button>
                <button class="btn-small btn-outline delete-template-btn" data-template-id="${template.id}" title="Excluir">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3,6 5,6 21,6"></polyline>
                    <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
            </div>
          ` : ''}
        </div>
      `;
    }).join("");

    if (els.templatesList) {
      els.templatesList.innerHTML = templatesHtml;
      console.log("Templates renderizados no DOM com sucesso");
    } else {
      console.error("Elemento templatesList não encontrado!");
      return;
    }

    // Adicionar eventos de clique aos templates (para selecionar)
    const templateItems = els.templatesList.querySelectorAll(".template-item");
    console.log(`Adicionando eventos de clique a ${templateItems.length} templates`);
    
    templateItems.forEach(item => {
      item.addEventListener("click", (e) => {
        // Não selecionar se clicou nos botões de ação
        if (e.target.closest('.template-actions')) return;
        console.log("Template selecionado:", item.dataset.templateId);
        selectTemplate(item);
      });
    });
    
    // Adicionar eventos de administração (apenas para admins)
    if (isAdmin) {
      console.log("Configurando eventos de administração");
      
      // Botões de editar
      const editBtns = els.templatesList.querySelectorAll(".edit-template-btn");
      editBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const templateId = parseInt(btn.dataset.templateId);
          const template = state.messageTemplates.find(t => t.id === templateId);
          if (template) {
            console.log("Abrindo editor para template:", template.title);
            showTemplateEditor(template);
          }
        });
      });
      
      // Botões de excluir
      const deleteBtns = els.templatesList.querySelectorAll(".delete-template-btn");
      deleteBtns.forEach(btn => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const templateId = parseInt(btn.dataset.templateId);
          const template = state.messageTemplates.find(t => t.id === templateId);
          if (template && confirm(`Tem certeza que deseja excluir o template "${template.title}"?`)) {
            console.log("Excluindo template:", template.title);
            deleteTemplate(templateId);
          }
        });
      });
    }
    
    // Adicionar botão de novo template (apenas para admins)
    if (isAdmin) {
      const addTemplateBtn = document.createElement("button");
      addTemplateBtn.className = "btn btn-primary add-template-btn";
      addTemplateBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        Novo Template
      `;
      addTemplateBtn.addEventListener("click", () => {
        console.log("Abrindo editor para novo template");
        showTemplateEditor();
      });
      
      // Inserir antes da lista de templates
      els.templatesList.parentElement.insertBefore(addTemplateBtn, els.templatesList);
    }
    
    console.log("Renderização de templates concluída com sucesso");
    
  } catch (error) {
    console.error("ERRO AO RENDERIZAR TEMPLATES:", error);
    if (els.templatesList) {
      els.templatesList.innerHTML = `
        <div class="template-error-state">
          <p>Erro ao renderizar templates.</p>
          <p>Tente recarregar a página.</p>
        </div>
      `;
    }
  }
  
  console.log("=== FIM DA RENDERIZAÇÃO DE TEMPLATES ===");
}

function selectTemplate(templateElement) {
  const templateId = parseInt(templateElement.dataset.templateId);
  const template = state.messageTemplates.find(t => t.id === templateId);
  
  if (template) {
    // Remove seleção anterior
    els.templatesList.querySelectorAll(".template-item").forEach(item => {
      item.classList.remove("selected");
    });
    
    // Adiciona seleção ao item clicado
    templateElement.classList.add("selected");
    
    // Insere o conteúdo no campo de mensagem
    els.textContent.value = template.content;
    
    // Fecha o modal após breve delay para mostrar feedback visual
    setTimeout(() => {
      hideTemplates();
      els.textContent.focus();
    }, 300);
    
    console.log(`Template selecionado: ${template.title}`);
  }
}

function handleTextContentInput(event) {
  const value = event.target.value;
  
  // Verifica se o usuário digitou "/" para mostrar templates
  if (value === "/" && !state.showTemplates) {
    event.preventDefault();
    showTemplates();
    return;
  }
  
  // Se estiver mostrando templates e o usuário continuar digitando, esconde
  if (state.showTemplates && value !== "/") {
    hideTemplates();
  }
}

// ===== Funções de Verificação de Conexão =====
async function checkBackendConnection() {
  console.log("=== VERIFICANDO CONEXÃO COM BACKEND ===");
  
  try {
    // Tentar uma requisição simples para verificar conexão
    const response = await apiRequest("/auth/me");
    console.log("Conexão com backend OK - usuário autenticado");
    return true;
  } catch (error) {
    console.error("Erro na verificação de conexão:", error);
    
    if (error.status === 0) {
      // Erro de rede
      console.error("Backend não está acessível - erro de rede");
      return false;
    } else if (error.status === 401) {
      // Erro de autenticação
      console.error("Usuário não autenticado");
      return false;
    } else {
      // Outro erro
      console.error("Erro inesperado na verificação de conexão:", error);
      return false;
    }
  }
}

// ===== Funções de Templates (Backend) =====
async function loadTemplates() {
  console.log("=== INICIANDO CARREGAMENTO DE TEMPLATES ===");
  console.log("Token disponível:", !!state.token);
  console.log("Usuário logado:", !!state.user);
  console.log("Usuário é admin:", state.user?.is_admin);
  console.log("Configuração pública:", state.publicConfig);
  
  // Verificar conexão primeiro
  const isBackendConnected = await checkBackendConnection();
  if (!isBackendConnected) {
    console.warn("Backend não está conectado, usando templates de fallback");
    
    // Usar templates de fallback sem mostrar erro de rede
    state.messageTemplates = [
      {
        id: 1,
        title: "Termo de Consentimento LGPD",
        content: `*Termo de Consentimento para Tratamento de Dados Pessoais*

Precisamos do seu consentimento para coletar e tratar dados pessoais (como nome, e-mail, CPF e informações da solicitação) usados apenas para prestar e aprimorar o atendimento. Seus dados não serão compartilhados sem autorização, e você pode acessá-los, corrigi-los ou solicitar sua exclusão a qualquer momento. Ao prosseguir, você concorda com esses termos.

Deseja continuar o atendimento?`,
        category: "LGPD",
        is_system: true
      },
      {
        id: 2,
        title: "Pesquisa de Satisfação",
        content: `Sua opinião é muito importante para nós. 
Em uma escala de 1 a 5, como você avalia o atendimento que acabou de receber neste canal?

1 estrela - Muito insatisfeito
2 estrelas - Insatisfeito
3 estrelas - Neutro
4 estrelas - Satisfeito
5 estrelas - Muito satisfeito`,
        category: "Pesquisa",
        is_system: true
      }
    ];
    
    console.log(`Usando ${state.messageTemplates.length} templates de fallback (offline)`);
    showToast("Usando templates offline. Verifique sua conexão com o servidor.", "warning");
    return;
  }
  
  try {
    console.log("Fazendo requisição para /templates/...");
    const response = await apiRequest("/templates/");
    
    console.log("Resposta recebida:", response);
    console.log("Tipo da resposta:", typeof response);
    console.log("Chaves da resposta:", Object.keys(response || {}));
    
    if (response && response.templates) {
      state.messageTemplates = response.templates;
      console.log(`Templates carregados com sucesso: ${state.messageTemplates.length}`);
      console.log("Detalhes dos templates:", state.messageTemplates.map(t => ({
        id: t.id,
        title: t.title,
        category: t.category,
        is_system: t.is_system
      })));
      
      // Mostrar toast de sucesso apenas se não for carregamento inicial silencioso
      if (state.messageTemplates.length > 0) {
        console.log("Templates disponíveis para uso:");
      } else {
        console.warn("Nenhum template encontrado!");
        showToast("Nenhum template encontrado. Entre em contato com o administrador.", "warning");
      }
    } else {
      console.error("Resposta inválida da API:", response);
      showToast("Resposta inválida do servidor ao carregar templates", "error");
      
      // Usar fallback mesmo com resposta inválida
      state.messageTemplates = [
        // Templates LGPD e Pesquisa
      ];
    }
    
  } catch (error) {
    console.error("=== ERRO DETALHADO AO CARREGAR TEMPLATES ===");
    console.error("Erro completo:", error);
    console.error("Status do erro:", error.status);
    console.error("Mensagem do erro:", error.message);
    console.error("Stack trace:", error.stack);
    
    // Tentativa de fallback com templates locais
    console.log("Tentando usar templates de fallback...");
    state.messageTemplates = [
      {
        id: 1,
        title: "Termo de Consentimento LGPD",
        content: `*Termo de Consentimento para Tratamento de Dados Pessoais*

Precisamos do seu consentimento para coletar e tratar dados pessoais (como nome, e-mail, CPF e informações da solicitação) usados apenas para prestar e aprimorar o atendimento. Seus dados não serão compartilhados sem autorização, e você pode acessá-los, corrigi-los ou solicitar sua exclusão a qualquer momento. Ao prosseguir, você concorda com esses termos.

Deseja continuar o atendimento?`,
        category: "LGPD",
        is_system: true
      },
      {
        id: 2,
        title: "Pesquisa de Satisfação",
        content: `Sua opinião é muito importante para nós. 
Em uma escala de 1 a 5, como você avalia o atendimento que acabou de receber neste canal?

1 estrela - Muito insatisfeito
2 estrelas - Insatisfeito
3 estrelas - Neutro
4 estrelas - Satisfeito
5 estrelas - Muito satisfeito`,
        category: "Pesquisa",
        is_system: true
      }
    ];
    
    console.log(`Usando ${state.messageTemplates.length} templates de fallback`);
    
    // Mostrar mensagem mais informativa
    const errorMessage = error.status === 401 
      ? "Erro de autenticação ao carregar templates. Faça login novamente."
      : error.status === 403
      ? "Você não tem permissão para acessar templates."
      : error.status === 404
      ? "Endpoint de templates não encontrado. Verifique se o backend está atualizado."
      : error.status === 0
      ? "Erro de conexão com o servidor. Usando templates offline."
      : `Erro ao carregar templates: ${error.message || 'Erro desconhecido'}`;
    
    console.error("Mensagem para usuário:", errorMessage);
    showToast(errorMessage, error.status === 0 ? "warning" : "error");
  }
  
  console.log("=== FIM DO CARREGAMENTO DE TEMPLATES ===");
  console.log("Estado final dos templates:", state.messageTemplates.length);
  
  // Atualizar resumo administrativo
  updateTemplatesSummary();

  // Atualiza a visualização caso a lista de templates esteja aberta
  if (state.showTemplates) {
    renderTemplates();
  }
}

// ===== Funções de Administração de Templates (Apenas Admin) =====
async function createTemplate(templateData) {
  try {
    const response = await apiRequest("/templates/", {
      method: "POST",
      body: JSON.stringify(templateData)
    });
    
    showToast("Template criado com sucesso", "success");
    await loadTemplates(); // Recarregar lista
    return response;
  } catch (error) {
    console.error("Erro ao criar template:", error);
    showToast(error.message || "Erro ao criar template", "error");
    throw error;
  }
}

async function updateTemplate(templateId, templateData) {
  try {
    const response = await apiRequest(`/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(templateData)
    });
    
    showToast("Template atualizado com sucesso", "success");
    await loadTemplates(); // Recarregar lista
    return response;
  } catch (error) {
    console.error("Erro ao atualizar template:", error);
    showToast(error.message || "Erro ao atualizar template", "error");
    throw error;
  }
}

async function deleteTemplate(templateId) {
  try {
    await apiRequest(`/templates/${templateId}`, {
      method: "DELETE"
    });
    
    showToast("Template excluído com sucesso", "success");
    await loadTemplates(); // Recarregar lista
  } catch (error) {
    console.error("Erro ao excluir template:", error);
    showToast(error.message || "Erro ao excluir template", "error");
    throw error;
  }
}

// ===== Interface de Edição de Templates =====
function showTemplateEditor(template = null) {
  const isEdit = !!template;
  const title = isEdit ? "Editar Template" : "Novo Template";
  
  // Criar modal de edição
  const modalHtml = `
    <div id="templateEditorOverlay" class="overlay">
      <div class="modal template-editor-modal">
        <div class="modal-header">
          <h2>${title}</h2>
          <button id="closeTemplateEditorBtn" class="btn-icon" title="Fechar">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <form id="templateEditorForm">
            <div class="form-group">
              <label for="templateTitle">Título</label>
              <input type="text" id="templateTitle" required maxlength="200" 
                     value="${template ? template.title : ''}" placeholder="Título do template">
            </div>
            <div class="form-group">
              <label for="templateCategory">Categoria</label>
              <input type="text" id="templateCategory" required maxlength="50" 
                     value="${template ? template.category : ''}" placeholder="Categoria (ex: LGPD, Pesquisa)">
            </div>
            <div class="form-group">
              <label for="templateContent">Conteúdo</label>
              <textarea id="templateContent" required rows="8" 
                        placeholder="Conteúdo do template (use * para negrito)">${template ? template.content : ''}</textarea>
            </div>

            <div class="form-actions">
              <button type="button" id="cancelTemplateEditorBtn" class="btn btn-outline">Cancelar</button>
              <button type="submit" id="submitTemplateEditorBtn" class="btn">${isEdit ? 'Atualizar' : 'Criar'}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
  
  // Adicionar modal ao body
  document.body.insertAdjacentHTML('beforeend', modalHtml);
  
  // Configurar eventos
  const overlay = document.getElementById("templateEditorOverlay");
  const form = document.getElementById("templateEditorForm");
  const closeBtn = document.getElementById("closeTemplateEditorBtn");
  const cancelBtn = document.getElementById("cancelTemplateEditorBtn");
  
  // Evento de submit
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const formData = {
      title: document.getElementById("templateTitle").value.trim(),
      category: document.getElementById("templateCategory").value.trim(),
      content: document.getElementById("templateContent").value.trim()
    };
    
    const submitBtn = document.getElementById("submitTemplateEditorBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Processando...';
    }

    try {
      if (isEdit) {
        await updateTemplate(template.id, formData);
      } else {
        await createTemplate(formData);
      }
      closeTemplateEditor();
    } catch (error) {
      // Erro já tratado nas funções
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = isEdit ? 'Atualizar' : 'Criar';
      }
    }
  });
  
  // Eventos de fechar
  const closeTemplateEditor = () => {
    overlay.remove();
  };
  
  closeBtn.addEventListener("click", closeTemplateEditor);
  cancelBtn.addEventListener("click", closeTemplateEditor);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeTemplateEditor();
  });
}

function closeTemplateEditor() {
  const overlay = document.getElementById("templateEditorOverlay");
  if (overlay) overlay.remove();
}

// ===== Funções Administrativas de Templates =====
function updateTemplatesSummary() {
  if (!els.templatesSummary) return;
  
  const templates = state.messageTemplates || [];
  const systemTemplates = templates.filter(t => t.is_system);
  const customTemplates = templates.filter(t => !t.is_system);
  const categories = [...new Set(templates.map(t => t.category))];
  
  const summaryHtml = `
    <p>
      <span class="templates-count">${templates.length}</span> templates no total
      (${systemTemplates.length} do sistema, ${customTemplates.length} personalizados)
    </p>
    ${categories.length > 0 ? `
      <div class="templates-list">
        ${categories.map(category => {
          const count = templates.filter(t => t.category === category).length;
          const isSystemCategory = systemTemplates.some(t => t.category === category);
          return `<span class="template-badge ${isSystemCategory ? 'system' : ''}">${category} (${count})</span>`;
        }).join('')}
      </div>
    ` : ''}
  `;
  
  els.templatesSummary.innerHTML = summaryHtml;
}

function openTemplatesManager() {
  console.log("Abrindo gerenciador de templates administrativos");
  // Abrir o modal de templates com foco em administração
  showTemplates();
  
  // Adicionar aviso informativo para admins
  if (state.messageTemplates.length === 0) {
    showToast("Nenhum template encontrado. Use o botão 'Novo Template' para criar o primeiro.", "info");
  }
}

// ===== Funções de Emojis =====
const emojiData = {
  smileys: ['grinning', 'smiley', 'smile', 'grin', 'laughing', 'satisfied', 'wink', 'blush', 'heart_eyes', 'kissing_heart'],
  people: ['thumbsup', 'thumbsdown', 'clap', 'wave', 'ok_hand', 'pray', 'handshake', 'raised_hands', 'open_hands', 'muscle'],
  animals: ['dog', 'cat', 'mouse', 'hamster', 'rabbit', 'fox', 'bear', 'panda', 'koala', 'tiger'],
  food: ['pizza', 'hamburger', 'fries', 'hotdog', 'taco', 'burrito', 'ramen', 'spaghetti', 'ice_cream', 'donut'],
  activities: ['soccer', 'basketball', 'football', 'tennis', 'volleyball', 'baseball', 'golf', 'swimming', 'running', 'biking'],
  objects: ['phone', 'computer', 'keyboard', 'mouse', 'monitor', 'printer', 'camera', 'tv', 'radio', 'clock'],
  symbols: ['heart', 'broken_heart', 'sparkling_heart', 'two_hearts', 'revolving_hearts', 'heartpulse', 'heartbeat', 'arrow_forward', 'arrow_backward', 'star']
};

function initializeEmojis() {
  console.log("Inicializando seletor de emojis");
  loadEmojis('all');
}

function loadEmojis(category) {
  const grid = els.emojiGrid;
  if (!grid) return;
  
  grid.innerHTML = '';
  
  let emojis = [];
  if (category === 'all') {
    emojis = Object.values(emojiData).flat();
  } else {
    emojis = emojiData[category] || [];
  }
  
  // Adicionar emojis comuns
  const commonEmojis = ['thumbsup', 'thumbsdown', 'clap', 'heart', 'star', 'ok_hand', 'pray', 'wave', 'smile', 'laughing'];
  emojis = [...new Set([...commonEmojis, ...emojis])];
  
  emojis.forEach(emoji => {
    const emojiItem = document.createElement('div');
    emojiItem.className = 'emoji-item';
    emojiItem.textContent = getEmojiByShortcode(emoji);
    emojiItem.dataset.emoji = getEmojiByShortcode(emoji);
    emojiItem.dataset.shortcode = emoji;
    emojiItem.title = emoji;
    emojiItem.addEventListener('click', () => selectEmoji(emojiItem.dataset.emoji));
    grid.appendChild(emojiItem);
  });
}

function getEmojiByShortcode(shortcode) {
  // Mapeamento de shortcodes para emojis Unicode reais
  const unicodeEmojis = {
    'grinning': '😀',
    'smiley': '😃',
    'smile': '😄',
    'grin': '😁',
    'laughing': '😆',
    'satisfied': '😌',
    'wink': '😉',
    'blush': '😊',
    'heart_eyes': '😍',
    'kissing_heart': '😘',
    'thumbsup': '👍',
    'thumbsdown': '👎',
    'clap': '👏',
    'wave': '👋',
    'ok_hand': '👌',
    'pray': '🙏',
    'handshake': '🤝',
    'raised_hands': '🙌',
    'open_hands': '👐',
    'muscle': '💪',
    'dog': '🐶',
    'cat': '🐱',
    'mouse': '🐭',
    'hamster': '🐹',
    'rabbit': '🐰',
    'fox': '🦊',
    'bear': '🐻',
    'panda': '🐼',
    'koala': '🐨',
    'tiger': '🐯',
    'pizza': '🍕',
    'hamburger': '🍔',
    'fries': '🍟',
    'hotdog': '🌭',
    'taco': '🌮',
    'burrito': '🌯',
    'ramen': '🍜',
    'spaghetti': '🍝',
    'ice_cream': '🍦',
    'donut': '🍩',
    'soccer': '⚽',
    'basketball': '🏀',
    'football': '🏈',
    'tennis': '🎾',
    'volleyball': '🏐',
    'baseball': '⚾',
    'golf': '⛳',
    'swimming': '🏊',
    'running': '🏃',
    'biking': '🚴',
    'phone': '📱',
    'computer': '💻',
    'keyboard': '⌨️',
    'mouse': '🖱️',
    'monitor': '🖥️',
    'printer': '🖨️',
    'camera': '📷',
    'tv': '📺',
    'radio': '📻',
    'clock': '🕰️',
    'heart': '❤️',
    'broken_heart': '💔',
    'sparkling_heart': '💖',
    'two_hearts': '💕',
    'revolving_hearts': '💞',
    'heartpulse': '💗',
    'heartbeat': '💓',
    'arrow_forward': '▶️',
    'arrow_backward': '◀️',
    'star': '⭐'
  };
  
  // Retornar emojis Unicode reais
  return unicodeEmojis[shortcode] || shortcode;
}

function selectEmoji(emoji) {
  console.log("Emoji selecionado:", emoji);
  
  // Inserir emoji no campo de texto
  const textContent = els.textContent;
  if (textContent) {
    const cursorPosition = textContent.selectionStart || textContent.value.length;
    const textBefore = textContent.value.substring(0, cursorPosition);
    const textAfter = textContent.value.substring(cursorPosition);
    textContent.value = textBefore + emoji + textAfter;
    
    // Mover cursor para depois do emoji
    const newCursorPosition = cursorPosition + emoji.length;
    textContent.setSelectionRange(newCursorPosition, newCursorPosition);
    
    // Focar no campo de texto
    textContent.focus();
  }
  
  // Fechar modal
  closeEmojiModal();
}

function showEmojiModal() {
  console.log("Abrindo modal de emojis");
  
  if (!els.emojiOverlay) return;
  
  els.emojiOverlay.classList.remove("hidden");
  initializeEmojis();
  
  // Focar no campo de busca
  if (els.emojiSearch) {
    els.emojiSearch.focus();
  }
}

function closeEmojiModal() {
  console.log("Fechando modal de emojis");
  
  if (els.emojiOverlay) {
    els.emojiOverlay.classList.add("hidden");
  }
  
  // Limpar busca
  if (els.emojiSearch) {
    els.emojiSearch.value = '';
  }
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

async function loadPublicConfig() {
  try {
    const response = await apiRequest("/auth/config");
    state.publicConfig = response;
    console.log('Configuração pública carregada:', response);
  } catch (error) {
    console.error('Erro ao carregar configuração pública:', error);
    state.publicConfig = {
      public_domain: window.location.origin,
      api_prefix: "/api/v1",
      environment: "development",
      debug: true
    };
  }
}

async function fetchLoginChallenge(autoGenerate = false) {
  try {
    console.log('Buscando nova charada... autoGenerate:', autoGenerate);
    
    const response = await fetch(`${apiPrefix}/auth/challenge?ts=${Date.now()}`, {
      method: "GET",
      cache: "no-store",
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
      }
    });
    
    const data = await response.json();
    
    if (!data.challenge_id || !data.question) {
      throw new Error("Resposta da charada inválida.");
    }
    
    state.loginChallengeId = data.challenge_id;
    els.challengeQuestion.textContent = `${data.question} (expira em ${data.expires_in_seconds}s)`;
    els.challengeAnswer.value = "";
    els.loginError.textContent = "";
    
    console.log('Charada carregada com sucesso:', {
      id: data.challenge_id,
      question: data.question,
      expires_in: data.expires_in_seconds
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
  if (s === "queued") return "🕒";
  if (s === "sent") return "✓";
  if (s === "delivered") return "✓✓";
  if (s === "read") return "✓✓";
  if (s === "failed") return "❌";
  if (s === "received") return "";
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

function formatWhatsAppText(text) {
  if (!text) return "";
  
  // Reservar blocos de código
  const codeBlocks = [];
  let formatted = text.replace(/```([\s\S]*?)```/g, (match, p1) => {
    codeBlocks.push(p1);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });
  
  // Reservar código inline
  const inlineCodes = [];
  formatted = formatted.replace(/`([^`]+)`/g, (match, p1) => {
    inlineCodes.push(p1);
    return `__INLINE_CODE_${inlineCodes.length - 1}__`;
  });
  
  // Negrito (*texto*)
  formatted = formatted.replace(/\*(?!\s)([^*]+?)(?<!\s)\*/g, '<strong>$1</strong>');
  
  // Itálico (_texto_)
  formatted = formatted.replace(/_(?!\s)([^_]+?)(?<!\s)_/g, '<em>$1</em>');
  
  // Tachado (~texto~)
  formatted = formatted.replace(/~(?!\s)([^~]+?)(?<!\s)~/g, '<del>$1</del>');
  
  // Restaurar códigos inline
  formatted = formatted.replace(/__INLINE_CODE_(\d+)__/g, (match, i) => `<code>${inlineCodes[i]}</code>`);
  
  // Restaurar blocos de código
  formatted = formatted.replace(/__CODE_BLOCK_(\d+)__/g, (match, i) => `<pre style="margin: 0.5em 0; padding: 0.5em; background: rgba(0,0,0,0.05); border-radius: 4px; overflow-x: auto;"><code>${codeBlocks[i]}</code></pre>`);
  
  return formatted;
}

function buildMessageBody(message) {
  const safeText = formatWhatsAppText(escapeHtml(message.text_content || ""));
  const safeCaption = formatWhatsAppText(escapeHtml(message.media_caption || ""));
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
  if (message.message_type === "text" || !message.message_type) {
    if (message.text_content && message.text_content.includes("🚫 Essa mensagem foi apagada")) {
      return `<p class="deleted-msg" style="font-style: italic; color: var(--muted); margin: 0;">${safeText}</p>`;
    }
    return `<p style="white-space: pre-wrap; margin: 0;">${safeText || "[mensagem sem conteúdo textual]"}</p>`;
  }
  return `<p style="white-space: pre-wrap; margin: 0;">${safeText || "[mensagem sem conteúdo textual]"}</p>`;
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

  const safeNameForTitle = data.contact_name.replace(/\\s+/g, "_");
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${escapeHtml(safeNameForTitle)}_${escapeHtml(data.date)}</title></head>
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
  const safePhone = (data.contact_phone || "").replace(/\D/g, "") || "sem_telefone";
  const filename = `${safePhone}_${date}.html`;
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
  // Extrair nome do arquivo do header Content-Disposition
  const disposition = response.headers.get("Content-Disposition");
  let filename = null;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="([^"]+)"/);
    if (match) filename = match[1];
  }
  // Fallback: usar a mesma lógica do HTML se não conseguir extrair do header
  if (!filename) {
    const conv = state.activeConversations && state.activeConversations.find(c => c.id === state.exportContext.conversationId);
    const contactPhone = conv ? (conv.contact_phone || "") : "";
    const safePhone = contactPhone.replace(/\D/g, "") || "sem_telefone";
    filename = `${safePhone}_${date}.pdf`;
  }
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
        const sender = message.direction === "outbound"
            ? ((message.sender_name && message.sender_name.trim().toLowerCase() !== "cau") ? message.sender_name : state.user?.name || "Funcionário")
            : (message.sender_name || "Cliente");
        const revokeBtn = (message.direction === "outbound" && message.external_message_id) 
            ? `<button class="revoke-msg-btn" onclick="revokeMessage(${message.id}, this)" title="Apagar para todos">🗑️</button>` : '';
        return `<article class="message-item ${klass} message-new" data-id="${message.id}">
            <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span class="msg-status status-${message.delivery_status || 'received'}">${formatDeliveryStatus(message.delivery_status)}</span>${revokeBtn}</div>
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
        const sender = message.direction === "outbound"
            ? ((message.sender_name && message.sender_name.trim().toLowerCase() !== "cau") ? message.sender_name : state.user?.name || "Funcionário")
            : (message.sender_name || "Cliente");
        const revokeBtn = (message.direction === "outbound" && message.external_message_id) 
            ? `<button class="revoke-msg-btn" onclick="revokeMessage(${message.id}, this)" title="Apagar para todos">🗑️</button>` : '';
        return `<article class="message-item ${klass}" data-id="${message.id}">
            <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span class="msg-status status-${message.delivery_status || 'received'}">${formatDeliveryStatus(message.delivery_status)}</span>${revokeBtn}</div>
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
        const sender = message.direction === "outbound"
            ? ((message.sender_name && message.sender_name.trim().toLowerCase() !== "cau") ? message.sender_name : state.user?.name || "Funcionário")
            : (message.sender_name || "Cliente");
        const revokeBtn = (message.direction === "outbound" && message.external_message_id) 
            ? `<button class="revoke-msg-btn" onclick="revokeMessage(${message.id}, this)" title="Apagar para todos">🗑️</button>` : '';
        return `<article class="message-item ${klass}" data-id="${message.id}">
            <div class="message-meta"><span>${escapeHtml(sender)}</span><span>${formatDate(message.created_at)}</span><span class="msg-status status-${message.delivery_status || 'received'}">${formatDeliveryStatus(message.delivery_status)}</span>${revokeBtn}</div>
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
    
    if (!loadMore) {
      const signature = buildMessageSignature(messages);
      state.messageSignaturesByConversation[conversationId] = signature;
    }
    
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
  
  if (id) {
    document.querySelector(".app-shell").classList.add("mobile-chat-active");
  }
  
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
  
  // Carrega configuração pública do backend
  await loadPublicConfig();
  
  // Carregar templates do backend
  await loadTemplates();
  
  if (state.user?.is_admin) {
    await loadAdminUsers();
    await loadAiSettings();
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

function openAiConsultModal() {
  els.aiQuestion.value = "";
  els.aiResponse.value = "";
  els.aiConsultOverlay.classList.remove("hidden");
  els.aiQuestion.focus();
  // Scroll para o final do histórico
  if (els.aiHistory) {
    els.aiHistory.scrollTop = els.aiHistory.scrollHeight;
  }
}

// Adicionar mensagem ao histórico de IA
function addAiMessage(text, type = "assistant") {
  if (!els.aiHistory) return;

  // Esconder mensagem vazia
  if (els.aiHistoryEmpty) {
    els.aiHistoryEmpty.style.display = "none";
  }

  const messageDiv = document.createElement("div");
  messageDiv.className = `ai-message ${type}`;

  const time = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  messageDiv.innerHTML = `
    <div class="ai-message-content">${escapeHtml(text)}</div>
    <div class="ai-message-time">${time}</div>
  `;

  els.aiHistory.appendChild(messageDiv);

  // Scroll para a nova mensagem
  els.aiHistory.scrollTop = els.aiHistory.scrollHeight;
}

// Limpar histórico de IA
function clearAiHistory() {
  if (!els.aiHistory) return;

  // Remover todas as mensagens (manter apenas o empty state)
  const messages = els.aiHistory.querySelectorAll(".ai-message");
  messages.forEach(msg => msg.remove());

  // Mostrar mensagem vazia
  if (els.aiHistoryEmpty) {
    els.aiHistoryEmpty.style.display = "flex";
  }

  // Limpar textarea hidden também
  els.aiResponse.value = "";

  showToast("Histórico limpo!", "success");
}

// Escape HTML para segurança
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function closeAiConsultModal() {
  els.aiConsultOverlay.classList.add("hidden");
}

async function askAi() {
  const question = els.aiQuestion.value.trim();
  if (!question) {
    showToast("Por favor, digite uma pergunta.");
    return;
  }

  // Adicionar mensagem do usuário ao histórico
  addAiMessage(question, "user");

  // Limpar input
  els.aiQuestion.value = "";
  els.aiQuestion.focus();

  els.askAiBtn.disabled = true;
  els.askAiBtn.textContent = "Processando...";

  // Adicionar indicador de "pensando"
  const thinkingDiv = document.createElement("div");
  thinkingDiv.className = "ai-message assistant ai-thinking";
  thinkingDiv.innerHTML = `
    <div class="ai-message-content">
      <span class="ai-typing-indicator">
        <span></span><span></span><span></span>
      </span>
    </div>
  `;
  if (els.aiHistory) {
    els.aiHistory.appendChild(thinkingDiv);
    els.aiHistory.scrollTop = els.aiHistory.scrollHeight;
  }

  try {
    const response = await apiRequest("/ai/ask", {
      method: "POST",
      body: JSON.stringify({ question })
    });

    // Remover indicador de "pensando"
    thinkingDiv.remove();

    const answer = response.answer || "Sem resposta da IA.";
    els.aiResponse.value = answer;

    // Adicionar resposta da IA ao histórico
    addAiMessage(answer, "assistant");

  } catch (error) {
    // Remover indicador de "pensando"
    thinkingDiv.remove();

    const errorMsg = "❌ " + (error.message || "Erro desconhecido ao consultar a IA.");
    els.aiResponse.value = errorMsg;

    // Adicionar erro ao histórico
    addAiMessage(errorMsg, "assistant");
  } finally {
    els.askAiBtn.disabled = false;
    els.askAiBtn.textContent = "Perguntar";
  }
}

function copyAiResponse() {
  // Pegar a última resposta do histórico (mensagem do assistant mais recente)
  const assistantMessages = els.aiHistory?.querySelectorAll(".ai-message.assistant");
  let responseText = els.aiResponse.value;

  // Se houver mensagens no histórico, pegar a última
  if (assistantMessages && assistantMessages.length > 0) {
    const lastMessage = assistantMessages[assistantMessages.length - 1];
    const content = lastMessage.querySelector(".ai-message-content");
    if (content) {
      responseText = content.textContent;
    }
  }

  if (!responseText || responseText === "Pensando..." || responseText.startsWith("❌") || responseText.startsWith("Erro")) {
    showToast("Não há resposta válida para copiar.");
    return;
  }

  navigator.clipboard.writeText(responseText).then(() => {
    showToast("Resposta copiada para a área de transferência!", "success");
  }).catch(err => {
    console.error('Erro ao copiar:', err);
    showToast("Falha ao copiar resposta.");
  });
}

// AI Config Logic
async function loadAiSettings() {
  try {
    const settings = await apiRequest("/admin/ai-settings");
    els.configAiProvider.value = settings.ai_provider;
    if (els.configAiAgentEnabled) {
      els.configAiAgentEnabled.checked = settings.ai_agent_enabled;
    }
  } catch (error) {
    console.error("Erro ao carregar configurações de IA:", error);
  }
}

async function saveAiSettings() {
  const payload = {
    ai_provider: els.configAiProvider.value,
    ai_agent_enabled: els.configAiAgentEnabled ? els.configAiAgentEnabled.checked : false,
  };

  try {
    els.saveAiConfigBtn.disabled = true;
    await apiRequest("/admin/ai-settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    });
    showToast("Configuração de IA salva com sucesso!", "success");
  } catch (error) {
    showToast("Erro ao salvar configuração: " + error.message);
  } finally {
    els.saveAiConfigBtn.disabled = false;
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
  
  // Eventos do sistema de templates
  els.textContent.addEventListener("input", handleTextContentInput);
  els.closeTemplatesBtn.addEventListener("click", hideTemplates);
  
  // Fecha modal de templates ao clicar fora
  els.templatesOverlay.addEventListener("click", (event) => {
    if (event.target === els.templatesOverlay) {
      hideTemplates();
    }
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
  els.searchGlobalBtn.addEventListener("click", () => {
    els.searchGlobalInput.value = "";
    els.searchGlobalStatus.textContent = "";
    els.searchGlobalResults.innerHTML = "";
    els.searchGlobalOverlay.classList.remove("hidden");
    setTimeout(() => els.searchGlobalInput.focus(), 50);
  });
  
  els.closeSearchGlobalBtn.addEventListener("click", () => els.searchGlobalOverlay.classList.add("hidden"));
  els.doSearchGlobalBtn.addEventListener("click", performGlobalSearch);
  els.searchGlobalInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") performGlobalSearch();
  });
  // Eventos do seletor de emojis
  if (els.emojiBtn) {
    els.emojiBtn.addEventListener("click", showEmojiModal);
  }
  if (els.closeEmojiBtn) {
    els.closeEmojiBtn.addEventListener("click", closeEmojiModal);
  }
  if (els.emojiOverlay) {
    els.emojiOverlay.addEventListener("click", (e) => {
      if (e.target === els.emojiOverlay) {
        closeEmojiModal();
      }
    });
  }
  if (els.emojiSearch) {
    els.emojiSearch.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const items = els.emojiGrid.querySelectorAll(".emoji-item");
      items.forEach((item) => {
        const shortcode = item.dataset.shortcode || "";
        if (shortcode.includes(q)) {
          item.style.display = "";
        } else {
          item.style.display = "none";
        }
      });
    });
  }
  const categoryBtns = document.querySelectorAll(".emoji-category-btn");
  if (categoryBtns.length > 0) {
    categoryBtns.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        categoryBtns.forEach((b) => b.classList.remove("active"));
        e.target.classList.add("active");
        loadEmojis(e.target.dataset.category);
      });
    });
  }

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
  els.openTemplatesManagerBtn.addEventListener("click", () => {
    openTemplatesManager();
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

  if (els.mobileBackBtn) {
    els.mobileBackBtn.addEventListener("click", () => {
      document.querySelector(".app-shell").classList.remove("mobile-chat-active");
    });
  }

  if (els.mobileComposerBackBtn) {
    els.mobileComposerBackBtn.addEventListener("click", () => {
      document.querySelector(".app-shell").classList.remove("mobile-chat-active");
    });
  }

  els.aiConsultBtn.addEventListener("click", openAiConsultModal);
  els.closeAiConsultBtn.addEventListener("click", closeAiConsultModal);
  els.askAiBtn.addEventListener("click", askAi);
  els.copyAiResponseBtn.addEventListener("click", copyAiResponse);
  if (els.clearAiHistoryBtn) {
    els.clearAiHistoryBtn.addEventListener("click", clearAiHistory);
  }

  // Permitir enviar com Enter (sem Shift) no campo de pergunta
  if (els.aiQuestion) {
    els.aiQuestion.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        askAi();
      }
    });
  }

  // AI Admin Config
  els.saveAiConfigBtn.addEventListener("click", saveAiSettings);
  
  // Load initial if admin
  if (state.user && state.user.is_admin) {
    loadAiSettings();
  }
}

async function performGlobalSearch() {
  const q = els.searchGlobalInput.value.trim();
  if (q.length < 3) {
    els.searchGlobalStatus.textContent = "Digite pelo menos 3 caracteres.";
    return;
  }
  els.searchGlobalStatus.textContent = "Pesquisando...";
  els.searchGlobalResults.innerHTML = "";
  els.doSearchGlobalBtn.disabled = true;
  
  try {
    const results = await apiRequest(`/conversations/search/messages?q=${encodeURIComponent(q)}`);
    if (!results || !results.length) {
      els.searchGlobalStatus.textContent = "Nenhuma mensagem encontrada.";
      els.doSearchGlobalBtn.disabled = false;
      return;
    }
    
    els.searchGlobalStatus.textContent = `${results.length} resultado(s) encontrado(s).`;
    els.searchGlobalResults.innerHTML = results.map(r => {
      const name = r.contact_name || r.contact_phone || "Contato";
      const shortText = r.text_content && r.text_content.length > 120 
        ? r.text_content.substring(0, 120) + "..." 
        : (r.text_content || "[Mídia/Anexo]");
      const date = formatDate(r.created_at);
      
      return `
        <li class="catalog-item" style="cursor: pointer; padding: 14px 16px; border-bottom: 1px solid #eee; display: flex; flex-direction: column; gap: 6px;" onclick="selectConversationAndCloseSearch(${r.conversation_id})">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
            <strong style="color: var(--text); font-size: 0.95rem;">${escapeHtml(name)}</strong>
            <span style="font-size: 0.72rem; color: #4e6c62; background: #e0f2ec; padding: 3px 8px; border-radius: 12px; font-weight: 600; white-space: nowrap;">${date}</span>
          </div>
          <div style="font-size: 0.85rem; color: #4e6c62; line-height: 1.4;">${escapeHtml(shortText)}</div>
        </li>
      `;
    }).join("");
  } catch (error) {
    els.searchGlobalStatus.textContent = "Erro ao pesquisar.";
  } finally {
    els.doSearchGlobalBtn.disabled = false;
  }
}

window.selectConversationAndCloseSearch = async function(conversationId) {
  els.searchGlobalOverlay.classList.add("hidden");
  await selectConversation(conversationId);
};

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

async function revokeMessage(messageId, btnElement) {
  if (!state.selectedConversationId) return;
  const conversationId = state.selectedConversationId;
  const confirmed = confirm("Tem certeza que deseja apagar essa mensagem para todos? Essa ação não pode ser desfeita.");
  if (!confirmed) return;

  btnElement.disabled = true;
  btnElement.style.opacity = 0.3;

  try {
    const updatedMessage = await apiRequest(`/conversations/${conversationId}/messages/${messageId}/revoke`, {
      method: "POST"
    });
    showSuccessToast("Mensagem apagada com sucesso.");
    
    // Atualizar UI no ato sem precisar refazer tudo se já voltou ok.
    const messageContainer = btnElement.closest('.message-item[data-id="' + messageId + '"]');
    if (messageContainer) {
      const msgBody = messageContainer.querySelector('.message-body');
      if (msgBody) {
        msgBody.innerHTML = '<span class="deleted-msg">🚫 Essa mensagem foi apagada</span>';
      }
      btnElement.remove(); // remove o botao depois que apagou
    }
  } catch (error) {
    btnElement.disabled = false;
    btnElement.style.opacity = 1.0;
    showErrorToast(error.message || "Erro ao apagar mensagem.");
  }
}

bootstrap();
