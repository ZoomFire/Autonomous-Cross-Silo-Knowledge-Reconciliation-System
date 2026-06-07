import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Login from "../components/Login.jsx";

vi.mock("../api.js", () => ({ login: vi.fn() }));

describe("Login smoke", () => {
  it("renders email and password fields", () => {
    render(<Login onLogin={vi.fn()} onShowSignup={vi.fn()} />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });
});
