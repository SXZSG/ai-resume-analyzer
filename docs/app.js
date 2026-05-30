const apiBaseInput = document.getElementById("apiBase");
const saveApiButton = document.getElementById("saveApi");
const resumeFileInput = document.getElementById("resumeFile");
const fileName = document.getElementById("fileName");
const jobDescriptionInput = document.getElementById("jobDescription");
const analyzeButton = document.getElementById("analyzeBtn");
const message = document.getElementById("message");
const statusPill = document.getElementById("statusPill");

const storageKey = "ai-resume-analyzer-api-base";

function init() {
  const savedApiBase = localStorage.getItem(storageKey);
  if (savedApiBase) {
    apiBaseInput.value = savedApiBase;
  }

  saveApiButton.addEventListener("click", saveApiBase);
  resumeFileInput.addEventListener("change", handleFileChange);
  analyzeButton.addEventListener("click", analyzeResume);
}

function saveApiBase() {
  const value = normalizeApiBase(apiBaseInput.value);
  apiBaseInput.value = value;
  localStorage.setItem(storageKey, value);
  setMessage("API 地址已保存。");
}

function handleFileChange() {
  const file = resumeFileInput.files[0];
  fileName.textContent = file ? file.name : "选择 PDF 简历";
}

async function analyzeResume() {
  const apiBase = normalizeApiBase(apiBaseInput.value);
  const file = resumeFileInput.files[0];
  const jobDescription = jobDescriptionInput.value.trim();

  if (!file) {
    setMessage("请先选择 PDF 简历。", true);
    return;
  }
  if (!jobDescription) {
    setMessage("请填写岗位 JD。", true);
    return;
  }

  localStorage.setItem(storageKey, apiBase);
  apiBaseInput.value = apiBase;

  const formData = new FormData();
  formData.append("resume", file);
  formData.append("job_description", jobDescription);

  setLoading(true);
  setMessage("正在解析 PDF 并计算匹配度...");

  try {
    const response = await fetch(`${apiBase}/api/analyze`, {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    if (!response.ok || !result.success) {
      throw new Error(result.message || "分析失败。");
    }

    renderResult(result);
    setStatus(result.cached ? "命中缓存" : "分析完成", "ready");
    setMessage(result.cached ? "已从缓存读取结果。" : "分析完成。");
  } catch (error) {
    setStatus("分析失败", "error");
    setMessage(error.message || "服务不可用，请检查 API 地址和后端状态。", true);
  } finally {
    setLoading(false);
  }
}

function renderResult(result) {
  const data = result.data || {};
  const basicInfo = data.basic_info || {};
  const jobIntention = data.job_intention || {};
  const background = data.background || {};
  const match = data.match_result || {};

  setText("overallScore", formatScore(match.overall_score));
  setText("skillScore", formatScore(match.skill_score));
  setText("experienceScore", formatScore(match.experience_score));
  setText("educationScore", formatScore(match.education_score));
  setText("summaryText", match.summary || "--");

  setText("name", basicInfo.name || "--");
  setText("phone", basicInfo.phone || "--");
  setText("email", basicInfo.email || "--");
  setText("address", basicInfo.address || "--");
  setText("position", jobIntention.position || "--");
  setText("education", background.education || "--");
  setText("workYears", background.work_years || "--");

  renderTags("skills", background.skills || []);
  renderList("projects", background.projects || []);
  renderTags("matchedKeywords", match.matched_keywords || []);
  renderTags("missingKeywords", match.missing_keywords || []);
  renderList("advantages", match.advantages || []);
  renderList("risks", match.risks || []);

  document.getElementById("jsonOutput").textContent = JSON.stringify(result, null, 2);
}

function renderTags(id, values) {
  const element = document.getElementById(id);
  element.innerHTML = "";
  values.forEach((value) => {
    const tag = document.createElement("span");
    tag.textContent = value;
    element.appendChild(tag);
  });
}

function renderList(id, values) {
  const element = document.getElementById(id);
  element.innerHTML = "";
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    element.appendChild(item);
  });
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function setMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function setStatus(text, variant = "") {
  statusPill.textContent = text;
  statusPill.className = `status-pill ${variant}`.trim();
}

function setLoading(isLoading) {
  analyzeButton.disabled = isLoading;
  analyzeButton.innerHTML = isLoading
    ? '<span class="button-icon">…</span>分析中'
    : '<span class="button-icon">▶</span>开始分析';
}

function normalizeApiBase(value) {
  return (value || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
}

function formatScore(value) {
  if (value === 0) {
    return "0";
  }
  return value ? String(value) : "--";
}

init();
