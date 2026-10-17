const apiUrl = process.env.EXPO_PUBLIC_API_URL?.trim() || "http://localhost:8000";

export const API_BASE_URL = apiUrl.replace(/\/+$/, "");
