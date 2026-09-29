"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { FormActions, FormError, useSavedFlag, type FormSlots } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Alert } from "@/components/ui/alert";
import { TextField } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { usePreferences, useUpdatePreferences } from "@/hooks/use-preferences";
import { applyApiError } from "@/lib/form-errors";
import { requiredInteger } from "@/lib/validation";
import type { Preferences } from "@/types/api";

// Upper bounds here are only for input sanity; the backend enforces the real
// platform-wide caps and its error is shown on the field.
const schema = z
  .object({
    auto_fill_enabled: z.boolean(),
    auto_answer_enabled: z.boolean(),
    review_before_submit: z.boolean(),
    auto_submit_enabled: z.boolean(),
    min_match_score: requiredInteger({ min: 0, max: 100 }),
    max_applications_per_day: requiredInteger({ min: 0, max: 1000 }),
    max_concurrent_browser_sessions: requiredInteger({ min: 1, max: 50 }),
    max_retries_per_application: requiredInteger({ min: 0, max: 20 }),
  })
  .refine((v) => !(v.auto_submit_enabled && v.review_before_submit), {
    path: ["auto_submit_enabled"],
    message: "Turn off “Review before submitting” to allow automatic submission.",
  });

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = Object.keys(schema.shape) as (keyof Input)[];

function toInput(p: Preferences): Input {
  return {
    auto_fill_enabled: p.auto_fill_enabled,
    auto_answer_enabled: p.auto_answer_enabled,
    review_before_submit: p.review_before_submit,
    auto_submit_enabled: p.auto_submit_enabled,
    min_match_score: String(p.min_match_score),
    max_applications_per_day: String(p.max_applications_per_day),
    max_concurrent_browser_sessions: String(p.max_concurrent_browser_sessions),
    max_retries_per_application: String(p.max_retries_per_application),
  };
}

/** How much the agent may do without asking: autonomy switches and limits. */
export function AgentSettingsForm(slots: FormSlots) {
  const query = usePreferences();
  return <QueryState query={query}>{(preferences) => <Inner preferences={preferences} {...slots} />}</QueryState>;
}

function Inner({ preferences, submitLabel, onSaved, secondaryAction }: FormSlots & { preferences: Preferences }) {
  const update = useUpdatePreferences();
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, markSaved] = useSavedFlag();
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: toInput(preferences),
  });
  const { errors, isSubmitting } = form.formState;
  const reviewBeforeSubmit = useWatch({ control: form.control, name: "review_before_submit" });

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await update.mutateAsync(values);
      markSaved();
      onSaved?.();
    } catch (error) {
      setFormError(applyApiError(error, form.setError, FIELDS));
    }
  });

  const toggle = (name: "auto_fill_enabled" | "auto_answer_enabled", label: string, description: string) => (
    <Controller
      control={form.control}
      name={name}
      render={({ field }) => (
        <Switch id={name} label={label} description={description} checked={field.value} onChange={field.onChange} />
      )}
    />
  );

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-8">
      <FormError message={formError} />

      <Alert tone="info" title="You stay in control">
        Whatever you choose here, the agent always stops and asks you before account creation,
        CAPTCHA or MFA steps, legal declarations, sensitive questions, and any answer it isn’t
        confident about. It only uses information from your profile and resumes.
      </Alert>

      <fieldset>
        <legend className="text-sm font-semibold">What the agent may do</legend>
        <div className="mt-2 divide-y divide-line">
          {toggle(
            "auto_fill_enabled",
            "Fill standard fields automatically",
            "Name, contact details, work history and other facts copied from your profile.",
          )}
          {toggle(
            "auto_answer_enabled",
            "Draft answers to application questions",
            "Written only from your verified profile. Low-confidence answers still come to you.",
          )}
          <Controller
            control={form.control}
            name="review_before_submit"
            render={({ field }) => (
              <Switch
                id="review_before_submit"
                label="Review before submitting"
                description="You see and approve every completed application before it's sent. Recommended."
                checked={field.value}
                onChange={(checked) => {
                  field.onChange(checked);
                  if (checked) form.setValue("auto_submit_enabled", false, { shouldValidate: true });
                }}
              />
            )}
          />
          <Controller
            control={form.control}
            name="auto_submit_enabled"
            render={({ field }) => (
              <Switch
                id="auto_submit_enabled"
                label="Submit routine applications automatically"
                description={
                  reviewBeforeSubmit
                    ? "Available only when “Review before submitting” is off."
                    : "Applications with no open questions are sent without waiting for you."
                }
                checked={field.value}
                disabled={reviewBeforeSubmit}
                onChange={field.onChange}
              />
            )}
          />
        </div>
        {errors.auto_submit_enabled && (
          <p className="text-xs text-danger" role="alert">
            {errors.auto_submit_enabled.message}
          </p>
        )}
      </fieldset>

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">Limits</legend>
        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            id="min_match_score"
            label="Minimum match score (0–100)"
            inputMode="numeric"
            hint="Jobs scoring below this are skipped. The score explains fit; it doesn't predict hiring."
            error={errors.min_match_score?.message}
            {...form.register("min_match_score")}
          />
          <TextField
            id="max_applications_per_day"
            label="Applications per day"
            inputMode="numeric"
            error={errors.max_applications_per_day?.message}
            {...form.register("max_applications_per_day")}
          />
          <TextField
            id="max_concurrent_browser_sessions"
            label="Browser sessions at once"
            inputMode="numeric"
            error={errors.max_concurrent_browser_sessions?.message}
            {...form.register("max_concurrent_browser_sessions")}
          />
          <TextField
            id="max_retries_per_application"
            label="Retries per application"
            inputMode="numeric"
            hint="Submissions are never retried blindly."
            error={errors.max_retries_per_application?.message}
            {...form.register("max_retries_per_application")}
          />
        </div>
      </fieldset>

      <FormActions
        submitLabel={submitLabel}
        submitting={isSubmitting}
        secondaryAction={secondaryAction}
        saved={saved && !onSaved}
      />
    </form>
  );
}
