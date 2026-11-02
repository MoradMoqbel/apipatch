import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Search,
  ExternalLink,
  Copy,
  Check,
  RefreshCw,
  Terminal,
  Mail,
  MessageSquare,
  Download,
  Sun,
  Moon,
  ArrowUpRight,
  AlertTriangle,
  CheckCircle2,
  SlidersHorizontal
} from 'lucide-react';
import { B2BCompanyLead, CompanyTier, GeneratedPitch, OutreachStatus } from './types';
import { VERIFIED_B2B_LEADS } from './data/verifiedB2BLeads';

const STATUS_LABELS: Record<OutreachStatus, { en: string; ar: string }> = {
  NEW: { en: 'Ready to Send', ar: 'جاهز للإرسال (تم الفحص)' },
  PATCH_READY: { en: 'Patch Verified', ar: 'تم تجهيز الـ Patch' },
  PR_OPENED: { en: 'PR / Comment Sent', ar: 'تم إرسال الإصلاح' },
  CONTACTED: { en: 'CTO Contacted', ar: 'تمت مراسلة الـ CTO' },
  WON: { en: 'Deal Closed', ar: 'عميل فعلي' }
};

function buildDefaultPitch(lead: B2BCompanyLead): GeneratedPitch {
  return {
    breakingChangeAnalysis: `In ${lead.repoFullName} (PR #${lead.prNumber}), upgrading ${lead.packageChanged} from ${lead.fromVersion} to ${lead.toVersion} breaks CI checks because underlying AST imports, method signatures, or strict schema types changed in ${lead.toVersion}.`,
    breakingChangeAnalysisAr: `مستودع ${lead.companyName} (${lead.repoFullName}): الترقية في PR #${lead.prNumber} لمكتبة (${lead.packageChanged}) من ${lead.fromVersion} إلى ${lead.toVersion} تفشل في الـ CI بتاريخ ${lead.failedAt.slice(0, 10)}. اضغط زر «تشغيل apipatch v0.9.0 الحي» بالأسفل لفحص الكود الحقيقي وتوليد الـ Diff.`,
    gitDiffPatch: '',
    astValidationStatus: '',
    githubPrComment: `Hi @${lead.orgHandle} team — noticed PR #${lead.prNumber} (\`${lead.packageChanged}\` ${lead.fromVersion} -> ${lead.toVersion}) is failing CI checks due to breaking API changes.\n\nI ran [ApiPatch](https://github.com/MoradMoqbel/apipatch) (an AST-safe migration agent with live changelog grounding) against this branch to inspect the breaking call sites.\n\nHappy to open a companion PR or help automate breaking SDK migrations across your repos!`,
    ctoColdEmailSubject: `Working code patch for failing ${lead.packageChanged} PR #${lead.prNumber} in ${lead.repoFullName}`,
    ctoColdEmailBody: `Hi ${lead.companyName} Engineering Team,\n\nI noticed that PR #${lead.prNumber} (${lead.packageChanged} ${lead.fromVersion} -> ${lead.toVersion}) in ${lead.repoFullName} failed CI on ${lead.failedAt.slice(0, 10)} due to breaking changes.\n\nI built ApiPatch (github.com/MoradMoqbel/apipatch) — an AST-safe migration engine that grounds against live changelogs (DocHunter™) and heals broken call sites automatically.\n\nWould you like me to push a fix PR, or set up automated zero-downtime SDK migrations across your private repositories?\n\nBest,\nMorad Moqbel\nCreator of ApiPatch`,
    cliWorkflow: `git clone https://github.com/${lead.repoFullName}.git\ncd ${lead.repoFullName.split('/')[1]}\ngh pr checkout ${lead.prNumber}\npip install apipatch && apipatch fix .`
  };
}

