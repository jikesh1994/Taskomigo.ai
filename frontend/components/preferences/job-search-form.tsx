"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { FormActions, FormError, useSavedFlag, type FormSlots } from "@/components/forms/form-actions";
import { QueryState } from "@/components/query-state";
import { Checkbox, SelectField, TextField } from "@/components/ui/field";
import { TagInput } from "@/components/ui/tag-input";
import { usePreferences, useUpdatePreferences } from "@/hooks/use-preferences";
import { useProfile, useUpdateProfile } from "@/hooks/use-profile";
import { applyApiError } from "@/lib/form-errors";
import { EMPLOYMENT_TYPE_OPTIONS, REMOTE_PREFERENCE_OPTIONS, currencyOptions } from "@/lib/options";
import { numberToInput, optionalNumber } from "@/lib/validation";
import type { EmploymentType, Preferences, Profile, RemotePreference } from "@/types/api";

const salary = () => optionalNumber({ min: 0, max: 1_000_000_000, integer: true });
const list = z.array(z.string()).max(50, "Keep it to 50 entries or fewer");

const schema = z
  .object({
    preferred_titles: list,
    preferred_locations: list,
    remote_preference: z.enum(["any", "remote", "hybrid", "onsite"]),
    remote_only: z.boolean(),
    employment_types: z.array(z.string()),
    keywords: list,
    excluded_companies: list,
    excluded_industries: list,
    currency: z.string(),
    expected_salary_min: salary(),
    expected_salary_max: salary(),
    min_salary: salary(),
  })
  .superRefine((v, ctx) => {
    const { expected_salary_min: lo, expected_salary_max: hi } = v;
    if (lo !== null && hi !== null && lo > hi) {
      ctx.addIssue({ code: "custom", path: ["expected_salary_max"], message: "Must be at least the minimum" });
    }
    if ((lo !== null || hi !== null || v.min_salary !== null) && !v.currency) {
      ctx.addIssue({ code: "custom", path: ["currency"], message: "Choose a currency for your salary figures" });
    }
  });

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = Object.keys(schema.shape) as (keyof Input)[];
// Both endpoints report the currency under their own name.
const ALIASES = { salary_currency: "currency", expected_salary: "expected_salary_max" } as const;

function toInput(profile: Profile, preferences: Preferences): Input {
  return {
    preferred_titles: profile.preferred_titles,
    preferred_locations: profile.preferred_locations,
    remote_preference: profile.remote_preference,
    remote_only: preferences.remote_only,
    employment_types: preferences.employment_types,
    keywords: preferences.keywords,
    excluded_companies: preferences.excluded_companies,
    excluded_industries: preferences.excluded_industries,
    currency: profile.currency ?? preferences.salary_currency ?? "",
    expected_salary_min: numberToInput(profile.expected_salary_min),
    expected_salary_max: numberToInput(profile.expected_salary_max),
    min_salary: numberToInput(preferences.min_salary),
  };
}

/**
 * Job-search criteria. The fields live on two resources: what you'd tell an employer
 * (profile: titles, locations, expected salary) and how the agent filters jobs
 * (preferences: keywords, exclusions, minimum salary). The form saves both.
 */
export function JobSearchForm(slots: FormSlots) {
  const profile = useProfile();
  const preferences = usePreferences();
  return (
    <QueryState query={profile}>
      {(p) => (
        <QueryState query={preferences}>{(prefs) => <Inner profile={p} preferences={prefs} {...slots} />}</QueryState>
      )}
    </QueryState>
  );
}

