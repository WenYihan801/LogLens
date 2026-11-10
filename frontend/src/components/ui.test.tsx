import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "../services/api";
import { ErrorMessage, Pagination, RawLog, SeverityBadge } from "./ui";

describe("RawLog", () => {
  it("renders untrusted log content as text, never as HTML", () => {
    const evil = '<img src=x onerror="alert(1)"><script>alert(2)</script>';
    const { container } = render(<RawLog text={evil} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByText(evil)).toBeInTheDocument();
  });
});

describe("Pagination", () => {
  it("shows range and disables prev on the first page", async () => {
    const onPage = vi.fn();
    render(<Pagination page={1} pages={3} total={120} pageSize={50} onPage={onPage} />);
    expect(screen.getByText("1–50 of 120")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });

  it("disables next on the last page and shows the partial range", () => {
    render(<Pagination page={3} pages={3} total={120} pageSize={50} onPage={() => {}} />);
    expect(screen.getByText("101–120 of 120")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  });

  it("handles zero results", () => {
    render(<Pagination page={1} pages={1} total={0} pageSize={50} onPage={() => {}} />);
    expect(screen.getByText("0–0 of 0")).toBeInTheDocument();
  });
});

describe("ErrorMessage", () => {
  it("shows the API message, error code and a retry action", async () => {
    const retry = vi.fn();
    render(<ErrorMessage error={new ApiError(413, { error_code: "FILE_TOO_LARGE", message: "Too big." })} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Too big.");
    expect(screen.getByText("FILE_TOO_LARGE")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Retry"));
    expect(retry).toHaveBeenCalled();
  });
});

it("SeverityBadge renders the level", () => {
  render(<SeverityBadge severity="HIGH" />);
  expect(screen.getByText("HIGH")).toBeInTheDocument();
});
