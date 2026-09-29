import type { Metadata } from "next";
import { PageHeader } from "@/components/page-header";
import { EducationSection } from "@/components/profile/education-section";
import { ExperienceSection } from "@/components/profile/experience-section";
import { PersonalForm } from "@/components/profile/personal-form";
import { ProfessionalForm } from "@/components/profile/professional-form";
import { SkillsSection } from "@/components/profile/skills-section";
import { Card, CardBody, CardHeader } from "@/components/ui/card";

export const metadata: Metadata = { title: "Profile" };

export default function ProfilePage() {
  return (
    <>
      <PageHeader
        title="Profile"
        description="The verified information your agent uses. It never adds anything you haven't entered."
      />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Personal information" />
          <CardBody>
            <PersonalForm />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Professional information" />
          <CardBody>
            <ProfessionalForm />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Experience" description="Changes save as soon as you add, edit or delete an entry." />
          <CardBody>
            <ExperienceSection />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Education" />
          <CardBody>
            <EducationSection />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Skills" />
          <CardBody>
            <SkillsSection />
          </CardBody>
        </Card>
      </div>
    </>
  );
}
