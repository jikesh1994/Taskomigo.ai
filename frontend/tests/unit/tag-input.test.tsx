import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { TagInput } from "@/components/ui/tag-input";

function Harness({ initial = [] as string[] }) {
  const [value, setValue] = useState(initial);
  return (
    <>
      <TagInput id="titles" label="Job titles" value={value} onChange={setValue} />
      <output data-testid="value">{JSON.stringify(value)}</output>
    </>
  );
}

const value = () => JSON.parse(screen.getByTestId("value").textContent ?? "[]");

describe("TagInput", () => {
  it("adds entries on Enter and comma, trimming and de-duplicating", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByLabelText("Job titles");

    await user.type(input, "  Backend   Engineer {Enter}");
    await user.type(input, "SRE,");
    await user.type(input, "backend engineer{Enter}");

    expect(value()).toEqual(["Backend Engineer", "SRE"]);
    expect(input).toHaveValue("");
  });

  it("removes the last entry with Backspace and a specific one with its button", async () => {
    const user = userEvent.setup();
    render(<Harness initial={["Python", "Go", "Rust"]} />);

    await user.click(screen.getByRole("button", { name: "Remove Go" }));
    expect(value()).toEqual(["Python", "Rust"]);

    await user.type(screen.getByLabelText("Job titles"), "{Backspace}");
    expect(value()).toEqual(["Python"]);
  });

  it("commits a pending entry when the field loses focus", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.type(screen.getByLabelText("Job titles"), "Data Engineer");
    await user.tab();
    expect(value()).toEqual(["Data Engineer"]);
  });
});
