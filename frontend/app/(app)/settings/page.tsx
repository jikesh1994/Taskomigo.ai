import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { AgentSettingsForm } from "@/components/preferences/agent-settings-form";
import { JobSearchForm } from "@/components/preferences/job-search-form";
import { MatchWeightsForm } from "@/components/preferences/match-weights-form";
import { ChangePasswordForm } from "@/components/settings/change-password-form";
import { Card, CardBody, CardHeader } from "@/components/ui/card";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Job-search criteria, agent behaviour and account security." />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Job preferences" description="Which jobs the agent looks for and which it skips." />
          <CardBody>
            <JobSearchForm />
          </CardBody>
        </Card>
        <Card>
          <CardHeader
            title="Matching"
            description="How much each part of a job counts towards its match score."
          />
          <CardBody>
            <div id="matching" className="scroll-mt-24" />
            <MatchWeightsForm />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Agent behaviour" description="How much the agent may do before checking with you." />
          <CardBody>
            <AgentSettingsForm />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Password" description="Changing your password signs you out everywhere else." />
          <CardBody>
            <ChangePasswordForm />
          </CardBody>
        </Card>
      </div>
    </>
  );
}
