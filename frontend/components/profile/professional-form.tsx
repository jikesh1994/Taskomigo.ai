"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormActions, FormError, useSavedFlag, type FormSlots } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { SelectField, TextAreaField, TextField } from "@/components/ui/field";
import { useProfile, useUpdateProfile } from "@/hooks/use-profile";
import { applyApiError } from "@/lib/form-errors";
import { TRI_STATE_OPTIONS } from "@/lib/options";
import {
  numberToInput,
  optionalNumber,
  optionalText,
  optionalUrl,
  toTriState,
  triStateSchema,
} from "@/lib/validation";
import type { Profile } from "@/types/api";

const schema = z.object({
  headline: optionalText(200),
  current_title: optionalText(200),
  current_company: optionalText(200),
  years_of_experience: optionalNumber({ min: 0, max: 60 }),
  summary: optionalText(5000),
  notice_period_days: optionalNumber({ min: 0, max: 365, integer: true }),
  work_authorization: optionalText(255),
  sponsorship_required: triStateSchema,
  willing_to_relocate: triStateSchema,
  linkedin_url: optionalUrl,
  github_url: optionalUrl,
  portfolio_url: optionalUrl,
});

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = Object.keys(schema.shape) as (keyof Input)[];

function toInput(profile: Profile): Input {
  return {
    headline: profile.headline ?? "",
    current_title: profile.current_title ?? "",
    current_company: profile.current_company ?? "",
    years_of_experience: numberToInput(profile.years_of_experience),
    summary: profile.summary ?? "",
    notice_period_days: numberToInput(profile.notice_period_days),
    work_authorization: profile.work_authorization ?? "",
    sponsorship_required: toTriState(profile.sponsorship_required),
    willing_to_relocate: toTriState(profile.willing_to_relocate),
    linkedin_url: profile.linkedin_url ?? "",
    github_url: profile.github_url ?? "",
    portfolio_url: profile.portfolio_url ?? "",
  };
}

export function ProfessionalForm(slots: FormSlots) {
  const query = useProfile();
  return <QueryState query={query}>{(profile) => <Inner profile={profile} {...slots} />}</QueryState>;
}

function Inner({ profile, submitLabel, onSaved, secondaryAction }: FormSlots & { profile: Profile }) {
  const update = useUpdateProfile();
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, markSaved] = useSavedFlag();
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: toInput(profile),
  });
  const { errors, isSubmitting } = form.formState;

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

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <FormError message={formError} />
      <TextField
        id="headline"
        label="Professional headline"
        optional
        placeholder="Senior Python Engineer · Distributed systems"
        error={errors.headline?.message}
        {...form.register("headline")}
      />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          id="current_title"
          label="Current job title"
          optional
          autoComplete="organization-title"
          error={errors.current_title?.message}
          {...form.register("current_title")}
        />
        <TextField
          id="current_company"
          label="Current company"
          optional
          autoComplete="organization"
          error={errors.current_company?.message}
          {...form.register("current_company")}
        />
        <TextField
          id="years_of_experience"
          label="Total years of experience"
          optional
          inputMode="decimal"
          error={errors.years_of_experience?.message}
          {...form.register("years_of_experience")}
        />
        <TextField
          id="notice_period_days"
          label="Notice period (days)"
          optional
          inputMode="numeric"
          error={errors.notice_period_days?.message}
          {...form.register("notice_period_days")}
        />
      </div>
      <TextAreaField
        id="summary"
        label="Professional summary"
        optional
        rows={5}
        hint="A few sentences in your own words. The agent only uses what you write here; it never invents experience."
        error={errors.summary?.message}
        {...form.register("summary")}
      />

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">Work eligibility</legend>
        <p className="text-sm text-muted">
          Leave these as “Not specified” if unsure. The agent will ask you instead of guessing.
        </p>
        <TextField
          id="work_authorization"
          label="Work authorization"
          optional
          placeholder="e.g. Indian citizen; US H-1B; EU Blue Card"
          error={errors.work_authorization?.message}
          {...form.register("work_authorization")}
        />
        <div className="grid gap-5 sm:grid-cols-2">
          <SelectField
            id="sponsorship_required"
            label="Require visa sponsorship?"
            options={TRI_STATE_OPTIONS}
            error={errors.sponsorship_required?.message}
            {...form.register("sponsorship_required")}
          />
          <SelectField
            id="willing_to_relocate"
            label="Willing to relocate?"
            options={TRI_STATE_OPTIONS}
            error={errors.willing_to_relocate?.message}
            {...form.register("willing_to_relocate")}
          />
        </div>
      </fieldset>

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">Links</legend>
        <div className="grid gap-5 sm:grid-cols-3">
          <TextField
            id="linkedin_url"
            label="LinkedIn"
            type="url"
            optional
            placeholder="https://linkedin.com/in/…"
            error={errors.linkedin_url?.message}
            {...form.register("linkedin_url")}
          />
          <TextField
            id="github_url"
            label="GitHub"
            type="url"
            optional
            placeholder="https://github.com/…"
            error={errors.github_url?.message}
            {...form.register("github_url")}
          />
          <TextField
            id="portfolio_url"
            label="Portfolio"
            type="url"
            optional
            placeholder="https://…"
            error={errors.portfolio_url?.message}
            {...form.register("portfolio_url")}
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
