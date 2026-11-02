export type CompanyTier = 'YC_AI' | 'MID_INFRA' | 'SCALEUP';

export type OutreachStatus = 'NEW' | 'PATCH_READY' | 'PR_OPENED' | 'CONTACTED' | 'WON';

export interface B2BCompanyLead {
  id: string;
  companyName: string;
  orgHandle: string;
  tier: CompanyTier;
  fundingStage: string;
  fundingAmount: string;
  companyUrl: string;
  contactChannel: string;
  decisionMakerRole: string;
  repoFullName: string;
  prNumber: number;
  prTitle: string;
  prUrl: string;
  branchHint: string;
  packageChanged: string;
  fromVersion: string;
  toVersion: string;
  isMajorUpgrade: boolean;
  language: 'Python' | 'TypeScript' | 'JavaScript' | 'Multi-Stack';
  createdAt: string;
  failedAt: string;
  failureSummary: string;
  whyTheyPay: string;
  whyTheyPayAr: string;
  isLiveScanned?: boolean;
  verifiedDiffPatch?: string;
}

export interface GeneratedPitch {
  breakingChangeAnalysis: string;
  breakingChangeAnalysisAr: string;
  githubPrComment: string;
  ctoColdEmailSubject: string;
  ctoColdEmailBody: string;
  cliWorkflow: string;
  gitDiffPatch?: string;
  astValidationStatus?: string;
}
