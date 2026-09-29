import type { Metadata } from "next";
import { JobsPage } from "@/components/jobs/jobs-page";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = { title: "Jobs" };

export default function Page() {
  return (
    <>
      <PageHeader
        title="Jobs"
        description="Open roles from the company job boards you follow, scored against your profile."
      />
      <JobsPage />
    </>
  );
}