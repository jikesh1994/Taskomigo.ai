"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { FormError } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { ConfirmButton } from "@/components/ui/confirm-button";
import { Checkbox, SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { TagInput } from "@/components/ui/tag-input";
import {
  useAddExperience,
  useDeleteExperience,
  useProfile,
  useUpdateExperience,
} from "@/hooks/use-profile";
import { currentMonth, formatRange, fromMonthInput, toMonthInput } from "@/lib/dates";
import { applyApiError } from "@/lib/form-errors";
import { EMPLOYMENT_TYPE_OPTIONS, labelFor } from "@/lib/options";
import { optionalText, requiredText } from "@/lib/validation";
import { describeError } from "@/services/errors";
import type { EmploymentType, Experience } from "@/types/api";

const schema = z
  .object({
    title: requiredText(200, "Enter your job title"),
    company: requiredText(200, "Enter the company name"),
    location: optionalText(200),
    employment_type: z.string(),
    start_month: z.string().regex(/^\d{4}-\d{2}$/, "Choose a start month"),
    end_month: z.string(),
    is_current: z.boolean(),
    description: optionalText(10000),
    technologies: z.array(z.string()).max(50),
  })
  .superRefine((v, ctx) => {
    if (v.start_month > currentMonth()) {
      ctx.addIssue({ code: "custom", path: ["start_month"], message: "Start can't be in the future" });
    }
    if (!v.is_current && v.end_month && v.end_month < v.start_month) {
      ctx.addIssue({ code: "custom", path: ["end_month"], message: "End can't be before the start" });
    }
  })
  .transform((v) => ({
    title: v.title,
    company: v.company,
    location: v.location,
    employment_type: (v.employment_type || null) as EmploymentType | null,
    start_date: fromMonthInput(v.start_month) as string,
    end_date: v.is_current ? null : fromMonthInput(v.end_month),
    is_current: v.is_current,
    description: v.description,
    technologies: v.technologies,
  }));

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;

const FIELDS = [
  "title",
  "company",
  "location",
  "employment_type",
  "start_month",
  "end_month",
  "is_current",
  "description",
  "technologies",
] as const;
const ALIASES = { start_date: "start_month", end_date: "end_month" } as const;

const EMPTY: Input = {
  title: "",
  company: "",
  location: "",
  employment_type: "",
  start_month: "",
  end_month: "",
  is_current: false,
  description: "",
  technologies: [],
};

function toInput(experience: Experience): Input {
  return {
    title: experience.title,
    company: experience.company,
    location: experience.location ?? "",
    employment_type: experience.employment_type ?? "",
    start_month: toMonthInput(experience.start_date),
    end_month: toMonthInput(experience.end_date),
    is_current: experience.is_current,
    description: experience.description ?? "",
    technologies: experience.technologies,
  };
}

function sortExperiences(items: Experience[]): Experience[] {
  return [...items].sort((a, b) => {
    if (a.is_current !== b.is_current) return a.is_current ? -1 : 1;
    return b.start_date.localeCompare(a.start_date);
  });
}

export function ExperienceSection() {
  const query = useProfile();
  return (
    <QueryState query={query}>
      {(profile) => <ExperienceList experiences={sortExperiences(profile.experiences)} />}
    </QueryState>
  );
}

function ExperienceList({ experiences }: { experiences: Experience[] }) {
  const [editing, setEditing] = useState<string | "new" | null>(experiences.length === 0 ? "new" : null);
  const remove = useDeleteExperience();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <FormError message={deleteError} />
      {experiences.length > 0 && (
        <ul className="space-y-3">
          {experiences.map((experience) =>
            editing === experience.id ? (
              <li key={experience.id}>
                <ExperienceForm experience={experience} onDone={() => setEditing(null)} />
              </li>
            ) : (
              <li key={experience.id} className="rounded-lg border border-line p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">
                      {experience.title} · {experience.company}
                    </p>
                    <p className="text-sm text-muted">
                      {[
                        formatRange(experience.start_date, experience.end_date, experience.is_current),
                        labelFor(EMPLOYMENT_TYPE_OPTIONS, experience.employment_type),
                        experience.location,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Edit ${experience.title} at ${experience.company}`}
                      onClick={() => setEditing(experience.id)}
                    >
                      Edit
                    </Button>
                    <ConfirmButton
                      label="Delete"
                      ariaLabel={`Delete ${experience.title} at ${experience.company}`}
                      onConfirm={async () => {
                        setDeleteError(null);
                        try {
                          await remove.mutateAsync(experience.id);
                        } catch (error) {
                          setDeleteError(describeError(error));
                        }
                      }}
                    />
                  </div>
                </div>
                {experience.technologies.length > 0 && (
                  <p className="mt-2 text-sm text-muted">{experience.technologies.join(", ")}</p>
                )}
              </li>
            ),
          )}
        </ul>
      )}
      {editing === "new" ? (
        <ExperienceForm
          onDone={() => setEditing(null)}
          onCancel={experiences.length > 0 ? () => setEditing(null) : undefined}
        />
      ) : (
        <Button variant="secondary" onClick={() => setEditing("new")}>
          Add experience
        </Button>
      )}
    </div>
  );
}

interface ExperienceFormProps {
  experience?: Experience;
  onDone: () => void;
  onCancel?: () => void;
}

function ExperienceForm({ experience, onDone, onCancel }: ExperienceFormProps) {
  const add = useAddExperience();
  const update = useUpdateExperience();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: experience ? toInput(experience) : EMPTY,
  });
  const { errors, isSubmitting } = form.formState;
  const isCurrent = useWatch({ control: form.control, name: "is_current" });
  const prefix = experience ? `exp-${experience.id}` : "exp-new";

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (experience) await update.mutateAsync({ id: experience.id, data: values });
      else await add.mutateAsync(values);
      onDone();
    } catch (error) {
      setFormError(applyApiError(error, form.setError, FIELDS, ALIASES));
    }
  });

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      aria-label={experience ? "Edit experience" : "Add experience"}
      className="space-y-5 rounded-lg border border-line bg-surface-2/50 p-4"
    >
      <FormError message={formError} />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField id={`${prefix}-title`} label="Job title" error={errors.title?.message} {...form.register("title")} />
        <TextField id={`${prefix}-company`} label="Company" error={errors.company?.message} {...form.register("company")} />
        <TextField
          id={`${prefix}-location`}
          label="Location"
          optional
          error={errors.location?.message}
          {...form.register("location")}
        />
        <SelectField
          id={`${prefix}-employment_type`}
          label="Employment type"
          optional
          options={[{ value: "", label: "Not specified" }, ...EMPLOYMENT_TYPE_OPTIONS]}
          error={errors.employment_type?.message}
          {...form.register("employment_type")}
        />
        <TextField
          id={`${prefix}-start`}
          label="Start month"
          type="month"
          max={currentMonth()}
          error={errors.start_month?.message}
          {...form.register("start_month")}
        />
        <TextField
          id={`${prefix}-end`}
          label="End month"
          type="month"
          disabled={isCurrent}
          optional={!isCurrent}
          error={errors.end_month?.message}
          {...form.register("end_month")}
        />
      </div>
      <Checkbox id={`${prefix}-current`} label="I currently work here" {...form.register("is_current")} />
      <TextAreaField
        id={`${prefix}-description`}
        label="What you did"
        optional
        rows={4}
        hint="Responsibilities and achievements, in your own words."
        error={errors.description?.message}
        {...form.register("description")}
      />
      <Controller
        control={form.control}
        name="technologies"
        render={({ field, fieldState }) => (
          <TagInput
            id={`${prefix}-technologies`}
            label="Technologies used"
            optional
            placeholder="Type and press Enter, e.g. Python"
            value={field.value}
            onChange={field.onChange}
            error={fieldState.error?.message}
          />
        )}
      />
      <div className="flex justify-end gap-3">
        {(onCancel || experience) && (
          <Button variant="ghost" onClick={onCancel ?? onDone}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={isSubmitting}>
          {experience ? "Save experience" : "Add experience"}
        </Button>
      </div>
    </form>
  );
}