function Inner({
  profile,
  preferences,
  submitLabel,
  onSaved,
  secondaryAction,
}: FormSlots & { profile: Profile; preferences: Preferences }) {
  const updateProfile = useUpdateProfile();
  const updatePreferences = useUpdatePreferences();
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, markSaved] = useSavedFlag();
  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: toInput(profile, preferences),
  });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (v) => {
    setFormError(null);
    const currency = v.currency || null;
    try {
      // Both PATCHes are idempotent, so retrying after a partial failure is safe.
      await updateProfile.mutateAsync({
        preferred_titles: v.preferred_titles,
        preferred_locations: v.preferred_locations,
        remote_preference: v.remote_preference as RemotePreference,
        expected_salary_min: v.expected_salary_min,
        expected_salary_max: v.expected_salary_max,
        currency,
      });
      await updatePreferences.mutateAsync({
        remote_only: v.remote_only,
        employment_types: v.employment_types as EmploymentType[],
        keywords: v.keywords,
        excluded_companies: v.excluded_companies,
        excluded_industries: v.excluded_industries,
        min_salary: v.min_salary,
        salary_currency: currency,
      });
      markSaved();
      onSaved?.();
    } catch (error) {
      setFormError(applyApiError(error, form.setError, FIELDS, ALIASES));
    }
  });

  const tags = (name: "preferred_titles" | "preferred_locations" | "keywords" | "excluded_companies" | "excluded_industries", label: string, placeholder: string, hint?: string) => (
    <Controller
      control={form.control}
      name={name}
      render={({ field, fieldState }) => (
        <TagInput
          id={name}
          label={label}
          optional
          placeholder={placeholder}
          hint={hint}
          value={field.value}
          onChange={field.onChange}
          error={fieldState.error?.message}
        />
      )}
    />
  );

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-8">
      <FormError message={formError} />

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">What you’re looking for</legend>
        {tags("preferred_titles", "Job titles", "e.g. Senior Backend Engineer")}
        {tags("keywords", "Keywords", "e.g. Django, fintech", "Jobs mentioning these rank higher.")}
        <Controller
          control={form.control}
          name="employment_types"
          render={({ field }) => (
            <fieldset>
              <legend className="text-sm font-medium">Employment types</legend>
              <p className="mb-2 text-xs text-muted">Leave all unchecked to consider any type.</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {EMPLOYMENT_TYPE_OPTIONS.map((option) => (
                  <Checkbox
                    key={option.value}
                    id={`employment-${option.value}`}
                    label={option.label}
                    checked={field.value.includes(option.value)}
                    onChange={(event) =>
                      field.onChange(
                        event.target.checked
                          ? [...field.value, option.value]
                          : field.value.filter((value) => value !== option.value),
                      )
                    }
                  />
                ))}
              </div>
            </fieldset>
          )}
        />
      </fieldset>

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">Where</legend>
        {tags("preferred_locations", "Preferred locations", "e.g. Bengaluru, Remote")}
        <div className="grid gap-5 sm:grid-cols-2">
          <SelectField
            id="remote_preference"
            label="Work arrangement"
            options={REMOTE_PREFERENCE_OPTIONS}
            error={errors.remote_preference?.message}
            {...form.register("remote_preference")}
          />
        </div>
        <Checkbox
          id="remote_only"
          label="Only show remote jobs"
          description="Skip every job that isn't fully remote."
          {...form.register("remote_only")}
        />
      </fieldset>

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">Compensation</legend>
        <div className="grid gap-5 sm:grid-cols-3">
          <SelectField
            id="currency"
            label="Currency"
            options={currencyOptions(form.getValues("currency"))}
            error={errors.currency?.message}
            {...form.register("currency")}
          />
          <TextField
            id="expected_salary_min"
            label="Expected salary from"
            optional
            inputMode="numeric"
            error={errors.expected_salary_min?.message}
            {...form.register("expected_salary_min")}
          />
          <TextField
            id="expected_salary_max"
            label="Expected salary to"
            optional
            inputMode="numeric"
            error={errors.expected_salary_max?.message}
            {...form.register("expected_salary_max")}
          />
        </div>
        <p className="text-xs text-muted">
          Your expected range is used to answer salary questions on applications. Annual, before tax.
        </p>
        <TextField
          id="min_salary"
          label="Minimum salary filter"
          optional
          inputMode="numeric"
          hint="Jobs that advertise less than this are skipped. Jobs without a listed salary are kept."
          className="sm:max-w-xs"
          error={errors.min_salary?.message}
          {...form.register("min_salary")}
        />
      </fieldset>

      <fieldset className="space-y-5">
        <legend className="text-sm font-semibold">Exclusions</legend>
        {tags("excluded_companies", "Companies to avoid", "e.g. your current employer")}
        {tags("excluded_industries", "Industries to avoid", "e.g. gambling")}
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
