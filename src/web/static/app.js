document.addEventListener('DOMContentLoaded', () => {
  const logInput = document.getElementById('logInput');
  const providerSelect = document.getElementById('providerSelect');
  const apiKeyGroup = document.getElementById('apiKeyGroup');
  const apiKeyInput = document.getElementById('apiKeyInput');
  const modelInput = document.getElementById('modelInput');
  const summarizeBtn = document.getElementById('summarizeBtn');
  const clearBtn = document.getElementById('clearBtn');
  const presetContainer = document.getElementById('presetContainer');
  const fileUploadInput = document.getElementById('fileUploadInput');

  // Diagnostics elements
  const resultsContainer = document.getElementById('resultsContainer');
  const emptyState = document.getElementById('emptyState');
  const errorBadge = document.getElementById('errorBadge');
  const metricCategory = document.getElementById('metricCategory');
  const metricConfidence = document.getElementById('metricConfidence');
  const metricReduction = document.getElementById('metricReduction');
  const metricLatency = document.getElementById('metricLatency');
  const execSummary = document.getElementById('execSummary');
  const failingStep = document.getElementById('failingStep');
  const rootCause = document.getElementById('rootCause');
  const compTags = document.getElementById('compTags');
  const fixList = document.getElementById('fixList');
  const codeBox = document.getElementById('codeBox');
  const codePatchContainer = document.getElementById('codePatchContainer');
  const copyCodeBtn = document.getElementById('copyCodeBtn');

  // Tab views
  const tabVisual = document.getElementById('tabVisual');
  const tabMarkdown = document.getElementById('tabMarkdown');
  const tabJson = document.getElementById('tabJson');
  const viewVisual = document.getElementById('viewVisual');
  const viewMarkdown = document.getElementById('viewMarkdown');
  const viewJson = document.getElementById('viewJson');
  const markdownText = document.getElementById('markdownText');
  const jsonText = document.getElementById('jsonText');
  const copyMarkdownBtn = document.getElementById('copyMarkdownBtn');

  let currentMarkdown = "";
  let currentJson = "";

  // Show/hide API key input based on provider
  providerSelect.addEventListener('change', () => {
    const val = providerSelect.value;
    if (val === 'offline') {
      apiKeyGroup.style.display = 'none';
      modelInput.value = 'offline-rules';
    } else if (val === 'gemini') {
      apiKeyGroup.style.display = 'flex';
      modelInput.value = 'gemini-1.5-flash';
    } else if (val === 'openai') {
      apiKeyGroup.style.display = 'flex';
      modelInput.value = 'gpt-4o-mini';
    } else if (val === 'ollama') {
      apiKeyGroup.style.display = 'none';
      modelInput.value = 'llama3';
    }
  });

  // Load presets from server
  fetch('/api/presets')
    .then(r => r.json())
    .then(data => {
      if (data.presets && data.presets.length > 0) {
        data.presets.forEach((preset, idx) => {
          const btn = document.createElement('button');
          btn.className = 'preset-btn';
          btn.textContent = preset.name;
          btn.addEventListener('click', () => {
            logInput.value = preset.content;
            triggerSummarize();
          });
          presetContainer.appendChild(btn);

          // Auto-load the first preset into input
          if (idx === 0 && !logInput.value) {
            logInput.value = preset.content;
          }
        });
      }
    })
    .catch(err => console.error("Could not fetch presets:", err));

  // File Upload
  fileUploadInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        logInput.value = event.target.result;
      };
      reader.readAsText(file);
    }
  });

  clearBtn.addEventListener('click', () => {
    logInput.value = '';
    emptyState.style.display = 'block';
    resultsContainer.style.display = 'none';
  });

  function triggerSummarize() {
    const text = logInput.value.trim();
    if (!text) {
      alert("Please paste a build/error log or select a preset.");
      return;
    }

    summarizeBtn.disabled = true;
    summarizeBtn.textContent = "Analyzing Log...";

    const payload = {
      log_text: text,
      provider: providerSelect.value,
      api_key: apiKeyInput.value.trim() || null,
      model: modelInput.value.trim() || null
    };

    fetch('/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(r => r.json())
      .then(res => {
        summarizeBtn.disabled = false;
        summarizeBtn.textContent = "⚡ Summarize Log";

        if (res.status === 'success') {
          renderResults(res.data, res.markdown);
        } else {
          alert("Error analyzing log: " + (res.message || "Unknown error"));
        }
      })
      .catch(err => {
        summarizeBtn.disabled = false;
        summarizeBtn.textContent = "⚡ Summarize Log";
        alert("Failed to contact server: " + err);
      });
  }

  summarizeBtn.addEventListener('click', triggerSummarize);

  function renderResults(data, markdown) {
    emptyState.style.display = 'none';
    resultsContainer.style.display = 'flex';

    currentMarkdown = markdown;
    currentJson = JSON.stringify(data, null, 2);

    errorBadge.textContent = data.error_category;
    metricCategory.textContent = data.error_category;
    metricConfidence.textContent = `${Math.round(data.confidence_score * 100)}%`;
    metricReduction.textContent = `${data.compression_ratio_percent}%`;
    metricLatency.textContent = `${data.total_latency_ms}ms`;

    execSummary.textContent = data.executive_summary;
    failingStep.textContent = data.failing_step;
    rootCause.textContent = data.root_cause;

    // Affected Components
    compTags.innerHTML = '';
    if (data.affected_components && data.affected_components.length > 0) {
      data.affected_components.forEach(comp => {
        const span = document.createElement('span');
        span.className = 'comp-tag';
        span.textContent = comp;
        compTags.appendChild(span);
      });
    } else {
      compTags.innerHTML = '<span class="text-muted">None specified</span>';
    }

    // Fixes
    fixList.innerHTML = '';
    if (data.suggested_fixes && data.suggested_fixes.length > 0) {
      data.suggested_fixes.forEach(fix => {
        const li = document.createElement('li');
        li.textContent = fix;
        fixList.appendChild(li);
      });
    }

    // Code patch
    if (data.code_patch) {
      codePatchContainer.style.display = 'block';
      codeBox.textContent = data.code_patch;
    } else {
      codePatchContainer.style.display = 'none';
    }

    markdownText.value = currentMarkdown;
    jsonText.value = currentJson;
  }

  // Tabs switching
  tabVisual.addEventListener('click', () => {
    tabVisual.classList.add('active');
    tabMarkdown.classList.remove('active');
    tabJson.classList.remove('active');
    viewVisual.style.display = 'flex';
    viewMarkdown.style.display = 'none';
    viewJson.style.display = 'none';
  });

  tabMarkdown.addEventListener('click', () => {
    tabVisual.classList.remove('active');
    tabMarkdown.classList.add('active');
    tabJson.classList.remove('active');
    viewVisual.style.display = 'none';
    viewMarkdown.style.display = 'block';
    viewJson.style.display = 'none';
  });

  tabJson.addEventListener('click', () => {
    tabVisual.classList.remove('active');
    tabMarkdown.classList.remove('active');
    tabJson.classList.add('active');
    viewVisual.style.display = 'none';
    viewMarkdown.style.display = 'none';
    viewJson.style.display = 'block';
  });

  copyCodeBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(codeBox.textContent);
    copyCodeBtn.textContent = 'Copied!';
    setTimeout(() => { copyCodeBtn.textContent = 'Copy Patch'; }, 2000);
  });

  copyMarkdownBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(currentMarkdown);
    copyMarkdownBtn.textContent = 'Copied PR Comment!';
    setTimeout(() => { copyMarkdownBtn.textContent = '📋 Copy PR Comment'; }, 2000);
  });
});

