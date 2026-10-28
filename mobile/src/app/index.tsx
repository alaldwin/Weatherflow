
import React, { useCallback, useEffect, useState } from "react";

import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  getCurrentWeatherList,
  getCurrentWeatherByCoordinates,
  getForecast,
  searchLocations,
  type CurrentWeather,
  type LocationResult,
  type WeatherForecast,
} from "../services/weatherApi";

import { BxsMapIcon } from "../components/icons/BxsMapicon";

import WeatherLineChart from "../components/WeatherLineChart";
import * as Location from "expo-location";

function weatherEmoji(condition?: string | null) {
  const value = (condition ?? "").toLowerCase();

  if (value.includes("thunder")) return "⛈️";
  if (value.includes("rain") || value.includes("drizzle")) return "🌧️";
  if (value.includes("snow")) return "❄️";
  if (value.includes("cloud")) return "☁️";
  if (value.includes("clear")) return "☀️";
  if (value.includes("mist") || value.includes("fog")) return "🌫️";

  return "🌤️";
}

function Metric({
  label,
  value,
  unit,
  icon,
}: {
  label: string;
  value: string;
  unit?: string;
  icon: string;
}) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricIcon}>{icon}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>
        {value}
        {unit ? <Text style={styles.metricUnit}> {unit}</Text> : null}
      </Text>
    </View>
  );
}

