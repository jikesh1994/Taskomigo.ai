// Mirrors the backend Pydantic schemas (backend/app/schemas). Keep in sync.

export type UUID = string;
export type ISODate = string; // YYYY-MM-DD
export type ISODateTime = string;

export type UserRole = "user" | "admin";
export type RemotePreference = "remote" | "hybrid" | "onsite" | "any";
export type SkillProficiency = "beginner" | "intermediate" | "advanced" | "expert";
export type EmploymentType =
  | "full_time"
  | "part_time"
  | "contract"
  | "internship"
  | "temporary"
  | "freelance";

// ------------------------------------------------------------------ auth / user

export interface User {
  id: UUID;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  timezone: string;
  role: UserRole;
  is_active: boolean;
  onboarding_completed_at: ISODateTime | null;
  created_at: ISODateTime;
}

export interface AuthResponse {
  access_token: string;
  // Also delivered as an httpOnly cookie. The frontend relies on the cookie only
  // and never keeps this value.
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  refresh_expires_at: ISODateTime;
  user: User;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  timezone?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface UserUpdate {
  first_name?: string;
  last_name?: string;
  phone?: string | null;
  timezone?: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

// ------------------------------------------------------------------ profile

export interface Experience {
  id: UUID;
  company: string;
  title: string;
  location: string | null;
  employment_type: EmploymentType | null;
  start_date: ISODate;
  end_date: ISODate | null;
  is_current: boolean;
  description: string | null;
  technologies: string[];
}

export type ExperienceInput = Omit<Experience, "id">;

export interface Education {
  id: UUID;
  institution: string;
  degree: string;
  field_of_study: string | null;
  start_date: ISODate | null;
  end_date: ISODate | null;
  grade: string | null;
}

export type EducationInput = Omit<Education, "id">;

export interface Skill {
  id: UUID;
  name: string;
  years: number | null;
  proficiency: SkillProficiency | null;
}

export type SkillInput = Omit<Skill, "id">;

export interface ProfileFields {
  headline: string | null;
  summary: string | null;
  years_of_experience: number | null;
  current_title: string | null;
  current_company: string | null;
  preferred_titles: string[];
  preferred_locations: string[];
  remote_preference: RemotePreference;
  expected_salary_min: number | null;
  expected_salary_max: number | null;
  currency: string | null;
  notice_period_days: number | null;
  work_authorization: string | null;
  sponsorship_required: boolean | null;
  willing_to_relocate: boolean | null;
  portfolio_url: string | null;
  github_url: string | null;
  linkedin_url: string | null;
}

export interface Profile extends ProfileFields {
  id: UUID;
  experiences: Experience[];
  education: Education[];
  skills: Skill[];
  updated_at: ISODateTime;
}

export type ProfileUpdate = Partial<ProfileFields>;

// ------------------------------------------------------------------ preferences

export interface PreferenceFields {
  keywords: string[];
  employment_types: EmploymentType[];
  excluded_companies: string[];
  excluded_industries: string[];
  min_salary: number | null;
  salary_currency: string | null;
  remote_only: boolean;
  min_match_score: number;
  /** Relative weight per match component; `{}` means the defaults. */
  match_weights: Partial<Record<MatchComponent, number>>;
  max_applications_per_day: number;
  max_concurrent_browser_sessions: number;
  max_retries_per_application: number;
  auto_fill_enabled: boolean;
  auto_answer_enabled: boolean;
  review_before_submit: boolean;
  auto_submit_enabled: boolean;
}

export interface Preferences extends PreferenceFields {
  id: UUID;
  updated_at: ISODateTime;
}

export type PreferencesUpdate = Partial<PreferenceFields>;

// ------------------------------------------------------------------ resumes

export type ResumeFileType = "pdf" | "docx";
export type ResumeParseStatus = "pending" | "processing" | "parsed" | "failed";

export interface Resume {
  id: UUID;
  name: string;
  original_filename: string;
  file_type: ResumeFileType;
  size_bytes: number;
  is_default: boolean;
  parse_status: ResumeParseStatus;
  parse_error_code: string | null;
  parse_error: string | null;
  parser: string | null;
  parsed_at: ISODateTime | null;
  created_at: ISODateTime;
  pending_review: number;
}

export interface ParsedResume {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  headline: string | null;
  summary: string | null;
  total_years_experience: number | null;
  total_years_evidence: string | null;
  links: { kind: "linkedin" | "github" | "portfolio" | "other"; url: string }[];
  skills: { name: string; years: number | null; evidence: string }[];
  experiences: {
    title: string | null;
    company: string | null;
    location: string | null;
    start: string | null;
    end: string | null;
    is_current: boolean;
    description: string | null;
    technologies: string[];
    evidence: string;
  }[];
  education: {
    institution: string | null;
    degree: string | null;
    field_of_study: string | null;
    start_year: number | null;
    end_year: number | null;
    grade: string | null;
    evidence: string;
  }[];
  certifications: { name: string; issuer: string | null; year: number | null; evidence: string }[];
}

export interface ResumeDetail extends Resume {
  parsed: ParsedResume | null;
}

export interface ResumeUpdate {
  name?: string;
  is_default?: true;
}

export type ReviewAction = "use_resume" | "keep_profile" | "add" | "skip";

export interface ReviewItem {
  id: string;
  kind: "conflict" | "addition";
  field: string;
  label: string;
  question: string;
  profile_value: string | null;
  resume_value: string;
  evidence: string | null;
}

export interface ResumeReview {
  resume_id: UUID;
  items: ReviewItem[];
}

export interface ReviewApplyResult {
  applied: number;
  skipped: number;
  errors: string[];
  review: ResumeReview;
}

// ------------------------------------------------------------------ jobs

export type MatchComponent = "skills" | "experience" | "location" | "salary" | "preferences" | "other";
export type WorkplaceType = "remote" | "hybrid" | "onsite" | "unknown";
export type JobMatchStatus = "new" | "saved" | "skipped";
export type JobTab = "matches" | "saved" | "skipped" | "hidden";
export type SearchRunStatus = "queued" | "running" | "succeeded" | "failed";
export type AnalysisStatus = "none" | "pending" | "processing" | "done" | "failed";

export interface JobSource {
  id: UUID;
  platform: string;
  board: string;
  company_name: string;
  enabled: boolean;
  last_synced_at: ISODateTime | null;
  last_job_count: number | null;
  last_error: string | null;
}

export interface CatalogEntry {
  platform: string;
  board: string;
  company: string;
  added: boolean;
}

export interface SearchRun {
  id: UUID;
  status: SearchRunStatus;
  started_at: ISODateTime | null;
  finished_at: ISODateTime | null;
  sources_total: number;
  sources_done: number;
  jobs_fetched: number;
  jobs_new: number;
  jobs_closed: number;
  matches: number;
  source_errors: { source: string; message: string }[];
  error: string | null;
  created_at: ISODateTime;
}

export type MatchScores = Record<MatchComponent, number>;

export interface JobSummary {
  id: UUID;
  platform: string;
  company: string;
  title: string;
  location: string | null;
  workplace: WorkplaceType;
  employment_type: EmploymentType | null;
  department: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  posted_at: ISODateTime | null;
  first_seen_at: ISODateTime;
  is_active: boolean;
  application_url: string;
  overall_match: number;
  scores: MatchScores;
  reasons: string[];
  missing_requirements: string[];
  concerns: string[];
  excluded_reason: string | null;
  below_min_score: boolean;
  status: JobMatchStatus;
}

export interface JobFacts {
  required_skills: string[];
  preferred_skills: string[];
  skill_evidence: Record<string, string>;
  min_years: number | null;
  years_evidence: string | null;
  workplace: WorkplaceType;
  workplace_evidence: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  salary_evidence: string | null;
  sponsorship: boolean | null;
  sponsorship_evidence: string | null;
  employment_type: EmploymentType | null;
}

export type Basis = "explicit" | "inferred" | "unknown";

export interface AnalyzedFact {
  value: string;
  basis: Basis;
  evidence: string;
}

export interface AnalyzedRequirement {
  text: string;
  category: "skill" | "experience" | "education" | "certification" | "language" | "other";
  importance: "required" | "preferred";
  basis: "explicit" | "inferred";
  evidence: string;
}

export interface JobAnalysis {
  summary: string;
  seniority: AnalyzedFact;
  requirements: AnalyzedRequirement[];
  responsibilities: string[];
  benefits: string[];
  work_authorization: AnalyzedFact;
  downgraded: number;
}

export interface JobDetail extends JobSummary {
  description: string;
  notes: string[];
  facts: JobFacts;
  weights: Record<MatchComponent, number>;
  min_match_score: number;
  recommended_resume: { id: UUID; name: string; reason: string | null } | null;
  computed_at: ISODateTime;
  closed_at: ISODateTime | null;
  analysis_status: AnalysisStatus;
  analysis: JobAnalysis | null;
  analysis_error: string | null;
  analyzed_at: ISODateTime | null;
}

export interface JobList {
  items: JobSummary[];
  total: number;
  counts: Record<JobTab, number>;
  min_match_score: number;
}

export interface JobListParams {
  tab?: JobTab;
  q?: string;
  workplace?: WorkplaceType;
  sort?: "score" | "newest";
  limit?: number;
  offset?: number;
}

export interface JobStats {
  sources: number;
  matches: number;
  saved: number;
  new_this_week: number;
  last_search: SearchRun | null;
}

// ------------------------------------------------------------------ errors

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: unknown;
    request_id: string | null;
  };
}
