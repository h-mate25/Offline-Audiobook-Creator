const form = document.querySelector("#jobForm");
const fileInput = document.querySelector("#fileInput");
const fileLabel = document.querySelector("#fileLabel");
const fileDrop = document.querySelector("#fileDrop");
const pathField = document.querySelector("#pathField");
const localPath = document.querySelector("#localPath");
const language = document.querySelector("#language");
const voice = document.querySelector("#voice");
const normalizer = document.querySelector("#normalizer");
const normalizerStatus = document.querySelector("#normalizerStatus");
const guideButton = document.querySelector("#guideButton");
const guideModal = document.querySelector("#guideModal");
const closeGuideButton = document.querySelector("#closeGuide");
const sourcePanel = document.querySelector("[data-wizard-step='1']");
const voicePanel = document.querySelector("[data-wizard-step='2']");
const editorPanel = document.querySelector("#editorPanel");
const runPanel = document.querySelector("[data-wizard-step='4']");
const logPanel = document.querySelector("#logPanel");
const editor = document.querySelector("#editor");
const loadPreviewButton = document.querySelector("#loadPreview");
const audioPreviewButton = document.querySelector("#audioPreview");
const audioPreviewAudio = document.querySelector("#audioPreviewAudio");
const audioPreviewDownload = document.querySelector("#audioPreviewDownload");
const audioPreviewStatus = document.querySelector("#audioPreviewStatus");
const voiceTestButton = document.querySelector("#voiceTest");
const voiceTestSentence = document.querySelector("#voiceTestSentence");
const voiceTestAudio = document.querySelector("#voiceTestAudio");
const voiceTestStatus = document.querySelector("#voiceTestStatus");
const previewStatus = document.querySelector("#previewStatus");
const charCount = document.querySelector("#charCount");
const chunkCount = document.querySelector("#chunkCount");
const logBox = document.querySelector("#logBox");
const progressBar = document.querySelector("#progressBar");
const progressText = document.querySelector("#progressText");
const progressCount = document.querySelector("#progressCount");
const downloadLink = document.querySelector("#downloadLink");
const wizardPanels = [...document.querySelectorAll(".wizard-panel")];
const actionButtons = [...document.querySelectorAll(".action")];

const sliders = {
  sentenceSilence: document.querySelector("#sentenceSilence"),
  lengthScale: document.querySelector("#lengthScale"),
  maxChars: document.querySelector("#maxChars"),
};

const outputs = {
  sentenceSilence: document.querySelector("#sentenceSilenceValue"),
  lengthScale: document.querySelector("#lengthScaleValue"),
  maxChars: document.querySelector("#maxCharsValue"),
};

const presets = {
  natural: { sentenceSilence: 0.18, lengthScale: 1.07, maxChars: 1200, noiseScale: 0.28, noiseWScale: 0.11 },
  calm: { sentenceSilence: 0.36, lengthScale: 1.16, maxChars: 1000, noiseScale: 0.25, noiseWScale: 0.12 },
  compact: { sentenceSilence: 0.12, lengthScale: 0.98, maxChars: 1450, noiseScale: 0.25, noiseWScale: 0.12 },
};

let voices = [];
let activeJob = null;
let activeJobKind = "";
let pollTimer = null;
let sourcePath = "";
let previewReady = false;
let currentStep = 1;

init();

async function init() {
  bindEvents();
  updateSliderLabels();
  showStep(1);

  try {
    const response = await fetch("/api/settings", { cache: "no-store" });
    const settings = await response.json();
    voices = settings.voices || [];
    populateVoices();
    configureNormalizer(settings.normalization || {});
  } catch (error) {
    normalizerStatus.textContent = "A helyi szolgáltatás nem érhető el.";
  }
}

