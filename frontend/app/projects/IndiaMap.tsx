"use client";

import { useEffect, useState } from "react";
import { MapContainer, GeoJSON } from "react-leaflet";
import type { FeatureCollection } from "geojson";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const STATUS_COLORS: Record<string, { color: string; label: string }> = {
  NORMAL: { color: "#55c4a2", label: "On Track" },
  WATCH: { color: "#f0c040", label: "At Risk" },
  ELEVATED: { color: "#ee9a3f", label: "Likely Delayed" },
  HIGH: { color: "#e86450", label: "Likely Delayed" },
  CRITICAL: { color: "#a855f7", label: "Severe Risk" },
  DATA_NOT_AVAILABLE: { color: "#9db4c4", label: "Data Unavailable" },
};

function formatCrore(value: number): string {
  if (value >= 10000) return `₹${(value / 1000).toFixed(1)}K Cr`;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

interface IndiaMapProps {
  stateData: Record<string, { count: number; cost: number; worstHealth: string }>;
}

export default function IndiaMap({ stateData }: IndiaMapProps) {
  const [geoData, setGeoData] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    fetch("/india_states.geojson")
      .then((res) => res.json())
      .then((data) => setGeoData(data))
      .catch((err) => console.error("Failed to load map data:", err));
  }, []);

  if (!geoData) {
    return <div className="text-xs text-slate-400 p-4">Loading map data...</div>;
  }

  // Center of India roughly
  const center: L.LatLngTuple = [22.9, 78.9];

  return (
    <MapContainer
      center={center}
      zoom={4.5}
      zoomControl={false}
      scrollWheelZoom={false}
      dragging={false}
      doubleClickZoom={false}
      touchZoom={false}
      style={{ height: "400px", width: "100%", background: "transparent" }}
      attributionControl={false}
    >
      <GeoJSON
        data={geoData}
        style={(feature) => {
          const stateName = feature?.properties?.NAME_1 || "";
          
          // Match state name ignoring case and extra spaces
          const matchedKey = Object.keys(stateData).find(
            (k) => k.toLowerCase().replace(/&/g, "and") === stateName.toLowerCase().replace(/&/g, "and")
          );
          
          const data = matchedKey ? stateData[matchedKey] : null;
          const health = data ? data.worstHealth : "UNKNOWN";
          const fillColor = data && STATUS_COLORS[health] ? STATUS_COLORS[health].color : "#dce5eb";
          
          return {
            fillColor,
            weight: 0.8,
            opacity: 1,
            color: "white",
            fillOpacity: data ? 0.9 : 0.6,
            className: data ? "cursor-pointer" : "cursor-default"
          };
        }}
        onEachFeature={(feature, layer) => {
          const stateName = feature?.properties?.NAME_1 || "";
          const matchedKey = Object.keys(stateData).find(
            (k) => k.toLowerCase().replace(/&/g, "and") === stateName.toLowerCase().replace(/&/g, "and")
          );
          const data = matchedKey ? stateData[matchedKey] : null;
          
          if (data) {
            layer.on({
              mouseover: (e) => {
                const l = e.target;
                l.setStyle({ fillOpacity: 1, weight: 1.5 });
                l.bringToFront();
              },
              mouseout: (e) => {
                const l = e.target;
                l.setStyle({ fillOpacity: 0.9, weight: 0.8 });
              }
            });

            // Bind tooltip
            layer.bindTooltip(
              `<div class="text-xs">
                <strong class="block text-[#f6c66e] mb-1 font-bold">${matchedKey}</strong>
                ${data.count} project${data.count !== 1 ? 's' : ''} &middot; ${formatCrore(data.cost)}<br/>
                Status: ${STATUS_COLORS[data.worstHealth]?.label ?? "Unknown"}
              </div>`,
              { sticky: true, className: "dash-map-leaflet-tooltip" }
            );
          } else {
             layer.bindTooltip(`<div class="text-xs text-slate-500">${stateName}</div>`, { sticky: true });
          }
        }}
      />
    </MapContainer>
  );
}
