"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormError } from "@/components/forms/form-actions";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { useAuth } from "@/hooks/use-auth";
import { applyApiError } from "@/lib/form-errors";
import { browserTimeZone } from "@/lib/options";
import { emailSchema, passwordSchema, requiredText } from "@/lib/validation";
import { ApiError } from "@/services/errors";

const schema = z.object({
  first_name: requiredText(100, "Enter your first name"),
  last_name: requiredText(100, "Enter your last name"),
  email: emailSchema,
  password: passwordSchema,
});

type Values = z.infer<typeof schema>;
const FIELDS = ["first_name", "last_name", "email", "password"] as const;

export function RegisterForm() {
  const { register: signUp } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { first_name: "", last_name: "", email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await signUp({ ...values, timezone: browserTimeZone() });
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_taken") {
        form.setError("email", { type: "server", message: error.message }, { shouldFocus: true });
        return;
      }
      setFormError(applyApiError(error, form.setError, FIELDS));
    }
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Create your account</h1>
        <p className="mt-1 text-sm text-muted">
          Set up your profile once. Your agent applies with it, and asks you whenever it isn’t sure.
        </p>
      </div>
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <FormError message={formError} />
        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            id="first_name"
            label="First name"
            autoComplete="given-name"
            autoFocus
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
        </div>
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...form.register("email")}
        />
        <TextField
          id="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          hint="At least 10 characters, with a letter and a number."
          error={errors.password?.message}
          {...form.register("password")}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create account
        </Button>
      </form>
      <p className="text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
