import { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

export default function ChartPanel({ chart }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!chart || !ref.current) return;
    const x = chart.data.map((row) => row[chart.x]);
    const y = chart.data.map((row) => row[chart.y]);
    const color = "#0f766e";
    let traces;
    if (chart.type === "pie") {
      traces = [{ type: "pie", labels: x, values: y, hole: 0.35 }];
    } else if (chart.type === "scatter") {
      traces = [{ type: "scatter", mode: "markers", x, y, marker: { color, size: 9 } }];
    } else if (chart.type === "line" || chart.type === "area") {
      traces = [
        {
          type: "scatter",
          mode: "lines+markers",
          x,
          y,
          fill: chart.type === "area" ? "tozeroy" : "none",
          line: { color, width: 2 },
        },
      ];
    } else {
      traces = [{ type: "bar", x, y, marker: { color } }];
    }
    Plotly.react(
      ref.current,
      traces,
      {
        title: { text: chart.title, font: { family: "IBM Plex Serif, serif", size: 16 } },
        margin: { t: 48, r: 16, b: 48, l: 48 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { family: "IBM Plex Sans, sans-serif", color: "#1c1917" },
      },
      { displayModeBar: false, responsive: true }
    );
  }, [chart]);

  if (!chart) {
    return <div className="empty">Charts appear here after you ask for a trend, ranking, or visualization.</div>;
  }
  return <div className="plot" ref={ref} />;
}
