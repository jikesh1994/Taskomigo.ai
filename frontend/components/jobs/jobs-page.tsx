"use client";

import { JobsBrowser } from "@/components/jobs/jobs-browser";
import { SearchPanel } from "@/components/jobs/search-panel";
import { SourcesManager } from "@/components/jobs/sources-card";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { useJobSources } from "@/hooks/use-jobs";

/** The /jobs page body: search, job lists and the job boards being followed. */
export function JobsPage() {
  const sources = useJobSources();
  const hasSources = (sources.data?.filter((s) => s.enabled).length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <Card>
        <CardBody>
          <SearchPanel hasSources={hasSources} />
        </CardBody>
      </Card>
      <Card>
        <CardBody>
          <JobsBrowser />
        </CardBody>
      </Card>
      <Card>
        <CardHeader
          title="Job boards"
          description="Taskomigo reads these companies' public job listings. Nothing about you is shared with them."
        />
        <CardBody>
          <SourcesManager />
        </CardBody>
      </Card>
    </div>
  );
}
