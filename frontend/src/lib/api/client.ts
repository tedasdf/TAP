const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

type RequestOptions = RequestInit & {
  params?: Record<string, string | number | boolean | undefined | null>;
};

function buildUrl(path: string, params?: RequestOptions["params"]) {
  const url = new URL(path, API_BASE_URL);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  return url.toString();
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, ...rest } = options;

  const response = await fetch(buildUrl(path, params), {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      // ignore json parse failure
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}