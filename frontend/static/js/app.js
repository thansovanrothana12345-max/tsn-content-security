// Copyright Security - Frontend SPA Controller

class CopyrightDefenderApp {
    constructor() {
        this.activeView = "dashboard";
        this.activeCaseId = null;
        this.cases = [];
        this.allCases = []; // Full unfiltered cases list
        this.users = []; // Cache list of registered users
        this.caseCurrentPage = 1;
        this.casePageLimit = 10;
        this.casesTotalCount = 0;
        this.hasSigned = false;
        this.currentReportId = null;
        this.token = null;
        this.username = null;
        this.role = null;
        
        this.charts = {
            platform: null,
            similarity: null,
            status: null
        };
        
        // Bind UI Elements
        this.initElements();
        // Bind Events
        this.initEvents();
        
        // Startup Initialization
        this.initAuth().then(() => {
            this.loadSettings();
            if (this.token) {
                this.loadCases();
            }
            this.initSignaturePad();
            this.initAutoRefresh();
        });
    }

    initElements() {
        this.viewPanes = document.querySelectorAll(".view-pane");
        this.navItems = document.querySelectorAll(".nav-item");
        this.pageTitle = document.getElementById("page-current-title");
        this.globalCaseSelect = document.getElementById("global-case-select");
        
        // Case Modals
        this.newCaseModal = document.getElementById("modal-new-case-overlay");
        this.btnHeaderNewCase = document.getElementById("btn-header-new-case");
        this.btnCasesNewCase = document.getElementById("btn-cases-new-case");
        this.btnCloseCaseModal = document.getElementById("btn-close-case-modal");
        this.btnCancelCaseModal = document.getElementById("btn-cancel-case-modal");
        this.newCaseForm = document.getElementById("new-case-form");
        
        // Edit Case Modal
        this.editCaseModal = document.getElementById("modal-edit-case-overlay");
        this.btnCloseEditCaseModal = document.getElementById("btn-close-edit-case-modal");
        this.btnCancelEditCaseModal = document.getElementById("btn-cancel-edit-case-modal");
        this.editCaseForm = document.getElementById("edit-case-form");
        
        // Filters & Search
        this.caseSearchInput = document.getElementById("case-search-input");
        this.caseFilterStatus = document.getElementById("case-filter-status");
        this.caseFilterPriority = document.getElementById("case-filter-priority");
        this.caseFilterPlatform = document.getElementById("case-filter-platform");
        this.caseFilterOwner = document.getElementById("case-filter-owner");
        this.caseFilterStartDate = document.getElementById("case-filter-start-date");
        this.caseFilterEndDate = document.getElementById("case-filter-end-date");
        this.caseSortBy = document.getElementById("case-sort-by");
        
        // Pagination & Table elements
        this.casePaginationLimit = document.getElementById("case-pagination-limit");
        this.casePaginationInfo = document.getElementById("case-pagination-info");
        this.btnCasePagePrev = document.getElementById("btn-case-page-prev");
        this.btnCasePageNext = document.getElementById("btn-case-page-next");
        this.casesTableBody = document.getElementById("cases-table-body");
        
        // Case Details & Timeline Panel
        this.caseDetailsEmptyState = document.getElementById("case-details-empty-state");
        this.caseDetailsContent = document.getElementById("case-details-content");
        this.btnEditCase = document.getElementById("btn-edit-case");
        this.btnDeleteCaseAction = document.getElementById("btn-delete-case-action");
        this.btnSaveCaseNote = document.getElementById("btn-save-case-note");
        this.caseAddNoteInput = document.getElementById("case-add-note-input");
        this.caseTimelineContainer = document.getElementById("case-timeline-container");
        
        // Tabs Elements
        this.tabBtnDetails = document.getElementById("tab-btn-details");
        this.tabBtnEvidence = document.getElementById("tab-btn-evidence");
        this.panelTabDetails = document.getElementById("panel-tab-details");
        this.panelTabEvidence = document.getElementById("panel-tab-evidence");
        
        // Evidence Manager
        this.evidenceUploadZone = document.getElementById("evidence-upload-zone");
        this.evidenceFileInput = document.getElementById("evidence-file-input");
        this.evidenceSearchInput = document.getElementById("evidence-search-input");
        this.evidenceFilterType = document.getElementById("evidence-filter-type");
        this.evidenceUploadProgress = document.getElementById("evidence-upload-progress");
        this.evidenceUploadPercent = document.getElementById("evidence-upload-percent");
        this.evidenceUploadFill = document.getElementById("evidence-upload-fill");
        this.evidenceFilesList = document.getElementById("evidence-files-list");
        
        // Evidence Viewer Modal
        this.evidenceViewerOverlay = document.getElementById("modal-evidence-viewer-overlay");
        this.btnCloseEvidenceViewer = document.getElementById("btn-close-evidence-viewer");
        this.evidenceViewerTitle = document.getElementById("evidence-viewer-title");
        
        this.viewerImgContainer = document.getElementById("evidence-viewer-image-container");
        this.viewerImg = document.getElementById("evidence-viewer-image");
        this.btnZoomIn = document.getElementById("btn-zoom-in");
        this.btnZoomOut = document.getElementById("btn-zoom-out");
        this.btnZoomReset = document.getElementById("btn-zoom-reset");
        
        this.viewerVideoContainer = document.getElementById("evidence-viewer-video-container");
        this.viewerVideo = document.getElementById("evidence-viewer-video");
        
        this.viewerDocContainer = document.getElementById("evidence-viewer-doc-container");
        this.viewerDocName = document.getElementById("evidence-viewer-doc-name");
        this.viewerDocSize = document.getElementById("evidence-viewer-doc-size");
        this.btnDownloadEvidenceDoc = document.getElementById("btn-download-evidence-doc");
        
        this.viewerLinkContainer = document.getElementById("evidence-viewer-link-container");
        this.viewerLinkTitle = document.getElementById("evidence-viewer-link-title");
        this.viewerLinkUrl = document.getElementById("evidence-viewer-link-url");
        this.btnOpenEvidenceLink = document.getElementById("btn-open-evidence-link");
        
        this.viewerUploader = document.getElementById("evidence-viewer-uploader");
        this.viewerTimestamp = document.getElementById("evidence-viewer-timestamp");
        
        // Library Uploads
        this.uploadZone = document.getElementById("original-upload-zone");
        this.originalFileInput = document.getElementById("original-file-input");
        this.originalsFileList = document.getElementById("originals-file-list");
        this.uploadProgressContainer = document.getElementById("upload-progress-bar-container");
        this.uploadProgressPercent = document.getElementById("upload-progress-percent");
        this.uploadProgressFill = document.getElementById("upload-progress-fill");
        
        // Scanner
        this.scannerUrlInput = document.getElementById("scanner-url-input");
        this.btnRunScan = document.getElementById("btn-run-scan");
        this.scanResultsPanel = document.getElementById("scan-results-panel");
        this.scanResultsContent = document.getElementById("scan-results-content");
        this.scannedEvidenceList = document.getElementById("scanned-evidence-list");
        
        // DMCA Form & Output
        this.dmcaForm = document.getElementById("dmca-config-form");
        this.dmcaEvidenceSelect = document.getElementById("dmca-evidence-select");
        this.dmcaNoticeOutput = document.getElementById("dmca-notice-output");
        this.btnCopyDmca = document.getElementById("btn-copy-dmca");
        this.btnDownloadDmca = document.getElementById("btn-download-dmca");
        this.dmcaTemplateSelect = document.getElementById("dmca-template-select");
        this.signatureCanvas = document.getElementById("dmca-signature-canvas");
        this.btnClearSignature = document.getElementById("btn-clear-signature");
        this.dmcaDeclarationCheck = document.getElementById("dmca-declaration-check");
        this.btnExportPdf = document.getElementById("btn-export-pdf");
        this.btnExportDocx = document.getElementById("btn-export-docx");
        
        // Settings Form
        this.settingsForm = document.getElementById("settings-defaults-form");
        
        // Security Center Elements (Epic 6)
        this.securityActionFilter = document.getElementById("security-action-filter");
        this.btnRefreshAudit = document.getElementById("btn-refresh-audit");
        this.securityAuditTbody = document.getElementById("security-audit-tbody");
        this.btnAuditPrev = document.getElementById("btn-audit-prev");
        this.btnAuditNext = document.getElementById("btn-audit-next");
        this.auditPaginationInfo = document.getElementById("audit-pagination-info");
        
        this.securityAuditPage = 0;
        this.securityAuditLimit = 15;

        // Login / Auth elements
        this.loginOverlay = document.getElementById("login-screen-overlay");
        this.loginForm = document.getElementById("login-form");
        this.loginErrorMsg = document.getElementById("login-error-msg");
        this.btnLogout = document.getElementById("btn-logout");
        
        // User registration
        this.userRegistrationForm = document.getElementById("user-registration-form");

        // Verification Center Elements
        this.verifyTableBody = document.getElementById("verification-table-body");
        this.verifyRefreshBtn = document.getElementById("btn-verify-refresh");
        this.verifyDetailPanel = document.getElementById("verification-detail-panel");
        this.verifyDetailCaseTitle = document.getElementById("verify-detail-case-title");
        this.verifyApproveBtn = document.getElementById("btn-verify-approve");
        this.verifyRejectBtn = document.getElementById("btn-verify-reject");
        this.verifyDetailSummary = document.getElementById("verify-detail-summary");
        this.verifyDetailMetaVal = document.getElementById("verify-detail-meta-val");
        this.verifyDetailHashVal = document.getElementById("verify-detail-hash-val");
        this.verifyDetailOriginals = document.getElementById("verify-detail-originals");
        this.verifyDetailEvidence = document.getElementById("verify-detail-evidence");
        this.verifyDetailAiScore = document.getElementById("verify-detail-ai-score");
        this.verifyDetailConfidenceBadge = document.getElementById("verify-detail-confidence-badge");
        this.verifyDetailNotesTimeline = document.getElementById("verify-detail-notes-timeline");
        this.verifyAddNoteBtn = document.getElementById("btn-verify-add-note");

        this.verifyStatVerified = document.getElementById("verify-stat-verified");
        this.verifyStatPending = document.getElementById("verify-stat-pending");
        this.verifyStatRejected = document.getElementById("verify-stat-rejected");
        this.verifyStatRate = document.getElementById("verify-stat-rate");

        this.modalVerifyApprove = document.getElementById("modal-verify-approve");
        this.modalVerifyReject = document.getElementById("modal-verify-reject");
        this.modalVerifyAddNote = document.getElementById("modal-verify-add-note");
        this.verifyApproveForm = document.getElementById("verify-approve-form");
        this.verifyRejectForm = document.getElementById("verify-reject-form");
        this.verifyNoteForm = document.getElementById("verify-note-form");
    }

