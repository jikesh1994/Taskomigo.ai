import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/services/config";

describe("apiBaseUrl", () => {
  it("follows the page's loopback hostname so localhost and 127.0.0.1 both work", () => {
    expect(apiBaseUrl("http://localhost:8000", "127.0.0.1")).toBe("http://127.0.0.1:8000");
    expect(apiBaseUrl("http://127.0.0.1:8000", "localhost")).toBe("http://localhost:8000");
    expect(apiBaseUrl("http://localhost:8000", "localhost")).toBe("http://localhost:8000");
  });

  it("never rewrites real deployments", () => {
    expect(apiBaseUrl("https://api.taskomigo.com", "app.taskomigo.com")).toBe("https://api.taskomigo.com");
    // A loopback API opened from a real host is left alone (misconfiguration, not ours to guess).
    expect(apiBaseUrl("http://localhost:8000", "app.taskomigo.com")).toBe("http://localhost:8000");
  });

  it("uses the configured value during server rendering", () => {
    expect(apiBaseUrl("http://localhost:8000", undefined)).toBe("http://localhost:8000");
  });
});
