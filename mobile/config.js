const apiUrl = process.env.EXPO_PUBLIC_API_URL?.trim();

if (!apiUrl) {
  throw new Error(
    "Missing EXPO_PUBLIC_API_URL. Copy mobile/.env.example to mobile/.env and set it to your backend URL."
  );
}

export const API_BASE_URL = apiUrl.replace(/\/+$/, "");
