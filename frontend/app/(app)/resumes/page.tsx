import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { ResumesManager } from "@/components/resumes/resumes-manager";
import { Card, CardBody } from "@/components/ui/card";

export const metadata: Metadata = { title: "Resumes" };

export default function ResumesPage() {
  return (
    <>
      <PageHeader
        title="Resumes"
        description="Keep a resume for each kind of role. Your default is used unless a better match is suggested for a job."
      />
      <Card>
        <CardBody>
          <ResumesManager />
        </CardBody>
      </Card>
    </>
  );
}
