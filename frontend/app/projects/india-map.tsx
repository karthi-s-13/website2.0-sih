"use client";

import { useMemo, useState } from "react";

/* ------------------------------------------------------------------ */
/*  India SVG map — simplified state boundaries                        */
/*  ViewBox: 0 0 480 560                                               */
/*  Coordinate system: x ≈ (lon-67)*14.5, y ≈ (37.5-lat)*17.5         */
/* ------------------------------------------------------------------ */

interface StateRegion {
  id: string;
  name: string;
  d: string;
}

const STATES: StateRegion[] = [
  { id: "JK", name: "Jammu & Kashmir",
    d: "M75,8 L105,0 L140,0 L168,8 L175,30 L168,55 L152,72 L135,80 L115,78 L98,68 L88,48 L80,28 Z" },
  { id: "HP", name: "Himachal Pradesh",
    d: "M135,80 L152,72 L168,75 L178,85 L172,100 L160,110 L145,108 L135,98 Z" },
  { id: "PB", name: "Punjab",
    d: "M98,88 L115,82 L135,82 L135,98 L145,108 L140,122 L128,130 L115,128 L105,118 L98,105 Z" },
  { id: "UK", name: "Uttarakhand",
    d: "M168,75 L182,65 L202,68 L218,78 L215,95 L202,108 L188,112 L178,108 L172,100 L178,85 Z" },
  { id: "HR", name: "Haryana",
    d: "M98,135 L110,130 L128,132 L140,138 L148,150 L148,170 L142,180 L130,185 L118,182 L108,172 L100,158 Z" },
  { id: "DL", name: "Delhi",
    d: "M148,168 L153,165 L158,170 L155,178 L148,175 Z" },
  { id: "RJ", name: "Rajasthan",
    d: "M22,180 L45,162 L70,148 L98,140 L100,158 L108,172 L118,182 L130,188 L142,198 L148,220 L142,250 L130,268 L110,278 L85,272 L60,260 L40,242 L28,222 L20,200 Z" },
  { id: "UP", name: "Uttar Pradesh",
    d: "M140,138 L152,128 L160,112 L178,108 L188,112 L202,108 L220,102 L245,108 L270,118 L295,128 L310,142 L315,162 L310,188 L300,212 L285,232 L265,245 L245,250 L225,248 L205,242 L188,232 L175,218 L165,202 L158,185 L155,178 L148,175 L148,150 Z" },
  { id: "BR", name: "Bihar",
    d: "M295,128 L318,135 L340,148 L355,165 L358,188 L348,212 L330,225 L312,228 L298,222 L295,210 L300,195 L310,188 L315,162 Z" },
  { id: "SK", name: "Sikkim",
    d: "M368,205 L380,198 L388,210 L385,225 L375,228 L368,220 Z" },
  { id: "NE", name: "Northeast India",
    d: "M388,200 L410,188 L435,180 L460,178 L472,192 L470,215 L462,238 L448,255 L430,268 L410,275 L395,272 L382,258 L380,238 L382,218 Z" },
  { id: "WB", name: "West Bengal",
    d: "M355,225 L368,218 L378,228 L385,248 L388,278 L385,308 L380,338 L375,365 L368,388 L358,408 L350,418 L342,408 L348,382 L355,365 L360,348 L365,328 L368,305 L368,272 L362,248 L355,232 Z" },
  { id: "JH", name: "Jharkhand",
    d: "M298,222 L312,228 L330,225 L348,232 L362,248 L368,272 L360,295 L345,310 L325,315 L308,310 L298,298 L295,280 L292,258 L290,238 Z" },
  { id: "MP", name: "Madhya Pradesh",
    d: "M130,300 L155,288 L182,282 L212,278 L245,280 L275,285 L300,292 L318,308 L315,335 L302,358 L280,368 L258,372 L232,368 L208,362 L185,358 L162,352 L145,340 L132,322 Z" },
  { id: "GJ", name: "Gujarat",
    d: "M10,300 L28,282 L52,265 L85,272 L110,278 L130,292 L130,300 L132,322 L125,345 L112,365 L92,382 L70,392 L50,388 L32,375 L18,358 L10,335 Z" },
  { id: "CG", name: "Chhattisgarh",
    d: "M280,348 L300,338 L320,345 L340,358 L348,382 L342,408 L330,428 L315,438 L298,440 L282,432 L272,415 L270,395 L275,372 Z" },
  { id: "MH", name: "Maharashtra",
    d: "M112,385 L125,365 L132,342 L145,355 L162,372 L185,378 L208,382 L232,388 L255,400 L262,422 L258,445 L242,462 L222,472 L200,475 L178,468 L158,455 L140,438 L125,418 L115,398 Z" },
  { id: "OD", name: "Odisha",
    d: "M282,432 L298,440 L315,442 L335,445 L350,458 L362,478 L368,502 L360,522 L345,535 L325,540 L300,532 L280,518 L265,498 L258,475 L260,452 L270,438 Z" },
  { id: "TS", name: "Telangana",
    d: "M215,395 L238,388 L260,392 L278,402 L285,422 L280,442 L270,458 L255,465 L238,462 L222,455 L215,438 L210,418 Z" },
  { id: "GA", name: "Goa",
    d: "M130,478 L142,472 L150,480 L148,492 L138,495 L128,490 Z" },
  { id: "KA", name: "Karnataka",
    d: "M138,495 L150,492 L168,480 L188,475 L208,478 L230,485 L245,498 L248,522 L240,545 L228,562 L210,572 L190,575 L170,570 L152,558 L140,542 L132,522 L130,502 Z" },
  { id: "AP", name: "Andhra Pradesh",
    d: "M245,462 L262,465 L282,470 L300,485 L312,505 L318,528 L310,548 L298,562 L280,572 L262,575 L245,568 L230,558 L240,548 L248,522 L245,498 L238,478 Z" },
  { id: "TN", name: "Tamil Nadu",
    d: "M190,575 L210,572 L230,570 L248,572 L270,580 L285,595 L290,618 L280,638 L265,650 L245,655 L225,650 L208,638 L198,618 L190,598 Z" },
  { id: "KL", name: "Kerala",
    d: "M152,558 L170,570 L180,585 L188,608 L188,632 L180,652 L170,668 L158,675 L148,665 L142,645 L140,622 L142,598 L145,578 Z" },
];

