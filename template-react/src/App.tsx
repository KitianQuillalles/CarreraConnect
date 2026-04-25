// src/App.tsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { PantallaInicio } from "./components/PantallaInicio.tsx";
import { MuralPrincipal } from "./components/MuralPrincipal.tsx";

function App() {
  return (
    <Router>
      <Routes>
        {/* Ruta raíz: Muestra el menú de selección */}
        <Route path="/" element={<PantallaInicio />} />

        {/* Ruta del mural: Recibe el ID del área en la URL */}
        <Route path="/mural/:areaId" element={<MuralPrincipal />} />
      </Routes>
    </Router>
  );
}

export default App;
