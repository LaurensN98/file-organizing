import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import Page from "../app/(main)/page";

test("Home page renders welcome message", () => {
  render(<Page />);
  // Look for your title or description text
  const heading = screen.getByRole("heading", { level: 1 });
  expect(heading).toBeDefined();
});
