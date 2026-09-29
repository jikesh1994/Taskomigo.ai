"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FormError } from "@/components/forms/form-actions";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TextField } from "@/components/ui/field";
import { useAuth } from "@/hooks/use-auth";
import { applyApiError } from "@/lib/form-errors";
import { emailSchema } from "@/lib/validation";

const schema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Enter your password"),
});

type Values = z.infer<typeof schema>;

export function LoginForm() {
  const { login, endReason } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  // RedirectIfAuthenticated navigates once the session is set.
  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login(values);
    } catch (error) {
      setFormError(applyApiError(error, form.setError, ["email", "password"]));
      form.setValue("password", "");
    }
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Sign in</h1>
        <p className="mt-1 text-sm text-muted">Welcome back. Your agent is waiting.</p>
      </div>
      {endReason === "expired" && !formError && (
        <Alert tone="warning">Your session ended. Please sign in again.</Alert>
      )}
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <FormError message={formError} />
        <TextField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          autoFocus
          error={errors.email?.message}
          {...form.register("email")}
        />
        <TextField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...form.register("password")}
        />
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Sign in
        </Button>
      </form>
      <p className="text-center text-sm text-muted">
        New here?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
