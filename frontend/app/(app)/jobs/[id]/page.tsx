import type { Metadata } from "next";
import { JobDetailView } from "@/components/jobs/job-detail";

export const metadata: Metadata = { title: "Job" };

export default async function JobPage(props: PageProps<"/jobs/[id]">) {
  const { id } = await props.params;
  return <JobDetailView id={id} />;
}
