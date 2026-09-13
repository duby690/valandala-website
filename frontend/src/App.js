import { useEffect } from "react";

function App() {
  useEffect(() => {
    window.location.replace("/valandala-landing.html");
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#07100a", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: "rgba(255,255,255,0.3)", fontFamily: "Inter, sans-serif", fontSize: "0.9rem", letterSpacing: "0.1em" }}>
        Se încarcă...
      </p>
    </div>
  );
}

export default App;
