import { useEffect } from "react";

function App() {
  useEffect(() => {
    window.location.replace("/valandala-landing.html");
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#FFF8F3", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <p style={{ color: "#756d76", fontFamily: "Inter, sans-serif", fontSize: "0.9rem", letterSpacing: "0.1em" }}>
        Se încarcă...
      </p>
    </div>
  );
}

export default App;
