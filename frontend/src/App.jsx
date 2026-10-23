import { useEffect, useMemo, useRef, useState } from "react";
import ChartPanel from "./ChartPanel.jsx";
import { chat, createSession, uploadFiles } from "./api.js";

const PROMPTS = [
  "Which region generated the highest revenue?",
  "Show monthly sales trends.",
  "Which products are underperforming?",
  "What are the top five customers?",
  "Generate SQL for this analysis.",
  "Detect anomalies in the dataset.",
  "Summarize business insights.",
];

export default function App() {
  const [sessionId, setSessionId] = useState("");
  const [datasets, setDatasets] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [chart, setChart] = useState(null);
  const [sql, setSql] = useState("");
  const [pandasCode, setPandasCode] = useState("");
  const [mode, setMode] = useState("");
  const fileRef = useRef(null);
  const logRef = useRef(null);

  useEffect(() => {
    createSession()
      .then((data) => setSessionId(data.session_id))
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const columns = useMemo(
    () =>
      datasets.map((ds) => ({
        name: ds.name,
        rows: ds.rows,
        types: ds.column_types,
        warnings: ds.warnings || [],
      })),
    [datasets]
  );

  async function onUpload(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length || !sessionId) return;
    setBusy(true);
    setError("");
    try {
      const data = await uploadFiles(sessionId, files);
      setDatasets(data.datasets);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Loaded ${data.datasets.length} file(s): ${data.datasets
            .map((d) => `${d.name} (${d.rows} rows)`)
            .join(", ")}. Ask a question about the data.`,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function send(text) {
    const message = (text ?? input).trim();
    if (!message || !sessionId) return;
    setInput("");
    setBusy(true);
    setError("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    try {
      const data = await chat(sessionId, message);
      setChart(data.chart);
      setSql(data.sql || "");
      setPandasCode(data.pandas_code || "");
      setMode(data.llm_mode);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.answer,
          reasoning: data.reasoning,
          anomalies: data.anomalies,
        },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="mark">Lens</span>
          <p>AI Data Analyst</p>
        </div>
        <button className="upload" onClick={() => fileRef.current?.click()} disabled={!sessionId || busy}>
          Upload CSV files
        </button>
        <input ref={fileRef} type="file" accept=".csv" multiple hidden onChange={onUpload} />
        <div className="hint">One or more CSVs. Sample files live in <code>sample_data/</code>.</div>
        {columns.map((ds) => (
          <section key={ds.name} className="table-card">
            <h3>
              {ds.name} <em>{ds.rows} rows</em>
            </h3>
            <ul>
              {Object.entries(ds.types).map(([col, type]) => (
                <li key={col}>
                  <span>{col}</span>
                  <small>{type}</small>
                </li>
              ))}
            </ul>
            {ds.warnings.map((w) => (
              <p key={w} className="warn">
                {w}
              </p>
            ))}
          </section>
        ))}
      </aside>

      <main>
        <header>
          <div>
            <h1>Ask the data anything.</h1>
            <p>Natural-language analysis with SQL, charts, anomalies, and an explanation of the reasoning.</p>
          </div>
          {mode && <span className="mode">{mode}</span>}
        </header>

        <div className="prompts">
          {PROMPTS.map((item) => (
            <button key={item} disabled={busy || !datasets.length} onClick={() => send(item)}>
              {item}
            </button>
          ))}
        </div>

        <div className="log" ref={logRef}>
          {messages.length === 0 && (
            <div className="empty">Upload a CSV, then try “Which region generated the highest revenue?”</div>
          )}
          {messages.map((msg, index) => (
            <article key={index} className={msg.role}>
              <strong>{msg.role === "user" ? "You" : "Lens"}</strong>
              <pre>{msg.text}</pre>
              {msg.reasoning && (
                <details>
                  <summary>Why this answer</summary>
                  <p>{msg.reasoning}</p>
                </details>
              )}
              {msg.anomalies?.filter((a) => a.count).map((item, i) => (
                <div className="anomaly" key={i}>
                  <b>
                    {item.table}.{item.column}
                  </b>
                  <span>{item.reason}</span>
{item.sample_rows?.length > 0 && (
  <details className="anomaly-samples">
    <summary>View sample rows ({item.sample_rows.length})</summary>
    <div className="sample-table-wrap">
      <table>
        <thead>
          <tr>
            {Object.keys(item.sample_rows[0]).map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {item.sample_rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {Object.keys(item.sample_rows[0]).map((column) => (
                <td key={column}>
                  {row[column] == null ? "—" : String(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </details>
)}
                </div>
              ))}
            </article>
          ))}
          {busy && <div className="empty">Working…</div>}
        </div>

        {error && <div className="error">{error}</div>}

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            send();
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={datasets.length ? "Ask about revenue, trends, quality…" : "Upload CSVs first"}
            disabled={busy || !datasets.length}
          />
          <button type="submit" disabled={busy || !datasets.length}>
            Send
          </button>
        </form>
      </main>

      <section className="viz">
        <h2>Visualization</h2>
        <ChartPanel chart={chart} />
        {sql && (
          <>
            <h2>SQL</h2>
            <pre className="code">{sql}</pre>
          </>
        )}
        {pandasCode && (
          <>
            <h2>Pandas</h2>
            <pre className="code">{pandasCode}</pre>
          </>
        )}
      </section>
    </div>
  );
}
