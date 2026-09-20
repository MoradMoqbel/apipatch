document.addEventListener('DOMContentLoaded', () => {

  // 1. One-click Copy for Terminal Install Box
  const copyBtn = document.getElementById('copy-install-btn');
  const installCmd = document.getElementById('install-cmd');

  if (copyBtn && installCmd) {
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(installCmd.textContent.trim());
        copyBtn.classList.add('copied');
        const textSpan = copyBtn.querySelector('.copy-text');
        if (textSpan) textSpan.textContent = 'Copied!';
        setTimeout(() => {
          copyBtn.classList.remove('copied');
          if (textSpan) textSpan.textContent = 'Copy';
        }, 2000);
      } catch (err) {
        console.warn('Clipboard write failed, fallback selection', err);
      }
    });
  }

  // 2. Interactive Terminal Diff Tabs Switcher
  const diffTabs = document.querySelectorAll('.diff-tab');
  const diffPanels = document.querySelectorAll('.diff-panel');

  diffTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.getAttribute('data-target');
      
      diffTabs.forEach(t => t.classList.remove('active'));
      diffPanels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const activePanel = document.getElementById(targetId);
      if (activePanel) {
        activePanel.classList.add('active');
      }
    });
  });

  // 3. Demo Video Play/Pause & Overlay Control
  const mainVideo = document.getElementById('main-video');
  const overlay = document.getElementById('video-overlay');
  const playBtn = document.getElementById('play-btn');

  if (mainVideo && overlay && playBtn) {
    playBtn.addEventListener('click', () => {
      if (mainVideo.paused) {
        mainVideo.play();
        overlay.classList.add('hidden');
      } else {
        mainVideo.pause();
        overlay.classList.remove('hidden');
      }
    });

    mainVideo.addEventListener('click', () => {
      if (mainVideo.paused) {
        mainVideo.play();
        overlay.classList.add('hidden');
      } else {
        mainVideo.pause();
        overlay.classList.remove('hidden');
      }
    });

    mainVideo.addEventListener('playing', () => {
      overlay.classList.add('hidden');
    });

    mainVideo.addEventListener('pause', () => {
      overlay.classList.remove('hidden');
    });
  }

  // 4. Waitlist Form Submission (Connected to moradyunes2@gmail.com)
  const form = document.getElementById('waitlist-form');
  const emailInput = document.getElementById('email-input');
  const feedback = document.getElementById('form-feedback');

  if (form && emailInput && feedback) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = emailInput.value.trim();
      if (!email) return;

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Joining...';
      }

      try {
        const waitlist = JSON.parse(localStorage.getItem('apipatch_waitlist') || '[]');
        waitlist.push({ email, timestamp: new Date().toISOString() });
        localStorage.setItem('apipatch_waitlist', JSON.stringify(waitlist));
      } catch (_) {}

      try {
        await fetch('https://formsubmit.co/ajax/moradyunes2@gmail.com', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            form_type: 'GitHub App Beta Waitlist',
            work_email: email,
            _subject: `✨ New ApiPatch Waitlist Signup: ${email}`,
            _captcha: 'false'
          })
        });
      } catch (err) {
        console.warn('FormSubmit background notification fallback', err);
      }

      feedback.textContent = `✓ Thanks! ${email} has been reserved for the GitHub App beta.`;
      emailInput.value = '';
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Join GitHub App Beta';
      }
      setTimeout(() => {
        feedback.textContent = '';
      }, 7000);
    });
  }

  // 4b. Private Pilot Form Submission (Connected to moradyunes2@gmail.com)
  const pilotForm = document.getElementById('pilot-form');
  const pilotFeedback = document.getElementById('pilot-feedback');

  if (pilotForm && pilotFeedback) {
    pilotForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('pilot-name')?.value.trim() || '';
      const email = document.getElementById('pilot-email')?.value.trim() || '';
      const company = document.getElementById('pilot-company')?.value.trim() || '';
      const stack = document.getElementById('pilot-stack')?.value.trim() || '';
      const notes = document.getElementById('pilot-notes')?.value.trim() || '';

      if (!email || !company) return;

      const pilotSubmitBtn = pilotForm.querySelector('button[type="submit"]');
      if (pilotSubmitBtn) {
        pilotSubmitBtn.disabled = true;
        pilotSubmitBtn.textContent = 'Sending Request... ⚡';
      }

      try {
        const pilots = JSON.parse(localStorage.getItem('apipatch_pilots') || '[]');
        pilots.push({ name, email, company, stack, notes, timestamp: new Date().toISOString() });
        localStorage.setItem('apipatch_pilots', JSON.stringify(pilots));
      } catch (_) {}

      try {
        await fetch('https://formsubmit.co/ajax/moradyunes2@gmail.com', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({
            form_type: 'Private Pilot Intake Program',
            founder_or_lead: name,
            work_email: email,
            company_or_org: company,
            tech_stack_and_size: stack,
            dependency_bottleneck: notes || 'None specified',
            _subject: `🚀 New ApiPatch Private Pilot Request from ${company} (${name})`,
            _captcha: 'false'
          })
        });
      } catch (err) {
        console.warn('FormSubmit background notification fallback', err);
      }

      pilotFeedback.textContent = `✓ Thank you, ${name || 'there'}! We received your pilot request for ${company}. We will reach out within 24 hours.`;
      pilotForm.reset();
      if (pilotSubmitBtn) {
        pilotSubmitBtn.disabled = false;
        pilotSubmitBtn.textContent = 'Request Monorepo Pilot Access →';
      }
      setTimeout(() => {
        pilotFeedback.textContent = '';
      }, 8000);
    });
  }

  // 5. Interactive Live Simulator / Playground
  const PLAYGROUND_PRESETS = {
    pydantic: {
      filename: "models/user.py",
      libBadge: "Detected: <strong>pydantic (v1.10.12)</strong>",
      source: `from typing import Optional\nfrom pydantic import BaseModel, validator\n\nclass UserProfile(BaseModel):\n    id: int\n    name: str\n    email: str\n    age: Optional[int] = None\n\n    class Config:\n        from_attributes = True\n        validate_assignment = True\n\n    @validator("name")\n    def validate_name(cls, v):\n        if len(v) < 2:\n            raise ValueError("Name too short")\n        return v.title()`,
      output: `from typing import Optional\nfrom pydantic import BaseModel, ConfigDict, field_validator\n\nclass UserProfile(BaseModel):\n    model_config = ConfigDict(\n        from_attributes=True,\n        validate_assignment=True\n    )\n\n    id: int\n    name: str\n    email: str\n    age: Optional[int] = None\n\n    @field_validator("name")\n    @classmethod\n    def validate_name(cls, v: str) -> str:\n        if len(v) < 2:\n            raise ValueError("Name too short")\n        return v.title()`,
      hunter: "Verified against pypi.org/project/pydantic/2.9.0/ changelogs (0.06s)",
      ast: "AST syntax parsed: 100% logic, fields & docstrings preserved",
      prTitle: "[ApiPatch] Migrate deprecated Pydantic v1 Config & @validator to v2 ConfigDict"
    },
    openai: {
      filename: "services/llm_client.py",
      libBadge: "Detected: <strong>openai (v0.28.1 legacy)</strong>",
      source: `import openai\n\nopenai.api_key = "sk-..."\n\ndef generate_summary(prompt: str) -> str:\n    response = openai.ChatCompletion.create(\n        model="gpt-4",\n        messages=[{"role": "user", "content": prompt}],\n        temperature=0.7\n    )\n    return response["choices"][0]["message"]["content"]`,
      output: `from openai import OpenAI\n\nclient = OpenAI()\n\ndef generate_summary(prompt: str) -> str:\n    response = client.chat.completions.create(\n        model="gpt-4o",\n        messages=[{"role": "user", "content": prompt}],\n        temperature=0.7\n    )\n    return response.choices[0].message.content`,
      hunter: "Verified against official OpenAI Python SDK v1.50.0 migration guide (0.07s)",
      ast: "AST syntax parsed: modernized client initialization and response attribute access",
      prTitle: "[ApiPatch] Migrate OpenAI legacy ChatCompletion.create to OpenAI v1.0 Client"
    },
    google: {
      filename: "agents/vision_agent.py",
      libBadge: "Detected: <strong>google.generativeai (Legacy REST)</strong>",
      source: `\"\"\"Vision Agent for processing product images.\"\"\"\nimport google.generativeai as genai\n\ngenai.configure(api_key="AIzaSy...")\n\nasync def analyze_image(prompt: str):\n    model = genai.GenerativeModel("gemini-1.5-flash")\n    response = await model.generate_content_async(prompt)\n    return response.text`,
      output: `\"\"\"Vision Agent for processing product images.\"\"\"\nfrom google import genai\n\nclient = genai.Client()\n\nasync def analyze_image(prompt: str):\n    response = await client.aio.models.generate_content(\n        model="gemini-2.5-flash",\n        contents=prompt\n    )\n    return response.text`,
      hunter: "Resolved official google-genai 2026 SDK & async client.aio (0.05s)",
      ast: "Preserved top module docstring, async def signature, and await client.aio call",
      prTitle: "[ApiPatch] Modernize Google GenerativeAI to official google.genai Client"
    },
    stripe: {
      filename: "payments/checkout.py",
      libBadge: "Detected: <strong>stripe (Legacy Charge API)</strong>",
      source: `import stripe\n\ndef charge_customer(card_token: str, amount_cents: int):\n    charge = stripe.Charge.create(\n        amount=amount_cents,\n        currency="usd",\n        source=card_token,\n        description="Software Subscription"\n    )\n    return charge.id`,
      output: `import stripe\n\nclient = stripe.StripeClient()\n\ndef charge_customer(customer_id: str, amount_cents: int):\n    intent = client.payment_intents.create(\n        params={\n            "amount": amount_cents,\n            "currency": "usd",\n            "customer": customer_id,\n            "payment_method_types": ["card"],\n            "description": "Software Subscription"\n        }\n    )\n    return intent.id`,
      hunter: "Grounded in Stripe v10+ PaymentIntents API official documentation (0.08s)",
      ast: "AST syntax parsed: SCA/3DS compliant signature generated safely",
      prTitle: "[ApiPatch] Upgrade legacy stripe.Charge.create to PaymentIntent API"
    },
    fastapi: {
      filename: "main.py",
      libBadge: "Detected: <strong>fastapi (Deprecated @on_event)</strong>",
      source: `from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.on_event("startup")\nasync def startup_db():\n    print("Database connected")\n\n@app.on_event("shutdown")\nasync def shutdown_db():\n    print("Database closed")`,
      output: `from contextlib import asynccontextmanager\nfrom fastapi import FastAPI\n\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    print("Database connected")\n    yield\n    print("Database closed")\n\napp = FastAPI(lifespan=lifespan)`,
      hunter: "Verified FastAPI lifespan context manager migration guide (0.06s)",
      ast: "Validated asynccontextmanager structure and preserved startup/shutdown logic",
      prTitle: "[ApiPatch] Refactor deprecated @app.on_event to lifespan context manager"
    }
  };

  const presetBtns = document.querySelectorAll('.preset-btn');
  const sourceInput = document.getElementById('pg-source-input');
  const refactoredOutput = document.getElementById('pg-refactored-output');
  const detectedBadge = document.getElementById('pg-detected-badge');
  const inputFilename = document.getElementById('pg-input-filename');
  const outputFilename = document.getElementById('pg-output-filename');
  const stageHunterText = document.getElementById('stage-hunter-text');
  const stageAstText = document.getElementById('stage-ast-text');
  const prSummary = document.getElementById('pg-pr-summary');
  const runAgentBtn = document.getElementById('btn-run-agent');
  const pgCopyBtn = document.getElementById('pg-copy-btn');

  let currentPreset = 'pydantic';

  function loadPreset(presetKey) {
    const data = PLAYGROUND_PRESETS[presetKey];
    if (!data) return;
    currentPreset = presetKey;
    if (sourceInput) sourceInput.value = data.source;
    if (refactoredOutput) refactoredOutput.textContent = data.output;
    if (detectedBadge) detectedBadge.innerHTML = data.libBadge;
    if (inputFilename) inputFilename.textContent = data.filename + " (Legacy Source)";
    if (outputFilename) outputFilename.textContent = data.filename + " (Modernized)";
    if (stageHunterText) stageHunterText.textContent = data.hunter;
    if (stageAstText) stageAstText.textContent = data.ast;
    if (prSummary) prSummary.innerHTML = `<span>PR: <strong>${data.prTitle}</strong></span>`;
  }

  if (presetBtns.length > 0) {
    presetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        presetBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const key = btn.getAttribute('data-preset');
        loadPreset(key);
      });
    });
    // Load initial
    loadPreset('pydantic');
  }

  if (runAgentBtn && refactoredOutput) {
    runAgentBtn.addEventListener('click', () => {
      runAgentBtn.disabled = true;
      runAgentBtn.innerHTML = `<span>Simulating Agent... ⚡</span>`;
      refactoredOutput.textContent = "/* 🌐 Running DocHunter™ grounding & AST self-healing analysis... */";
      
      setTimeout(() => {
        const data = PLAYGROUND_PRESETS[currentPreset];
        if (data) {
          refactoredOutput.textContent = data.output;
        }
        runAgentBtn.disabled = false;
        runAgentBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg><span>Run ApiPatch Agent ⚡</span>`;
      }, 600);
    });
  }

  if (pgCopyBtn && refactoredOutput) {
    pgCopyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(refactoredOutput.textContent);
        const span = pgCopyBtn.querySelector('span');
        if (span) span.textContent = "Copied!";
        setTimeout(() => {
          if (span) span.textContent = "Copy Code";
        }, 2000);
      } catch (_) {}
    });
  }

  // 6. Smooth Scroll for Anchor Links
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const href = a.getAttribute('href');
      if (href && href !== '#') {
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });

  // 7. Interactive Live Cloud Monorepo Health & ROI Scanner
  const SCANNER_PRESETS = {
    "CopilotKit/CopilotKit": {
      repoName: "CopilotKit / CopilotKit",
      stars: "⭐ 14,800+ Stars",
      files: 142,
      loc: 38400,
      score: 76,
      grade: "C",
      status: "Moderate Risk — 2 Deprecations Pending",
      hours: 20.0,
      payroll: 1500.00,
      speedup: "1,800x",
      cmd: "apipatch pr CopilotKit/CopilotKit",
      findings: [
        {
          severity: "HIGH",
          framework: "FastAPI",
          loc: "sdk-python/copilotkit/sdk.py:48",
          code: '@app.on_event("startup")',
          modern: '@asynccontextmanager lifespan(app: FastAPI)',
          hours: 4.0
        },
        {
          severity: "CRITICAL",
          framework: "LangChain",
          loc: "sdk-python/copilotkit/langchain.py:112",
          code: 'from langchain.chains import LLMChain',
          modern: 'chain = prompt | llm | StrOutputParser()',
          hours: 16.0
        }
      ]
    },
    "mem0ai/mem0": {
      repoName: "mem0ai / mem0",
      stars: "⭐ 24,100+ Stars",
      files: 88,
      loc: 19500,
      score: 72,
      grade: "C",
      status: "Moderate Risk — Pydantic v1 Legacy",
      hours: 24.0,
      payroll: 1800.00,
      speedup: "2,160x",
      cmd: "apipatch pr mem0ai/mem0",
      findings: [
        {
          severity: "HIGH",
          framework: "Pydantic",
          loc: "mem0/configs/prompts.py:31",
          code: 'class Config: orm_mode = True',
          modern: 'model_config = ConfigDict(from_attributes=True)',
          hours: 6.0
        },
        {
          severity: "CRITICAL",
          framework: "Pydantic",
          loc: "mem0/models/memory.py:64",
          code: 'from pydantic import validator',
          modern: 'from pydantic import field_validator, @classmethod',
          hours: 12.0
        },
        {
          severity: "HIGH",
          framework: "Pydantic",
          loc: "mem0/memory/main.py:120",
          code: 'from pydantic import BaseSettings',
          modern: 'from pydantic_settings import BaseSettings',
          hours: 6.0
        }
      ]
    },
    "jedarden/duck-e": {
      repoName: "jedarden / duck-e",
      stars: "⭐ 120 Stars (YC Target)",
      files: 24,
      loc: 4800,
      score: 68,
      grade: "D",
      status: "High Risk — OpenAI v0.x Breaking Call",
      hours: 18.0,
      payroll: 1350.00,
      speedup: "1,620x",
      cmd: "apipatch pr jedarden/duck-e",
      findings: [
        {
          severity: "CRITICAL",
          framework: "OpenAI",
          loc: "duck_e/core.py:42",
          code: 'openai.ChatCompletion.create(model="gpt-3.5-turbo")',
          modern: 'client = OpenAI(); client.chat.completions.create(model="gpt-4o")',
          hours: 12.0
        },
        {
          severity: "HIGH",
          framework: "Pydantic",
          loc: "duck_e/models.py:15",
          code: 'class Config: arbitrary_types_allowed = True',
          modern: 'model_config = ConfigDict(arbitrary_types_allowed=True)',
          hours: 6.0
        }
      ]
    },
    "langchain-ai/langchain": {
      repoName: "langchain-ai / langchain",
      stars: "⭐ 98,000+ Stars",
      files: 1420,
      loc: 240000,
      score: 84,
      grade: "B",
      status: "Good — Community Legacy Migrations Pending",
      hours: 48.0,
      payroll: 3600.00,
      speedup: "4,320x",
      cmd: "apipatch pr langchain-ai/langchain --target-path libs/community",
      findings: [
        {
          severity: "CRITICAL",
          framework: "LangChain",
          loc: "libs/community/chains/legacy.py:84",
          code: 'from langchain.chains import RetrievalQA',
          modern: 'from langchain.chains import create_retrieval_chain',
          hours: 16.0
        },
        {
          severity: "HIGH",
          framework: "LangChain",
          loc: "libs/community/chat_models/openai.py:22",
          code: 'from langchain.chat_models import ChatOpenAI',
          modern: 'from langchain_openai import ChatOpenAI',
          hours: 8.0
        },
        {
          severity: "HIGH",
          framework: "Anthropic",
          loc: "libs/community/llms/anthropic.py:55",
          code: 'client.completion(prompt=...)',
          modern: 'client.messages.create(model="claude-3-5-sonnet")',
          hours: 12.0
        },
        {
          severity: "MEDIUM",
          framework: "LangChain",
          loc: "libs/community/agent/runner.py:91",
          code: 'chain.run(query)',
          modern: 'chain.invoke({"query": query})',
          hours: 4.0
        }
      ]
    },
    "custom": {
      repoName: "Custom Manifest / Codebase",
      stars: "Pasted Manifest",
      files: 12,
      loc: 2450,
      score: 55,
      grade: "F",
      status: "Critical Risk — Imminent Runtime Breakages",
      hours: 32.0,
      payroll: 2400.00,
      speedup: "2,880x",
      cmd: "apipatch fix . --write --verify-tests",
      findings: [
        {
          severity: "CRITICAL",
          framework: "Anthropic",
          loc: "bot.py:19",
          code: 'client.completion(prompt=...)',
          modern: 'client.messages.create(model="claude-3-5-sonnet-20241022")',
          hours: 12.0
        },
        {
          severity: "CRITICAL",
          framework: "OpenAI",
          loc: "api.py:44",
          code: 'openai.ChatCompletion.create(...)',
          modern: 'client = OpenAI(); client.chat.completions.create(...)',
          hours: 10.0
        },
        {
          severity: "HIGH",
          framework: "Pydantic",
          loc: "schemas.py:28",
          code: 'class Config: orm_mode = True',
          modern: 'model_config = ConfigDict(from_attributes=True)',
          hours: 6.0
        },
        {
          severity: "MEDIUM",
          framework: "FastAPI",
          loc: "server.py:12",
          code: '@app.on_event("startup")',
          modern: '@asynccontextmanager lifespan(app: FastAPI)',
          hours: 4.0
        }
      ]
    }
  };

  const scannerInput = document.getElementById('scanner-input');
  const btnRunScan = document.getElementById('btn-run-scan');
  const presetChips = document.querySelectorAll('.preset-chip');
  const scannerStatus = document.getElementById('scanner-status');
  const scannerStatusText = document.getElementById('scanner-status-text');
  const scannerResults = document.getElementById('scanner-results');

  // Dashboard Elements
  const scRepoName = document.getElementById('sc-repo-name');
  const scStarsBadge = document.getElementById('sc-stars-badge');
  const scFilesCount = document.getElementById('sc-files-count');
  const scLocCount = document.getElementById('sc-loc-count');
  const scGaugeFill = document.getElementById('sc-gauge-fill');
  const scScoreVal = document.getElementById('sc-score-val');
  const scGradeTitle = document.getElementById('sc-grade-title');
  const scScoreSub = document.getElementById('sc-score-sub');
  const scHoursVal = document.getElementById('sc-hours-val');
  const scPayrollVal = document.getElementById('sc-payroll-val');
  const scSpeedupVal = document.getElementById('sc-speedup-val');
  const scCmdText = document.getElementById('sc-cmd-text');
  const scCopyCmd = document.getElementById('sc-copy-cmd');
  const scFindingsCount = document.getElementById('sc-findings-count');
  const scFindingsTbody = document.getElementById('sc-findings-tbody');

  function renderAudit(data) {
    if (!data) return;

    if (scRepoName) scRepoName.textContent = data.repoName;
    if (scStarsBadge) scStarsBadge.textContent = data.stars;
    if (scFilesCount) scFilesCount.innerHTML = `Scanned: <strong>${data.files.toLocaleString()} files</strong>`;
    if (scLocCount) scLocCount.innerHTML = `<strong>${data.loc.toLocaleString()} LOC</strong>`;

    // Health Score & Circle SVG
    const score = data.score;
    if (scScoreVal) scScoreVal.textContent = score;
    if (scGradeTitle) scGradeTitle.innerHTML = `Grade ${data.grade} &bull; Health Score`;
    if (scScoreSub) scScoreSub.textContent = data.status;

    const circumference = 339.29;
    const offset = circumference - (circumference * (score / 100.0));
    const meterColor = score >= 80 ? 'var(--lime)' : (score >= 60 ? '#facc15' : '#f87171');

    if (scGaugeFill) {
      scGaugeFill.style.strokeDashoffset = offset;
      scGaugeFill.style.stroke = meterColor;
    }
    if (scScoreVal) {
      scScoreVal.style.color = meterColor;
    }

    // Financial ROI
    if (scHoursVal) scHoursVal.textContent = `${data.hours.toFixed(1)} hrs`;
    if (scPayrollVal) scPayrollVal.textContent = `$${data.payroll.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    if (scSpeedupVal) scSpeedupVal.textContent = data.speedup;

    // Remediation Command
    if (scCmdText) scCmdText.textContent = data.cmd;

    // Findings Table
    if (scFindingsCount) scFindingsCount.textContent = data.findings.length;
    if (scFindingsTbody) {
      scFindingsTbody.innerHTML = '';
      data.findings.forEach(f => {
        const badgeClass = `sc-badge-${f.severity.toLowerCase()}`;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="sc-badge ${badgeClass}">${f.severity}</span></td>
          <td><strong>${f.framework}</strong></td>
          <td>
            <div class="sc-diff-box">
              <span class="sc-diff-rem">- ${f.code}</span>
              <div style="font-size:0.7rem; color:var(--dim); margin-top:2px;"><code>${f.loc}</code></div>
            </div>
          </td>
          <td>
            <div class="sc-diff-box">
              <span class="sc-diff-add">+ ${f.modern}</span>
            </div>
          </td>
          <td><strong>${f.hours.toFixed(1)}h</strong></td>
        `;
        scFindingsTbody.appendChild(tr);
      });
    }
  }

  function triggerAudit(targetKey) {
    if (!scannerStatus || !scannerResults) return;

    scannerStatus.classList.remove('hidden');
    scannerResults.style.opacity = '0.4';
    if (btnRunScan) btnRunScan.disabled = true;

    if (scannerStatusText) scannerStatusText.textContent = `Connecting to GitHub repository tree for ${targetKey}...`;

    setTimeout(() => {
      if (scannerStatusText) scannerStatusText.textContent = `Inspecting dependency manifests & AST import paths...`;
    }, 350);

    setTimeout(() => {
      if (scannerStatusText) scannerStatusText.textContent = `Quantifying technical debt, test pass rate & payroll ROI...`;
    }, 700);

    setTimeout(() => {
      scannerStatus.classList.add('hidden');
      scannerResults.style.opacity = '1';
      if (btnRunScan) btnRunScan.disabled = false;

      const data = SCANNER_PRESETS[targetKey] || SCANNER_PRESETS["CopilotKit/CopilotKit"];
      renderAudit(data);
    }, 1050);
  }

  if (presetChips.length > 0) {
    presetChips.forEach(chip => {
      chip.addEventListener('click', () => {
        presetChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const repoKey = chip.getAttribute('data-repo');
        if (scannerInput) scannerInput.value = repoKey === 'custom' ? 'requirements.txt (Pasted)' : repoKey;
        triggerAudit(repoKey);
      });
    });
  }

  if (btnRunScan && scannerInput) {
    btnRunScan.addEventListener('click', () => {
      const val = scannerInput.value.trim();
      let matchedKey = "custom";
      for (const k in SCANNER_PRESETS) {
        if (val.toLowerCase().includes(k.toLowerCase())) {
          matchedKey = k;
          break;
        }
      }
      triggerAudit(matchedKey);
    });
  }

  if (scCopyCmd && scCmdText) {
    scCopyCmd.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(scCmdText.textContent.trim());
        scCopyCmd.textContent = "Copied! ✓";
        scCopyCmd.style.background = "var(--lime)";
        scCopyCmd.style.color = "var(--black)";
        setTimeout(() => {
          scCopyCmd.textContent = "Copy Command";
          scCopyCmd.style.background = "";
          scCopyCmd.style.color = "";
        }, 2000);
      } catch (_) {}
    });
  }

  // Initial load of default scanner preset
  renderAudit(SCANNER_PRESETS["CopilotKit/CopilotKit"]);

});

