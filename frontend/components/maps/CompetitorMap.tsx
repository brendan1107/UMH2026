"use client";

import { GoogleMap, useJsApiLoader, Marker, InfoWindow } from "@react-google-maps/api";
import { useState, useCallback, useMemo } from "react";
import { Competitor, TargetLocation } from "../../lib/api/types";

interface CompetitorMapProps {
  target: TargetLocation;
  competitors: Competitor[];
}

const containerStyle = {
  width: "100%",
  height: "400px",
  borderRadius: "0.75rem",
  boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
};

// Strict coordinate conversion
function toFiniteNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export default function CompetitorMap({ target, competitors }: CompetitorMapProps) {
  const [selectedPlace, setSelectedPlace] = useState<Competitor | TargetLocation | null>(null);
  const [map, setMap] = useState<google.maps.Map | null>(null);

  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "";

  const { isLoaded, loadError } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: apiKey,
    libraries: ["places"]
  });

  const onUnmount = useCallback(function callback(map: google.maps.Map) {
    setMap(null);
  }, []);

  // Validate all coordinates
  const validTarget = useMemo(() => {
    const lat = toFiniteNumber(target.lat);
    const lng = toFiniteNumber(target.lng);
    return lat !== null && lng !== null ? { lat, lng } : null;
  }, [target.lat, target.lng]);

  const validCompetitors = useMemo(() => {
    return competitors
      .map(c => ({
        ...c,
        lat: toFiniteNumber(c.lat),
        lng: toFiniteNumber(c.lng)
      }))
      .filter(c => c.lat !== null && c.lng !== null) as Competitor[];
  }, [competitors]);

  // Determine center: Target first, then first competitor, then null
  const center = useMemo(() => {
    if (validTarget) return validTarget;
    if (validCompetitors.length > 0) {
      return { lat: validCompetitors[0].lat, lng: validCompetitors[0].lng };
    }
    return null;
  }, [validTarget, validCompetitors]);

  if (loadError) {
    return (
      <div className="w-full h-[400px] bg-red-50 rounded-xl flex flex-col items-center justify-center p-6 text-center border border-red-100">
        <p className="text-sm text-red-600 font-bold mb-1">Map preview could not be loaded</p>
        <p className="text-xs text-red-500 font-medium">Please check the Google Maps API key.</p>
      </div>
    );
  }

  if (!apiKey) {
    return (
      <div className="w-full h-[400px] bg-slate-50 rounded-xl flex flex-col items-center justify-center p-6 text-center border border-slate-200 border-dashed">
        <p className="text-sm text-slate-500 font-bold mb-1">Map preview unavailable</p>
        <p className="text-xs text-slate-400 font-medium italic">API key is missing.</p>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="w-full h-[400px] bg-slate-50 rounded-xl flex items-center justify-center animate-pulse border border-slate-100">
        <span className="text-[10px] text-slate-400 font-black tracking-widest uppercase">Initializing Map Engine...</span>
      </div>
    );
  }

  if (!center) {
    return (
      <div className="w-full h-[400px] bg-slate-100 rounded-xl flex flex-col items-center justify-center p-6 text-center border border-slate-200">
        <svg className="w-8 h-8 text-slate-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <p className="text-xs text-slate-500 font-bold">Map preview is unavailable because this location has no valid coordinates.</p>
      </div>
    );
  }

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={center}
      zoom={14}
      onUnmount={onUnmount}
      options={{
        disableDefaultUI: true,
        zoomControl: true,
        scrollwheel: true,
        styles: [
          {
            featureType: "poi",
            elementType: "labels",
            stylers: [{ visibility: "off" }]
          }
        ]
      }}
    >
      {validTarget && (
        <Marker
          position={validTarget}
          title={target.name}
          onClick={() => setSelectedPlace(target)}
          icon={{
            url: "https://maps.google.com/mapfiles/ms/icons/blue-dot.png"
          }}
        />
      )}

      {validCompetitors.map((comp) => (
        <Marker
          key={comp.id}
          position={{ lat: comp.lat, lng: comp.lng }}
          title={comp.name}
          onClick={() => setSelectedPlace(comp)}
          icon={{
            url: "https://maps.google.com/mapfiles/ms/icons/red-dot.png"
          }}
        />
      ))}

      {selectedPlace && (
        <InfoWindow
          position={{
            lat: toFiniteNumber(selectedPlace.lat)!,
            lng: toFiniteNumber(selectedPlace.lng)!
          }}
          onCloseClick={() => setSelectedPlace(null)}
        >
          <div className="p-1 max-w-[150px]">
            <h4 className="text-[11px] font-black text-slate-900 mb-0.5">{"name" in selectedPlace ? selectedPlace.name : "Target Site"}</h4>
            <p className="text-[10px] text-slate-500 line-clamp-2 leading-tight">{"address" in selectedPlace ? selectedPlace.address : ""}</p>
          </div>
        </InfoWindow>
      )}
    </GoogleMap>
  );
}