function configureNormalizer(status) {
  const nemoOption = normalizer.querySelector("option[value='nemo']");
  if (status.available) {
    nemoOption.disabled = false;
    normalizerStatus.textContent = "NeMo elérhető; az Automatikus mód ezt választja.";
    return;
  }

  nemoOption.disabled = true;
  if (normalizer.value === "nemo") normalizer.value = "auto";
  normalizerStatus.textContent = "NeMo nincs telepítve; az Automatikus mód helyi szabályokra vált.";
}

function bindEvents() {
  document.querySelectorAll("input[name='source_mode']").forEach((input) => {
    input.addEventListener("change", () => {
      const pathMode = input.value === "path" && input.checked;
      pathField.classList.toggle("is-hidden", !pathMode);
      fileDrop.classList.toggle("is-hidden", pathMode);
      resetPreview();
    });
  });

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    fileLabel.textContent = file ? file.name : "Válassz dokumentumot";
    resetPreview();
  });

  language.addEventListener("change", populateVoices);

  Object.values(sliders).forEach((slider) => {
    slider.addEventListener("input", updateSliderLabels);
  });

  document.querySelectorAll(".preset").forEach((button) => {
    button.addEventListener("click", () => applyPreset(button.dataset.preset));
  });

  document.querySelectorAll("[data-pause]").forEach((button) => {
    button.addEventListener("click", () => insertPause(button.dataset.pause));
  });

  guideButton.addEventListener("click", () => setGuideOpen(true));
  closeGuideButton.addEventListener("click", () => setGuideOpen(false));
  guideModal.addEventListener("click", (event) => {
    if (event.target === guideModal) setGuideOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !guideModal.classList.contains("is-hidden")) {
      setGuideOpen(false);
    }
  });

  loadPreviewButton.addEventListener("click", async () => {
    const loaded = await loadTextPreview();
    if (loaded) showStep(2);
  });
  voiceTestButton.addEventListener("click", runVoiceTest);
  audioPreviewButton.addEventListener("click", () => submitAudioJob("audio-preview"));
  document.querySelector("#toText").addEventListener("click", () => showStep(3));
  document.querySelector("#toGeneration").addEventListener("click", () => showStep(4));
  document.querySelector("#backToSource").addEventListener("click", () => showStep(1));
  document.querySelector("#backToVoice").addEventListener("click", () => showStep(2));
  document.querySelector("#backToText").addEventListener("click", () => showStep(3));

  editor.addEventListener("input", updateEditorStats);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAudioJob("full");
  });
}

function setGuideOpen(isOpen) {
  guideModal.classList.toggle("is-hidden", !isOpen);
  guideModal.setAttribute("aria-hidden", String(!isOpen));
  document.body.classList.toggle("modal-open", isOpen);
  if (isOpen) closeGuideButton.focus();
  else guideButton.focus();
}

function showStep(step) {
  currentStep = step;
  wizardPanels.forEach((panel) => {
    panel.classList.toggle("is-hidden", Number(panel.dataset.wizardStep) !== step);
  });
  document.querySelectorAll("[data-step-indicator]").forEach((indicator) => {
    const indicatorStep = Number(indicator.dataset.stepIndicator);
    indicator.classList.toggle("is-active", indicatorStep === step);
    indicator.classList.toggle("is-done", indicatorStep < step);
  });
}

function populateVoices() {
  const selectedLanguage = language.value;
  const matching = voices.filter((item) => !item.language || item.language === selectedLanguage);
  voice.innerHTML = "";

  for (const item of matching.length ? matching : voices) {
    const option = document.createElement("option");
    option.value = item.path;
    option.textContent = item.name;
    voice.append(option);
  }
}

function applyPreset(name) {
  const preset = presets[name];
  if (!preset) return;

  sliders.sentenceSilence.value = preset.sentenceSilence;
  sliders.lengthScale.value = preset.lengthScale;
  sliders.maxChars.value = preset.maxChars;
  document.querySelector("#noiseScale").value = preset.noiseScale;
  document.querySelector("#noiseWScale").value = preset.noiseWScale;
  document.querySelectorAll(".preset").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.preset === name);
  });
  updateSliderLabels();
}