export default function Index() {
  const [weather, setWeather] = useState<CurrentWeather | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [forecast, setForecast] = useState<WeatherForecast | null>(null);
  const [activeTab, setActiveTab] = useState<"today" | "forecast">("today");
  const [forecastError, setForecastError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [locationResults, setLocationResults] = useState<LocationResult[]>([]);
  const [searchingLocations, setSearchingLocations] = useState(false);
  const [selectingLocation, setSelectingLocation] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const [locating, setLocating] = useState(false);
  const [locationMessage, setLocationMessage] = useState<string | null>(null);


  const loadWeather = useCallback(async () => {
    setError(null);
    setForecastError(null);

    try {
      const records = await getCurrentWeatherList();

      if (!records.length) {
        throw new Error("The API returned no weather records.");
      }

      const preferred =
        records.find(
          (item) => item.city.toLowerCase() === "manila"
        ) ?? records[0];

      setWeather(preferred);

      if (
        preferred.latitude == null ||
        preferred.longitude == null
      ) {
        setForecastError(
          "Coordinates are unavailable for this city."
        );
        return;
      }

      try {
        const result = await getForecast(
          preferred.latitude,
          preferred.longitude,
          5
        );

          setForecast(result);
        } catch (err) {
          setForecast(null);
          setForecastError(
            err instanceof Error
              ? err.message
              : "Unable to load the forecast."
          );
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load weather from the API."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    }, []);


  useEffect(() => {
    void loadWeather();
  }, [loadWeather]);

  const onRefresh = () => {
    setRefreshing(true);
    void loadWeather();
  };

  const handleSearchLocations = async () => {
  const query = searchQuery.trim();

  if (query.length < 2) {
    setLocationError("Enter at least two characters.");
    setLocationResults([]);
    return;
  }

  setSearchingLocations(true);
  setLocationError(null);

  try {
    const results = await searchLocations(query, 5);
    setLocationResults(results);

    if (results.length === 0) {
      setLocationError("No matching locations found.");
    }
  } catch (err) {
    setLocationResults([]);
    setLocationError(
      err instanceof Error
        ? err.message
        : "Unable to search for locations."
    );
  } finally {
    setSearchingLocations(false);
  }
};

const handleSelectLocation = async (location: LocationResult) => {
  const latitude = location.latitude ?? location.lat;
  const longitude = location.longitude ?? location.lon;

  if (
    typeof latitude !== "number" ||
    typeof longitude !== "number" ||
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude)
  ) {
    setLocationError("This search result has no valid coordinates.");
    return;
  }

  setSelectingLocation(true);
  setLocationError(null);
  setForecastError(null);

  try {
    const selectedWeather = await getCurrentWeatherByCoordinates(
      latitude,
      longitude
    );

    setWeather(selectedWeather);
    setLocationResults([]);
    setSearchQuery("");
    setActiveTab("today");

    try {
      const result = await getForecast(latitude, longitude, 5);
      setForecast(result);
    } catch (err) {
      setForecastError(
        err instanceof Error
          ? err.message
          : "Unable to load the forecast."
      );
    }
  } catch (err) {
    setLocationError(
      err instanceof Error
        ? err.message
        : "Unable to load weather for this location."
    );
  } finally {
    setSelectingLocation(false);
  }
};


const handleUseMyLocation = async () => {
  setLocating(true);
  setLocationMessage(null);
  setLocationError(null);
  setForecastError(null);

  try {
    const permission = await Location.requestForegroundPermissionsAsync();

    if (permission.status !== "granted") {
      setLocationMessage(
        "Location permission was denied. Enable it in your device settings to use GPS."
      );
      return;
    }

    const position = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });

    const { latitude, longitude } = position.coords;

    const selectedWeather = await getCurrentWeatherByCoordinates(
      latitude,
      longitude
    );

    setWeather(selectedWeather);
    setLocationResults([]);
    setSearchQuery("");
    setActiveTab("today");

    try {
      const result = await getForecast(latitude, longitude, 5);
      setForecast(result);
    } catch (err) {
      setForecastError(
        err instanceof Error
          ? err.message
          : "Unable to load the forecast for your location."
      );
    }
  } catch (err) {
    setLocationMessage(
      err instanceof Error
        ? err.message
        : "Unable to determine your current location."
    );
  } finally {
    setLocating(false);
  }
};

  return (
    <LinearGradient
      colors={["#171238", "#29205B", "#111329"]}
      locations={[0, 0.52, 1]}
      style={styles.background}
    >
      <StatusBar barStyle="light-content" />
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor="#FFFFFF"
            />
          }
        >
          <View style={styles.header}>
            <View>
              <Text style={styles.eyebrow}>WEATHERFLOW</Text>
              <Text style={styles.headerTitle}>Weather today</Text>
            </View>
            <View style={styles.liveBadge}>
              <View style={styles.liveDot} />
              <Text style={styles.liveText}>LIVE API</Text>
            </View>
          </View>


          {loading ? (
            <View style={styles.statusCard}>
              <ActivityIndicator size="large" color="#C4B5FD" />
              <Text style={styles.statusTitle}>Loading weather…</Text>
              <Text style={styles.mutedText}>
                Connecting to your Weatherflow API
              </Text>
            </View>
          ) : error ? (
            <View style={styles.statusCard}>
              <Text style={styles.statusEmoji}>⚠️</Text>
              <Text style={styles.statusTitle}>Couldn't load weather</Text>
              <Text style={styles.errorText}>{error}</Text>
              <Pressable style={styles.retryButton} onPress={onRefresh}>
                <Text style={styles.retryText}>Try again</Text>
              </Pressable>
            </View>
          ) : weather ? (
            <>
            <View style={styles.searchCard}>

              <View style={styles.searchInputRow}>
                <TextInput
                  value={searchQuery}
                  onChangeText={setSearchQuery}
                  onSubmitEditing={() => void handleSearchLocations()}
                  placeholder="Search city, e.g. Cebu"
                  placeholderTextColor="#9691B8"
                  returnKeyType="search"
                  autoCapitalize="words"
                  autoCorrect={false}
                  style={styles.searchInput}
                />

                <Pressable
                  style={styles.searchButton}
                  onPress={() => void handleSearchLocations()}
                  disabled={searchingLocations || selectingLocation}
                >
                  {searchingLocations ? (
                    <ActivityIndicator color="#171238" />
                  ) : (
                    <Text style={styles.searchButtonText}>Search</Text>
                  )}
                </Pressable>
                <Pressable
                  style={styles.gpsButton}
                  onPress={() => void handleUseMyLocation()}
                  disabled={locating || selectingLocation}
                >
                  {locating ? (
                    <ActivityIndicator color="#FFFFFF" size="small" />
                  ) : (
                    <>
                      <BxsMapIcon
                        width={18}
                        height={18}
                        color="#FFFFFF"
                      />
                    </>
                  )}
                </Pressable>

                {locationMessage ? (
                  <Text style={styles.locationError}>{locationMessage}</Text>
                ) : null}
              </View>

              {locationError ? (
                <Text style={styles.locationError}>{locationError}</Text>
              ) : null}

              {selectingLocation ? (
                <View style={styles.searchLoading}>
                  <ActivityIndicator color="#C4B5FD" />
                  <Text style={styles.mutedText}>
                    Loading selected location…
                  </Text>
                </View>
              ) : null}

              {locationResults.map((location, index) => {
                const name = location.name ?? location.city ?? "Unknown location";
                const subtitle = [
                  location.state,
                  location.country,
                ]
                  .filter(Boolean)
                  .join(", ");

                return (
                  <Pressable
                    key={`${name}-${location.latitude ?? location.lat}-${location.longitude ?? location.lon}-${index}`}
                    style={styles.locationResult}
                    onPress={() => void handleSelectLocation(location)}
                    disabled={selectingLocation}
                  >
                    <View style={styles.locationResultText}>
                      <Text style={styles.locationResultName}>{name}</Text>
                      {subtitle ? (
                        <Text style={styles.locationResultSubtitle}>
                          {subtitle}
                        </Text>
                      ) : null}
                    </View>
                    <Text style={styles.locationResultArrow}>›</Text>
                  </Pressable>
                );
              })}
          </View>
              <View style={styles.tabRow}>
                <Pressable
                  style={[
                    styles.tabButton,
                    activeTab === "today" && styles.activeTabButton,
                  ]}
                  onPress={() => setActiveTab("today")}
                >
                  <Text
                    style={[
                      styles.tabText,
                      activeTab === "today" && styles.activeTabText,
                    ]}
                  >
                    Today
                  </Text>
                </Pressable>

                <Pressable
                  style={[
                    styles.tabButton,
                    activeTab === "forecast" && styles.activeTabButton,
                  ]}
                  onPress={() => setActiveTab("forecast")}
                >
                  <Text
                    style={[
                      styles.tabText,
                      activeTab === "forecast" && styles.activeTabText,
                    ]}
                  >
                    Daily Forecast
                  </Text>
                </Pressable>
              </View>

              {activeTab === "today" ? (
                <>
                  <View style={styles.heroCard}>
                    <View style={styles.locationRow}>
                      <Text style={styles.locationPin}>⌖</Text>
                      <View>
                        <Text style={styles.city}>
                          {weather.city}
                          {weather.country ? `, ${weather.country}` : ""}
                        </Text>
                      </View>
                    </View>

                    <View style={styles.heroWeather}>
                      <View>
                        <Text style={styles.temperature}>
                          {weather.temperature == null
                            ? "--"
                            : Math.round(weather.temperature)}
                          <Text style={styles.degree}>°</Text>
                        </Text>
                        <Text style={styles.condition}>
                          {weather.weather_description ??
                            weather.weather_main ??
                            "Weather unavailable"}
                        </Text>
                        <Text style={styles.feelsLike}>
                          Feels like{" "}
                          {weather.feels_like == null
                            ? "--"
                            : `${Math.round(weather.feels_like)}°`}
                        </Text>
                      </View>
                      <Text style={styles.weatherEmoji}>
                        {weatherEmoji(weather.weather_main)}
                      </Text>
                    </View>

                    <View style={styles.highLowRow}>
                      <Text style={styles.highLow}>
                        ↑ {weather.temp_max == null ? "--" : Math.round(weather.temp_max)}°
                      </Text>
                      <Text style={styles.highLow}>
                        ↓ {weather.temp_min == null ? "--" : Math.round(weather.temp_min)}°
                      </Text>
                      <Text style={styles.highLow}>
                        ☁ {weather.cloudiness ?? "--"}% clouds
                      </Text>
                    </View>
                  </View>

                  <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>Weather details</Text>
                    <Text style={styles.sectionCaption}>Latest observation</Text>
                  </View>

                  <View style={styles.metricsGrid}>
                    <Metric
                      label="Humidity"
                      value={weather.humidity == null ? "--" : String(weather.humidity)}
                      unit="%"
                      icon="💧"
                    />
                    <Metric
                      label="Wind speed"
                      value={
                        weather.wind_speed == null
                          ? "--"
                          : (weather.wind_speed * 3.6).toFixed(1)
                      }
                      unit="km/h"
                      icon="💨"
                    />
                    <Metric
                      label="Pressure"
                      value={weather.pressure == null ? "--" : String(weather.pressure)}
                      unit="hPa"
                      icon="◉"
                    />
                    <Metric
                      label="Visibility"
                      value={
                        weather.visibility == null
                          ? "--"
                          : (weather.visibility / 1000).toFixed(1)
                      }
                      unit="km"
                      icon="👁️"
                    />
                  </View>

                  <View style={styles.footerCard}>
                    <Text style={styles.footerTitle}>Weatherflow data pipeline</Text>
                    <Text style={styles.footerDescription}>
                      Current conditions loaded from your FastAPI backend.
                    </Text>
                    <Text style={styles.observation}>
                      Observation:{" "}
                      {weather.observation_time
                        ? new Date(weather.observation_time).toLocaleString()
                        : "Time unavailable"}
                    </Text>
                  </View>
                </>
              ) : (
                <View style={styles.forecastSection}>
                  <Text style={styles.sectionTitle}>Daily</Text>
                  <Text style={styles.forecastSubtitle}>
                    {forecast?.location.name ?? weather.city}
                  </Text>

                  {forecastError ? (
                    <View style={styles.statusCard}>
                      <Text style={styles.errorText}>{forecastError}</Text>
                      <Pressable style={styles.retryButton} onPress={onRefresh}>
                        <Text style={styles.retryText}>Try again</Text>
                      </Pressable>
                    </View>
                  ) : !forecast ? (
                    <View style={styles.statusCard}>
                      <ActivityIndicator color="#C4B5FD" />
                      <Text style={styles.mutedText}>Loading forecast…</Text>
                    </View>
                  ) : (
                    <>
                      {forecast.daily.map((day) => (
                        <View key={day.date} style={styles.forecastCard}>
                          <View style={styles.forecastDayInfo}>
                            <Text style={styles.forecastDay}>
                              {new Date(`${day.date}T12:00:00`).toLocaleDateString(
                                "en-US",
                                { weekday: "short", month: "short", day: "numeric" }
                              )}
                            </Text>

                            <Text style={styles.forecastCondition}>
                              {weatherEmoji(day.weather_main)} {day.weather_main ?? "Unknown"}
                            </Text>

                            <View style={styles.dailyMetrics}>
                              <Text style={styles.dailyMetric}>
                                💧 {day.humidity == null ? "--" : `${Math.round(day.humidity)}%`}
                              </Text>
                              <Text style={styles.dailyMetric}>
                                💨 {day.wind_speed == null ? "--" : `${day.wind_speed.toFixed(1)} m/s`}
                              </Text>
                              <Text style={styles.dailyMetric}>
                                ☁️ {day.cloudiness == null ? "--" : `${Math.round(day.cloudiness)}%`}
                              </Text>
                            </View>
                          </View>

                          <View style={styles.forecastTemperatures}>
                            <Text style={styles.forecastHigh}>
                              {day.temp_max == null ? "--" : `${Math.round(day.temp_max)}°`}
                            </Text>
                            <Text style={styles.forecastLow}>
                              {day.temp_min == null ? "--" : `${Math.round(day.temp_min)}°`}
                            </Text>
                          </View>
                        </View>
                      ))}

                      <Text style={styles.sectionTitle}>Hourly Forecast</Text>
                      <ScrollView
                        horizontal
                        showsHorizontalScrollIndicator={false}
                        contentContainerStyle={styles.hourlyList}
                      >
                        {forecast.hourly.slice(0, 12).map((hour, index) => (
                          <View
                            key={String(hour.timestamp ?? hour.datetime ?? index)}
                            style={styles.hourCard}
                          >
                            <Text style={styles.hourTime}>
                              {hour.datetime
                                ? new Date(hour.datetime).toLocaleTimeString(
                                    "en-US",
                                    { hour: "numeric" }
                                  )
                                : "--"}
                            </Text>
                            <Text style={styles.hourIcon}>
                              {weatherEmoji(hour.weather_main)}
                            </Text>
                            <Text style={styles.hourTemperature}>
                              {hour.temperature == null
                                ? "--"
                                : `${Math.round(hour.temperature)}°`}
                            </Text>
                            <Text style={styles.hourMetric}>
                              💧 {hour.humidity ?? "--"}%
                            </Text>
                            <Text style={styles.hourMetric}>
                              💨 {hour.wind_speed == null
                                ? "--"
                                : (hour.wind_speed * 3.6).toFixed(1)}
                            </Text>
                          </View>
                        ))}
                      </ScrollView>
                      
                      <Text style={styles.sectionTitle}>
                        Weather Analytics
                      </Text>
                      <Text style={styles.forecastSubtitle}>
                        Forecast trends for {forecast.location.name}
                      </Text>

                      <WeatherLineChart
                        title="Temperature"
                        unit="°"
                        color="#A78BFA"
                        points={forecast.hourly.slice(0, 8).map((hour) => ({
                          label: hour.datetime
                            ? new Date(hour.datetime).toLocaleTimeString(
                                "en-US",
                                { hour: "numeric" }
                              )
                            : "--",
                          value: hour.temperature,
                        }))}
                      />

                      <WeatherLineChart
                        title="Wind Speed"
                        unit=" km/h"
                        color="#38BDF8"
                        points={forecast.hourly.slice(0, 8).map((hour) => ({
                          label: hour.datetime
                            ? new Date(hour.datetime).toLocaleTimeString(
                                "en-US",
                                { hour: "numeric" }
                              )
                            : "--",
                          value:
                            hour.wind_speed == null
                              ? null
                              : hour.wind_speed * 3.6,
                        }))}
                      />

                      <WeatherLineChart
                        title="Humidity"
                        unit="%"
                        color="#34D399"
                        maxValue={100}
                        points={forecast.hourly.slice(0, 8).map((hour) => ({
                          label: hour.datetime
                            ? new Date(hour.datetime).toLocaleTimeString(
                                "en-US",
                                { hour: "numeric" }
                              )
                            : "--",
                          value: hour.humidity,
                        }))}
                      />

                      <WeatherLineChart
                        title="Cloud Coverage"
                        unit="%"
                        color="#FBBF24"
                        maxValue={100}
                        points={forecast.hourly.slice(0, 8).map((hour) => ({
                          label: hour.datetime
                            ? new Date(hour.datetime).toLocaleTimeString(
                                "en-US",
                                { hour: "numeric" }
                              )
                            : "--",
                          value: hour.cloudiness,
                        }))}
                      />
                    </>
                  )}
                </View>
              )}
            </>
          ) : null}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  background: { flex: 1 },
  safeArea: { flex: 1 },
  content: { padding: 22, paddingBottom: 36 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 28,
  },
  eyebrow: {
    color: "#B9ACFF",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 3,
    marginBottom: 6,
  },
  headerTitle: { color: "#FFFFFF", fontSize: 25, fontWeight: "700" },
  liveBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF12",
    borderColor: "#FFFFFF20",
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 11,
    paddingVertical: 8,
    gap: 6,
  },
  liveDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#6EE7B7",
  },
  liveText: {
    color: "#D7FFF0",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1,
  },
  heroCard: {
    backgroundColor: "#FFFFFF12",
    borderColor: "#FFFFFF20",
    borderWidth: 1,
    borderRadius: 28,
    padding: 23,
    marginBottom: 28,
  },
  locationRow: { flexDirection: "row", alignItems: "center", gap: 11 },
  locationPin: { color: "#C4B5FD", fontSize: 28 },
  city: { color: "#FFFFFF", fontSize: 19, fontWeight: "700" },
  subtitle: { color: "#B7B4D4", fontSize: 12, marginTop: 4 },
  heroWeather: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 28,
    marginBottom: 22,
  },
  temperature: {
    color: "#FFFFFF",
    fontSize: 82,
    fontWeight: "300",
    letterSpacing: -4,
  },
  degree: { fontSize: 48, fontWeight: "300" },
  condition: {
    color: "#E6E1FF",
    fontSize: 16,
    fontWeight: "600",
    textTransform: "capitalize",
    marginTop: -3,
  },
  feelsLike: { color: "#B7B4D4", fontSize: 13, marginTop: 7 },
  weatherEmoji: { fontSize: 78 },
  highLowRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderTopWidth: 1,
    borderTopColor: "#FFFFFF20",
    paddingTop: 17,
    gap: 8,
  },
  highLow: { color: "#DAD6F4", fontSize: 12, fontWeight: "600" },
  sectionHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 15,
  },
  sectionTitle: { color: "#FFFFFF", fontSize: 19, fontWeight: "700" },
  sectionCaption: { color: "#AAA6C8", fontSize: 11 },
  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  metric: {
    width: "48%",
    flexGrow: 1,
    minHeight: 135,
    borderRadius: 21,
    padding: 17,
    backgroundColor: "#FFFFFF0D",
    borderWidth: 1,
    borderColor: "#FFFFFF15",
  },
  metricIcon: { fontSize: 22, marginBottom: 13 },
  metricLabel: { color: "#B7B4D4", fontSize: 12 },
  metricValue: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "700",
    marginTop: 7,
  },
  metricUnit: { color: "#C3BEDD", fontSize: 12, fontWeight: "500" },
  footerCard: {
    marginTop: 24,
    borderRadius: 20,
    padding: 18,
    backgroundColor: "#0D102B80",
  },
  footerTitle: { color: "#EAE7FF", fontSize: 14, fontWeight: "700" },
  footerDescription: {
    color: "#AAA6C8",
    fontSize: 12,
    lineHeight: 19,
    marginTop: 7,
  },
  observation: { color: "#8F8BAF", fontSize: 10, marginTop: 12 },
  statusCard: {
    minHeight: 270,
    borderRadius: 26,
    backgroundColor: "#FFFFFF12",
    alignItems: "center",
    justifyContent: "center",
    padding: 25,
    gap: 12,
  },
  statusEmoji: { fontSize: 36 },
  statusTitle: { color: "#FFFFFF", fontSize: 18, fontWeight: "700" },
  mutedText: { color: "#B7B4D4", fontSize: 13, textAlign: "center" },
  errorText: {
    color: "#FFD0D0",
    fontSize: 12,
    lineHeight: 19,
    textAlign: "center",
  },
  retryButton: {
    marginTop: 7,
    backgroundColor: "#A78BFA",
    borderRadius: 14,
    paddingHorizontal: 22,
    paddingVertical: 12,
  },
  retryText: { color: "#171238", fontSize: 13, fontWeight: "800" },


    tabRow: {
    flexDirection: "row",
    padding: 5,
    marginBottom: 22,
    borderRadius: 16,
    backgroundColor: "#FFFFFF0D",
    borderWidth: 1,
    borderColor: "#FFFFFF15",
  },
  tabButton: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 13,
    borderRadius: 12,
  },
  activeTabButton: {
    backgroundColor: "#A78BFA",
  },
  tabText: {
    color: "#C3BEDD",
    fontSize: 13,
    fontWeight: "700",
  },
  activeTabText: {
    color: "#171238",
  },
  forecastSection: {
    gap: 14,
    marginBottom: 24,
  },
  forecastSubtitle: {
    color: "#B7B4D4",
    fontSize: 13,
    marginTop: -6,
    marginBottom: 4,
  },
  forecastCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 16,
    borderRadius: 18,
    backgroundColor: "#FFFFFF0D",
    borderWidth: 1,
    borderColor: "#FFFFFF15",
  },
  forecastDayInfo: {
    flex: 1,
    gap: 6,
  },
  forecastDay: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
  forecastCondition: {
    color: "#C3BEDD",
    fontSize: 12,
    textTransform: "capitalize",
  },
  forecastTemperatures: {
    flexDirection: "row",
    gap: 14,
  },
  forecastHigh: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
  },
  forecastLow: {
    color: "#AAA6C8",
    fontSize: 17,
  },
  hourlyList: {
    gap: 10,
    paddingVertical: 4,
  },
  hourCard: {
    width: 100,
    alignItems: "center",
    gap: 10,
    paddingVertical: 16,
    borderRadius: 18,
    backgroundColor: "#FFFFFF0D",
    borderWidth: 1,
    borderColor: "#FFFFFF15",
  },
  hourTime: {
    color: "#C3BEDD",
    fontSize: 12,
  },
  hourIcon: {
    fontSize: 25,
  },
  hourTemperature: {
    color: "#FFFFFF",
    fontSize: 20,
    fontWeight: "700",
  },
  hourMetric: {
    color: "#C3BEDD",
    fontSize: 11,
  },
