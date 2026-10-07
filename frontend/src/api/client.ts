/**
 * Backend API client with graceful demo-data fallback:
 * if the backend isn't running (e.g. sharing the prototype statically),
 * pages still render with the bundled demo dataset.
 */
export async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`/api${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export async function postJson<T>(path: string, body: unknown, fallback: T): Promise<T> {
  try {
    const res = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}