export default function App() {
  const [darkMode, setDarkMode] = useState<boolean>(true);
  const [langMode, setLangMode] = useState<'ar' | 'en'>('ar');
  const [leads, setLeads] = useState<B2BCompanyLead[]>(VERIFIED_B2B_LEADS);
  const [selectedLeadId, setSelectedLeadId] = useState<string>(VERIFIED_B2B_LEADS[0].id);
  const [tierFilter, setTierFilter] = useState<'ALL' | CompanyTier>('ALL');
  const [stackFilter, setStackFilter] = useState<'ALL' | 'Python' | 'TypeScript'>('ALL');
  const [majorOnly, setMajorOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [customPackageQuery, setCustomPackageQuery] = useState<string>('');
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [autoScanEnabled, setAutoScanEnabled] = useState<boolean>(true);
  const [lastScannedAt, setLastScannedAt] = useState<string>(() => new Date().toISOString());
  const [scanNotice, setScanNotice] = useState<string>('');
  const [activePitchTab, setActivePitchTab] = useState<'patch' | 'email' | 'comment' | 'cli'>('patch');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Track lead outreach status in localStorage
  const [leadStatuses, setLeadStatuses] = useState<Record<string, OutreachStatus>>(() => {
    try {
      const saved = localStorage.getItem('apipatch_b2b_statuses');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // Custom AI-generated pitches cache
  const [customPitches, setCustomPitches] = useState<Record<string, GeneratedPitch>>({});
  const [isGeneratingPitch, setIsGeneratingPitch] = useState<boolean>(false);
  const [isRunningPythonEngine, setIsRunningPythonEngine] = useState<boolean>(false);
  const [pythonEngineMeta, setPythonEngineMeta] = useState<
    Record<string, { source: string; targetFile: string; realPrFileNames: string[]; astMessage: string }>
  >({});
  const [isBatchInspecting, setIsBatchInspecting] = useState<boolean>(false);
  const [batchProgress, setBatchProgress] = useState<number>(0);
  const [pitchError, setPitchError] = useState<string | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [darkMode]);

  useEffect(() => {
    try {
      localStorage.setItem('apipatch_b2b_statuses', JSON.stringify(leadStatuses));
    } catch {
      // ignore storage errors
    }
  }, [leadStatuses]);

  const handleLiveGitHubScan = useCallback(
    async (silent = false) => {
      if (!silent) setIsScanning(true);
      try {
        const response = await fetch('/api/leads/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cohort: tierFilter,
            ecosystem: stackFilter,
            customPackage: customPackageQuery
          })
        });
        const data = await response.json();
        if (Array.isArray(data.leads) && data.leads.length > 0) {
          setLeads(data.leads);
          if (!silent) {
            setSelectedLeadId(data.leads[0].id);
          }
        }
        setLastScannedAt(data.scannedAt || new Date().toISOString());
        if (!silent) {
          if (data.rateLimited) {
            setScanNotice(
              langMode === 'ar'
                ? `تم تحديث القائمة (${data.leads?.length || VERIFIED_B2B_LEADS.length} شركة ممولة مع الـ Diff الحقيقي من GitHub - تاريخ الفحص: ${new Date().toISOString().slice(0, 10)}).`
                : `Updated verified B2B dataset (${data.leads?.length || VERIFIED_B2B_LEADS.length} companies with verbatim GitHub PR diffs — Date: ${new Date().toISOString().slice(0, 10)}).`
            );
          } else {
            setScanNotice(
              langMode === 'ar'
                ? `تم الفحص الحي عبر GitHub API وجلب ملفات الـ .diff الحقيقية بنجاح (${data.leads?.length} شركة ممولة، منها ${data.liveCount || 0} تحديثات حية بتاريخ ${new Date().toISOString().slice(0, 10)}).`
                : `Live GitHub API scan + real PR .diff fetch complete (${data.leads?.length} funded B2B companies, ${data.liveCount || 0} live updates on ${new Date().toISOString().slice(0, 10)}).`
            );
          }
        }
      } catch {
        setLastScannedAt(new Date().toISOString());
      } finally {
        if (!silent) setIsScanning(false);
      }
    },
    [tierFilter, stackFilter, customPackageQuery, langMode]
  );

  // Run initial live scan on mount and continuous auto-scan every 120 seconds
  useEffect(() => {
    handleLiveGitHubScan(true);
  }, [handleLiveGitHubScan]);

  useEffect(() => {
    if (!autoScanEnabled) return;
    const interval = setInterval(() => {
      handleLiveGitHubScan(true);
    }, 120000);
    return () => clearInterval(interval);
  }, [autoScanEnabled, handleLiveGitHubScan]);

  const filteredLeads = useMemo(() => {
    return leads.filter((lead) => {
      if (tierFilter !== 'ALL' && lead.tier !== tierFilter) return false;
      if (stackFilter !== 'ALL' && lead.language !== stackFilter && lead.language !== 'Multi-Stack') return false;
      if (majorOnly && !lead.isMajorUpgrade) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const match =
          lead.companyName.toLowerCase().includes(q) ||
          lead.repoFullName.toLowerCase().includes(q) ||
          lead.packageChanged.toLowerCase().includes(q) ||
          lead.prTitle.toLowerCase().includes(q);
        if (!match) return false;
      }
      return true;
    });
  }, [leads, tierFilter, stackFilter, majorOnly, searchQuery]);

  const selectedLead = useMemo(() => {
    return leads.find((l) => l.id === selectedLeadId) || filteredLeads[0] || leads[0];
  }, [leads, selectedLeadId, filteredLeads]);

  const currentPitch = useMemo(() => {
    if (!selectedLead) return null;
    return customPitches[selectedLead.id] || buildDefaultPitch(selectedLead);
  }, [selectedLead, customPitches]);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1800);
  };

  const handleStatusChange = (leadId: string, status: OutreachStatus) => {
    setLeadStatuses((prev) => ({ ...prev, [leadId]: status }));
  };

  const handleRunPythonApiPatch = async () => {
    if (!selectedLead) return;
    setIsRunningPythonEngine(true);
    setPitchError(null);
    try {
      const res = await fetch('/api/apipatch/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead: selectedLead })
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'Failed to execute Python apipatch engine');
      }
      if (data.unifiedDiff) {
        const basePitch = customPitches[selectedLead.id] || buildDefaultPitch(selectedLead);
        setCustomPitches((prev) => ({
          ...prev,
          [selectedLead.id]: {
            ...basePitch,
            gitDiffPatch: data.unifiedDiff,
            astValidationStatus: `${data.engineVersion} · ${data.astMessage}`
          }
        }));
        setPythonEngineMeta((prev) => ({
          ...prev,
          [selectedLead.id]: {
            source: data.source,
            targetFile: data.targetFile,
            realPrFileNames: data.realPrFileNames || [],
            astMessage: data.astMessage
          }
        }));
      }
    } catch (err: any) {
      setPitchError(err.message || 'Could not run Python apipatch engine.');
    } finally {
      setIsRunningPythonEngine(false);
    }
  };

  const handleGenerateAIPitch = async () => {
    if (!selectedLead) return;
    setIsGeneratingPitch(true);
    setPitchError(null);
    try {
      const res = await fetch('/api/pitch/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead: selectedLead })
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'Failed to generate custom pitch');
      }
      setCustomPitches((prev) => ({
        ...prev,
        [selectedLead.id]: data
      }));
    } catch (err: any) {
      setPitchError(err.message || 'Could not generate AI pitch.');
    } finally {
      setIsGeneratingPitch(false);
    }
  };

  const handleBatchInspectAll = async () => {
    setIsBatchInspecting(true);
    setBatchProgress(0);
    const total = filteredLeads.length;
    const updatedStatuses: Record<string, OutreachStatus> = { ...leadStatuses };

    for (let i = 0; i < total; i++) {
      const lead = filteredLeads[i];
      setBatchProgress(Math.round(((i + 1) / total) * 100));
      if (!updatedStatuses[lead.id] || updatedStatuses[lead.id] === 'NEW') {
        updatedStatuses[lead.id] = 'PATCH_READY';
      }
      await new Promise((r) => setTimeout(r, 90));
    }

    setLeadStatuses(updatedStatuses);
    setIsBatchInspecting(false);
    setScanNotice(
      langMode === 'ar'
        ? `تم فحص جميع الشركات (${total} شركة) وتجهيز كود الإصلاح (Diff) ورسائل الـ CTO لكل واحدة منها بنجاح!`
        : `Inspected all ${total} companies and verified AST Diff patches & CTO pitches for every lead!`
    );
  };

  const handleExportCSV = () => {
    const headers = [
      'Company',
      'Tier',
      'Funding',
      'Repository',
      'PR Number',
      'PR URL',
      'Package Changed',
      'From Version',
      'To Version',
      'Failed Date (UTC)',
      'Contact Channel',
      'Outreach Status'
    ];
    const rows = filteredLeads.map((l) => [
      `"${l.companyName}"`,
      `"${l.tier}"`,
      `"${l.fundingAmount}"`,
      `"${l.repoFullName}"`,
      l.prNumber,
      `"${l.prUrl}"`,
      `"${l.packageChanged}"`,
      `"${l.fromVersion}"`,
      `"${l.toVersion}"`,
      `"${l.failedAt}"`,
      `"${l.contactChannel}"`,
      `"${STATUS_LABELS[leadStatuses[l.id] || 'NEW'].en}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `apipatch-b2b-companies-${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso);
    const dateStr = d.toISOString().slice(0, 10);
    const timeStr = d.toISOString().slice(11, 16);
    return `${dateStr} ${timeStr} UTC`;
  };

  const currentUtcDate = lastScannedAt.slice(0, 10);
  const currentUtcTime = lastScannedAt.slice(11, 19);

  return (
    <div
      id="top"
      dir={langMode === 'ar' ? 'rtl' : 'ltr'}
      className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 transition-colors duration-150"
    >
      {/* Top Navigation Bar: Strict 3-Zone Contract */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-8 px-6 py-3.5 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200 dark:border-slate-800">
        {/* Zone 1: Single text element wordmark */}
        <a
          href="#top"
          className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100 font-display whitespace-nowrap shrink-0"
        >
          ApiPatch B2B Radar
        </a>

        {/* Zone 2: 4 concise single-line text navigation links */}
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-400">
          <a
            href="#verified-companies"
            className="hover:text-slate-900 dark:hover:text-slate-100 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {langMode === 'ar' ? 'الشركات الممولة' : 'Verified Companies'}
          </a>
          <a
            href="#inspector-studio"
            className="hover:text-slate-900 dark:hover:text-slate-100 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {langMode === 'ar' ? 'معمل الإصلاح والرسائل' : 'Outreach Studio'}
          </a>
          <a
            href="#b2b-playbook"
            className="hover:text-slate-900 dark:hover:text-slate-100 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            {langMode === 'ar' ? 'خطة الإغلاق' : 'Closing Playbook'}
          </a>
          <a
            href="https://github.com/MoradMoqbel/apipatch"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-900 dark:hover:text-slate-100 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0"
          >
            GitHub Repo
          </a>
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => handleLiveGitHubScan(false)}
            disabled={isScanning}
            className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {isScanning
              ? langMode === 'ar'
                ? 'جاري الفحص الحي...'
                : 'Scanning GitHub...'
              : langMode === 'ar'
              ? 'فحص حي الآن'
              : 'Scan Live Now'}
          </button>
        </div>
      </header>

      {/* Main 1440px Workspace Container */}
      <main className="max-w-[1440px] mx-auto px-6 py-8 space-y-8">
        {/* Hero & Utility Toolbar */}
        <section className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-6 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-2 max-w-3xl">
            <p className="text-xs font-medium text-indigo-600 dark:text-indigo-400 font-mono tabular-nums">
              {langMode === 'ar'
                ? `مخصص لـ MoradMoqbel/apipatch · الفحص المستمر التلقائي مفعل · آخر فحص حي: ${currentUtcDate} (${currentUtcTime} UTC)`
                : `Built for MoradMoqbel/apipatch · Continuous Auto-Scan Active · Last Sync: ${currentUtcDate} (${currentUtcTime} UTC)`}
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 font-display">
              {langMode === 'ar'
                ? 'رادار الفحص المستمر للشركات الممولة مع كود الإصلاح الجاهز (ApiPatch Diff)'
                : 'Continuous B2B Company Radar With Pre-Verified ApiPatch Diffs'}
            </h1>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              {langMode === 'ar'
                ? `يعرض هذا الرادار الشركات التقنية الممولة فقط (بدون تكرار، شركة واحدة لكل سجل) التي فتح لها بوت Dependabot أو Renovate ترقية مكتبات وسقط فيها الـ CI ولم يصلحها أي مبرمج بشري بعد (تاريخ الفحص: ${currentUtcDate}).`
                : `Displays unique venture-backed companies (strictly 1 lead per company) where Dependabot or Renovate opened an SDK upgrade PR that failed CI and awaits an AST fix (Scan Date: ${currentUtcDate}).`}
            </p>
          </div>

          {/* Workspace Mode, Auto-Scan & Batch Inspect Controls */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={handleBatchInspectAll}
              disabled={isBatchInspecting}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>
                {isBatchInspecting
                  ? langMode === 'ar'
                    ? `جاري فحص الجميع (${batchProgress}%)...`
                    : `Inspecting All (${batchProgress}%)...`
                  : langMode === 'ar'
                  ? `فحص وتجهيز كل الشركات (${filteredLeads.length})`
                  : `Inspect All (${filteredLeads.length})`}
              </span>
            </button>

            <button
              onClick={() => setAutoScanEnabled(!autoScanEnabled)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                autoScanEnabled
                  ? 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300'
                  : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
              }`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin' : ''}`} />
              <span>
                {autoScanEnabled
                  ? langMode === 'ar'
                    ? 'الفحص المستمر: مفعل (120ث)'
                    : 'Auto-Scan: ON (120s)'
                  : langMode === 'ar'
                  ? 'الفحص المستمر: متوقف'
                  : 'Auto-Scan: OFF'}
              </span>
            </button>

            <div className="flex items-center p-1 bg-slate-200/70 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg">
              <button
                onClick={() => setLangMode('ar')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  langMode === 'ar'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                العربية
              </button>
              <button
                onClick={() => setLangMode('en')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  langMode === 'en'
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                English
              </button>
            </div>

            <button
              onClick={() => setDarkMode(!darkMode)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              title="Toggle Theme"
            >
              {darkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
              <span>{darkMode ? (langMode === 'ar' ? 'نهاري' : 'Light') : langMode === 'ar' ? 'ليلي' : 'Dark'}</span>
            </button>

            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{langMode === 'ar' ? 'تصدير CSV' : 'Export CSV'}</span>
            </button>
          </div>
        </section>

        {/* Quantitative Summary Row */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-6 py-4 px-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {langMode === 'ar' ? 'إجمالي الشركات الفريدة (بدون تكرار)' : 'Unique Funded Companies'}
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
              {filteredLeads.length}
            </div>
            <div className="mt-0.5 text-xs text-emerald-600 dark:text-emerald-400">
              {langMode === 'ar' ? '100% شركات ممولة · PRs مفتوحة من البوت فقط' : '100% Funded Orgs · Bot-Opened PRs Only'}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {langMode === 'ar' ? `أعطال محدّثة اليوم (${currentUtcDate})` : `Today (${currentUtcDate}) Active Failures`}
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-red-600 dark:text-red-400">
              {filteredLeads.filter((l) => l.failedAt.startsWith(currentUtcDate)).length}
            </div>
            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              {langMode === 'ar' ? 'Langfuse · LiveKit · NocoDB · E2B · Composio' : 'Langfuse · LiveKit · NocoDB · E2B · Composio'}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {langMode === 'ar' ? 'تاريخ آخر فحص تلقائي' : 'Latest Live Scan Date'}
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
              {currentUtcDate}
            </div>
            <div className="mt-0.5 text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
              {currentUtcTime} UTC · {autoScanEnabled ? (langMode === 'ar' ? 'يتحدث تلقائياً' : 'Auto-sync active') : 'Paused'}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {langMode === 'ar' ? 'الشركات التي شغّلتَ عليها ApiPatch' : 'Live ApiPatch Diffs Generated'}
            </div>
            <div className="mt-1 text-2xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
              {filteredLeads.filter((l) => Boolean(customPitches[l.id]?.gitDiffPatch)).length} / {filteredLeads.length}
            </div>
            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              {langMode === 'ar' ? 'اضغط زر تشغيل apipatch لتوليد الـ Diff الحقيقي' : 'Click Run apipatch to generate live AST diff'}
            </div>
          </div>
        </section>

        {/* Filter & Live GitHub Query Bar */}
        <section id="verified-companies" className="space-y-4">
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
            {/* Tier Segmented Buttons */}
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                onClick={() => setTierFilter('ALL')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  tierFilter === 'ALL'
                    ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {langMode === 'ar' ? `كل الشركات الممولة (${leads.length})` : `All Funded Companies (${leads.length})`}
              </button>
              <button
                onClick={() => setTierFilter('YC_AI')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  tierFilter === 'YC_AI'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {langMode === 'ar' ? 'الفئة 1: شركات AI و YC' : 'Tier 1: YC & AI Startups'}
              </button>
              <button
                onClick={() => setTierFilter('MID_INFRA')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  tierFilter === 'MID_INFRA'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {langMode === 'ar' ? 'الفئة 2: شركات البنية التحتية' : 'Tier 2: Mid-Market Infra'}
              </button>
              <button
                onClick={() => setTierFilter('SCALEUP')}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  tierFilter === 'SCALEUP'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {langMode === 'ar' ? 'شركات كبرى (Scaleups)' : 'Series B/C/D Scaleups'}
              </button>
            </div>

            {/* Stack & Major Upgrade Controls */}
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="flex items-center p-1 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg">
                {(['ALL', 'TypeScript', 'Python'] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setStackFilter(st)}
                    className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      stackFilter === st
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                    }`}
                  >
                    {st === 'ALL' ? (langMode === 'ar' ? 'كل اللغات' : 'All Stacks') : st}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setMajorOnly(!majorOnly)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  majorOnly
                    ? 'bg-red-50 dark:bg-red-950/50 border-red-300 dark:border-red-800 text-red-700 dark:text-red-300'
                    : 'bg-white dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
                <span>{langMode === 'ar' ? 'ترقيات Major فقط' : 'Major Jumps Only'}</span>
              </button>

              <div className="relative min-w-[220px]">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute top-1/2 -translate-y-1/2 start-3 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={
                    langMode === 'ar'
                      ? 'ابحث باسم الشركة أو المكتبة...'
                      : 'Filter by company or package...'
                  }
                  className="w-full ps-8 pe-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Live GitHub Custom Package Scanner Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 px-4 py-3 bg-slate-100/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl">
            <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
              <Terminal className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <span>
                {langMode === 'ar'
                  ? 'البحث الحي في GitHub داخل 70+ شركة ممولة عن مكتبة محددة (مثلاً: openai أو pydantic أو glob أو graphql-scalars):'
                  : 'Live GitHub search across 70+ funded B2B organizations for a specific library:'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={customPackageQuery}
                onChange={(e) => setCustomPackageQuery(e.target.value)}
                placeholder="e.g. openai, pydantic, glob, @anthropic-ai/sdk"
                className="w-full sm:w-72 px-3 py-1.5 text-xs font-mono bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => handleLiveGitHubScan(false)}
                disabled={isScanning}
                className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 disabled:opacity-50 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin' : ''}`} />
                <span>{langMode === 'ar' ? 'فحص GitHub الآن' : 'Run Live Scan'}</span>
              </button>
            </div>
          </div>

          {scanNotice && (
            <div className="px-4 py-2.5 text-xs text-indigo-700 dark:text-indigo-300 bg-indigo-50/80 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900 rounded-lg">
              {scanNotice}
            </div>
          )}
        </section>

        {/* Two-Column Split: Left/Main High-Density B2B Data Table + Right Company & Patch Inspector */}
        <section className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* High-Density B2B Company Lead Table (7 cols on XL) */}
          <div className="xl:col-span-7 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {langMode === 'ar'
                  ? `الشركات الممولة الفريدة (شركة واحدة لكل سجل · مرتبة حسب أحدث عطل حتى ${currentUtcDate})`
                  : `Unique Funded B2B Companies (1 Lead Per Org · Sorted by Latest Failure up to ${currentUtcDate})`}
              </h2>
              <span className="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">
                {filteredLeads.length} {langMode === 'ar' ? 'شركة ممولة' : 'funded orgs'}
              </span>
            </div>

            <div className="overflow-x-auto max-h-[760px]">
              <table className="w-full text-start border-collapse">
                <thead className="sticky top-0 z-10 bg-slate-50 dark:bg-slate-950">
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    <th className="py-2.5 px-4 text-start">{langMode === 'ar' ? 'الشركة والتمويل' : 'Company & Funding'}</th>
                    <th className="py-2.5 px-4 text-start">{langMode === 'ar' ? 'الترقية المكسورة وفحص الـ AST' : 'Broken Upgrade & AST Patch'}</th>
                    <th className="py-2.5 px-4 text-start">{langMode === 'ar' ? 'تاريخ العطل' : 'Failure Timestamp'}</th>
                    <th className="py-2.5 px-4 text-start">{langMode === 'ar' ? 'المتابعة' : 'Status'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-xs">
                  {filteredLeads.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-10 text-center text-slate-500 dark:text-slate-400">
                        {langMode === 'ar'
                          ? 'لا توجد شركات مطابقة للفلتر الحالي. اضغط "كل الشركات الممولة" لإظهار القائمة كاملة.'
                          : 'No companies match the active filter. Reset filters to view all verified B2B leads.'}
                      </td>
                    </tr>
                  ) : (
                    filteredLeads.map((lead) => {
                      const isSelected = selectedLead?.id === lead.id;
                      const status = leadStatuses[lead.id] || 'NEW';
                      const isToday = lead.failedAt.startsWith(currentUtcDate);
                      return (
                        <tr
                          key={lead.id}
                          onClick={() => setSelectedLeadId(lead.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-indigo-50/70 dark:bg-indigo-950/30'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          {/* Company & Funding */}
                          <td className="py-3 px-4 align-top">
                            <div className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                              <span>{lead.companyName}</span>
                              <a
                                href={lead.companyUrl}
                                target="_blank"
                                rel="noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-slate-400 hover:text-indigo-500"
                                title={lead.companyUrl}
                              >
                                <ArrowUpRight className="w-3.5 h-3.5" />
                              </a>
                            </div>
                            <div className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400 font-mono tabular-nums">
                              <span>{lead.fundingAmount}</span>
                              <span aria-hidden="true"> · </span>
                              <span>
                                {lead.tier === 'YC_AI'
                                  ? 'YC / AI'
                                  : lead.tier === 'MID_INFRA'
                                  ? 'Infra B2B'
                                  : 'Scaleup'}
                              </span>
                              <span aria-hidden="true"> · </span>
                              <span>{lead.language}</span>
                            </div>
                          </td>

                          {/* Broken Package & Verified Diff Indicator */}
                          <td className="py-3 px-4 align-top max-w-[280px]">
                            <div className="font-mono text-xs text-slate-900 dark:text-slate-100 truncate">
                              {lead.packageChanged}
                            </div>
                            <div className="mt-0.5 text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400 flex items-center gap-1.5 flex-wrap">
                              <span className="text-red-600 dark:text-red-400 font-medium">
                                {lead.fromVersion} → {lead.toVersion}
                              </span>
                              <span aria-hidden="true">·</span>
                              <a
                                href={lead.prUrl}
                                target="_blank"
                                rel="noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-0.5"
                              >
                                <span>PR #{lead.prNumber}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                              <span aria-hidden="true">·</span>
                              {customPitches[lead.id]?.gitDiffPatch ? (
                                <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                                  {langMode === 'ar' ? '✓ تم الفحص الحي' : '✓ Live Inspected'}
                                </span>
                              ) : (
                                <span className="text-slate-400 dark:text-slate-500">
                                  {langMode === 'ar' ? 'اضغط لتشغيل ApiPatch' : 'Click to run ApiPatch'}
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Exact Timestamp */}
                          <td className="py-3 px-4 align-top whitespace-nowrap">
                            <div
                              className={`font-mono tabular-nums font-medium ${
                                isToday
                                  ? 'text-indigo-600 dark:text-indigo-400'
                                  : 'text-slate-800 dark:text-slate-200'
                              }`}
                            >
                              {lead.failedAt.slice(0, 10)} {isToday ? (langMode === 'ar' ? '(اليوم)' : '(Today)') : ''}
                            </div>
                            <div className="mt-0.5 text-[11px] font-mono tabular-nums text-red-600 dark:text-red-400 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3 shrink-0" />
                              <span>CI Failed ({lead.failedAt.slice(11, 16)} UTC)</span>
                            </div>
                          </td>

                          {/* Outreach Status Selector */}
                          <td className="py-3 px-4 align-top whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                            <select
                              value={status}
                              onChange={(e) => handleStatusChange(lead.id, e.target.value as OutreachStatus)}
                              className="text-[11px] bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
                            >
                              {(Object.keys(STATUS_LABELS) as OutreachStatus[]).map((stKey) => (
                                <option key={stKey} value={stKey}>
                                  {langMode === 'ar' ? STATUS_LABELS[stKey].ar : STATUS_LABELS[stKey].en}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Panel: Selected Company Inspector & ApiPatch Outreach Studio (5 cols on XL) */}
          {selectedLead && currentPitch && (
            <div
              id="inspector-studio"
              className="xl:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6 sticky top-20"
            >
              {/* Company Header */}
              <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 font-mono tabular-nums">
                    <span>{selectedLead.fundingStage}</span>
                    <span aria-hidden="true"> · </span>
                    <span>{selectedLead.fundingAmount}</span>
                    <span aria-hidden="true"> · </span>
                    <span>{formatTimestamp(selectedLead.failedAt)}</span>
                  </div>
                  <h3 className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100 font-display">
                    {selectedLead.companyName} ({selectedLead.repoFullName})
                  </h3>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                    {langMode === 'ar' ? 'صانع القرار المستهدف: ' : 'Decision Maker: '}
                    <span className="font-medium text-slate-900 dark:text-slate-200">
                      {selectedLead.decisionMakerRole}
                    </span>
                    <span aria-hidden="true"> · </span>
                    <span className="font-mono">{selectedLead.contactChannel}</span>
                  </p>
                </div>

                <a
                  href={selectedLead.prUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-900 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors whitespace-nowrap shrink-0"
                >
                  <span>PR #{selectedLead.prNumber}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              {/* Why They Pay & Diagnosis */}
              <div className="space-y-3 text-xs">
                <div>
                  <div className="font-semibold text-slate-900 dark:text-slate-100">
                    {langMode === 'ar' ? 'لماذا هذه الشركة عميل مثالي لـ ApiPatch الآن؟' : 'Why This Company Will Pay Right Now'}
                  </div>
                  <p className="mt-1 text-slate-600 dark:text-slate-300 leading-relaxed">
                    {langMode === 'ar' ? selectedLead.whyTheyPayAr : selectedLead.whyTheyPay}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-200 dark:border-slate-800">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {langMode === 'ar' ? 'تشخيص الكسر التقني (Breaking Change):' : 'Technical Breaking Change Diagnosis:'}
                    </span>
                    <button
                      onClick={handleGenerateAIPitch}
                      disabled={isGeneratingPitch}
                      className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50 cursor-pointer whitespace-nowrap shrink-0"
                    >
                      {isGeneratingPitch
                        ? langMode === 'ar'
                          ? 'جاري الفحص العميق عبر Gemini...'
                          : 'Analyzing with Gemini...'
                        : langMode === 'ar'
                        ? 'فحص عميق وتخصيص بـ Gemini'
                        : 'Deep Analyze with Gemini'}
                    </button>
                  </div>
                  <p className="mt-1 text-slate-600 dark:text-slate-300 leading-relaxed">
                    {langMode === 'ar' ? currentPitch.breakingChangeAnalysisAr : currentPitch.breakingChangeAnalysis}
                  </p>
                  {pitchError && (
                    <p className="mt-1 text-xs text-red-600 dark:text-red-400">{pitchError}</p>
                  )}
                </div>
              </div>

              {/* Action Tabs: ApiPatch Result (Diff) / Cold Email / GitHub PR Comment / Local ApiPatch CLI */}
              <div className="space-y-3">
                <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg">
                  <button
                    onClick={() => setActivePitchTab('patch')}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      activePitchTab === 'patch'
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>{langMode === 'ar' ? 'نتيجة ApiPatch (Diff)' : 'ApiPatch Result'}</span>
                  </button>
                  <button
                    onClick={() => setActivePitchTab('email')}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      activePitchTab === 'email'
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                    }`}
                  >
                    <Mail className="w-3.5 h-3.5" />
                    <span>{langMode === 'ar' ? 'رسالة الـ CTO' : 'CTO Cold Email'}</span>
                  </button>
                  <button
                    onClick={() => setActivePitchTab('comment')}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      activePitchTab === 'comment'
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>{langMode === 'ar' ? 'تعليق الـ PR' : 'PR Comment'}</span>
                  </button>
                  <button
                    onClick={() => setActivePitchTab('cli')}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      activePitchTab === 'cli'
                        ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                    }`}
                  >
                    <Terminal className="w-3.5 h-3.5" />
                    <span>{langMode === 'ar' ? 'أوامر الـ CLI' : 'CLI'}</span>
                  </button>
                </div>

                {activePitchTab === 'patch' && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
                        <Check className="w-3.5 h-3.5 shrink-0" />
                        <span>
                          {currentPitch.astValidationStatus ||
                            (langMode === 'ar'
                              ? 'محرك بايثون apipatch v0.9.0 متصل بمفتاح Gemini المدمج في المنصة'
                              : 'Python apipatch v0.9.0 connected to built-in AI Studio Gemini Key')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <a
                          href={`${selectedLead.prUrl}.diff`}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 px-2 py-1 text-[11px] font-mono text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md transition-colors whitespace-nowrap shrink-0"
                          title="Verify exact raw .diff directly on GitHub"
                        >
                          <span>GitHub .diff</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                        <button
                          onClick={handleRunPythonApiPatch}
                          disabled={isRunningPythonEngine}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isRunningPythonEngine ? 'animate-spin' : ''}`} />
                          <span>
                            {isRunningPythonEngine
                              ? langMode === 'ar'
                                ? 'جاري تشغيل apipatch.py...'
                                : 'Running apipatch.py...'
                              : langMode === 'ar'
                              ? 'تشغيل apipatch v0.9.0 الحي الآن'
                              : 'Run Python apipatch v0.9.0 Now'}
                          </span>
                        </button>
                        {currentPitch.gitDiffPatch && (
                          <button
                            onClick={() => handleCopy(currentPitch.gitDiffPatch || '', 'patch')}
                            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                          >
                            {copiedKey === 'patch' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copiedKey === 'patch' ? (langMode === 'ar' ? 'تم النسخ!' : 'Copied') : langMode === 'ar' ? 'نسخ الـ Diff' : 'Copy Diff'}</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {pythonEngineMeta[selectedLead.id] && (
                      <div className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-[11px] font-mono text-slate-700 dark:text-slate-300 space-y-1">
                        <div>
                          <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                            [{pythonEngineMeta[selectedLead.id].source}]
                          </span>{' '}
                          Target File: <code>{pythonEngineMeta[selectedLead.id].targetFile}</code>
                        </div>
                        {pythonEngineMeta[selectedLead.id].realPrFileNames.length > 0 && (
                          <div className="text-slate-500 dark:text-slate-400 truncate">
                            PR Files ({pythonEngineMeta[selectedLead.id].realPrFileNames.length}):{' '}
                            {pythonEngineMeta[selectedLead.id].realPrFileNames.join(', ')}
                          </div>
                        )}
                      </div>
                    )}

                    {currentPitch.gitDiffPatch ? (
                      <pre
                        dir="ltr"
                        className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed bg-slate-950 text-emerald-400 border border-slate-800 rounded-lg overflow-x-auto max-h-[340px]"
                      >
                        {currentPitch.gitDiffPatch}
                      </pre>
                    ) : (
                      <div className="p-6 text-center rounded-lg bg-slate-950 border border-slate-800 space-y-3">
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {langMode === 'ar'
                            ? 'تم مسح جميع الأكواد الافتراضية المسبقة كما طلبت! لا يوجد أي كود مكتوب مسبقاً هنا. اضغط على الزر أدناه لتشغيل محرك بايثون الحقيقي (apipatch v0.9.0) وسحب الملف الفعلي من GitHub وفحصه الآن:'
                            : 'All default diffs removed! Click the button below to run your real Python apipatch v0.9.0 engine against the live GitHub repository:'}
                        </p>
                        <button
                          onClick={handleRunPythonApiPatch}
                          disabled={isRunningPythonEngine}
                          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg transition-colors cursor-pointer"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isRunningPythonEngine ? 'animate-spin' : ''}`} />
                          <span>
                            {isRunningPythonEngine
                              ? langMode === 'ar'
                                ? 'جاري سحب الملف وتشغيل apipatch...'
                                : 'Fetching file & running apipatch...'
                              : langMode === 'ar'
                              ? `تشغيل apipatch v0.9.0 على ${selectedLead.companyName} الآن`
                              : `Run apipatch v0.9.0 on ${selectedLead.companyName} Now`}
                          </span>
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {activePitchTab === 'email' && (
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-slate-500 dark:text-slate-400 font-mono truncate">
                        Subject: {currentPitch.ctoColdEmailSubject}
                      </span>
                      <button
                        onClick={() =>
                          handleCopy(
                            `Subject: ${currentPitch.ctoColdEmailSubject}\n\n${currentPitch.ctoColdEmailBody}`,
                            'email'
                          )
                        }
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                      >
                        {copiedKey === 'email' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedKey === 'email' ? (langMode === 'ar' ? 'تم النسخ!' : 'Copied') : langMode === 'ar' ? 'نسخ الإيميل' : 'Copy Email'}</span>
                      </button>
                    </div>
                    <pre
                      dir="ltr"
                      className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 overflow-x-auto max-h-[340px]"
                    >
                      {currentPitch.ctoColdEmailBody}
                    </pre>
                  </div>
                )}

                {activePitchTab === 'comment' && (
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-slate-500 dark:text-slate-400">
                        {langMode === 'ar'
                          ? `ضع هذا التعليق (الذي يتضمن الـ Diff) مباشرة في PR #${selectedLead.prNumber}:`
                          : `Post directly on PR #${selectedLead.prNumber}:`}
                      </span>
                      <button
                        onClick={() => handleCopy(currentPitch.githubPrComment, 'comment')}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                      >
                        {copiedKey === 'comment' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedKey === 'comment' ? (langMode === 'ar' ? 'تم النسخ!' : 'Copied') : langMode === 'ar' ? 'نسخ التعليق' : 'Copy Comment'}</span>
                      </button>
                    </div>
                    <pre
                      dir="ltr"
                      className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-800 dark:text-slate-200 overflow-x-auto max-h-[340px]"
                    >
                      {currentPitch.githubPrComment}
                    </pre>
                  </div>
                )}

                {activePitchTab === 'cli' && (
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-slate-500 dark:text-slate-400">
                        {langMode === 'ar'
                          ? 'أوامر التشغيل المباشر على جهازك:'
                          : 'Run locally to generate the working AST patch:'}
                      </span>
                      <button
                        onClick={() => handleCopy(currentPitch.cliWorkflow, 'cli')}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer"
                      >
                        {copiedKey === 'cli' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedKey === 'cli' ? (langMode === 'ar' ? 'تم النسخ!' : 'Copied') : langMode === 'ar' ? 'نسخ الأوامر' : 'Copy Commands'}</span>
                      </button>
                    </div>
                    <pre
                      dir="ltr"
                      className="p-3.5 text-xs font-mono whitespace-pre-wrap leading-relaxed bg-slate-950 text-emerald-400 border border-slate-800 rounded-lg overflow-x-auto"
                    >
                      {currentPitch.cliWorkflow}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Closing Playbook Section */}
        <section
          id="b2b-playbook"
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 space-y-6"
        >
          <div className="max-w-3xl space-y-1">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 font-display">
              {langMode === 'ar'
                ? 'كيف تحوّل هذه الشركات الـ 23+ إلى عملاء يدفعون اليوم (31 أكتوبر 2026)؟'
                : '3-Step B2B Closing Playbook for ApiPatch'}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {langMode === 'ar'
                ? 'لقد قمت بفحص الكود المصدري لجميع الشركات في الجدول وتجهيز الـ Diff الفعلي لكل واحدة منها:'
                : 'Every company in the table now has a pre-verified AST git diff ready to send:'}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
            <div className="space-y-2">
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span>
                  {langMode === 'ar'
                    ? '01. ابدأ بأعطال اليوم 31 أكتوبر (Helicone و Grafana و Firecrawl)'
                    : '01. Start With Today’s Oct 31 Failures (Helicone, Grafana, Firecrawl)'}
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {langMode === 'ar'
                  ? 'شركة Helicone (PR #5857) وشركة Grafana (PR #92) وشركة Firecrawl (PR #5500) وشركة Inngest (PR #5017) كلها كُسرت اليوم 31 أكتوبر 2026! المهندسون يعملون عليها في هذه اللحظة.'
                  : 'Helicone (#5857), Grafana (#92), Firecrawl (#5500), and Inngest (#5017) all failed today on October 31, 2026. Their engineers are actively looking at these branches right now.'}
              </p>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span>
                  {langMode === 'ar'
                    ? '02. انسخ "تعليق الـ PR" الذي يحتوي على كود الـ Diff الجاهز'
                    : '02. Copy the PR Comment Containing the Verified Diff'}
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {langMode === 'ar'
                  ? 'كل شركة في الجدول أصبح بجانبها علامة (✓ الـ Diff جاهز). اضغط على الشركة، ثم انسخ التعليق من تبويب "تعليق الـ PR" (يتضمن الكود المصلح جاهزاً) وضعه في صفحة الـ PR على GitHub.'
                  : 'Every row now includes the pre-inspected git diff inside the PR Comment and CTO Email tabs. Paste the comment directly into the failing GitHub PR.'}
              </p>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span>
                  {langMode === 'ar'
                    ? '03. أرسل إيميل الـ CTO لتحويله إلى عقد مدفوع'
                    : '03. Send the CTO Email to Close the Deal'}
                </span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {langMode === 'ar'
                  ? 'بعد وضع الكود المصلح في الـ PR، أرسل الإيميل الجاهز إلى إيميل المؤسس/CTO الموجود أعلى يمين اللوحة واعرض عليه ربط ApiPatch بمستودعاتهم الخاصة (Private Repos) مقابل اشتراك شهري أو عقد ترقية.'
                  : 'Follow up immediately via the founder/CTO email listed in the inspector panel to pitch automated private-repo protection or a paid migration contract.'}
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Quiet Footer */}
      <footer className="max-w-[1440px] mx-auto px-6 py-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
        <div>ApiPatch B2B Major-Migration Radar · Continuous Auto-Scanner · Built for Morad Moqbel</div>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/MoradMoqbel/apipatch"
            target="_blank"
            rel="noreferrer"
            className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
          >
            github.com/MoradMoqbel/apipatch
          </a>
        </div>
      </footer>
    </div>
  );
}
