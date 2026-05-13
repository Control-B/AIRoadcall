const mediaBaseUrl = process.env.NEXT_PUBLIC_MEDIA_BASE_URL?.replace(/\/+$/, "") || "";

function normalizePath(path: string) {
  return path.replace(/^\/+/, "");
}

export function mediaUrl(path: string, fallback?: string) {
  const normalizedPath = normalizePath(path);
  if (!mediaBaseUrl) {
    return fallback ?? `/${normalizedPath}`;
  }
  return `${mediaBaseUrl}/${normalizedPath}`;
}
