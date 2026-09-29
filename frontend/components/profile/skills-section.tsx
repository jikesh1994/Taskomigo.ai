"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormError } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { ConfirmButton } from "@/components/ui/confirm-button";
import { SelectField, TextField } from "@/components/ui/field";
import { useAddSkill, useDeleteSkill, useProfile, useUpdateSkill } from "@/hooks/use-profile";
import { applyApiError } from "@/lib/form-errors";
import { PROFICIENCY_OPTIONS, labelFor } from "@/lib/options";
import { numberToInput, optionalNumber, requiredText } from "@/lib/validation";
import { ApiError, describeError } from "@/services/errors";
import type { Skill, SkillProficiency } from "@/types/api";

const schema = z
  .object({
    name: requiredText(100, "Enter a skill"),
    years: optionalNumber({ min: 0, max: 60 }),
    proficiency: z.string(),
  })
  .transform((v) => ({
    name: v.name,
    years: v.years,
    proficiency: (v.proficiency || null) as SkillProficiency | null,
  }));

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = ["name", "years", "proficiency"] as const;
const EMPTY: Input = { name: "", years: "", proficiency: "" };
const PROFICIENCY_SELECT = [{ value: "", label: "Not specified" }, ...PROFICIENCY_OPTIONS];

export function SkillsSection() {
  const query = useProfile();
  return (
    <QueryState query={query}>
      {(profile) => (
        <SkillList skills={[...profile.skills].sort((a, b) => a.name.localeCompare(b.name))} />
      )}
    </QueryState>
  );
}

function SkillList({ skills }: { skills: Skill[] }) {
  const [editing, setEditing] = useState<string | null>(null);
  const remove = useDeleteSkill();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  return (
    <div className="space-y-5">
      <SkillForm key="new" />
      <FormError message={deleteError} />
      {skills.length === 0 ? (
        <p className="text-sm text-muted">No skills yet. Add the ones you’d want a recruiter to see.</p>
      ) : (
        <ul className="divide-y divide-line rounded-lg border border-line" aria-label="Your skills">
          {skills.map((skill) =>
            editing === skill.id ? (
              <li key={skill.id} className="p-3">
                <SkillForm skill={skill} onDone={() => setEditing(null)} />
              </li>
            ) : (
              <li key={skill.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
                <div className="text-sm">
                  <span className="font-medium">{skill.name}</span>
                  <span className="text-muted">
                    {[
                      skill.years !== null && `${skill.years} ${skill.years === 1 ? "year" : "years"}`,
                      labelFor(PROFICIENCY_OPTIONS, skill.proficiency),
                    ]
                      .filter(Boolean)
                      .map((part) => ` · ${part}`)
                      .join("")}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" aria-label={`Edit ${skill.name}`} onClick={() => setEditing(skill.id)}>
                    Edit
                  </Button>
                  <ConfirmButton
                    label="Remove"
                    ariaLabel={`Remove ${skill.name}`}
                    onConfirm={async () => {
                      setDeleteError(null);
                      try {
                        await remove.mutateAsync(skill.id);
                      } catch (error) {
                        setDeleteError(describeError(error));
                      }
                    }}
                  />
                </div>
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}

function SkillForm({ skill, onDone }: { skill?: Skill; onDone?: () => void }) {
  const add = useAddSkill();
  const update = useUpdateSkill();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: skill
      ? { name: skill.name, years: numberToInput(skill.years), proficiency: skill.proficiency ?? "" }
      : EMPTY,
  });
  const { errors, isSubmitting } = form.formState;
  const prefix = skill ? `skill-${skill.id}` : "skill-new";

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (skill) {
        await update.mutateAsync({ id: skill.id, data: values });
        onDone?.();
      } else {
        await add.mutateAsync(values);
        form.reset(EMPTY);
        form.setFocus("name");
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        form.setError("name", { type: "server", message: "You've already added this skill." }, { shouldFocus: true });
        return;
      }
      setFormError(applyApiError(error, form.setError, FIELDS));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate aria-label={skill ? `Edit ${skill.name}` : "Add a skill"} className="space-y-3">
      <FormError message={formError} />
      <div className="grid items-start gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.3fr)_auto]">
        <TextField
          id={`${prefix}-name`}
          label="Skill"
          placeholder="e.g. Python"
          error={errors.name?.message}
          {...form.register("name")}
        />
        <TextField
          id={`${prefix}-years`}
          label="Years"
          optional
          inputMode="decimal"
          error={errors.years?.message}
          {...form.register("years")}
        />
        <SelectField
          id={`${prefix}-proficiency`}
          label="Proficiency"
          optional
          options={PROFICIENCY_SELECT}
          error={errors.proficiency?.message}
          {...form.register("proficiency")}
        />
        <div className="flex gap-2 sm:pt-6.5">
          {skill && (
            <Button variant="ghost" onClick={onDone}>
              Cancel
            </Button>
          )}
          <Button type="submit" variant={skill ? "primary" : "secondary"} loading={isSubmitting}>
            {skill ? "Save" : "Add skill"}
          </Button>
        </div>
      </div>
    </form>
  );
}
