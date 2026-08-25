/**
 * API error handling utilities
 */

export class APIError extends Error {
  status?: number;
  details?: unknown;

  constructor(
    message: string,
    status?: number,
    details?: unknown
  ) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.details = details;
  }
}

export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    let errorDetails: unknown;

    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
      errorDetails = errorData;
    } catch {
      // If parsing JSON fails, use status text
      errorMessage = response.statusText || errorMessage;
    }

    throw new APIError(errorMessage, response.status, errorDetails);
  }

  return response.json();
}
