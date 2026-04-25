// src/components/NavMenu.tsx
import { useState } from "react";

// 1. ACTUALIZAMOS LOS NOMBRES COMPLETOS EN LA DATA
const areasData = {
  "Centro Formación Técnica": [
    "Técnico en Enfermería",
    "Gastronomía",
    "Preparador Físico",
  ],
  "Instituto Profesional": [
    "Ingeniería Informática",
    "Diseño Gráfico",
    "Servicio Social",
  ],
  Universidad: ["Enfermería", "Psicología", "Derecho"],
  General: ["DAE", "Biblioteca", "Centro de Aprendizaje"],
};

interface NavMenuProps {
  onAreaSelect: (area: string) => void;
}

export function NavMenu({ onAreaSelect }: NavMenuProps) {
  // Estado inicial con un nombre completo por defecto
  const [areaActual, setAreaActual] = useState("Ingeniería Informática");

  const handleSeleccion = (area: string) => {
    setAreaActual(area);
    onAreaSelect(area);
  };

  return (
    <nav
      className="navbar navbar-expand-lg px-4 shadow-sm py-4"
      style={{ backgroundColor: "#007b33" }}
    >
      <div className="container-fluid">
        {/* LOGO Y SUBTÍTULO */}
        <div className="navbar-brand text-white d-flex flex-column lh-1">
          <span className="fw-bold fs-1">Carrera Connect</span>
          <span className="fw-light mt-2" style={{ fontSize: "1.5rem" }}>
            {areaActual}
          </span>
        </div>

        <button
          className="navbar-toggler bg-white"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        <div
          className="collapse navbar-collapse justify-content-end"
          id="navbarNav"
        >
          <ul className="navbar-nav gap-3 mt-4 mt-lg-0">
            {Object.entries(areasData).map(([nivel, carreras]) => (
              <li className="nav-item dropdown" key={nivel}>
                <button
                  /* ESTILOS MEJORADOS:
                    - btn-lg y fs-5: Para que el botón sea grande y legible.
                    - text-wrap: Por si el nombre es muy largo en pantallas pequeñas.
                    - px-4: Más espacio horizontal.
                  */
                  className="btn btn-light dropdown-toggle fw-semibold btn-lg py-2 fs-5 w-100 text-start text-lg-center text-wrap"
                  data-bs-toggle="dropdown"
                  aria-expanded="false"
                  style={{ minWidth: "200px" }} // Asegura un tamaño mínimo uniforme
                >
                  {nivel}
                </button>

                <ul className="dropdown-menu dropdown-menu-end shadow border-0 mt-2 p-2">
                  {carreras.map((carrera) => (
                    <li key={carrera}>
                      <button
                        className="dropdown-item py-2 px-3 fs-5 rounded text-wrap"
                        onClick={() => handleSeleccion(carrera)}
                      >
                        {carrera}
                      </button>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </nav>
  );
}