/* ------------------------------------------------------------------ */
/*  Health → colour mapping for map fills                              */
/* ------------------------------------------------------------------ */
const HEALTH_FILLS: Record<string, string> = {
  NORMAL:             "#34d399",
  WATCH:              "#fbbf24",
  ELEVATED:           "#fb923c",
  HIGH:               "#f87171",
  CRITICAL:           "#c084fc",
  DATA_NOT_AVAILABLE: "#94a3b8",
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */
export interface StateStats {
  projectCount: number;
  totalCost: number;
  worstHealth: string;
}

interface IndiaMapProps {
  stateData: Record<string, StateStats>;
}

export default function IndiaMap({ stateData }: IndiaMapProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number } | null>(null);

  const hoveredInfo = useMemo(() => {
    if (!hovered) return null;
    const state = STATES.find((s) => s.name === hovered);
    const data = stateData[hovered];
    return { name: hovered, id: state?.id, ...data };
  }, [hovered, stateData]);

  return (
    <div className="india-map-wrap">
      <svg
        viewBox="0 0 480 690"
        className="india-map-svg"
        role="img"
        aria-label="Map of India showing project distribution by state"
      >
        <defs>
          <filter id="map-glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="activeGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fbbf24" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.7" />
          </linearGradient>
        </defs>

        {STATES.map((state) => {
          const data = stateData[state.name];
          const hasProjects = data && data.projectCount > 0;
          const isHovered = hovered === state.name;
          const fill = hasProjects
            ? HEALTH_FILLS[data.worstHealth] || "#fbbf24"
            : "#e2e8f0";
          return (
            <path
              key={state.id}
              d={state.d}
              fill={isHovered ? (hasProjects ? fill : "#cbd5e1") : fill}
              stroke="#fff"
              strokeWidth={isHovered ? 2 : 1}
              opacity={isHovered ? 1 : hasProjects ? 0.92 : 0.65}
              filter={isHovered && hasProjects ? "url(#map-glow)" : undefined}
              style={{
                cursor: hasProjects ? "pointer" : "default",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                setHovered(state.name);
                const rect = (e.target as SVGElement).ownerSVGElement?.getBoundingClientRect();
                if (rect) {
                  const svgX = e.clientX - rect.left;
                  const svgY = e.clientY - rect.top;
                  setTip({ x: svgX, y: svgY });
                }
              }}
              onMouseMove={(e) => {
                const rect = (e.target as SVGElement).ownerSVGElement?.getBoundingClientRect();
                if (rect) {
                  setTip({ x: e.clientX - rect.left, y: e.clientY - rect.top });
                }
              }}
              onMouseLeave={() => {
                setHovered(null);
                setTip(null);
              }}
            >
              <title>{state.name}</title>
            </path>
          );
        })}

        {/* State labels for states with projects */}
        {STATES.filter((s) => stateData[s.name]?.projectCount > 0).map((state) => {
          const match = state.d.match(
            /M\s*([\d.]+)[,\s]+([\d.]+)/
          );
          if (!match) return null;
          // Rough centroid: average of first coordinate and parse remaining
          const coords = state.d.match(/[\d.]+/g)?.map(Number) || [];
          let cx = 0, cy = 0, count = 0;
          for (let i = 0; i < coords.length; i += 2) {
            cx += coords[i];
            cy += coords[i + 1];
            count++;
          }
          cx /= count;
          cy /= count;
          const data = stateData[state.name];
          return (
            <g key={`label-${state.id}`}>
              <circle cx={cx} cy={cy} r="8" fill="#082b4c" opacity="0.85" />
              <text
                x={cx}
                y={cy + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#fff"
                fontSize="7"
                fontWeight="700"
              >
                {data?.projectCount}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredInfo && tip && (
        <div
          className="map-tooltip"
          style={{
            left: tip.x + 12,
            top: tip.y - 10,
          }}
        >
          <strong>{hoveredInfo.name}</strong>
          {hoveredInfo.projectCount ? (
            <>
              <span>{hoveredInfo.projectCount} project{hoveredInfo.projectCount > 1 ? "s" : ""}</span>
              <span>₹{hoveredInfo.totalCost?.toLocaleString(undefined, { maximumFractionDigits: 0 })} Cr</span>
            </>
          ) : (
            <span className="map-tooltip-empty">No projects</span>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="map-legend">
        <div className="map-legend-item">
          <span className="map-legend-dot" style={{ background: "#34d399" }} />
          <span>On Track</span>
        </div>
        <div className="map-legend-item">
          <span className="map-legend-dot" style={{ background: "#fbbf24" }} />
          <span>Watch</span>
        </div>
        <div className="map-legend-item">
          <span className="map-legend-dot" style={{ background: "#fb923c" }} />
          <span>Elevated</span>
        </div>
        <div className="map-legend-item">
          <span className="map-legend-dot" style={{ background: "#f87171" }} />
          <span>High</span>
        </div>
        <div className="map-legend-item">
          <span className="map-legend-dot" style={{ background: "#e2e8f0" }} />
          <span>No data</span>
        </div>
      </div>
    </div>
  );
}