    initEvents() {
        // Nav menu click
        this.navItems.forEach(item => {
            item.addEventListener("click", (e) => {
                e.preventDefault();
                const view = item.getAttribute("data-view");
                this.switchView(view);
            });
        });
        
        // Global Case select change
        this.globalCaseSelect.addEventListener("change", (e) => {
            this.activeCaseId = e.target.value ? parseInt(e.target.value) : null;
            this.handleCaseChange();
        });
        
        // New Case Modals
        const openModal = () => {
            this.newCaseModal.classList.add("active");
            document.getElementById("case-title-input").focus();
        };
        const closeModal = () => this.newCaseModal.classList.remove("active");
        
        this.btnHeaderNewCase.addEventListener("click", openModal);
        this.btnCasesNewCase.addEventListener("click", openModal);
        this.btnCloseCaseModal.addEventListener("click", closeModal);
        this.btnCancelCaseModal.addEventListener("click", closeModal);
        
        this.newCaseForm.addEventListener("submit", (e) => {
            e.preventDefault();
            this.createCase();
        });
        
        // Edit Case Modals
        const closeEditModal = () => this.editCaseModal.style.display = "none";
        this.btnCloseEditCaseModal.addEventListener("click", closeEditModal);
        this.btnCancelEditCaseModal.addEventListener("click", closeEditModal);
        
        this.editCaseForm.addEventListener("submit", (e) => {
            e.preventDefault();
            this.updateCaseSubmit();
        });
        
        // Real-time search with debounce
        let searchTimeout;
        this.caseSearchInput.addEventListener("input", () => {
            clearTimeout(searchTimeout);
            this.caseCurrentPage = 1;
            searchTimeout = setTimeout(() => this.loadCases(), 300);
        });
        
        // Filter and Sort change events
        this.caseFilterStatus.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        this.caseFilterPriority.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        this.caseFilterPlatform.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        if (this.caseFilterOwner) this.caseFilterOwner.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        if (this.caseFilterStartDate) this.caseFilterStartDate.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        if (this.caseFilterEndDate) this.caseFilterEndDate.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        this.caseSortBy.addEventListener("change", () => { this.caseCurrentPage = 1; this.loadCases(); });
        
        // Pagination events
        if (this.casePaginationLimit) {
            this.casePaginationLimit.addEventListener("change", (e) => {
                this.casePageLimit = parseInt(e.target.value, 10);
                this.caseCurrentPage = 1;
                this.loadCases();
            });
        }
        if (this.btnCasePagePrev) {
            this.btnCasePagePrev.addEventListener("click", () => {
                if (this.caseCurrentPage > 1) {
                    this.caseCurrentPage--;
                    this.loadCases();
                }
            });
        }
        if (this.btnCasePageNext) {
            this.btnCasePageNext.addEventListener("click", () => {
                if (this.caseCurrentPage * this.casePageLimit < this.casesTotalCount) {
                    this.caseCurrentPage++;
                    this.loadCases();
                }
            });
        }
        
        // Case Details Panel actions
        this.btnEditCase.addEventListener("click", () => this.openEditCaseModal());
        this.btnDeleteCaseAction.addEventListener("click", (e) => this.deleteCase(this.activeCaseId, e));
        this.btnSaveCaseNote.addEventListener("click", () => this.saveCaseNote());
        this.caseAddNoteInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                this.saveCaseNote();
            }
        });
        
        // Tabs Toggling
        this.switchDetailsTab("details"); // Default
        this.tabBtnDetails.addEventListener("click", () => this.switchDetailsTab("details"));
        this.tabBtnEvidence.addEventListener("click", () => this.switchDetailsTab("evidence"));
        
        // Evidence Upload Select
        this.evidenceUploadZone.addEventListener("click", () => this.evidenceFileInput.click());
        this.evidenceFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                this.uploadEvidenceFiles(e.target.files);
            }
        });
        
        // Evidence Drag & Drop
        this.evidenceUploadZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            this.evidenceUploadZone.style.borderColor = "var(--accent)";
            this.evidenceUploadZone.style.background = "rgba(130, 84, 255, 0.03)";
        });
        this.evidenceUploadZone.addEventListener("dragleave", () => {
            this.evidenceUploadZone.style.borderColor = "var(--border-light)";
            this.evidenceUploadZone.style.background = "var(--bg-dark)";
        });
        this.evidenceUploadZone.addEventListener("drop", (e) => {
            e.preventDefault();
            this.evidenceUploadZone.style.borderColor = "var(--border-light)";
            this.evidenceUploadZone.style.background = "var(--bg-dark)";
            if (e.dataTransfer.files.length > 0) {
                this.uploadEvidenceFiles(e.dataTransfer.files);
            }
        });
        
        // Evidence Filters & Search
        let evidenceSearchTimeout;
        this.evidenceSearchInput.addEventListener("input", () => {
            clearTimeout(evidenceSearchTimeout);
            evidenceSearchTimeout = setTimeout(() => this.loadEvidenceFiles(), 300);
        });
        this.evidenceFilterType.addEventListener("change", () => this.loadEvidenceFiles());
        
        // Evidence Viewer zoom & close
        this.viewerZoomLevel = 1.0;
        this.btnCloseEvidenceViewer.addEventListener("click", () => {
            this.evidenceViewerOverlay.style.display = "none";
            this.viewerVideo.pause();
            this.viewerVideo.src = "";
        });
        this.btnZoomIn.addEventListener("click", () => {
            this.viewerZoomLevel = Math.min(4.0, this.viewerZoomLevel + 0.25);
            this.viewerImg.style.transform = `scale(${this.viewerZoomLevel})`;
        });
        this.btnZoomOut.addEventListener("click", () => {
            this.viewerZoomLevel = Math.max(0.25, this.viewerZoomLevel - 0.25);
            this.viewerImg.style.transform = `scale(${this.viewerZoomLevel})`;
        });
        this.btnZoomReset.addEventListener("click", () => {
            this.viewerZoomLevel = 1.0;
            this.viewerImg.style.transform = `scale(1)`;
        });

        // File Upload Zone
        this.uploadZone.addEventListener("click", () => this.originalFileInput.click());
        this.originalFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                this.uploadOriginalFile(e.target.files[0]);
            }
        });
        
        // Drag over effects
        this.uploadZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            this.uploadZone.classList.add("dragover");
        });
        this.uploadZone.addEventListener("dragleave", () => {
            this.uploadZone.classList.remove("dragover");
        });
        this.uploadZone.addEventListener("drop", (e) => {
            e.preventDefault();
            this.uploadZone.classList.remove("dragover");
            if (e.dataTransfer.files.length > 0) {
                this.uploadOriginalFile(e.dataTransfer.files[0]);
            }
        });
        
        // Scanner
        this.btnRunScan.addEventListener("click", () => this.runInfringementScan());
        
        // DMCA notices
        this.dmcaForm.addEventListener("submit", (e) => {
            e.preventDefault();
            this.generateDMCAReport();
        });
        
        this.btnCopyDmca.addEventListener("click", () => this.copyDMCAClipboard());
        this.btnDownloadDmca.addEventListener("click", () => this.downloadDMCANotice());
        this.btnExportPdf.addEventListener("click", () => this.exportReportDocument("pdf"));
        this.btnExportDocx.addEventListener("click", () => this.exportReportDocument("docx"));
        
        // Settings save
        this.settingsForm.addEventListener("submit", (e) => {
            e.preventDefault();
            this.saveSettings();
        });

        // Login Form submit
        if (this.loginForm) {
            this.loginForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }
        
        // Logout Click
        if (this.btnLogout) {
            this.btnLogout.addEventListener("click", (e) => {
                e.preventDefault();
                this.handleLogout();
            });
        }
        
        // User registration submit
        if (this.userRegistrationForm) {
            this.userRegistrationForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.handleUserRegistration();
            });
        }
        
        // Security Center Filters and Pagination
        if (this.btnRefreshAudit) {
            this.btnRefreshAudit.addEventListener("click", () => {
                this.securityAuditPage = 0;
                this.loadSecurityView();
            });
        }
        if (this.securityActionFilter) {
            this.securityActionFilter.addEventListener("change", () => {
                this.securityAuditPage = 0;
                this.loadSecurityView();
            });
        }
        if (this.btnAuditPrev) {
            this.btnAuditPrev.addEventListener("click", () => {
                if (this.securityAuditPage > 0) {
                    this.securityAuditPage--;
                    this.loadSecurityView();
                }
            });
        }
        if (this.btnAuditNext) {
            this.btnAuditNext.addEventListener("click", () => {
                this.securityAuditPage++;
                this.loadSecurityView();
            });
        }

        // Verification Center Event Listeners
        if (this.verifyRefreshBtn) {
            this.verifyRefreshBtn.addEventListener("click", () => this.loadVerificationCenter());
        }

        if (this.verifyApproveBtn) {
            this.verifyApproveBtn.addEventListener("click", () => {
                if (this.activeVerificationRecord) {
                    this.openApproveModal(this.activeVerificationRecord);
                }
            });
        }

        if (this.verifyRejectBtn) {
            this.verifyRejectBtn.addEventListener("click", () => {
                if (this.activeVerificationRecord) {
                    this.openRejectModal(this.activeVerificationRecord);
                }
            });
        }

        if (this.verifyAddNoteBtn) {
            this.verifyAddNoteBtn.addEventListener("click", () => {
                if (this.activeVerificationRecord) {
                    this.openAddNoteModal(this.activeVerificationRecord);
                }
            });
        }

        // Close verification modals
        const closeApprove = () => { if (this.modalVerifyApprove) this.modalVerifyApprove.style.display = "none"; };
        const closeReject = () => { if (this.modalVerifyReject) this.modalVerifyReject.style.display = "none"; };
        const closeNote = () => { if (this.modalVerifyAddNote) this.modalVerifyAddNote.style.display = "none"; };

        const elCloseApprove = document.getElementById("btn-close-verify-approve-modal");
        const elCancelApprove = document.getElementById("btn-cancel-verify-approve");
        const elCloseReject = document.getElementById("btn-close-verify-reject-modal");
        const elCancelReject = document.getElementById("btn-cancel-verify-reject");
        const elCloseNote = document.getElementById("btn-close-verify-note-modal");
        const elCancelNote = document.getElementById("btn-cancel-verify-note");

        if (elCloseApprove) elCloseApprove.addEventListener("click", closeApprove);
        if (elCancelApprove) elCancelApprove.addEventListener("click", closeApprove);
        if (elCloseReject) elCloseReject.addEventListener("click", closeReject);
        if (elCancelReject) elCancelReject.addEventListener("click", closeReject);
        if (elCloseNote) elCloseNote.addEventListener("click", closeNote);
        if (elCancelNote) elCancelNote.addEventListener("click", closeNote);

        // Submit actions
        if (this.verifyApproveForm) {
            this.verifyApproveForm.addEventListener("submit", (e) => this.handleApproveSubmit(e));
        }
        if (this.verifyRejectForm) {
            this.verifyRejectForm.addEventListener("submit", (e) => this.handleRejectSubmit(e));
        }
        if (this.verifyNoteForm) {
            this.verifyNoteForm.addEventListener("submit", (e) => this.handleNoteSubmit(e));
        }
    }

    async initAuth() {
        const token = localStorage.getItem("auth_token");
        const username = localStorage.getItem("auth_username");
        const role = localStorage.getItem("auth_role");
        
        if (token) {
            try {
                const parts = token.split('.');
                if (parts.length === 3) {
                    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
                    if (payload.exp && payload.exp * 1000 < Date.now()) {
                        this.clearAuth();
                        return;
                    }
                    this.token = token;
                    this.username = username;
                    this.role = role;
                    this.updateAuthUI();
                    return;
                }
            } catch (e) {
                console.error("Token decoding error", e);
            }
        }
        
        // Check for development bypass auth
        try {
            const res = await fetch("/api/v1/auth/roles/me");
            if (res.ok) {
                const user = await res.json();
                this.token = "dev_bypass";
                this.username = user.username;
                this.role = user.role;
                this.updateAuthUI();
                return;
            }
        } catch (e) {
            console.log("No development bypass", e);
        }
        
        this.clearAuth();
    }
    
    clearAuth() {
        this.token = null;
        this.username = null;
        this.role = null;
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_username");
        localStorage.removeItem("auth_role");
        
        if (document.getElementById("sidebar-user-info")) {
            document.getElementById("sidebar-user-info").style.display = "none";
        }
        if (document.getElementById("btn-logout")) {
            document.getElementById("btn-logout").style.display = "none";
        }
        if (document.getElementById("panel-user-management")) {
            document.getElementById("panel-user-management").style.display = "none";
        }
        
        if (this.loginOverlay) {
            this.loginOverlay.classList.add("active");
        }
    }
    
    updateAuthUI() {
        if (document.getElementById("sidebar-username-label")) {
            document.getElementById("sidebar-username-label").textContent = this.username;
        }
        if (document.getElementById("sidebar-user-info")) {
            document.getElementById("sidebar-user-info").style.display = "block";
        }
        if (document.getElementById("btn-logout")) {
            document.getElementById("btn-logout").style.display = "block";
        }
        
        if (this.role === "Admin") {
            if (document.getElementById("panel-user-management")) {
                document.getElementById("panel-user-management").style.display = "block";
            }
        } else {
            if (document.getElementById("panel-user-management")) {
                document.getElementById("panel-user-management").style.display = "none";
            }
        }
        
        if (this.loginOverlay) {
            this.loginOverlay.classList.remove("active");
        }
    }
    
    async authFetch(url, options = {}) {
        if (!options.headers) {
            options.headers = {};
        }
        
        if (this.token && this.token !== "dev_bypass") {
            options.headers["Authorization"] = `Bearer ${this.token}`;
        }
        
        const res = await fetch(url, options);
        
        if (res.status === 401) {
            if (this.token !== null) {
                this.clearAuth();
                this.showToast("Session expired or unauthorized. Please login again.", "danger");
            }
            throw new Error("UNAUTHORIZED");
        } else if (res.status === 403) {
            this.showToast("Forbidden: You do not have permission to execute this action.", "danger");
            throw new Error("FORBIDDEN");
        }
        
        return res;
    }
    
    async handleLogin() {
        const emailInput = document.getElementById("login-email-input");
        const passwordInput = document.getElementById("login-password-input");
        
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        
        if (!email || !password) return;
        
        try {
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });
            
            if (res.status === 401) {
                this.loginErrorMsg.classList.add("active");
                return;
            }
            
            if (!res.ok) {
                throw new Error("Login failed");
            }
            
            const data = await res.json();
            
            if (!data.success || !data.token || !data.user) {
                throw new Error("Invalid response format from authentication server.");
            }
            
            const token = data.token;
            const username = data.user.username;
            const role = data.user.role;
            
            // Store session
            localStorage.setItem("auth_token", token);
            localStorage.setItem("auth_username", username);
            localStorage.setItem("auth_role", role);
            
            this.token = token;
            this.username = username;
            this.role = role;
            
            this.loginErrorMsg.classList.remove("active");
            emailInput.value = "";
            passwordInput.value = "";
            
            this.updateAuthUI();
            this.showToast(`Logged in successfully as ${this.username}!`, "success");
            
            // Redirect to Dashboard and load layout stats
            this.switchView("dashboard");
            this.loadCases();
            
        } catch (e) {
            this.showToast("Network error or server unavailable.", "danger");
        }
    }
    
    async handleLogout() {
        try {
            await this.authFetch("/api/v1/auth/logout", { method: "POST" });
        } catch (e) {
            console.warn("Failed to request logout on server", e);
        }
        this.clearAuth();
        this.showToast("Logged out successfully.", "info");
    }
    
    async handleUserRegistration() {
        const usernameInput = document.getElementById("reg-username");
        const emailInput = document.getElementById("reg-email");
        const passwordInput = document.getElementById("reg-password");
        const roleInput = document.getElementById("reg-role");
        
        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const role = roleInput.value;
        
        if (!username || !email || !password || !role) {
            this.showToast("All fields are required for registration.", "warning");
            return;
        }
        
        try {
            const res = await this.authFetch("/api/v1/auth/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, email, password, role })
            });
            
            if (res.ok) {
                this.showToast(`User ${username} successfully registered!`, "success");
                usernameInput.value = "";
                emailInput.value = "";
                passwordInput.value = "";
                roleInput.value = "Guest";
            } else {
                const data = await res.json();
                this.showToast(data.detail?.message || "Registration failed.", "danger");
            }
        } catch (e) {
            console.error("User registration error", e);
        }
    }

    switchView(viewName) {
        this.activeView = viewName;
        
        // Update tabs active state
        this.navItems.forEach(item => {
            if (item.getAttribute("data-view") === viewName) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
        
        // Show/hide view panes
        this.viewPanes.forEach(pane => {
            if (pane.id === `view-${viewName}`) {
                pane.style.display = "block";
            } else {
                pane.style.display = "none";
            }
        });
        
        // Update Title Header
        const viewTitles = {
            dashboard: "Dashboard Overview",
            cases: "Case Manager",
            verification: "Verification Center",
            library: "Video Fingerprinter",
            scanner: "Infringement Scanner",
            reports: "DMCA notice generator",
            security: "Security Center",
            settings: "Default Settings"
        };
        this.pageTitle.textContent = viewTitles[viewName] || "Copyright Security";
        
        // Trigger view-specific loaders
        this.loadViewData(viewName);
    }

    // Load dynamic data based on active view
    loadViewData(view) {
        switch (view) {
            case "dashboard":
                this.loadDashboardData();
                break;
            case "cases":
                this.renderCasesList();
                this.showCaseDetails(this.activeCaseId);
                break;
            case "verification":
                this.loadVerificationCenter();
                break;
            case "library":
                this.loadOriginalsLibrary();
                break;
            case "scanner":
                this.loadScannedEvidence();
                break;
            case "reports":
                this.loadDMCAConfigData();
                break;
            case "security":
                this.securityAuditPage = 0;
                this.loadSecurityView();
                break;
            case "settings":
                this.loadSettings();
                break;
        }
    }

    initAutoRefresh() {
        setInterval(() => {
            if (this.token) {
                if (this.activeView === "dashboard") {
                    this.loadDashboardData();
                } else if (this.activeView === "cases") {
                    this.loadCases();
                } else if (this.activeView === "verification") {
                    this.loadVerificationCenter();
                }
            }
        }, 30000); // refresh every 30 seconds
    }

    handleCaseChange() {
        this.showToast(`Switched active case folder.`, "info");
        
        // Set context headers
        const caseObj = this.cases.find(c => c.id === this.activeCaseId);
        const name = caseObj ? caseObj.title : "No Active Case";
        
        const badges = ["library-case-badge", "scanner-case-badge", "reports-case-badge"];
        badges.forEach(b => {
            const el = document.getElementById(b);
            if (el) {
                el.textContent = name;
                if (this.activeCaseId) {
                    el.className = "badge badge-info";
                } else {
                    el.className = "badge badge-danger";
                }
            }
        });
        
        // Sync the view we are currently on
        this.loadViewData(this.activeView);
    }

    // -------------------------------------------------------------
    // DATABASE / CASES MANAGEMENT
    // -------------------------------------------------------------
    async loadUsers() {
        try {
            const res = await this.authFetch("/api/v1/auth/users");
            if (!res.ok) return;
            const users = await res.json();
            this.users = users;
            
            // Populate Create and Edit Modal owner selector
            const createOwnerSelect = document.getElementById("case-owner-input");
            const editOwnerSelect = document.getElementById("edit-case-owner-input");
            const filterOwnerSelect = document.getElementById("case-filter-owner");
            
            if (createOwnerSelect) {
                createOwnerSelect.innerHTML = '<option value="">-- Assign Owner --</option>';
                users.forEach(u => {
                    const opt = document.createElement("option");
                    opt.value = u.id;
                    opt.textContent = `${u.username} (${u.role})`;
                    createOwnerSelect.appendChild(opt);
                });
            }
            
            if (editOwnerSelect) {
                editOwnerSelect.innerHTML = '<option value="">-- Assign Owner --</option>';
                users.forEach(u => {
                    const opt = document.createElement("option");
                    opt.value = u.id;
                    opt.textContent = `${u.username} (${u.role})`;
                    editOwnerSelect.appendChild(opt);
                });
            }
            
            if (filterOwnerSelect) {
                filterOwnerSelect.innerHTML = '<option value="">All Owners</option>';
                users.forEach(u => {
                    const opt = document.createElement("option");
                    opt.value = u.id;
                    opt.textContent = u.username;
                    filterOwnerSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.error("Failed to load users for owner selector", e);
        }
    }

    async loadCases() {
        try {
            if (this.token && this.users.length === 0) {
                await this.loadUsers();
            }
            
            // 1. Fetch full list for the global dropdown (unfiltered active cases)
            const fullRes = await this.authFetch("/api/v1/cases");
            const allCases = await fullRes.json();
            this.allCases = allCases;
            
            // Populate select dropdown
            const currentSelected = this.globalCaseSelect.value;
            this.globalCaseSelect.innerHTML = '<option value="">-- Select Case Folder --</option>';
            
            allCases.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.id;
                opt.textContent = c.title;
                this.globalCaseSelect.appendChild(opt);
            });
            
            if (currentSelected && allCases.some(c => c.id == currentSelected)) {
                this.globalCaseSelect.value = currentSelected;
            } else if (allCases.length > 0 && !this.activeCaseId) {
                this.globalCaseSelect.value = allCases[0].id;
                this.activeCaseId = allCases[0].id;
                this.handleCaseChange();
            }
            
            // 2. Fetch filtered list for rendering if in cases view
            let renderList = allCases;
            this.casesTotalCount = allCases.length;
            
            if (this.activeView === "cases") {
                const queryParams = new URLSearchParams();
                if (this.caseSearchInput && this.caseSearchInput.value.trim()) {
                    queryParams.append("q", this.caseSearchInput.value.trim());
                }
                if (this.caseFilterStatus && this.caseFilterStatus.value) {
                    queryParams.append("status", this.caseFilterStatus.value);
                }
                if (this.caseFilterPriority && this.caseFilterPriority.value) {
                    queryParams.append("priority", this.caseFilterPriority.value);
                }
                if (this.caseFilterPlatform && this.caseFilterPlatform.value) {
                    queryParams.append("platform", this.caseFilterPlatform.value);
                }
                if (this.caseFilterOwner && this.caseFilterOwner.value) {
                    queryParams.append("owner_id", this.caseFilterOwner.value);
                }
                if (this.caseFilterStartDate && this.caseFilterStartDate.value) {
                    queryParams.append("start_date", this.caseFilterStartDate.value);
                }
                if (this.caseFilterEndDate && this.caseFilterEndDate.value) {
                    queryParams.append("end_date", this.caseFilterEndDate.value);
                }
                if (this.caseSortBy && this.caseSortBy.value) {
                    queryParams.append("sort_by", this.caseSortBy.value);
                }
                if (this.caseCurrentPage && this.casePageLimit) {
                    queryParams.append("page", this.caseCurrentPage);
                    queryParams.append("limit", this.casePageLimit);
                }
                const filteredRes = await this.authFetch(`/api/v1/cases?${queryParams.toString()}`);
                renderList = await filteredRes.json();
                
                const totalCountHeader = filteredRes.headers.get("X-Total-Count");
                this.casesTotalCount = totalCountHeader ? parseInt(totalCountHeader, 10) : allCases.length;
            }
            
            this.cases = renderList;
            if (this.activeView === "cases") {
                this.renderCasesList();
                this.showCaseDetails(this.activeCaseId);
            }
        } catch (e) {
            this.showToast("Failed to load cases database.", "danger");
        }
    }

    async createCase() {
        const titleInput = document.getElementById("case-title-input");
        const clientInput = document.getElementById("case-client-input");
        const platformInput = document.getElementById("case-platform-input");
        const priorityInput = document.getElementById("case-priority-input");
        const ownerInput = document.getElementById("case-owner-input");
        const tagsInput = document.getElementById("case-tags-input");
        const descInput = document.getElementById("case-desc-input");
        
        const title = titleInput.value.trim();
        const client_name = clientInput.value.trim();
        const platform = platformInput.value;
        const priority = priorityInput.value;
        const assigned_user_id = ownerInput && ownerInput.value ? parseInt(ownerInput.value, 10) : null;
        const tags = tagsInput ? tagsInput.value.trim() : "";
        const description = descInput.value.trim();
        
        if (!title || !client_name || !platform) {
            this.showToast("Please fill in all required fields.", "warning");
            return;
        }
        
        try {
            const res = await this.authFetch("/api/v1/cases", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, client_name, platform, priority, description, assigned_user_id, tags })
            });
            
            if (!res.ok) throw new Error("Failed to save");
            
            const newCase = await res.json();
            this.showToast(`Case "${newCase.title}" created!`, "success");
            
            // Clear inputs & close modal
            titleInput.value = "";
            clientInput.value = "";
            platformInput.value = "YouTube";
            priorityInput.value = "Medium";
            if (ownerInput) ownerInput.value = "";
            if (tagsInput) tagsInput.value = "";
            descInput.value = "";
            this.newCaseModal.classList.remove("active");
            
            // Reload cases
            await this.loadCases();
            
            // Set as active case
            this.globalCaseSelect.value = newCase.id;
            this.activeCaseId = newCase.id;
            this.handleCaseChange();
            
        } catch (e) {
            this.showToast("Error creating case folder.", "danger");
        }
    }

    async deleteCase(caseId, e) {
        if (e) e.stopPropagation();
        if (!confirm("Are you sure you want to delete this case? All uploaded videos, visual fingerprints, and matched reports inside this case will be soft-deleted!")) return;
        
        try {
            const res = await this.authFetch(`/api/v1/cases/${caseId}`, { method: "DELETE" });
            if (!res.ok) throw new Error();
            
            this.showToast("Case soft-deleted successfully.", "success");
            
            if (this.activeCaseId === caseId) {
                this.activeCaseId = null;
                this.globalCaseSelect.value = "";
                this.handleCaseChange();
            }
            this.loadCases();
        } catch (e) {
            this.showToast("Failed to delete case folder.", "danger");
        }
    }

    openEditCaseModal(c) {
        const caseObj = c || this.cases.find(item => item.id === this.activeCaseId);
        if (!caseObj) return;
        
        this.editingCaseId = caseObj.id;
        
        document.getElementById("edit-case-title-input").value = caseObj.title || "";
        document.getElementById("edit-case-client-input").value = caseObj.client_name || "";
        document.getElementById("edit-case-platform-input").value = caseObj.platform || "YouTube";
        document.getElementById("edit-case-priority-input").value = caseObj.priority || "Medium";
        document.getElementById("edit-case-status-input").value = caseObj.status || "Draft";
        if (document.getElementById("edit-case-owner-input")) {
            document.getElementById("edit-case-owner-input").value = caseObj.assigned_user_id || "";
        }
        if (document.getElementById("edit-case-tags-input")) {
            document.getElementById("edit-case-tags-input").value = caseObj.tags || "";
        }
        document.getElementById("edit-case-desc-input").value = caseObj.description || "";
        
        this.editCaseModal.style.display = "flex";
        document.getElementById("edit-case-title-input").focus();
    }
    
    async updateCaseSubmit() {
        const title = document.getElementById("edit-case-title-input").value.trim();
        const client_name = document.getElementById("edit-case-client-input").value.trim();
        const platform = document.getElementById("edit-case-platform-input").value;
        const priority = document.getElementById("edit-case-priority-input").value;
        const status = document.getElementById("edit-case-status-input").value;
        const ownerInput = document.getElementById("edit-case-owner-input");
        const tagsInput = document.getElementById("edit-case-tags-input");
        const assigned_user_id = ownerInput && ownerInput.value ? parseInt(ownerInput.value, 10) : null;
        const tags = tagsInput ? tagsInput.value.trim() : "";
        const description = document.getElementById("edit-case-desc-input").value.trim();
        
        if (!title || !client_name || !platform) {
            this.showToast("Please fill in all required fields.", "warning");
            return;
        }
        
        const targetId = this.editingCaseId || this.activeCaseId;
        if (!targetId) return;
        
        try {
            const res = await this.authFetch(`/api/v1/cases/${targetId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, client_name, platform, priority, status, description, assigned_user_id, tags })
            });
            
            if (!res.ok) throw new Error();
            
            const updated = await res.json();
            this.showToast(`Case "${updated.title}" updated successfully!`, "success");
            this.editCaseModal.style.display = "none";
            
            await this.loadCases();
            if (this.activeCaseId == targetId) {
                this.showCaseDetails(this.activeCaseId);
            }
        } catch (e) {
            this.showToast("Failed to update case folder.", "danger");
        }
    }
    
    switchDetailsTab(tabName) {
        if (tabName === "details") {
            this.tabBtnDetails.classList.add("active");
            this.tabBtnEvidence.classList.remove("active");
            this.panelTabDetails.style.display = "block";
            this.panelTabEvidence.style.display = "none";
        } else {
            this.tabBtnDetails.classList.remove("active");
            this.tabBtnEvidence.classList.add("active");
            this.panelTabDetails.style.display = "none";
            this.panelTabEvidence.style.display = "block";
            this.loadEvidenceFiles();
        }
    }

    async uploadEvidenceFiles(files) {
        if (!this.activeCaseId) {
            this.showToast("Please select a case folder first.", "warning");
            return;
        }
        
        const fileList = Array.from(files);
        if (fileList.length === 0) return;
        
        this.evidenceUploadProgress.style.display = "block";
        this.evidenceUploadPercent.textContent = "0%";
        this.evidenceUploadFill.style.width = "0%";
        
        let successCount = 0;
        let failCount = 0;
        
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            const MAX_SIZE = 50 * 1024 * 1024;
            if (file.size > MAX_SIZE) {
                this.showToast(`File "${file.name}" exceeds maximum size limit (50MB).`, "danger");
                failCount++;
                continue;
            }
            
            const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
            const allowed = [
                '.png', '.jpg', '.jpeg', '.gif', '.webp',
                '.mp4', '.avi', '.mov', '.mkv',
                '.pdf', '.txt', '.docx', '.doc'
            ];
            if (!allowed.includes(ext)) {
                this.showToast(`File "${file.name}" has an unsupported file type extension.`, "danger");
                failCount++;
                continue;
            }
            
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const percent = Math.round(((i) / fileList.length) * 100);
                this.evidenceUploadPercent.textContent = `${percent}%`;
                this.evidenceUploadFill.style.width = `${percent}%`;
                
                const token = localStorage.getItem("token");
                const res = await fetch(`/api/v1/evidence/upload/${this.activeCaseId}`, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`
                    },
                    body: formData
                });
                
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "Upload failed");
                }
                
                successCount++;
            } catch (err) {
                console.error(err);
                this.showToast(`Failed to upload file "${file.name}".`, "danger");
                failCount++;
            }
        }
        
        this.evidenceUploadPercent.textContent = "100%";
        this.evidenceUploadFill.style.width = "100%";
        
        setTimeout(() => {
            this.evidenceUploadProgress.style.display = "none";
        }, 1500);
        
        if (successCount > 0) {
            this.showToast(`Successfully uploaded ${successCount} file(s).`, "success");
            this.loadEvidenceFiles();
            this.loadCaseTimeline(this.activeCaseId);
        }
    }

    async loadEvidenceFiles() {
        if (!this.activeCaseId) {
            this.evidenceFilesList.innerHTML = `<p style="font-size: 12px; color: var(--text-secondary); text-align: center; margin-top: 10px;">No case folder selected.</p>`;
            return;
        }
        
        const q = this.evidenceSearchInput.value.trim();
        const type = this.evidenceFilterType.value;
        
        const queryParams = new URLSearchParams();
        if (q) queryParams.append("q", q);
        if (type) queryParams.append("file_type", type);
        
        try {
            const res = await this.authFetch(`/api/v1/evidence/${this.activeCaseId}?${queryParams.toString()}`);
            if (!res.ok) throw new Error();
            const list = await res.json();
            
            this.evidenceFilesList.innerHTML = "";
            if (list.length === 0) {
                this.evidenceFilesList.innerHTML = `<p style="font-size: 12px; color: var(--text-secondary); text-align: center; margin-top: 20px;">No evidence files found.</p>`;
                return;
            }
            
            list.forEach(item => {
                const el = document.createElement("div");
                el.className = "evidence-file-item";
                el.style.display = "flex";
                el.style.justifyContent = "space-between";
                el.style.alignItems = "center";
                el.style.background = "var(--bg-dark)";
                el.style.border = "1px solid var(--border-light)";
                el.style.borderRadius = "6px";
                el.style.padding = "10px 12px";
                el.style.marginBottom = "8px";
                el.style.cursor = "pointer";
                el.style.transition = "background-color 0.2s, border-color 0.2s";
                
                el.addEventListener("mouseenter", () => {
                    el.style.borderColor = "var(--accent)";
                    el.style.backgroundColor = "rgba(130, 84, 255, 0.02)";
                });
                el.addEventListener("mouseleave", () => {
                    el.style.borderColor = "var(--border-light)";
                    el.style.backgroundColor = "var(--bg-dark)";
                });
                
                el.addEventListener("click", (e) => {
                    if (e.target.closest("button") || e.target.closest("a")) return;
                    this.openEvidenceViewer(item);
                });
                
                let iconClass = "fa-solid fa-file";
                const ft = item.file_type || "";
                if (ft.startsWith("image/")) iconClass = "fa-solid fa-file-image";
                else if (ft.startsWith("video/")) iconClass = "fa-solid fa-file-video";
                else if (ft.startsWith("application/pdf")) iconClass = "fa-solid fa-file-pdf";
                else if (ft.startsWith("application/vnd") || ft.includes("word") || ft.includes("document")) iconClass = "fa-solid fa-file-word";
                else if (ft.startsWith("text/")) iconClass = "fa-solid fa-file-lines";
                else if (!item.file_type || ft === "link" || ft === "") iconClass = "fa-solid fa-link";
                
                let sizeStr = "";
                if (item.file_size) {
                    const sz = item.file_size;
                    if (sz < 1024) sizeStr = `${sz} B`;
                    else if (sz < 1024 * 1024) sizeStr = `${(sz / 1024).toFixed(1)} KB`;
                    else sizeStr = `${(sz / (1024 * 1024)).toFixed(1)} MB`;
                }
                
                const timeStr = new Date(item.created_at || item.upload_date).toLocaleString();
                
                el.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 12px; overflow: hidden; flex: 1;">
                        <i class="${iconClass}" style="font-size: 20px; color: var(--accent); flex-shrink: 0;"></i>
                        <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            <span style="font-size: 13px; font-weight: 600; color: var(--text-primary); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.title}</span>
                            <span style="font-size: 11px; color: var(--text-secondary); display: block;">${sizeStr ? sizeStr + ' • ' : ''}${timeStr}</span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 6px; flex-shrink: 0; margin-left: 8px;">
                        <button class="btn btn-danger btn-sm" style="padding: 4px 8px; font-size: 11px; background: rgba(234, 67, 53, 0.15); border: 1px solid rgba(234, 67, 53, 0.3); color: #ff5c5c;" onclick="event.stopPropagation(); app.deleteEvidenceFile(${item.id})">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                `;
                this.evidenceFilesList.appendChild(el);
            });
        } catch (e) {
            this.evidenceFilesList.innerHTML = `<p style="font-size: 12px; color: var(--accent); text-align: center; margin-top: 10px;">Failed to query evidence files.</p>`;
        }
    }

    async deleteEvidenceFile(id) {
        if (!confirm("Are you sure you want to delete this evidence entry? All associated physical storage records will be removed!")) return;
        
        try {
            const res = await this.authFetch(`/api/v1/evidence/${id}`, { method: "DELETE" });
            if (!res.ok) throw new Error();
            this.showToast("Evidence file deleted successfully.", "success");
            this.loadEvidenceFiles();
            this.loadCaseTimeline(this.activeCaseId);
        } catch (e) {
            this.showToast("Failed to delete evidence record.", "danger");
        }
    }

    openEvidenceViewer(item) {
        this.evidenceViewerTitle.textContent = item.title;
        this.viewerUploader.textContent = item.uploader || "System";
        this.viewerTimestamp.textContent = new Date(item.created_at || item.upload_date).toLocaleString();
        
        this.viewerZoomLevel = 1.0;
        this.viewerImg.style.transform = "scale(1)";
        
        this.viewerImgContainer.style.display = "none";
        this.viewerVideoContainer.style.display = "none";
        this.viewerDocContainer.style.display = "none";
        this.viewerLinkContainer.style.display = "none";
        
        this.viewerVideo.pause();
        this.viewerVideo.src = "";
        
        const ft = item.file_type || "";
        
        if (ft.startsWith("image/")) {
            this.viewerImg.src = item.url;
            this.viewerImgContainer.style.display = "block";
        } else if (ft.startsWith("video/")) {
            this.viewerVideo.src = item.url;
            this.viewerVideoContainer.style.display = "block";
            this.viewerVideo.load();
        } else if (!item.file_type || ft === "link" || ft === "") {
            this.viewerLinkTitle.textContent = item.title;
            this.viewerLinkUrl.textContent = item.url;
            this.btnOpenEvidenceLink.href = item.url;
            this.viewerLinkContainer.style.display = "block";
        } else {
            this.viewerDocName.textContent = item.title;
            
            let sizeStr = "Unknown Size";
            if (item.file_size) {
                const sz = item.file_size;
                if (sz < 1024) sizeStr = `${sz} B`;
                else if (sz < 1024 * 1024) sizeStr = `${(sz / 1024).toFixed(1)} KB`;
                else sizeStr = `${(sz / (1024 * 1024)).toFixed(1)} MB`;
            }
            this.viewerDocSize.textContent = sizeStr;
            this.btnDownloadEvidenceDoc.href = item.url;
            
            let iconClass = "fa-solid fa-file-pdf";
            if (ft.includes("pdf")) iconClass = "fa-solid fa-file-pdf";
            else if (ft.includes("word") || ft.includes("doc")) iconClass = "fa-solid fa-file-word";
            else if (ft.includes("text") || ft.includes("txt")) iconClass = "fa-solid fa-file-lines";
            
            const iconEl = document.getElementById("evidence-viewer-doc-icon");
            iconEl.className = `${iconClass}`;
            
            this.viewerDocContainer.style.display = "block";
        }
        
        this.evidenceViewerOverlay.style.display = "flex";
    }

    async showCaseDetails(caseId) {
        if (!caseId) {
            this.caseDetailsEmptyState.style.display = "flex";
            this.caseDetailsContent.style.display = "none";
            return;
        }
        
        const caseObj = this.cases.find(c => c.id === caseId);
        if (!caseObj) {
            this.caseDetailsEmptyState.style.display = "flex";
            this.caseDetailsContent.style.display = "none";
            return;
        }
        
        this.caseDetailsEmptyState.style.display = "none";
        this.caseDetailsContent.style.display = "block";
        
        document.getElementById("detail-case-id").textContent = caseObj.id;
        document.getElementById("detail-case-title").textContent = caseObj.title;
        document.getElementById("detail-case-client").textContent = caseObj.client_name || "N/A";
        
        const platformBadge = document.getElementById("detail-case-platform");
        platformBadge.textContent = caseObj.platform || "Unknown";
        platformBadge.className = `badge badge-active`;
        
        const priorityBadge = document.getElementById("detail-case-priority");
        priorityBadge.textContent = caseObj.priority || "Medium";
        if (caseObj.priority === "Critical") {
            priorityBadge.className = "badge badge-danger";
            priorityBadge.style.background = "#ea4335";
            priorityBadge.style.color = "#fff";
        } else if (caseObj.priority === "High") {
            priorityBadge.className = "badge badge-danger";
            priorityBadge.style.background = "";
            priorityBadge.style.color = "";
        } else if (caseObj.priority === "Low") {
            priorityBadge.className = "badge badge-secondary";
            priorityBadge.style.background = "";
            priorityBadge.style.color = "";
        } else {
            priorityBadge.className = "badge badge-warning";
            priorityBadge.style.background = "";
            priorityBadge.style.color = "";
        }
        
        const statusBadge = document.getElementById("detail-case-status");
        statusBadge.textContent = caseObj.status || "Draft";
        statusBadge.style.background = "";
        statusBadge.style.color = "";
        if (caseObj.status === "Investigating" || caseObj.status === "Active") {
            statusBadge.className = "badge badge-active";
        } else if (caseObj.status === "Scanning") {
            statusBadge.className = "badge badge-active";
            statusBadge.style.background = "rgba(0, 191, 255, 0.15)";
            statusBadge.style.color = "#00bfff";
        } else if (caseObj.status === "Evidence Collected") {
            statusBadge.className = "badge badge-active";
            statusBadge.style.background = "rgba(0, 206, 209, 0.15)";
            statusBadge.style.color = "#00ced1";
        } else if (caseObj.status === "Verified" || caseObj.status === "Resolved") {
            statusBadge.className = "badge badge-success";
        } else if (caseObj.status === "DMCA Draft" || caseObj.status === "DMCA Sent") {
            statusBadge.className = "badge badge-warning";
        } else {
            statusBadge.className = "badge badge-secondary";
        }
        
        document.getElementById("detail-case-description").textContent = caseObj.description || "No description notes available.";
        document.getElementById("detail-case-owner").textContent = caseObj.owner_username || "System Admin";
        
        const createdDate = new Date(caseObj.created_at);
        document.getElementById("detail-case-created").textContent = createdDate.toLocaleString();
        
        const tagsContainer = document.getElementById("detail-case-tags");
        if (tagsContainer) {
            tagsContainer.innerHTML = "";
            if (caseObj.tags) {
                const tagsList = caseObj.tags.split(",").map(t => t.trim()).filter(t => t.length > 0);
                if (tagsList.length > 0) {
                    tagsList.forEach(t => {
                        const tagEl = document.createElement("span");
                        tagEl.className = "badge";
                        tagEl.style.background = "rgba(130, 84, 255, 0.15)";
                        tagEl.style.color = "var(--accent)";
                        tagEl.style.fontSize = "11px";
                        tagEl.style.padding = "2px 6px";
                        tagEl.style.borderRadius = "4px";
                        tagEl.textContent = t;
                        tagsContainer.appendChild(tagEl);
                    });
                } else {
                    tagsContainer.innerHTML = '<span style="font-size: 12px; color: var(--text-secondary);">No tags</span>';
                }
            } else {
                tagsContainer.innerHTML = '<span style="font-size: 12px; color: var(--text-secondary);">No tags</span>';
            }
        }
        
        this.loadCaseTimeline(caseId);
        this.loadEvidenceFiles();
    }
    
    async loadCaseTimeline(caseId) {
        this.caseTimelineContainer.innerHTML = `<div class="spinner-container"><p><i class="fa-solid fa-spinner fa-spin"></i> Loading timeline...</p></div>`;
        try {
            const res = await this.authFetch(`/api/v1/cases/${caseId}/timeline`);
            if (!res.ok) throw new Error();
            const timeline = await res.json();
            
            this.caseTimelineContainer.innerHTML = "";
            if (timeline.length === 0) {
                this.caseTimelineContainer.innerHTML = `<p style="font-size: 12px; color: var(--text-secondary); text-align: center; margin-top: 10px;">No activity logs found.</p>`;
                return;
            }
            
            timeline.forEach(item => {
                const el = document.createElement("div");
                el.style.borderLeft = "2px solid var(--border-light)";
                el.style.paddingLeft = "12px";
                el.style.position = "relative";
                el.style.marginBottom = "12px";
                
                let dotColor = "var(--text-secondary)";
                if (item.type === "Created") dotColor = "var(--accent)";
                else if (item.type === "Note") dotColor = "#4caf50";
                else if (item.type === "History") dotColor = "#ff9800";
                
                const dot = document.createElement("div");
                dot.style.position = "absolute";
                dot.style.left = "-5px";
                dot.style.top = "4px";
                dot.style.width = "8px";
                dot.style.height = "8px";
                dot.style.borderRadius = "50%";
                dot.style.background = dotColor;
                el.appendChild(dot);
                
                const timeText = new Date(item.timestamp).toLocaleString();
                
                el.innerHTML += `
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                        <span><strong>${item.username}</strong> (${item.type})</span>
                        <span>${timeText}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-primary); line-height: 1.4;">${item.details}</div>
                `;
                this.caseTimelineContainer.appendChild(el);
            });
            
            this.caseTimelineContainer.scrollTop = this.caseTimelineContainer.scrollHeight;
        } catch (e) {
            this.caseTimelineContainer.innerHTML = `<p style="font-size: 12px; color: var(--accent); text-align: center; margin-top: 10px;">Failed to load timeline activity.</p>`;
        }
    }
    
    async saveCaseNote() {
        const text = this.caseAddNoteInput.value.trim();
        if (!text) return;
        
        try {
            const res = await this.authFetch(`/api/v1/cases/${this.activeCaseId}/notes`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ note: text })
            });
            
            if (!res.ok) throw new Error();
            
            this.caseAddNoteInput.value = "";
            this.showToast("Note added to timeline.", "success");
            this.loadCaseTimeline(this.activeCaseId);
        } catch (e) {
            this.showToast("Failed to save note.", "danger");
        }
    }

    renderCasesList() {
        const tbody = document.getElementById("cases-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";
        
        // Update pagination controls info and buttons
        const startIdx = this.cases.length > 0 ? (this.caseCurrentPage - 1) * this.casePageLimit + 1 : 0;
        const endIdx = Math.min(this.caseCurrentPage * this.casePageLimit, this.casesTotalCount);
        if (this.casePaginationInfo) {
            this.casePaginationInfo.textContent = this.casesTotalCount > 0 
                ? `${startIdx}-${endIdx} of ${this.casesTotalCount}` 
                : "0-0 of 0";
        }
        if (this.btnCasePagePrev) {
            this.btnCasePagePrev.disabled = this.caseCurrentPage <= 1;
        }
        if (this.btnCasePageNext) {
            this.btnCasePageNext.disabled = endIdx >= this.casesTotalCount;
        }
        
        if (this.cases.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" style="text-align: center; padding: 24px; color: var(--text-secondary);">
                        No protection cases matching search criteria found.
                    </td>
                </tr>
            `;
            return;
        }
        
        this.cases.forEach(c => {
            const row = document.createElement("tr");
            row.style.cursor = "pointer";
            row.style.borderBottom = "1px solid var(--border-light)";
            row.style.transition = "background 0.2s";
            
            if (this.activeCaseId === c.id) {
                row.style.background = "rgba(130, 84, 255, 0.08)";
                row.style.borderLeft = "3px solid var(--accent)";
            }
            
            // Priority badge styling
            let priorityBadgeColor = "";
            if (c.priority === "Critical") priorityBadgeColor = "background: #ea4335; color: #fff;";
            else if (c.priority === "High") priorityBadgeColor = "background: rgba(234, 67, 53, 0.15); color: #ea4335;";
            else if (c.priority === "Medium") priorityBadgeColor = "background: rgba(251, 188, 5, 0.15); color: #fbbc05;";
            else priorityBadgeColor = "background: rgba(52, 168, 83, 0.15); color: #34a853;";
            
            // Status badge styling
            let statusBadgeColor = "background: rgba(255, 255, 255, 0.1); color: var(--text-secondary);";
            if (c.status === "Investigating" || c.status === "Active") statusBadgeColor = "background: rgba(130, 84, 255, 0.15); color: var(--accent);";
            else if (c.status === "Scanning") statusBadgeColor = "background: rgba(0, 191, 255, 0.15); color: #00bfff;";
            else if (c.status === "Evidence Collected") statusBadgeColor = "background: rgba(0, 206, 209, 0.15); color: #00ced1;";
            else if (c.status === "Verified") statusBadgeColor = "background: rgba(52, 168, 83, 0.15); color: #34a853;";
            else if (c.status === "DMCA Draft" || c.status === "DMCA Sent") statusBadgeColor = "background: rgba(251, 188, 5, 0.15); color: #fbbc05;";
            else if (c.status === "Resolved") statusBadgeColor = "background: rgba(52, 168, 83, 0.15); color: #34a853;";
            else if (c.status === "Archived") statusBadgeColor = "background: rgba(255, 255, 255, 0.05); color: var(--text-secondary);";
            
            const createdDate = c.created_at ? new Date(c.created_at).toLocaleDateString() : "N/A";
            const updatedDate = c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "N/A";
            
            row.innerHTML = `
                <td style="padding: 10px 4px; font-weight: bold; color: var(--accent);">#${c.id}</td>
                <td style="padding: 10px 4px; font-weight: 500; color: var(--text-primary); max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${c.title}</td>
                <td style="padding: 10px 4px;">${c.owner_username || 'System'}</td>
                <td style="padding: 10px 4px;"><span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);">${c.platform || 'Other'}</span></td>
                <td style="padding: 10px 4px;"><span class="badge" style="${priorityBadgeColor}">${c.priority}</span></td>
                <td style="padding: 10px 4px;"><span class="badge" style="${statusBadgeColor}">${c.status}</span></td>
                <td style="padding: 10px 4px; color: var(--text-secondary);">${createdDate}</td>
                <td style="padding: 10px 4px; color: var(--text-secondary);">${updatedDate}</td>
                <td style="padding: 10px 4px; text-align: center;">${c.evidence_count || 0}</td>
                <td style="padding: 10px 4px; text-align: center; font-weight: bold; color: ${c.matches_count > 0 ? '#ea4335' : 'var(--text-secondary)'};">${c.matches_count || 0}</td>
                <td style="padding: 10px 4px;"><span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary);">${c.verification_status || 'Pending'}</span></td>
                <td style="padding: 10px 4px; text-align: center;">
                    <div style="display: flex; gap: 4px; justify-content: center;">
                        <button class="btn btn-secondary btn-xs btn-action-edit" style="padding: 3px 6px; font-size: 10px;" title="Edit Case"><i class="fa-solid fa-pen"></i></button>
                        <button class="btn btn-secondary btn-xs btn-action-duplicate" style="padding: 3px 6px; font-size: 10px; background: rgba(130, 84, 255, 0.1); color: var(--accent); border-color: rgba(130, 84, 255, 0.2);" title="Duplicate Case"><i class="fa-solid fa-clone"></i></button>
                        <button class="btn btn-secondary btn-xs btn-action-archive" style="padding: 3px 6px; font-size: 10px;" title="Archive Case"><i class="fa-solid fa-box-archive"></i></button>
                        <button class="btn btn-danger btn-xs btn-action-delete" style="padding: 3px 6px; font-size: 10px; background: #ea4335; border-color: #ea4335;" title="Delete Case"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </td>
            `;
            
            row.addEventListener("click", (ev) => {
                if (ev.target.closest("button") || ev.target.closest("i") || ev.target.closest("a")) return;
                this.globalCaseSelect.value = c.id;
                this.activeCaseId = c.id;
                this.handleCaseChange();
                
                document.querySelectorAll("#cases-table-body tr").forEach(r => {
                    r.style.background = "";
                    r.style.borderLeft = "";
                });
                row.style.background = "rgba(130, 84, 255, 0.08)";
                row.style.borderLeft = "3px solid var(--accent)";
            });
            
            // Wire action buttons
            row.querySelector(".btn-action-edit").addEventListener("click", (e) => {
                e.stopPropagation();
                this.openEditCaseModal(c);
            });
            
            row.querySelector(".btn-action-duplicate").addEventListener("click", async (e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to duplicate case "${c.title}"?`)) {
                    try {
                        const res = await this.authFetch(`/api/v1/cases/${c.id}/duplicate`, { method: "POST" });
                        if (res.ok) {
                            const newCase = await res.json();
                            this.showToast("Case duplicated successfully!", "success");
                            await this.loadCases();
                            // Switch to the newly duplicated case
                            this.globalCaseSelect.value = newCase.id;
                            this.activeCaseId = newCase.id;
                            this.handleCaseChange();
                        } else {
                            this.showToast("Failed to duplicate case.", "danger");
                        }
                    } catch (err) {
                        this.showToast("Network error trying to duplicate case.", "danger");
                    }
                }
            });
            
            row.querySelector(".btn-action-archive").addEventListener("click", async (e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to archive case "${c.title}"?`)) {
                    try {
                        const res = await this.authFetch(`/api/v1/cases/${c.id}/archive`, { method: "POST" });
                        if (res.ok) {
                            this.showToast("Case archived successfully!", "success");
                            await this.loadCases();
                        } else {
                            this.showToast("Failed to archive case.", "danger");
                        }
                    } catch (err) {
                        this.showToast("Network error trying to archive case.", "danger");
                    }
                }
            });
            
            row.querySelector(".btn-action-delete").addEventListener("click", (e) => {
                e.stopPropagation();
                this.deleteCase(c.id, e);
            });
            
            tbody.appendChild(row);
        });
    }

    // -------------------------------------------------------------
    // DASHBOARD VIEWS
    // -------------------------------------------------------------
    async loadDashboardData() {
        const recentList = document.getElementById("dashboard-recent-evidence");
        
        // Calculate case metrics from allCases list
        const totalCases = this.allCases.length;
        const openCases = this.allCases.filter(c => c.status !== "Resolved" && c.status !== "Archived").length;
        const resolvedCases = this.allCases.filter(c => c.status === "Resolved").length;
        const archivedCases = this.allCases.filter(c => c.status === "Archived").length;
        this.updateStatsCounters(totalCases, openCases, resolvedCases, archivedCases);
        
        if (!this.activeCaseId) {
            recentList.innerHTML = `<div class="spinner-container"><p>Select an active case above to load dashboard metrics.</p></div>`;
            this.updateDashboardCharts([]);
            return;
        }
        
        try {
            // Load evidence
            const res = await this.authFetch(`/api/v1/evidence/${this.activeCaseId}`);
            const evidence = await res.json();
            
            this.updateDashboardCharts(evidence);
            
            // Populate list
            recentList.innerHTML = "";
            if (evidence.length === 0) {
                recentList.innerHTML = `<div class="spinner-container"><p>No scanned links found for this case. Try scanning a social media link in the Scanner tab!</p></div>`;
                return;
            }
            
            // Show top 3 matches
            evidence.slice(0, 4).forEach(ev => {
                recentList.appendChild(this.createEvidenceRowElement(ev));
            });
            
        } catch (e) {
            recentList.innerHTML = `<div class="spinner-container"><p>Error loading dashboard metrics.</p></div>`;
        }
    }

    updateStatsCounters(total, open, resolved, archived) {
        if (document.getElementById("stat-cases-count"))
            document.getElementById("stat-cases-count").textContent = total;
        if (document.getElementById("stat-open-cases-count"))
            document.getElementById("stat-open-cases-count").textContent = open;
        if (document.getElementById("stat-resolved-cases-count"))
            document.getElementById("stat-resolved-cases-count").textContent = resolved;
        if (document.getElementById("stat-archived-cases-count"))
            document.getElementById("stat-archived-cases-count").textContent = archived;
            
        // Also keep legacy selectors updated if any tests/utilities depend on them
        if (document.getElementById("stat-originals-count")) {
            const totalOriginals = this.allCases.reduce((sum, c) => sum + (c.originals_count || c.original_count || 0), 0);
            document.getElementById("stat-originals-count").textContent = totalOriginals;
        }
        if (document.getElementById("stat-leaks-count")) {
            const totalLeaks = this.allCases.reduce((sum, c) => sum + (c.evidence_count || 0), 0);
            document.getElementById("stat-leaks-count").textContent = totalLeaks;
        }
        if (document.getElementById("stat-verified-count")) {
            const totalVerified = this.allCases.reduce((sum, c) => sum + (c.matches_count || 0), 0);
            document.getElementById("stat-verified-count").textContent = totalVerified;
        }
    }

    // -------------------------------------------------------------
    // ORIGINAL WORKS / FINGERPRINTER LIBRARY
    // -------------------------------------------------------------
    async loadOriginalsLibrary() {
        if (!this.activeCaseId) {
            this.originalsFileList.innerHTML = `<div class="spinner-container"><p>Select a case in the top dropdown to upload and inspect original videos.</p></div>`;
            return;
        }
        
        try {
            const res = await this.authFetch(`/api/v1/originals/${this.activeCaseId}`);
            const originals = await res.json();
            
            this.originalsFileList.innerHTML = "";
            
            if (originals.length === 0) {
                this.originalsFileList.innerHTML = `
                    <div class="spinner-container">
                        <p>No original videos registered under this case case. Use the drag & drop area above to register files.</p>
                    </div>
                `;
                return;
            }
            
            originals.forEach(orig => {
                const li = document.createElement("li");
                li.className = "file-row";
                
                const mb = (orig.filesize / (1024 * 1024)).toFixed(1);
                const minutes = Math.floor(orig.duration / 60);
                const seconds = Math.round(orig.duration % 60);
                
                li.innerHTML = `
                    <i class="fa-solid fa-file-video" style="font-size: 24px; color: var(--accent);"></i>
                    <div class="file-name">
                        <div style="font-weight: 600; color: white;">${orig.filename}</div>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Fingerprint generated: ${new Date(orig.created_at).toLocaleString()}</div>
                    </div>
                    <span class="file-duration"><i class="fa-solid fa-clock"></i> ${minutes}:${seconds < 10 ? '0' : ''}${seconds}</span>
                    <span class="file-size"><i class="fa-solid fa-database"></i> ${mb} MB</span>
                    <button class="btn btn-danger btn-sm" onclick="app.deleteOriginal(${orig.id})">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                `;
                this.originalsFileList.appendChild(li);
            });
        } catch (e) {
            this.originalsFileList.innerHTML = `<div class="spinner-container"><p>Error fetching work library.</p></div>`;
        }
    }

    uploadOriginalFile(file) {
        if (!this.activeCaseId) {
            this.showToast("Select a Case Folder before uploading original files.", "warning");
            return;
        }
        
        const formData = new FormData();
        formData.append("case_id", this.activeCaseId);
        formData.append("file", file);
        
        // Show progress bar
        this.uploadProgressContainer.style.display = "block";
        this.uploadProgressPercent.textContent = "0%";
        this.uploadProgressFill.style.width = "0%";
        
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/v1/originals/upload", true);
        if (this.token && this.token !== "dev_bypass") {
            xhr.setRequestHeader("Authorization", `Bearer ${this.token}`);
        }
        
        // Track upload progress
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                // Cap progress at 95% until fingerprint processing is fully finished on server
                const displayPercent = Math.min(percent, 95);
                this.uploadProgressPercent.textContent = `${displayPercent}%`;
                this.uploadProgressFill.style.width = `${displayPercent}%`;
            }
        };
        
        xhr.onload = () => {
            this.uploadProgressContainer.style.display = "none";
            this.originalFileInput.value = ""; // Reset
            
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                this.showToast(`Successfully hashed and added ${result.filename}!`, "success");
                this.loadOriginalsLibrary();
                this.loadCases(); // Update case video counts
            } else {
                let err = "Upload failed.";
                try {
                    err = JSON.parse(xhr.responseText).detail || err;
                } catch(e) {}
                this.showToast(`Fingerprinting failed: ${err}`, "danger");
            }
        };
        
        xhr.onerror = () => {
            this.uploadProgressContainer.style.display = "none";
            this.showToast("Network upload error.", "danger");
        };
        
        xhr.send(formData);
    }

    async deleteOriginal(origId) {
        if (!confirm("Are you sure you want to delete this original video record? Visual scans referencing this work will retain match stats but the original database file will be deleted.")) return;
        
        try {
            const res = await this.authFetch(`/api/v1/originals/${origId}`, { method: "DELETE" });
            if (!res.ok) throw new Error();
            
            this.showToast("Original record deleted.", "success");
            this.loadOriginalsLibrary();
            this.loadCases(); // Refresh counts
        } catch (e) {
            this.showToast("Error deleting original record.", "danger");
        }
    }

    // -------------------------------------------------------------
    // SCANNER / SCRAPER VIEWS
    // -------------------------------------------------------------
    async loadScannedEvidence() {
        if (!this.activeCaseId) {
            this.scannedEvidenceList.innerHTML = `<div class="spinner-container"><p>Select a case above to load scanned URL evidence logs.</p></div>`;
            return;
        }
        
        try {
            const res = await this.authFetch(`/api/v1/evidence/${this.activeCaseId}`);
            const evidence = await res.json();
            
            this.scannedEvidenceList.innerHTML = "";
            if (evidence.length === 0) {
                this.scannedEvidenceList.innerHTML = `
                    <div class="spinner-container">
                        <p>No logged URL scans found under this case directory yet.</p>
                    </div>
                `;
                return;
            }
            
            evidence.forEach(ev => {
                this.scannedEvidenceList.appendChild(this.createEvidenceRowElement(ev));
            });
        } catch (e) {
            this.scannedEvidenceList.innerHTML = `<div class="spinner-container"><p>Error fetching evidence list.</p></div>`;
        }
    }

    async runInfringementScan() {
        const url = this.scannerUrlInput.value.trim();
        if (!url) {
            this.showToast("Please enter a valid video link URL.", "warning");
            return;
        }
        if (!this.activeCaseId) {
            this.showToast("Please select an active Case Folder first.", "warning");
            return;
        }
        
        // Check if there are originals in this case first
        const caseObj = this.cases.find(c => c.id === this.activeCaseId);
        if (!caseObj || caseObj.original_count === 0) {
            this.showToast("You must upload at least one original video in the Fingerprinter tab before scanning links for visual matches.", "warning");
            return;
        }
        
        // Show spinner state
        this.scanResultsPanel.style.display = "block";
        this.scanResultsContent.innerHTML = `
            <div class="spinner-container">
                <div class="spinner"></div>
                <p>Fetching platform metadata and resolving download stream...</p>
                <span style="font-size:12px; color:var(--text-muted); margin-top:8px;">(This downloads a worst-quality media buffer and computes frame hashes)</span>
            </div>
        `;
        
        this.btnRunScan.disabled = true;
        this.btnRunScan.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Scanning...`;
        
        try {
            const res = await this.authFetch("/api/v1/evidence/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ case_id: this.activeCaseId, url: url })
            });
            
            if (!res.ok) {
                const errDetail = await res.json();
                throw new Error(errDetail.detail || "Scan request failed.");
            }
            
            const result = await res.json();
            
            // Format match text
            const matchPercent = (result.similarity_score * 100).toFixed(1);
            let scoreClass = "low-match";
            let alertMsg = "Visual match checks finished. No substantial copies detected.";
            
            if (result.similarity_score >= 0.8) {
                scoreClass = "high-match";
                alertMsg = `Visual match detected! Found a visual overlap of ${matchPercent}% with original work: "${result.matched_original_name || 'Original Video'}".`;
                this.showToast("Visual duplicate verified!", "warning");
            } else if (result.similarity_score >= 0.4) {
                scoreClass = "mid-match";
                alertMsg = `Possible clip reuse detected (${matchPercent}% match score). Check details.`;
            }
            
            this.scanResultsContent.innerHTML = `
                <div style="display: flex; gap: 24px; align-items: center;">
                    ${result.screenshot_path ? `<img src="${result.screenshot_path}" class="evidence-thumbnail" style="width: 200px; height: 120px; border-radius: var(--radius-md); border: 1px solid var(--border-light);">` : `<div class="evidence-placeholder" style="width: 200px; height: 120px; border-radius: var(--radius-md);"><i class="fa-solid fa-image"></i></div>`}
                    <div style="flex-grow: 1;">
                        <h3 style="color: white; font-size: 16px; margin-bottom: 6px;">${result.title}</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">Uploader: <strong>${result.uploader}</strong> | Platform: <strong>${result.platform}</strong></p>
                        <div class="badge ${result.similarity_score >= 0.8 ? 'badge-danger' : 'badge-info'}" style="margin-bottom: 8px;">
                            ${result.status}
                        </div>
                        <p style="font-size: 13px; color: var(--text-primary); font-weight: 500;">${alertMsg}</p>
                    </div>
                    <div class="evidence-similarity" style="border: none; padding: 0 16px;">
                        <span class="similarity-value ${scoreClass}">${matchPercent}%</span>
                        <span class="similarity-label">Visual Match</span>
                    </div>
                </div>
            `;
            
            // Clear input
            this.scannerUrlInput.value = "";
            
            // Refresh counts and lists
            this.loadScannedEvidence();
            this.loadCases();
            
        } catch (e) {
            this.showToast(e.message || "An error occurred during scanning.", "danger");
            this.scanResultsPanel.style.display = "none";
        } finally {
            this.btnRunScan.disabled = false;
            this.btnRunScan.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Scan URL`;
        }
    }

    createEvidenceRowElement(ev) {
        const row = document.createElement("div");
        row.className = "evidence-row";
        
        const matchPercent = (ev.similarity_score * 100).toFixed(1);
        let scoreClass = "low-match";
        if (ev.similarity_score >= 0.8) scoreClass = "high-match";
        else if (ev.similarity_score >= 0.4) scoreClass = "mid-match";
        
        let platformIcon = "fa-globe";
        if (ev.platform === "YouTube") platformIcon = "fa-youtube platform-youtube";
        else if (ev.platform === "TikTok") platformIcon = "fa-tiktok platform-tiktok";
        else if (ev.platform === "Facebook") platformIcon = "fa-facebook platform-facebook";
        else if (ev.platform === "Instagram") platformIcon = "fa-instagram platform-instagram";
        
        row.innerHTML = `
            ${ev.screenshot_path ? `<img src="${ev.screenshot_path}" class="evidence-thumbnail">` : `<div class="evidence-placeholder"><i class="fa-solid fa-image"></i></div>`}
            
            <div class="evidence-body">
                <div class="evidence-top">
                    <div>
                        <a href="${ev.url}" target="_blank" class="evidence-title">${ev.title || ev.url}</a>
                        <div class="evidence-uploader" style="margin-top: 4px;">Uploaded by: <strong>${ev.uploader || 'Unknown'}</strong></div>
                    </div>
                    <span class="badge ${ev.similarity_score >= 0.8 ? 'badge-danger' : 'badge-warning'}">${ev.status}</span>
                </div>
                
                <div class="evidence-footer">
                    <div class="evidence-stats">
                        <span><i class="fa-brands ${platformIcon}"></i> ${ev.platform}</span>
                        <span><i class="fa-solid fa-calendar"></i> ${ev.upload_date || 'N/A'}</span>
                    </div>
                    <div>
                        <button class="btn btn-secondary btn-sm" style="padding: 4px 8px; font-size: 11px;" onclick="app.switchDMCAEvidence(${ev.id})">
                            <i class="fa-solid fa-scale-balanced"></i> Prepare Claim
                        </button>
                        <button class="btn btn-danger btn-sm" style="padding: 4px 8px; font-size: 11px;" onclick="app.deleteEvidence(${ev.id})">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
            
            <div class="evidence-similarity">
                <span class="similarity-value ${scoreClass}">${matchPercent}%</span>
                <span class="similarity-label">Similarity</span>
            </div>
        `;
        return row;
    }

    async deleteEvidence(evId) {
        if (!confirm("Are you sure you want to delete this evidence record? This will delete local screenshot files and remove visual logs.")) return;
        
        try {
            const res = await this.authFetch(`/api/v1/evidence/${evId}`, { method: "DELETE" });
            if (!res.ok) throw new Error();
            
            this.showToast("Evidence record deleted.", "success");
            this.loadScannedEvidence();
            this.loadCases();
            if (this.activeView === "dashboard") {
                this.loadDashboardData();
            }
        } catch (e) {
            this.showToast("Error deleting evidence record.", "danger");
        }
    }

    // Direct redirection helper to step 1 notice form
    switchDMCAEvidence(evId) {
        this.switchView("reports");
        this.dmcaEvidenceSelect.value = evId;
    }

    // -------------------------------------------------------------
    // DMCA REPORT notice generator
    // -------------------------------------------------------------
    async loadDMCAConfigData() {
        if (!this.activeCaseId) {
            this.dmcaEvidenceSelect.innerHTML = '<option value="">-- Choose verified leak --</option>';
            return;
        }
        
        try {
            const res = await this.authFetch(`/api/v1/evidence/${this.activeCaseId}`);
            const evidence = await res.json();
            
            // Only list items with positive scans (usually match score >= 40%)
            const selectedVal = this.dmcaEvidenceSelect.value;
            this.dmcaEvidenceSelect.innerHTML = '<option value="">-- Choose verified leak --</option>';
            
            evidence.forEach(ev => {
                const opt = document.createElement("option");
                opt.value = ev.id;
                const matchPercent = (ev.similarity_score * 100).toFixed(0);
                opt.textContent = `[${ev.platform}] ${ev.title} (${matchPercent}% match)`;
                this.dmcaEvidenceSelect.appendChild(opt);
            });
            
            if (selectedVal && evidence.some(e => e.id == selectedVal)) {
                this.dmcaEvidenceSelect.value = selectedVal;
            }
            
            // Autofill settings defaults if settings are stored in local storage
            const owner = localStorage.getItem("default_owner");
            const sender = localStorage.getItem("default_sender");
            const email = localStorage.getItem("default_email");
            const phone = localStorage.getItem("default_phone");
            const address = localStorage.getItem("default_address");
            
            if (owner) document.getElementById("dmca-owner-name").value = owner;
            if (sender) document.getElementById("dmca-sender-name").value = sender;
            if (email) document.getElementById("dmca-sender-email").value = email;
            if (phone) document.getElementById("dmca-sender-phone").value = phone;
            if (address) document.getElementById("dmca-sender-address").value = address;
            
        } catch (e) {
            this.showToast("Failed to load claims config details.", "danger");
        }
    }

    async generateDMCAReport() {
        const evId = this.dmcaEvidenceSelect.value;
        const ownerName = document.getElementById("dmca-owner-name").value.trim();
        const senderName = document.getElementById("dmca-sender-name").value.trim();
        const senderEmail = document.getElementById("dmca-sender-email").value.trim();
        const senderPhone = document.getElementById("dmca-sender-phone").value.trim();
        const senderAddress = document.getElementById("dmca-sender-address").value.trim();
        
        if (!evId || !ownerName || !senderName || !senderEmail) {
            this.showToast("Please fill in all required fields.", "warning");
            return;
        }
        
        let sigBase64 = null;
        if (this.hasSigned) {
            sigBase64 = this.signatureCanvas.toDataURL("image/png");
        }
        const templateType = this.dmcaTemplateSelect.value;
        const declarationCheck = this.dmcaDeclarationCheck.checked;
        
        try {
            const res = await this.authFetch("/api/v1/reports/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    case_id: this.activeCaseId,
                    evidence_id: parseInt(evId),
                    sender_name: senderName,
                    sender_email: senderEmail,
                    sender_phone: senderPhone || null,
                    sender_address: senderAddress || null,
                    copyright_owner_name: ownerName,
                    template_type: templateType,
                    signature_base64: sigBase64,
                    declaration_accepted: declarationCheck
                })
            });
            
            if (!res.ok) throw new Error("Failed to generate draft.");
            
            const result = await res.json();
            this.currentReportId = result.id;
            
            // Render text
            this.dmcaNoticeOutput.value = result.report_text;
            this.btnCopyDmca.disabled = false;
            this.btnDownloadDmca.disabled = false;
            this.btnExportPdf.disabled = false;
            this.btnExportDocx.disabled = false;
            
            this.showToast("DMCA report notice compiled successfully!", "success");
            
            // Reload evidence matching states to update badge to DMCA Drafted
            this.loadCases();
            
        } catch (e) {
            this.showToast("Failed to compile DMCA report text.", "danger");
        }
    }

    copyDMCAClipboard() {
        const txt = this.dmcaNoticeOutput.value;
        if (!txt) return;
        
        navigator.clipboard.writeText(txt).then(() => {
            this.showToast("DMCA report copied to clipboard!", "success");
        }).catch(err => {
            this.showToast("Copy to clipboard failed. Select and copy manually.", "danger");
        });
    }

    downloadDMCANotice() {
        const txt = this.dmcaNoticeOutput.value;
        if (!txt) return;
        
        const blob = new Blob([txt], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement("a");
        a.href = url;
        a.download = `DMCA_Notice_Case_${this.activeCaseId}_Draft.txt`;
        document.body.appendChild(a);
        a.click();
        
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.showToast("DMCA text notice saved to downloads directory.", "success");
    }

    // -------------------------------------------------------------
    // DEFAULT SETTINGS MANAGER
    // -------------------------------------------------------------
    loadSettings() {
        const owner = localStorage.getItem("default_owner");
        const sender = localStorage.getItem("default_sender");
        const email = localStorage.getItem("default_email");
        const phone = localStorage.getItem("default_phone");
        const address = localStorage.getItem("default_address");
        
        if (owner) document.getElementById("setting-owner").value = owner;
        if (sender) document.getElementById("setting-sender").value = sender;
        if (email) document.getElementById("setting-email").value = email;
        if (phone) document.getElementById("setting-phone").value = phone;
        if (address) document.getElementById("setting-address").value = address;
    }

    saveSettings() {
        const owner = document.getElementById("setting-owner").value.trim();
        const sender = document.getElementById("setting-sender").value.trim();
        const email = document.getElementById("setting-email").value.trim();
        const phone = document.getElementById("setting-phone").value.trim();
        const address = document.getElementById("setting-address").value.trim();
        
        localStorage.setItem("default_owner", owner);
        localStorage.setItem("default_sender", sender);
        localStorage.setItem("default_email", email);
        localStorage.setItem("default_phone", phone);
        localStorage.setItem("default_address", address);
        
        this.showToast("Settings saved successfully.", "success");
    }

    // -------------------------------------------------------------
    // TOAST NOTIFICATIONS DRAWER
    // -------------------------------------------------------------
    showToast(message, type = "info") {
        const drawer = document.getElementById("toast-drawer");
        if (!drawer) return;
        
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        
        let icon = "fa-info-circle";
        if (type === "success") icon = "fa-circle-check";
        else if (type === "warning") icon = "fa-triangle-exclamation";
        else if (type === "danger") icon = "fa-circle-xmark";
        
        toast.innerHTML = `
            <i class="fa-solid ${icon}"></i>
            <span>${message}</span>
        `;
        
        drawer.appendChild(toast);
        
        // Slide out and remove toast after 4s
        setTimeout(() => {
            toast.style.transform = "translateX(120%)";
            toast.style.transition = "transform 0.3s ease";
            setTimeout(() => {
                if (toast.parentNode === drawer) {
                    drawer.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    initSignaturePad() {
        if (!this.signatureCanvas) return;
        const ctx = this.signatureCanvas.getContext("2d");
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = 2;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";

        const getCoordinates = (e) => {
            const rect = this.signatureCanvas.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;
            return {
                x: (clientX - rect.left) * (this.signatureCanvas.width / rect.width),
                y: (clientY - rect.top) * (this.signatureCanvas.height / rect.height)
            };
        };

        const startDrawing = (e) => {
            e.preventDefault();
            this.isDrawing = true;
            const coords = getCoordinates(e);
            this.lastX = coords.x;
            this.lastY = coords.y;
        };

        const draw = (e) => {
            if (!this.isDrawing) return;
            e.preventDefault();
            const coords = getCoordinates(e);
            ctx.beginPath();
            ctx.moveTo(this.lastX, this.lastY);
            ctx.lineTo(coords.x, coords.y);
            ctx.stroke();
            this.lastX = coords.x;
            this.lastY = coords.y;
            this.hasSigned = true;
        };

        const stopDrawing = () => {
            this.isDrawing = false;
        };

        this.signatureCanvas.addEventListener("mousedown", startDrawing);
        this.signatureCanvas.addEventListener("mousemove", draw);
        this.signatureCanvas.addEventListener("mouseup", stopDrawing);
        this.signatureCanvas.addEventListener("mouseleave", stopDrawing);

        this.signatureCanvas.addEventListener("touchstart", startDrawing);
        this.signatureCanvas.addEventListener("touchmove", draw);
        this.signatureCanvas.addEventListener("touchend", stopDrawing);

        this.btnClearSignature.addEventListener("click", () => {
            ctx.clearRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
            this.hasSigned = false;
        });
    }

    async exportReportDocument(format) {
        if (!this.currentReportId) {
            this.showToast("Please draft and submit a report first.", "warning");
            return;
        }
        
        try {
            this.showToast(`Generating ${format.toUpperCase()} report...`, "info");
            
            const res = await this.authFetch(`/api/v1/reports/${this.currentReportId}/export/${format}`);
            if (!res.ok) throw new Error(`Server returned ${res.status}`);
            
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement("a");
            a.href = url;
            a.download = `DMCA_Report_Notice_${this.currentReportId}.${format}`;
            document.body.appendChild(a);
            a.click();
            
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showToast(`${format.toUpperCase()} report notice downloaded.`, "success");
        } catch (e) {
            this.showToast(`Failed to export ${format.toUpperCase()} report.`, "danger");
        }
    }

    // -------------------------------------------------------------
    // CHARTS RENDERING ENGINE (Epic 5)
    // -------------------------------------------------------------
    updateDashboardCharts(evidence) {
        const container = document.getElementById("dashboard-charts-container");
        if (!container) return;
        
        if (evidence.length === 0) {
            container.style.display = "none";
            return;
        }
        
        container.style.display = "grid";
        
        // 1. Platform Counts
        const platformCounts = { YouTube: 0, TikTok: 0, Facebook: 0, Instagram: 0, Other: 0 };
        // 2. Similarity Counts
        const similarityCounts = { High: 0, Medium: 0, Low: 0 };
        // 3. Status Counts
        const statusCounts = { Detected: 0, Verified: 0, "DMCA Drafted": 0, "DMCA Filed": 0, Resolved: 0 };
        
        evidence.forEach(ev => {
            const p = ev.platform || "Other";
            platformCounts[p] = (platformCounts[p] || 0) + 1;
            
            const score = ev.similarity_score || 0.0;
            if (score >= 0.8) similarityCounts.High++;
            else if (score >= 0.4) similarityCounts.Medium++;
            else similarityCounts.Low++;
            
            const s = ev.status || "Detected";
            statusCounts[s] = (statusCounts[s] || 0) + 1;
        });
        
        // Destroy existing chart instances if any
        if (this.charts.platform) this.charts.platform.destroy();
        if (this.charts.similarity) this.charts.similarity.destroy();
        if (this.charts.status) this.charts.status.destroy();
        
        // Setup shared chart configurations
        const fontConfig = {
            family: "'Outfit', sans-serif",
            size: 11
        };
        
        // Create Platform Distribution Chart
        const ctxPlatform = document.getElementById("chart-platform-dist").getContext("2d");
        this.charts.platform = new Chart(ctxPlatform, {
            type: 'doughnut',
            data: {
                labels: Object.keys(platformCounts),
                datasets: [{
                    data: Object.values(platformCounts),
                    backgroundColor: ['#ff4444', '#00f2fe', '#1877f2', '#e1306c', '#8254ff'],
                    borderColor: 'rgba(22, 28, 45, 0.8)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#8c9cb5',
                            font: fontConfig
                        }
                    }
                }
            }
        });
        
        // Create Similarity Ranges Chart
        const ctxSimilarity = document.getElementById("chart-similarity-ranges").getContext("2d");
        this.charts.similarity = new Chart(ctxSimilarity, {
            type: 'bar',
            data: {
                labels: ['High (≥80%)', 'Medium (40-80%)', 'Low (<40%)'],
                datasets: [{
                    label: 'Match Count',
                    data: [similarityCounts.High, similarityCounts.Medium, similarityCounts.Low],
                    backgroundColor: ['#00e676', '#ff9100', '#8c9cb5'],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8c9cb5', font: fontConfig }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#8c9cb5', font: fontConfig, precision: 0 }
                    }
                }
            }
        });
        
        // Create Status Breakdown Chart
        const ctxStatus = document.getElementById("chart-status-breakdown").getContext("2d");
        this.charts.status = new Chart(ctxStatus, {
            type: 'polarArea',
            data: {
                labels: Object.keys(statusCounts),
                datasets: [{
                    data: Object.values(statusCounts),
                    backgroundColor: [
                        'rgba(0, 176, 255, 0.4)', // Detected
                        'rgba(0, 230, 118, 0.4)', // Verified
                        'rgba(255, 145, 0, 0.4)', // DMCA Drafted
                        'rgba(255, 82, 82, 0.4)',  // DMCA Filed
                        'rgba(140, 156, 181, 0.4)' // Resolved
                    ],
                    borderColor: 'rgba(255, 255, 255, 0.08)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#8c9cb5',
                            font: fontConfig
                        }
                    }
                },
                scales: {
                    r: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { display: false }
                    }
                }
            }
        });
    }

    // -------------------------------------------------------------
    // SECURITY CENTER AUDIT TRAIL LOGS (Epic 6)
    // -------------------------------------------------------------
    async loadSecurityView() {
        if (this.activeView !== "security") return;
        if (!this.securityAuditTbody) return;
        
        this.securityAuditTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 32px;"><i class="fa-solid fa-spinner fa-spin fa-2x" style="color: var(--accent); margin-bottom: 8px; display: block;"></i> Loading audit trail...</td></tr>`;
        
        const action = this.securityActionFilter ? this.securityActionFilter.value : "";
        const limit = this.securityAuditLimit;
        const offset = this.securityAuditPage * limit;
        
        let url = `/api/v1/auth/audit/logs?limit=${limit}&offset=${offset}`;
        if (action) {
            url += `&action=${action}`;
        }
        
        try {
            const res = await this.authFetch(url);
            if (!res.ok) throw new Error("Failed to load logs");
            
            const logs = await res.json();
            
            this.securityAuditTbody.innerHTML = "";
            
            if (logs.length === 0) {
                this.securityAuditTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 32px; color: var(--text-secondary);">No audit logs found matching selected criteria.</td></tr>`;
                if (this.auditPaginationInfo) this.auditPaginationInfo.textContent = `Showing 0-0 entries`;
                if (this.btnAuditPrev) this.btnAuditPrev.disabled = true;
                if (this.btnAuditNext) this.btnAuditNext.disabled = true;
                return;
            }
            
            logs.forEach(log => {
                const tr = document.createElement("tr");
                
                const time = new Date(log.created_at).toLocaleString();
                
                // Set audit action badge class
                let badgeClass = "default";
                const act = log.action.toUpperCase();
                if (act.includes("LOGIN")) badgeClass = "login";
                else if (act.includes("LOGOUT")) badgeClass = "logout";
                else if (act.includes("CREATE") || act.includes("UPLOAD") || act.includes("ENQUEUE")) badgeClass = "create";
                else if (act.includes("UPDATE")) badgeClass = "update";
                else if (act.includes("DELETE") || act.includes("FAIL")) badgeClass = "delete";
                
                // Format target
                const targetText = log.entity_type ? `${log.entity_type.toUpperCase()} #${log.entity_id || ''}` : "SYSTEM";
                
                // Format details
                let detailsText = log.details_json || "";
                try {
                    const parsed = JSON.parse(log.details_json);
                    if (parsed.message) {
                        detailsText = parsed.message;
                    } else {
                        detailsText = Object.entries(parsed).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(", ");
                    }
                } catch (e) {}
                
                tr.innerHTML = `
                    <td style="color: var(--text-secondary); white-space: nowrap;">${time}</td>
                    <td><span class="audit-badge ${badgeClass}">${log.action}</span></td>
                    <td style="color: white; font-weight: 500;">${targetText}</td>
                    <td style="color: var(--text-secondary); max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${detailsText.replace(/"/g, '&quot;')}">${detailsText}</td>
                `;
                this.securityAuditTbody.appendChild(tr);
            });
            
            // Update pagination display
            const startEntry = offset + 1;
            const endEntry = offset + logs.length;
            if (this.auditPaginationInfo) this.auditPaginationInfo.textContent = `Showing ${startEntry}-${endEntry} entries`;
            
            if (this.btnAuditPrev) this.btnAuditPrev.disabled = this.securityAuditPage === 0;
            // Disable Next if we received less logs than limit (meaning no more pages)
            if (this.btnAuditNext) this.btnAuditNext.disabled = logs.length < limit;
            
        } catch (e) {
            this.securityAuditTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 32px; color: var(--color-danger);"><i class="fa-solid fa-triangle-exclamation"></i> Error loading audit logs: ${e.message}</td></tr>`;
            if (this.btnAuditPrev) this.btnAuditPrev.disabled = true;
            if (this.btnAuditNext) this.btnAuditNext.disabled = true;
        }
    }

    // -------------------------------------------------------------
    // VERIFICATION CENTER MODULE
    // -------------------------------------------------------------
    getCurrentUserId() {
        if (!this.token) return 1; // Default to admin user id
        if (this.token === "dev_bypass") return 1;
        try {
            const parts = this.token.split('.');
            if (parts.length === 3) {
                const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
                return payload.id || 1;
            }
        } catch (e) {
            console.error("Error decoding token for user ID", e);
        }
        return 1;
    }

    async loadVerificationCenter() {
        if (this.verifyTableBody) {
            this.verifyTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 32px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading verification queue...</td></tr>`;
        }
        if (this.verifyDetailPanel) {
            this.verifyDetailPanel.style.display = "none";
        }
        this.activeVerificationRecord = null;
        
        try {
            const res = await this.authFetch("/api/v1/verification");
            if (!res.ok) {
                throw new Error("Could not retrieve verification records.");
            }
            const records = await res.json();
            this.renderVerificationTable(records);
            this.updateVerificationStats(records);
        } catch (e) {
            if (this.verifyTableBody) {
                this.verifyTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--color-danger);"><i class="fa-solid fa-triangle-exclamation"></i> ${e.message}</td></tr>`;
            }
        }
    }

    updateVerificationStats(records) {
        let verifiedCount = 0;
        let pendingCount = 0;
        let rejectedCount = 0;
        
        records.forEach(rec => {
            if (rec.status === "Verified") verifiedCount++;
            else if (rec.status === "Pending") pendingCount++;
            else if (rec.status === "Rejected") rejectedCount++;
        });
        
        const total = verifiedCount + rejectedCount;
        const rate = total > 0 ? Math.round((verifiedCount / total) * 100) : 100;
        
        if (this.verifyStatVerified) this.verifyStatVerified.textContent = verifiedCount;
        if (this.verifyStatPending) this.verifyStatPending.textContent = pendingCount;
        if (this.verifyStatRejected) this.verifyStatRejected.textContent = rejectedCount;
        if (this.verifyStatRate) this.verifyStatRate.textContent = `${rate}%`;
    }

    renderVerificationTable(records) {
        if (!this.verifyTableBody) return;
        this.verifyTableBody.innerHTML = "";
        
        if (records.length === 0) {
            this.verifyTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--text-secondary);">No verification cases in the queue.</td></tr>`;
            return;
        }
        
        records.forEach(rec => {
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            
            // AI Score Color Coding
            const scorePercent = Math.round(rec.ai_score * 100);
            let scoreClass = "text-muted";
            if (rec.ai_score >= 0.8) scoreClass = "text-success";
            else if (rec.ai_score >= 0.5) scoreClass = "text-warning";
            else scoreClass = "text-danger";
            
            // Status Badge Formatting
            let badgeClass = "badge-warning";
            if (rec.status === "Verified") badgeClass = "badge-success";
            else if (rec.status === "Rejected") badgeClass = "badge-danger";
            
            const lastUpdated = new Date(rec.updated_at).toLocaleString();
            
            let deleteBtnHtml = "";
            if (this.role === "Admin") {
                deleteBtnHtml = `
                    <button class="btn btn-danger btn-xs btn-table-delete" style="margin-left: 4px; background: #ea4335; border-color: #ea4335;">
                        <i class="fa-solid fa-trash"></i> Delete
                    </button>
                `;
            }
            
            tr.innerHTML = `
                <td style="font-weight: 600; color: var(--accent);">#${rec.id}</td>
                <td style="color: white; font-weight: 500;">${rec.case_name}</td>
                <td>${rec.owner_username || 'Unassigned'}</td>
                <td style="text-align: center;">${rec.evidence_count}</td>
                <td class="${scoreClass}" style="font-weight: 700; text-align: center;">${scorePercent}%</td>
                <td><span class="badge ${badgeClass}">${rec.status}</span></td>
                <td>${rec.reviewer_username || 'System Admin'}</td>
                <td style="color: var(--text-secondary); font-size: 12px;">${lastUpdated}</td>
                <td style="text-align: right; white-space: nowrap;" class="table-actions">
                    <button class="btn btn-secondary btn-xs btn-table-view" style="margin-right: 4px;">
                        <i class="fa-solid fa-eye"></i> Details
                    </button>
                    <button class="btn btn-primary btn-xs btn-table-verify">
                        <i class="fa-solid fa-signature"></i> Verify
                    </button>
                    ${deleteBtnHtml}
                </td>
            `;
            
            // Click to load details
            tr.querySelector(".btn-table-view").addEventListener("click", (e) => {
                e.stopPropagation();
                this.showVerificationDetails(rec);
            });
            tr.querySelector(".btn-table-verify").addEventListener("click", (e) => {
                e.stopPropagation();
                this.showVerificationDetails(rec);
                // Auto scroll to details
                if (this.verifyDetailPanel) {
                    this.verifyDetailPanel.scrollIntoView({ behavior: "smooth" });
                }
            });
            if (this.role === "Admin") {
                tr.querySelector(".btn-table-delete").addEventListener("click", (e) => {
                    e.stopPropagation();
                    this.deleteVerificationRecord(rec.id);
                });
            }
            tr.addEventListener("click", () => this.showVerificationDetails(rec));
            
            this.verifyTableBody.appendChild(tr);
        });
    }

    showVerificationDetails(rec) {
        this.activeVerificationRecord = rec;
        if (!this.verifyDetailPanel) return;
        
        this.verifyDetailPanel.style.display = "block";
        if (this.verifyDetailCaseTitle) {
            this.verifyDetailCaseTitle.textContent = `Case #${rec.case_id}: ${rec.case_name} (Verification #${rec.id})`;
        }
        
        // Metadata / Hash validation badges
        const metaEl = this.verifyDetailMetaVal;
        if (metaEl) {
            metaEl.textContent = rec.metadata_validation;
            metaEl.className = ""; // clear
            metaEl.style.backgroundColor = "";
            metaEl.style.color = "";
            if (rec.metadata_validation === "Verified") {
                metaEl.style.backgroundColor = "rgba(0, 230, 118, 0.1)";
                metaEl.style.color = "var(--color-success)";
            } else if (rec.metadata_validation === "Warning") {
                metaEl.style.backgroundColor = "rgba(255, 145, 0, 0.1)";
                metaEl.style.color = "var(--color-warning)";
            } else if (rec.metadata_validation === "Failed") {
                metaEl.style.backgroundColor = "rgba(255, 82, 82, 0.1)";
                metaEl.style.color = "var(--color-danger)";
            } else {
                metaEl.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
                metaEl.style.color = "var(--text-secondary)";
            }
        }
        
        const hashEl = this.verifyDetailHashVal;
        if (hashEl) {
            hashEl.textContent = rec.hash_verification;
            hashEl.className = ""; // clear
            hashEl.style.backgroundColor = "";
            hashEl.style.color = "";
            if (rec.hash_verification === "Verified") {
                hashEl.style.backgroundColor = "rgba(0, 230, 118, 0.1)";
                hashEl.style.color = "var(--color-success)";
            } else if (rec.hash_verification === "Warning") {
                hashEl.style.backgroundColor = "rgba(255, 145, 0, 0.1)";
                hashEl.style.color = "var(--color-warning)";
            } else if (rec.hash_verification === "Failed") {
                hashEl.style.backgroundColor = "rgba(255, 82, 82, 0.1)";
                hashEl.style.color = "var(--color-danger)";
            } else {
                hashEl.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
                hashEl.style.color = "var(--text-secondary)";
            }
        }
        
        // Evidence Summary text
        if (this.verifyDetailSummary) {
            this.verifyDetailSummary.textContent = rec.evidence_summary || "No verification summary entered by the reviewer yet.";
        }
        
        // AI Metrics
        const scorePercent = Math.round(rec.ai_score * 100);
        if (this.verifyDetailAiScore) {
            this.verifyDetailAiScore.textContent = `${scorePercent}%`;
        }
        if (this.verifyDetailConfidenceBadge) {
            const badge = this.verifyDetailConfidenceBadge;
            badge.className = "";
            badge.style.color = "";
            badge.style.backgroundColor = "";
            if (rec.ai_score >= 0.8) {
                badge.textContent = "High Match Confidence";
                badge.style.backgroundColor = "rgba(0, 230, 118, 0.1)";
                badge.style.color = "var(--color-success)";
            } else if (rec.ai_score >= 0.5) {
                badge.textContent = "Medium Match Confidence";
                badge.style.backgroundColor = "rgba(255, 145, 0, 0.1)";
                badge.style.color = "var(--color-warning)";
            } else {
                badge.textContent = "Low Similarity Scan";
                badge.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
                badge.style.color = "var(--text-secondary)";
            }
        }
        
        // Populate Originals list
        if (this.verifyDetailOriginals) {
            this.verifyDetailOriginals.innerHTML = "";
            if (rec.originals.length === 0) {
                this.verifyDetailOriginals.innerHTML = `<div style="font-size: 13px; color: var(--text-muted);"><i class="fa-solid fa-circle-exclamation"></i> No original reference assets loaded for this case.</div>`;
            } else {
                rec.originals.forEach(orig => {
                    const row = document.createElement("div");
                    row.style.background = "rgba(255,255,255,0.02)";
                    row.style.padding = "10px 12px";
                    row.style.borderRadius = "6px";
                    row.style.display = "flex";
                    row.style.justifyContent = "space-between";
                    row.style.alignItems = "center";
                    row.style.fontSize = "13px";
                    row.style.border = "1px solid var(--border-light)";
                    
                    const sizeMb = (orig.filesize / (1024 * 1024)).toFixed(1);
                    row.innerHTML = `
                        <span style="color: white; font-weight: 500;"><i class="fa-solid fa-file-video" style="color: var(--accent); margin-right: 6px;"></i> ${orig.filename}</span>
                        <span style="color: var(--text-secondary); font-size: 11px;">${sizeMb} MB</span>
                    `;
                    this.verifyDetailOriginals.appendChild(row);
                });
            }
        }
        
        // Populate Evidence Files list
        if (this.verifyDetailEvidence) {
            this.verifyDetailEvidence.innerHTML = "";
            if (rec.evidence_files.length === 0) {
                this.verifyDetailEvidence.innerHTML = `<div style="font-size: 13px; color: var(--text-muted);"><i class="fa-solid fa-circle-exclamation"></i> No crawled evidence items found in this case.</div>`;
            } else {
                rec.evidence_files.forEach(ev => {
                    const row = document.createElement("div");
                    row.style.background = "rgba(255,255,255,0.02)";
                    row.style.padding = "10px 12px";
                    row.style.borderRadius = "6px";
                    row.style.display = "flex";
                    row.style.justifyContent = "space-between";
                    row.style.alignItems = "center";
                    row.style.fontSize = "13px";
                    row.style.border = "1px solid var(--border-light)";
                    
                    const simPercent = Math.round(ev.similarity_score * 100);
                    let scoreClr = "var(--text-secondary)";
                    if (ev.similarity_score >= 0.8) scoreClr = "var(--color-success)";
                    
                    row.innerHTML = `
                        <div style="display: flex; flex-direction: column;">
                            <span style="color: white; font-weight: 500;"><i class="fa-brands fa-youtube" style="color: red; margin-right: 6px;"></i> ${ev.title || ev.url}</span>
                            <span style="color: var(--text-secondary); font-size: 11px; margin-top: 2px;">Uploader: ${ev.uploader || 'Unknown'} (${ev.platform})</span>
                        </div>
                        <span style="color: ${scoreClr}; font-weight: 700;">${simPercent}% Similarity</span>
                    `;
                    this.verifyDetailEvidence.appendChild(row);
                });
            }
        }
        
        // Populate Notes Timeline
        if (this.verifyDetailNotesTimeline) {
            this.verifyDetailNotesTimeline.innerHTML = "";
            if (rec.notes.length === 0) {
                this.verifyDetailNotesTimeline.innerHTML = `<div style="font-size: 13px; color: var(--text-muted); text-align: center; padding: 24px;"><i class="fa-solid fa-note-sticky"></i> No activity notes recorded.</div>`;
            } else {
                rec.notes.forEach(n => {
                    const block = document.createElement("div");
                    block.style.background = "rgba(255,255,255,0.02)";
                    block.style.padding = "12px";
                    block.style.borderRadius = "6px";
                    block.style.border = "1px solid var(--border-light)";
                    
                    const stamp = new Date(n.created_at).toLocaleString();
                    block.innerHTML = `
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                            <span style="color: var(--accent); font-weight: 600;">${n.username}</span>
                            <span>${stamp}</span>
                        </div>
                        <div style="font-size: 13px; color: white; line-height: 1.4;">${n.note}</div>
                    `;
                    this.verifyDetailNotesTimeline.appendChild(block);
                });
            }
        }
    }

    openApproveModal(record) {
        if (!this.modalVerifyApprove) return;
        this.modalVerifyApprove.style.display = "flex";
        document.getElementById("verify-approve-record-id").value = record.id;
        document.getElementById("verify-approve-meta-check").checked = false;
        document.getElementById("verify-approve-hash-check").checked = false;
        document.getElementById("verify-approve-notes").value = "";
    }

    openRejectModal(record) {
        if (!this.modalVerifyReject) return;
        this.modalVerifyReject.style.display = "flex";
        document.getElementById("verify-reject-record-id").value = record.id;
        document.getElementById("verify-reject-notes").value = "";
    }

    openAddNoteModal(record) {
        if (!this.modalVerifyAddNote) return;
        this.modalVerifyAddNote.style.display = "flex";
        document.getElementById("verify-note-record-id").value = record.id;
        document.getElementById("verify-note-text").value = "";
    }

    async handleApproveSubmit(e) {
        e.preventDefault();
        const id = document.getElementById("verify-approve-record-id").value;
        const notes = document.getElementById("verify-approve-notes").value;
        
        try {
            const res = await this.authFetch(`/api/v1/verification/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    status: "Verified",
                    metadata_validation: "Verified",
                    hash_verification: "Verified",
                    reviewer_id: this.getCurrentUserId(),
                    reviewer_notes: notes || "Verification checked and approved by reviewer."
                })
            });
            
            if (res.ok) {
                this.showToast("Verification case successfully approved and signed.", "success");
                if (this.modalVerifyApprove) this.modalVerifyApprove.style.display = "none";
                this.loadVerificationCenter();
            } else {
                const data = await res.json();
                this.showToast(data.detail || "Approval submit failed.", "danger");
            }
        } catch (err) {
            this.showToast(err.message, "danger");
        }
    }

    async handleRejectSubmit(e) {
        e.preventDefault();
        const id = document.getElementById("verify-reject-record-id").value;
        const notes = document.getElementById("verify-reject-notes").value;
        
        try {
            const res = await this.authFetch(`/api/v1/verification/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    status: "Rejected",
                    metadata_validation: "Failed",
                    hash_verification: "Failed",
                    reviewer_id: this.getCurrentUserId(),
                    reviewer_notes: notes
                })
            });
            
            if (res.ok) {
                this.showToast("Verification case successfully rejected.", "warning");
                if (this.modalVerifyReject) this.modalVerifyReject.style.display = "none";
                this.loadVerificationCenter();
            } else {
                const data = await res.json();
                this.showToast(data.detail || "Rejection submit failed.", "danger");
            }
        } catch (err) {
            this.showToast(err.message, "danger");
        }
    }

    async handleNoteSubmit(e) {
        e.preventDefault();
        const id = document.getElementById("verify-note-record-id").value;
        const notes = document.getElementById("verify-note-text").value;
        
        try {
            const res = await this.authFetch(`/api/v1/verification/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reviewer_notes: notes
                })
            });
            
            if (res.ok) {
                this.showToast("Reviewer note added to timeline.", "success");
                if (this.modalVerifyAddNote) this.modalVerifyAddNote.style.display = "none";
                
                // Reload verification detail view specifically
                const refreshRes = await this.authFetch("/api/v1/verification");
                if (refreshRes.ok) {
                    const records = await refreshRes.json();
                    const updated = records.find(r => r.id === parseInt(id));
                    if (updated) {
                        this.showVerificationDetails(updated);
                    }
                }
            } else {
                const data = await res.json();
                this.showToast(data.detail || "Add note failed.", "danger");
            }
        } catch (err) {
            this.showToast(err.message, "danger");
        }
    }

    async deleteVerificationRecord(id) {
        if (!confirm("Are you sure you want to delete this verification record? This action cannot be undone.")) return;
        try {
            const res = await this.authFetch(`/api/v1/verification/${id}`, { method: "DELETE" });
            if (res.ok) {
                this.showToast("Verification record deleted successfully.", "success");
                this.loadVerificationCenter();
            } else {
                this.showToast("Failed to delete verification record.", "danger");
            }
        } catch (err) {
            this.showToast("Network error trying to delete verification record.", "danger");
        }
    }
}

// Instantiate application on DOM content load
document.addEventListener("DOMContentLoaded", () => {
    window.app = new CopyrightDefenderApp();
});
