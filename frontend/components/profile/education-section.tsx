"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormError } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { ConfirmButton } from "@/components/ui/confirm-button";
import { TextField } from "@/components/ui/field";
import {
  useAddEducation,
  useDeleteEducation,
  useProfile,
  useUpdateEducation,
} from "@/hooks/use-profile";
import { formatRange, fromMonthInput, toMonthInput } from "@/lib/dates";
import { applyApiError } from "@/lib/form-errors";
import { optionalText, requiredText } from "@/lib/validation";
import { describeError } from "@/services/errors";
import type { Education } from "@/types/api";

const schema = z
  .object({
    institution: requiredText(200, "Enter the institution"),
    degree: requiredText(200, "Enter the degree or qualification"),
    field_of_study: optionalText(200),
    start_month: z.string(),
    end_month: z.string(),
    grade: optionalText(50),
  })
  .superRefine((v, ctx) => {
    if (v.start_month && v.end_month && v.end_month < v.start_month) {
      ctx.addIssue({ code: "custom", path: ["end_month"], message: "End can't be before the start" });
    }
  })
  .transform((v) => ({
    institution: v.institution,
    degree: v.degree,
    field_of_study: v.field_of_study,
    start_date: fromMonthInput(v.start_month),
    end_date: fromMonthInput(v.end_month),
    grade: v.grade,
  }));

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = ["institution", "degree", "field_of_study", "start_month", "end_month", "grade"] as const;
const ALIASES = { start_date: "start_month", end_date: "end_month" } as const;

const EMPTY: Input = {
  institution: "",
  degree: "",
  field_of_study: "",
  start_month: "",
  end_month: "",
  grade: "",
};

function toInput(education: Education): Input {
  return {
    institution: education.institution,
    degree: education.degree,
    field_of_study: education.field_of_study ?? "",
    start_month: toMonthInput(education.start_date),
    end_month: toMonthInput(education.end_date),
    grade: education.grade ?? "",
  };
}

export function EducationSection() {
  const query = useProfile();
  return (
    <QueryState query={query}>
      {(profile) => (
        <EducationList
          items={[...profile.education].sort((a, b) =>
            (b.end_date ?? b.start_date ?? "").localeCompare(a.end_date ?? a.start_date ?? ""),
          )}
        />
      )}
    </QueryState>
  );
}

function EducationList({ items }: { items: Education[] }) {
  const [editing, setEditing] = useState<string | "new" | null>(items.length === 0 ? "new" : null);
  const remove = useDeleteEducation();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <FormError message={deleteError} />
      {items.length > 0 && (
        <ul className="space-y-3">
          {items.map((item) =>
            editing === item.id ? (
              <li key={item.id}>
                <EducationForm education={item} onDone={() => setEditing(null)} />
              </li>
            ) : (
              <li key={item.id} className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-line p-4">
                <div>
                  <p className="font-medium">
                    {item.degree}
                    {item.field_of_study ? `, ${item.field_of_study}` : ""}
                  </p>
                  <p className="text-sm text-muted">
                    {[item.institution, formatRange(item.start_date, item.end_date), item.grade]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Edit ${item.degree} at ${item.institution}`}
                    onClick={() => setEditing(item.id)}
                  >
                    Edit
                  </Button>
                  <ConfirmButton
                    label="Delete"
                    ariaLabel={`Delete ${item.degree} at ${item.institution}`}
                    onConfirm={async () => {
                      setDeleteError(null);
                      try {
                        await remove.mutateAsync(item.id);
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
      {editing === "new" ? (
        <EducationForm
          onDone={() => setEditing(null)}
          onCancel={items.length > 0 ? () => setEditing(null) : undefined}
        />
      ) : (
        <Button variant="secondary" onClick={() => setEditing("new")}>
          Add education
        </Button>
      )}
    </div>
  );
}

interface EducationFormProps {
  education?: Education;
  onDone: () => void;
  onCancel?: () => void;
}

function EducationForm({ education, onDone, onCancel }: EducationFormProps) {
  const add = useAddEducation();
  const update = useUpdateEducation();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: education ? toInput(education) : EMPTY,
  });
  const { errors, isSubmitting } = form.formState;
  const prefix = education ? `edu-${education.id}` : "edu-new";

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (education) await update.mutateAsync({ id: education.id, data: values });
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
      aria-label={education ? "Edit education" : "Add education"}
      className="space-y-5 rounded-lg border border-line bg-surface-2/50 p-4"
    >
      <FormError message={formError} />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          id={`${prefix}-institution`}
          label="Institution"
          error={errors.institution?.message}
          {...form.register("institution")}
        />
        <TextField
          id={`${prefix}-degree`}
          label="Degree or qualification"
          placeholder="B.Tech, MSc, …"
          error={errors.degree?.message}
          {...form.register("degree")}
        />
        <TextField
          id={`${prefix}-field`}
          label="Field of study"
          optional
          error={errors.field_of_study?.message}
          {...form.register("field_of_study")}
        />
        <TextField
          id={`${prefix}-grade`}
          label="Grade"
          optional
          placeholder="8.6 CGPA, First class, …"
          error={errors.grade?.message}
          {...form.register("grade")}
        />
        <TextField
          id={`${prefix}-start`}
          label="Start month"
          type="month"
          optional
          error={errors.start_month?.message}
          {...form.register("start_month")}
        />
        <TextField
          id={`${prefix}-end`}
          label="End month (or expected)"
          type="month"
          optional
          error={errors.end_month?.message}
          {...form.register("end_month")}
        />
      </div>
      <div className="flex justify-end gap-3">
        {(onCancel || education) && (
          <Button variant="ghost" onClick={onCancel ?? onDone}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={isSubmitting}>
          {education ? "Save education" : "Add education"}
        </Button>
      </div>
    </form>
  );
}
