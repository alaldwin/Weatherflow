
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, {
  Line,
  Circle,
  Polyline,
  Text as SvgText,
} from "react-native-svg";

type ChartPoint = {
  label: string;
  value: number | null;
};

type Props = {
  title: string;
  unit: string;
  points: ChartPoint[];
  color?: string;
  maxValue?: number;
};

export default function WeatherLineChart({
  title,
  unit,
  points,
  color = "#A78BFA",
  maxValue,
}: Props) {
  const validValues = points
    .map((point) => point.value)
    .filter(
      (value): value is number =>
        typeof value === "number" && Number.isFinite(value)
    );

  if (validValues.length === 0) {
    return (
      <View style={styles.card}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.empty}>No forecast data available.</Text>
      </View>
    );
  }

  const width = 320;
  const height = 190;
  const left = 38;
  const right = 12;
  const top = 24;
  const bottom = 38;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;

  const actualMin = Math.min(...validValues);
  const actualMax = Math.max(...validValues);

  // Use a readable scale while preserving fixed percentage limits.
  const lower =
    actualMin === actualMax
      ? Math.max(0, actualMin - 1)
      : Math.max(0, actualMin - (actualMax - actualMin) * 0.15);

  const upper =
    maxValue ??
    (actualMin === actualMax
      ? actualMax + 1
      : actualMax + (actualMax - actualMin) * 0.15);

  const chartLower = maxValue === 100 ? 0 : lower;
  const chartUpper = Math.max(upper, chartLower + 1);
  const chartRange = chartUpper - chartLower;

  // Keep original indexes so missing values don't shift timestamps.
  const coordinates = points.map((point, index) => {
    const x =
      points.length <= 1
        ? left + plotWidth / 2
        : left + (index / (points.length - 1)) * plotWidth;

    if (
      typeof point.value !== "number" ||
      !Number.isFinite(point.value)
    ) {
      return { x, y: null, value: null, label: point.label };
    }

    const y =
      top +
      ((chartUpper - point.value) / chartRange) * plotHeight;

    return { x, y, value: point.value, label: point.label };
  });

  // Break the line at missing readings instead of joining across gaps.
  const segments: string[][] = [];
  let currentSegment: string[] = [];

  coordinates.forEach((point) => {
    if (point.y === null || point.value === null) {
      if (currentSegment.length > 0) {
        segments.push(currentSegment);
        currentSegment = [];
      }
      return;
    }

    currentSegment.push(`${point.x},${point.y}`);
  });

  if (currentSegment.length > 0) {
    segments.push(currentSegment);
  }

  const formatValue = (value: number) =>
    `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}${unit}`;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.summary}>
        Low {formatValue(actualMin)} · High {formatValue(actualMax)}
      </Text>

      <Svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
      >
        {[0, 1, 2, 3].map((index) => {
          const y = top + (index / 3) * plotHeight;
          const value = chartUpper - (index / 3) * chartRange;

          return (
            <React.Fragment key={index}>
              <Line
                x1={left}
                y1={y}
                x2={width - right}
                y2={y}
                stroke="#3B3562"
                strokeWidth={1}
              />
              <SvgText
                x={left - 7}
                y={y + 3}
                fill="#B8B2D9"
                fontSize={9}
                textAnchor="end"
              >
                {Math.round(value)}
              </SvgText>
            </React.Fragment>
          );
        })}

        {segments.map((segment, index) =>
          segment.length >= 2 ? (
            <Polyline
              key={index}
              points={segment.join(" ")}
              fill="none"
              stroke={color}
              strokeWidth={3}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null
        )}

        {coordinates.map((point, index) => {
          if (point.y === null || point.value === null) {
            return null;
          }

          return (
            <React.Fragment key={`${point.label}-${index}`}>
              <Circle
                cx={point.x}
                cy={point.y}
                r={3.5}
                fill={color}
              />
              <SvgText
                x={point.x}
                y={Math.max(top + 11, point.y - 9)}
                fill="#FFFFFF"
                fontSize={9}
                textAnchor="middle"
              >
                {formatValue(point.value)}
              </SvgText>
              <SvgText
                x={point.x}
                y={height - 12}
                fill="#B8B2D9"
                fontSize={9}
                textAnchor="middle"
              >
                {point.label}
              </SvgText>
            </React.Fragment>
          );
        })}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#211D42",
    borderRadius: 18,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#37305F",
  },
  title: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  summary: {
    color: "#C4B5FD",
    marginTop: 6,
    fontSize: 13,
  },
  empty: {
    color: "#B8B2D9",
    marginTop: 12,
  },
});
