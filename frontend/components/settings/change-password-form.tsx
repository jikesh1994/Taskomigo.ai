"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormActions, FormError } from "@/components/forms/form-actions";
import { Alert } from "@/components/ui/alert";
import { TextField } from "@/components/ui/field";
import { useAuth, useCurrentUser } from "@/hooks/use-auth";
import { applyApiError } from "@/lib/form-errors";
import { passwordSchema } from "@/lib/validation";
import { ApiError } from "@/services/errors";
import { usersApi } from "@/services/users";

const schema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: passwordSchema,
    confirm_password: z.string(),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords don't match",
  })
  .refine((v) => v.new_password !== v.current_password, {
    path: ["new_password"],
    message: "Choose a password different from your current one",
  });

type Values = z.infer<typeof schema>;
const FIELDS = ["current_password", "new_password", "confirm_password"] as const;
const EMPTY: Values = { current_password: "", new_password: "", confirm_password: "" };

export function ChangePasswordForm() {
  const user = useCurrentUser();
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: EMPTY });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    setDone(false);
    try {
      await usersApi.changePassword({
        current_password: values.current_password,
        new_password: values.new_password,
      });
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_current_password") {
        form.setError("current_password", { type: "server", message: error.message }, { shouldFocus: true });
      } else {
        setFormError(applyApiError(error, form.setError, FIELDS));
      }
      return;
    }
    // Changing the password signs out every session, including this one. Sign straight
    // back in with the new password so the user isn't bounced to the login page.
    try {
      await login({ email: user.email, password: values.new_password });
    } catch {
      // The password did change; they'll be asked to sign in on the next request.
    }
    form.reset(EMPTY);
    setDone(true);
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      {done && (
        <Alert tone="success" title="Password changed">
          You’ve been signed out on all other devices.
        </Alert>
      )}
      <FormError message={formError} />
      <input type="email" autoComplete="username" value={user.email} readOnly hidden />
      <TextField
        id="current_password"
        label="Current password"
        type="password"
        autoComplete="current-password"
        className="sm:max-w-sm"
        error={errors.current_password?.message}
        {...form.register("current_password")}
      />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          id="new_password"
          label="New password"
          type="password"
          autoComplete="new-password"
          hint="At least 10 characters, with a letter and a number."
          error={errors.new_password?.message}
          {...form.register("new_password")}
        />
        <TextField
          id="confirm_password"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...form.register("confirm_password")}
        />
      </div>
      <FormActions submitLabel="Change password" submitting={isSubmitting} />
    </form>
  );
}
