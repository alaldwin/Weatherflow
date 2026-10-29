
import { env } from "../config/env";

export type CurrentWeather = {
  city: string;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  temperature?: number | null;
  feels_like?: number | null;
  temp_min?: number | null;
  temp_max?: number | null;
  humidity?: number | null;
  cloudiness?: number | null;
  pressure?: number | null;
  visibility?: number | null;
  wind_speed?: number | null;
  wind_direction?: number | null;
  wind_gust?: number | null;
  weather_main?: string | null;
  weather_description?: string | null;
  weather_icon?: string | null;
  observation_time?: string | null;
  sunrise?: string | number | null;
  sunset?: string | number | null;
};

export type DailyWeather = {
  city: string;
  country?: string | null;
  observation_date: string;
  avg_temperature?: number | null;
  min_temperature?: number | null;
  max_temperature?: number | null;
  avg_feels_like?: number | null;
  avg_humidity?: number | null;
  avg_pressure?: number | null;
  avg_wind_speed?: number | null;
  avg_cloudiness?: number | null;
  observation_count?: number | null;
};

export type LocationResult = {
  name?: string;
  city?: string;
  country?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  lat?: number;
  lon?: number;
  [key: string]: unknown;
};


export type ForecastHour = {
  datetime: string | null;
  timestamp: number | null;
  temperature: number | null;
  feels_like: number | null;
  humidity: number | null;
  wind_speed: number | null;
  cloudiness: number | null;
  weather_main: string | null;
  weather_description: string | null;
  weather_icon: string | null;
  precipitation_probability: number | null;
};

export type ForecastDay = {
  date: string;
  temp_min: number | null;
  temp_max: number | null;
  weather_main: string | null;
  humidity: number | null;
  wind_speed: number | null;
  cloudiness: number | null;
};

export type WeatherForecast = {
  location: {
    name: string;
    country: string;
    lat: number;
    lon: number;
  };
  hourly: ForecastHour[];
  daily: ForecastDay[];
  units: string;
  source: string;
};



export function isRequestCancelledError(error: unknown): boolean {
  return (
    error instanceof Error &&
    (error.name === "AbortError" ||
      /canceled|cancelled|aborted/i.test(error.message))
  );
}

async function request<T>(
  path: string,
  timeoutMs = 60000
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const url = `${env.API_BASE_URL}${path}`;

  try {
    console.log("[Weather API] GET", url);

    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    console.log("[Weather API] Response", response.status, url);

    if (!response.ok) {
      const body = await response.text();
      throw new Error(
        `Weather API error ${response.status}: ${body || response.statusText}`
      );
    }

    return (await response.json()) as T;
  } catch (error) {
    console.error("[Weather API] Request failed", url, error);

    if (isRequestCancelledError(error)) {
      throw new Error("Weather request was canceled. Please try again.");
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}


function queryString(
  params: Record<string, string | number | undefined>
): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.set(key, String(value));
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function getCurrentWeather(
  city: string
): Promise<CurrentWeather> {
  return request<CurrentWeather>(
    `/api/v1/weather/current/${encodeURIComponent(city)}`
  );
}

export async function getCurrentWeatherList(): Promise<
  CurrentWeather[]
> {
  const response = await request<{
    data: CurrentWeather[];
  }>("/api/v1/weather/current?limit=100");

  return response.data ?? [];
}


export async function getCurrentWeatherByCoordinates(
  lat: number,
  lon: number
): Promise<CurrentWeather> {
  const response = await request<{
    location: {
      name?: string | null;
      country?: string | null;
      lat?: number | null;
      lon?: number | null;
    };
    temperature?: number | null;
    feels_like?: number | null;
    humidity?: number | null;
    pressure?: number | null;
    wind_speed?: number | null;
    wind_direction?: number | null;
    visibility?: number | null;
    cloudiness?: number | null;
    weather?: {
      main?: string | null;
      description?: string | null;
      icon?: string | null;
    };
    observation_time?: string | number | null;
  }>(
    `/api/v1/weather/coordinates/current${queryString({ lat, lon })}`
  );

  return {
    city: response.location?.name ?? "Selected location",
    country: response.location?.country ?? null,
    latitude: response.location?.lat ?? lat,
    longitude: response.location?.lon ?? lon,
    temperature: response.temperature ?? null,
    feels_like: response.feels_like ?? null,
    humidity: response.humidity ?? null,
    pressure: response.pressure ?? null,
    wind_speed: response.wind_speed ?? null,
    wind_direction: response.wind_direction ?? null,
    visibility: response.visibility ?? null,
    cloudiness: response.cloudiness ?? null,
    weather_main: response.weather?.main ?? null,
    weather_description: response.weather?.description ?? null,
    weather_icon: response.weather?.icon ?? null,
    observation_time:
        response.observation_time == null
            ? null
            : String(response.observation_time),
        };
}


export async function getDailyWeather(
  city: string,
  limit = 30
): Promise<DailyWeather[]> {
  const response = await request<{
    data: DailyWeather[];
  }>(
    `/api/v1/weather/daily${queryString({ city, limit })}`
  );

  return response.data ?? [];
}

export async function getForecast(
  lat: number,
  lon: number,
  days = 5
): Promise<WeatherForecast> {
  return request(
    `/api/v1/weather/forecast${queryString({
      lat,
      lon,
      days,
    })}`
  );
}

export async function searchLocations(
    q: string,
    limit = 5
    ): Promise<LocationResult[]> {
    const response = await request<unknown>(
        `/api/v1/locations/search${queryString({ q, limit })}`
    );

    console.log("[Location Search] Query:", q);
    console.log("[Location Search] Raw response:", JSON.stringify(response));

    // Accommodate common response envelopes until the exact
    // location-search response schema is confirmed.
    if (Array.isArray(response)) {
        return response as LocationResult[];
    }

    if (response && typeof response === "object") {
      const data = response as Record<string, unknown>;
      const results = data.data ?? data.results ?? data.locations;

      if (Array.isArray(results)) {
        console.log("[Location Search] Parsed results:", results.length);
        return results as LocationResult[];
      }
    }

    console.warn("[Location Search] Unexpected response format");
    return [];
  }
