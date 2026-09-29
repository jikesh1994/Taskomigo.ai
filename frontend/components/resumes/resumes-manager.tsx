"use client";

import { QueryState } from "@/components/query-state";
import { ResumeList } from "@/components/resumes/resume-list";
import { ResumeUpload } from "@/components/resumes/resume-upload";
import { useResumes } from "@/hooks/use-resumes";

/** Upload plus the list of resumes; shared by onboarding step 6 and the Resumes page. */
export function ResumesManager({ compact = false }: { compact?: boolean }) {
  const query = useResumes();
  return (
    <div className="space-y-6">
      <ResumeUpload compact={compact} />
      <QueryState query={query}>{(resumes) => <ResumeList resumes={resumes} />}</QueryState>
    </div>
  );
}