dailyMetrics: {
  flexDirection: "row",
  flexWrap: "wrap",
  gap: 10,
  marginTop: 8,
},

dailyMetric: {
  color: "#C3BEDD",
  fontSize: 11,
},

  searchCard: {
    marginBottom: 22,
    padding: 16,
    borderRadius: 22,
    backgroundColor: "#FFFFFF0D",
    borderWidth: 1,
    borderColor: "#FFFFFF15",
    gap: 12,
  },
  searchTitle: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
  },
  searchDescription: {
    color: "#B7B4D4",
    fontSize: 12,
    lineHeight: 18,
  },
  searchInputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  searchInput: {
    flex: 1,
    minWidth: 0,
    color: "#FFFFFF",
    backgroundColor: "#111329",
    borderWidth: 1,
    borderColor: "#FFFFFF20",
    borderRadius: 13,
    paddingHorizontal: 12,
    paddingVertical: 12,
    fontSize: 14,
  },
  searchButton: {
    minHeight: 46,
    paddingHorizontal: 15,
    borderRadius: 13,
    backgroundColor: "#A78BFA",
    alignItems: "center",
    justifyContent: "center",
  },
  searchButtonText: {
    color: "#171238",
    fontSize: 13,
    fontWeight: "800",
  },
  locationResult: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 13,
    backgroundColor: "#FFFFFF0A",
    borderWidth: 1,
    borderColor: "#FFFFFF12",
  },
  locationResultText: {
    flex: 1,
    gap: 4,
  },
  locationResultName: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
  },
  locationResultSubtitle: {
    color: "#B7B4D4",
    fontSize: 12,
  },
  locationResultArrow: {
    color: "#C4B5FD",
    fontSize: 24,
    marginLeft: 8,
  },
  locationError: {
    color: "#FFD0D0",
    fontSize: 12,
    lineHeight: 18,
  },
  searchLoading: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 8,
  },

  gpsButton: {
    flexDirection: "row",
    gap: 8,
    minHeight: 46,
    borderRadius: 13,
    borderWidth: 1,
    borderColor: "#A78BFA80",
    backgroundColor: "#A78BFA20",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
},
gpsButtonText: {
  color: "#DDD6FE",
  fontSize: 14,
  fontWeight: "700",
},
});