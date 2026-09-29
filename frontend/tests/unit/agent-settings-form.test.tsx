import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AgentSettingsForm } from "@/components/preferences/agent-settings-form";
import { ApiError } from "@/services/errors";
import { preferencesApi } from "@/services/preferences";
import { renderWithQuery, testPreferences } from "../helpers";

vi.mock("@/services/preferences", () => ({
  preferencesApi: { get: vi.fn(), update: vi.fn() },
}));

const api = vi.mocked(preferencesApi);

beforeEach(() => {
  api.get.mockResolvedValue(testPreferences);
  api.update.mockImplementation(async (data) => ({ ...testPreferences, ...data }));
});

async function renderForm(onSaved = vi.fn()) {
  renderWithQuery(<AgentSettingsForm onSaved={onSaved} submitLabel="Save" />);
  await screen.findByRole("switch", { name: /review before submitting/i });
  return onSaved;
}

describe("AgentSettingsForm", () => {
  it("only allows automatic submission once review-before-submit is off", async () => {
    const user = userEvent.setup();
    await renderForm();
    const review = screen.getByRole("switch", { name: /review before submitting/i });
    const autoSubmit = screen.getByRole("switch", { name: /submit routine applications/i });

    expect(review).toHaveAttribute("aria-checked", "true");
    expect(autoSubmit).toBeDisabled();

    await user.click(review);
    expect(autoSubmit).toBeEnabled();
    await user.click(autoSubmit);
    expect(autoSubmit).toHaveAttribute("aria-checked", "true");

    // Turning review back on switches automatic submission off again.
    await user.click(review);
    expect(autoSubmit).toHaveAttribute("aria-checked", "false");
    expect(autoSubmit).toBeDisabled();
  });

  it("saves numeric limits as numbers", async () => {
    const user = userEvent.setup();
    const onSaved = await renderForm();

    const perDay = screen.getByLabelText("Applications per day");
    await user.clear(perDay);
    await user.type(perDay, "5");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(api.update.mock.calls[0][0]).toEqual(
      expect.objectContaining({ max_applications_per_day: 5, review_before_submit: true, auto_submit_enabled: false }),
    );
  });

  it("shows platform-limit errors from the API on the right field", async () => {
    const user = userEvent.setup();
    api.update.mockRejectedValueOnce(
      new ApiError({
        status: 422,
        code: "validation_error",
        message: "Preference exceeds platform limits.",
        fieldErrors: [{ field: "max_applications_per_day", message: "Must be at most 100" }],
      }),
    );
    const onSaved = await renderForm();

    const perDay = screen.getByLabelText("Applications per day");
    await user.clear(perDay);
    await user.type(perDay, "500");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Must be at most 100")).toBeInTheDocument();
    expect(perDay).toHaveAttribute("aria-invalid", "true");
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("rejects out-of-range values before calling the API", async () => {
    const user = userEvent.setup();
    await renderForm();
    const score = screen.getByLabelText(/minimum match score/i);
    await user.clear(score);
    await user.type(score, "150");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Enter a value from 0 to 100")).toBeInTheDocument();
    expect(api.update).not.toHaveBeenCalled();
  });
});
