import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";
import { AuthProvider } from "@/hooks/use-auth";
import * as authService from "@/services/auth";
import { ApiError } from "@/services/errors";
import { renderWithQuery, testUser } from "../helpers";

vi.mock("@/services/auth", () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  restoreSession: vi.fn(),
}));

const auth = vi.mocked(authService);

beforeEach(() => {
  auth.restoreSession.mockRejectedValue(new ApiError({ status: 401, code: "x", message: "x" }));
});

function renderWithAuth(ui: React.ReactElement) {
  return renderWithQuery(<AuthProvider>{ui}</AuthProvider>);
}

describe("LoginForm", () => {
  it("validates before calling the API", async () => {
    const user = userEvent.setup();
    renderWithAuth(<LoginForm />);
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter your email address")).toBeInTheDocument();
    expect(screen.getByText("Enter your password")).toBeInTheDocument();
    expect(auth.login).not.toHaveBeenCalled();
  });

  it("shows the server's generic message and clears the password on failure", async () => {
    const user = userEvent.setup();
    auth.login.mockRejectedValueOnce(
      new ApiError({ status: 401, code: "invalid_credentials", message: "Invalid email or password." }),
    );
    renderWithAuth(<LoginForm />);

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password-1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveValue("");
  });

  it("explains rate limiting", async () => {
    const user = userEvent.setup();
    auth.login.mockRejectedValueOnce(
      new ApiError({ status: 429, code: "rate_limited", message: "Too many", retryAfterSeconds: 30 }),
    );
    renderWithAuth(<LoginForm />);
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "whatever-123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/wait 30 seconds/)).toBeInTheDocument();
  });
});

describe("RegisterForm", () => {
  async function fill() {
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("First name"), "Ada");
    await user.type(screen.getByLabelText("Last name"), "Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-42");
    await user.click(screen.getByRole("button", { name: "Create account" }));
  }

  it("sends the browser timezone with the registration", async () => {
    auth.register.mockResolvedValueOnce(testUser);
    renderWithAuth(<RegisterForm />);
    await fill();
    await waitFor(() => expect(auth.register).toHaveBeenCalled());
    expect(auth.register).toHaveBeenCalledWith(
      expect.objectContaining({ email: "ada@example.com", timezone: expect.any(String) }),
    );
  });

  it("shows a taken email on the email field", async () => {
    auth.register.mockRejectedValueOnce(
      new ApiError({ status: 409, code: "email_taken", message: "An account with this email already exists." }),
    );
    renderWithAuth(<RegisterForm />);
    await fill();
    expect(await screen.findByText("An account with this email already exists.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });

  it("enforces the password policy client-side", async () => {
    const user = userEvent.setup();
    renderWithAuth(<RegisterForm />);
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Use at least 10 characters")).toBeInTheDocument();
    expect(auth.register).not.toHaveBeenCalled();
  });
});