function updateSliderLabels() {
  outputs.sentenceSilence.textContent = `${Number(sliders.sentenceSilence.value).toFixed(2)}s`;
  outputs.lengthScale.textContent = Number(sliders.lengthScale.value).toFixed(2);
  outputs.maxChars.textContent = sliders.maxChars.value;
}

async function loadTextPreview() {
  const data = buildSourceFormData();
  if (!data) return false;

  setBusy(true);
  progressText.textContent = "Szöveg előkészítése...";
  logBox.textContent = "A dokumentum szövegének tisztítása...";

  try {
    const response = await fetch("/api/preview", { method: "POST", body: data });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Nem sikerült előkészíteni a szöveget.");
    }
    const result = await response.json();
    sourcePath = result.sourcePath;
    editor.value = result.text;
    previewReady = true;
    previewStatus.textContent = `${result.inputName} · szerkeszthető előnézet`;
    charCount.textContent = result.characters;
    chunkCount.textContent = result.chunks;
    logBox.textContent = `Forrás betöltve: ${result.characters} karakter, ${result.chunks} feldolgozási darab.`;
    progressText.textContent = "Forrás kész";
    loadPreviewButton.textContent = "Forrás frissítése";
    return true;
  } catch (error) {
    previewReady = false;
    logBoxPanel();
    logBox.textContent = error.message;
    progressText.textContent = "Hiba";
    return false;
  } finally {
    setBusy(false);
  }
}

function buildSourceFormData() {
  const sourceMode = document.querySelector("input[name='source_mode']:checked").value;
  const data = new FormData();
  data.append("source_mode", sourceMode);

  if (sourceMode === "path") {
    if (!localPath.value.trim()) {
      logBoxPanel();
      logBox.textContent = "Adj meg egy helyi fájlútvonalat.";
      progressText.textContent = "Hiányzó forrás";
      return null;
    }
    data.append("local_path", localPath.value);
  } else {
    const file = fileInput.files[0];
    if (!file) {
      logBoxPanel();
      logBox.textContent = "Válassz ki egy dokumentumot.";
      progressText.textContent = "Hiányzó forrás";
      return null;
    }
    data.append("file", file);
  }
  return data;
}

async function runVoiceTest() {
  const sentence = voiceTestSentence.value.trim();
  if (!sentence) {
    voiceTestStatus.textContent = "Írj be egy tesztmondatot.";
    return;
  }
  await submitAudioJob("voice-test", sentence);
}

function insertPause(seconds) {
  if (!previewReady) {
    progressText.textContent = "Előbb töltsd be a forrást.";
    return;
  }
  const marker = ` [PAUSE:${seconds}] `;
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  editor.setRangeText(marker, start, end, "end");
  editor.focus();
  updateEditorStats();
}

function updateEditorStats() {
  const characters = editor.value.length;
  const estimatedChunks = Math.max(1, Math.ceil(characters / Number(sliders.maxChars.value)));
  charCount.textContent = characters;
  chunkCount.textContent = `~${estimatedChunks}`;
}

function resetPreview() {
  sourcePath = "";
  previewReady = false;
  voiceTestAudio.pause();
  voiceTestAudio.removeAttribute("src");
  voiceTestAudio.load();
  voiceTestAudio.classList.add("is-hidden");
  voiceTestStatus.textContent = "Még nincs hangminta.";
  audioPreviewAudio.pause();
  audioPreviewAudio.removeAttribute("src");
  audioPreviewAudio.load();
  audioPreviewAudio.classList.add("is-hidden");
  audioPreviewDownload.classList.add("is-hidden");
  audioPreviewStatus.textContent = "Még nincs dokumentum-hangminta.";
  editor.value = "";
  loadPreviewButton.textContent = "Fájl betöltése és tovább";
  showStep(1);
}

