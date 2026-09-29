"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormActions, FormError, useSavedFlag, type FormSlots } from "@/components/forms/form-actions";
import { SelectField, TextField } from "@/components/ui/field";
import { useAuth, useCurrentUser } from "@/hooks/use-auth";
import { applyApiError } from "@/lib/form-errors";
import { timeZoneOptions } from "@/lib/options";
import { phoneSchema, requiredText } from "@/lib/validation";
import { usersApi } from "@/services/users";

const schema = z.object({
  first_name: requiredText(100, "Enter your first name"),
  last_name: requiredText(100, "Enter your last name"),
  phone: phoneSchema,
  timezone: z.string().min(1, "Choose your timezone"),
});

type Input = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = ["first_name", "last_name", "phone", "timezone"] as const;

export function PersonalForm({ submitLabel, onSaved, secondaryAction }: FormSlots) {
  const user = useCurrentUser();
  const { setUser } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, markSaved] = useSavedFlag();
  const zones = useMemo(() => timeZoneOptions(user.timezone), [user.timezone]);

  const form = useForm<Input, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone ?? "",
      timezone: user.timezone,
    },
  });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      setUser(await usersApi.update(values));
      markSaved();
      onSaved?.();
    } catch (error) {
      setFormError(applyApiError(error, form.setError, FIELDS));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <FormError message={formError} />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          id="first_name"
          label="First name"
          autoComplete="given-name"
          error={errors.first_name?.message}
          {...form.register("first_name")}
        />
        <TextField
          id="last_name"
          label="Last name"
          autoComplete="family-name"
          error={errors.last_name?.message}
          {...form.register("last_name")}
        />
        <TextField
          id="email"
          label="Email"
          value={user.email}
          disabled
          readOnly
          hint="Your sign-in email can't be changed here."
        />
        <TextField
          id="phone"
          label="Phone"
          type="tel"
          autoComplete="tel"
          optional
          placeholder="+91 98765 43210"
          error={errors.phone?.message}
          {...form.register("phone")}
        />
        <SelectField
          id="timezone"
          label="Timezone"
          options={zones}
          hint="Used for scheduling and notification times."
          error={errors.timezone?.message}
          {...form.register("timezone")}
        />
      </div>
      <FormActions
        submitLabel={submitLabel}
        submitting={isSubmitting}
        secondaryAction={secondaryAction}
        saved={saved && !onSaved}
      />
    </form>
  );
}
