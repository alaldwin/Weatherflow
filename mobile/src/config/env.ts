import { Platform } from "react-native";

const configuredHost =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  process.env.API_BASE_URL ??
  undefined;

const host = Platform.select({
  android: "http://127.0.0.1:8000",
  ios: "http://127.0.0.1:8000",
  default: "http://localhost:8000",
});

export const env = {
  API_BASE_URL: configuredHost ?? host ?? "http://localhost:8000",
};