async function submitAudioJob(jobType, textOverride = null) {
  if (!previewReady) {
    const loaded = await loadTextPreview();
    if (!loaded) return;
  }

  const formData = new FormData(form);
  formData.set("source_mode", "path");
  formData.set("local_path", sourcePath);
  formData.delete("file");
  formData.set("edited_text", textOverride ?? editor.value);
  formData.set("job_type", jobType);
  formData.set("force", document.querySelector("#force").checked ? "true" : "false");

  activeJobKind = jobType;
  setBusy(true);
  logBoxPanel();
  downloadLink.classList.add("is-hidden");
  if (jobType === "audio-preview") {
    audioPreviewAudio.pause();
    audioPreviewAudio.classList.add("is-hidden");
    audioPreviewDownload.classList.add("is-hidden");
    audioPreviewStatus.textContent = "Dokumentum-hangminta készül...";
  }
  logBox.textContent = "Indítás...";
  progressText.textContent = jobType === "voice-test" ? "Hangminta készül..." : "Sorba állítva";
  progressCount.textContent = "0 / 0";
  progressBar.style.width = "0%";
  if (jobType === "voice-test") {
    voiceTestAudio.pause();
    voiceTestAudio.classList.add("is-hidden");
    voiceTestStatus.textContent = "Hangminta készül...";
  }

  try {
    const response = await fetch("/api/jobs", { method: "POST", body: formData });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Nem sikerült elindítani a munkát.");
    }
    const data = await response.json();
    activeJob = data.jobId;
    startPolling();
  } catch (error) {
    setBusy(false);
    logBox.textContent = error.message;
    progressText.textContent = "Hiba";
    if (jobType === "voice-test") voiceTestStatus.textContent = "A hangminta nem készült el.";
    if (jobType === "audio-preview") audioPreviewStatus.textContent = "A dokumentum-hangminta nem készült el.";
  }
}

function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(pollJob, 900);
  pollJob();
}

async function pollJob() {
  if (!activeJob) return;
  try {
    const response = await fetch(`/api/jobs/${activeJob}`, { cache: "no-store" });
    const job = await response.json();
    renderJob(job);
    if (job.status === "done" || job.status === "failed") {
      clearInterval(pollTimer);
      setBusy(false);
    }
  } catch (error) {
    clearInterval(pollTimer);
    setBusy(false);
    progressText.textContent = "Kapcsolati hiba";
  }
}

function renderJob(job) {
  const total = job.total || 0;
  const current = job.current || 0;
  const percent = total ? Math.round((current / total) * 100) : 0;

  progressBar.style.width = `${percent}%`;
  progressText.textContent = job.status === "failed" ? "Hiba" : job.message || job.status;
  progressCount.textContent = `${current} / ${total}`;
  logBox.textContent = (job.logs || []).join("\n") || job.message || "Fut...";
  logBox.scrollTop = logBox.scrollHeight;

  if (job.status === "failed") {
    logBox.textContent += `\n\n${job.error || "Ismeretlen hiba."}`;
  }

  if (job.status === "done" && job.downloadReady) {
    const downloadUrl = `/api/jobs/${job.id}/download?t=${Date.now()}`;
    if (activeJobKind === "voice-test") {
      voiceTestAudio.src = downloadUrl;
      voiceTestAudio.classList.remove("is-hidden");
      voiceTestStatus.textContent = "Hangminta kész. Lejátszhatod itt.";
    } else if (activeJobKind === "audio-preview") {
      audioPreviewAudio.src = downloadUrl;
      audioPreviewAudio.classList.remove("is-hidden");
      audioPreviewDownload.href = downloadUrl;
      audioPreviewDownload.classList.remove("is-hidden");
      audioPreviewStatus.textContent = "Dokumentum-hangminta kész. Lejátszhatod vagy letöltheted itt.";
    } else {
      downloadLink.href = downloadUrl;
      downloadLink.textContent = "MP3 letöltése";
      downloadLink.classList.remove("is-hidden");
    }
  }
}

function logBoxPanel() {
  logPanel.classList.remove("is-hidden");
}

function setBusy(isBusy) {
  actionButtons.forEach((button) => {
    button.disabled = isBusy;
  });
}

