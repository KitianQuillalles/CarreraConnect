// src/components/PantallaInicio.tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faUniversity,
  faTools,
  faCog,
  faGlobe,
  faChevronRight,
  faUserShield,
} from "@fortawesome/free-solid-svg-icons";
// Definimos la estructura de datos que esperamos de Django
interface Area {
  id: number;
  nombre: string;
}

interface AreasData {
  U: Area[];
  IP: Area[];
  CFT: Area[];
  GEN: Area[];
}

export function PantallaInicio() {
  const [areasData, setAreasData] = useState<AreasData | null>(null);
  const [tabActiva, setTabActiva] = useState<keyof AreasData | null>(null);
  const [cargando, setCargando] = useState(true);

  // Al cargar la pantalla, le pedimos las áreas a la API de Django
  useEffect(() => {
    fetch("/api/areas/")
      .then((res) => res.json())
      .then((data) => {
        setAreasData(data);
        setCargando(false);
      })
      .catch((err) => {
        console.error("Error cargando áreas:", err);
        setCargando(false);
      });
  }, []);

  // Función para determinar el título del "Paso 2"
  const obtenerTituloPaso2 = () => {
    switch (tabActiva) {
      case "U":
        return "Carreras Universitarias";
      case "IP":
        return "Carreras Instituto Profesional";
      case "CFT":
        return "Carreras Técnicas";
      case "GEN":
        return "Áreas Transversales";
      default:
        return "";
    }
  };

  return (
    <div
      className="min-vh-100 d-flex flex-column align-items-center justify-content-center"
      style={{ backgroundColor: "#005c3c", color: "white" }}
    >
      {/* BOTÓN AL ADMINISTRADOR DE DJANGO (Mundo Privado) */}
      <div className="position-absolute top-0 end-0 p-4">
        <a
          href="/panel/contenidos/"
          className="btn btn-outline-light d-flex align-items-center gap-2"
        >
          <FontAwesomeIcon icon={faUserShield} />
          Administrador
        </a>
      </div>

      <div className="container text-center py-5">
        {/* LOGO Y TÍTULO */}
        <div className="mb-5">
          <img
            src="/static/react/LogoCC.png"
            alt="Logo"
            className="mb-3"
            style={{ maxHeight: "90px" }}
          />
        </div>

        {/* PASO 1: BOTONES DE NIVELES */}
        <h5 className="fw-semibold mb-3">
          Paso 1: Seleccione un nivel para ver las carreras
        </h5>
        <div
          className="d-inline-flex flex-wrap justify-content-center gap-2 p-2 mb-5 rounded"
          style={{ backgroundColor: "rgba(255,255,255,0.08)" }}
        >
          <button
            className={`btn ${tabActiva === "U" ? "btn-light text-success fw-bold" : "btn-outline-light border-0 fw-semibold"}`}
            onClick={() => setTabActiva("U")}
          >
            <FontAwesomeIcon icon={faUniversity} className="me-2" /> UST
          </button>

          <button
            className={`btn ${tabActiva === "IP" ? "btn-light text-success fw-bold" : "btn-outline-light border-0 fw-semibold"}`}
            onClick={() => setTabActiva("IP")}
          >
            <FontAwesomeIcon icon={faTools} className="me-2" /> IPST
          </button>

          <button
            className={`btn ${tabActiva === "CFT" ? "btn-light text-success fw-bold" : "btn-outline-light border-0 fw-semibold"}`}
            onClick={() => setTabActiva("CFT")}
          >
            <FontAwesomeIcon icon={faCog} className="me-2" /> C.F.T.
          </button>

          <button
            className={`btn ${tabActiva === "GEN" ? "btn-light text-success fw-bold" : "btn-outline-light border-0 fw-semibold"}`}
            onClick={() => setTabActiva("GEN")}
          >
            <FontAwesomeIcon icon={faGlobe} className="me-2" /> General
          </button>
        </div>

        {/* PASO 2: GRILLA DE CARRERAS */}
        {cargando ? (
          <div className="spinner-border text-light" role="status"></div>
        ) : (
          tabActiva &&
          areasData && (
            <div className="animation-fade-in text-start">
              <h5 className="fw-semibold mb-4 text-center">
                {obtenerTituloPaso2()}
              </h5>
              <div className="row g-3 justify-content-center">
                {areasData[tabActiva].length > 0 ? (
                  areasData[tabActiva].map((area) => (
                    <div
                      className="col-12 col-md-6 col-lg-4 col-xl-3"
                      key={area.id}
                    >
                      {/* ESTE LINK NAVEGA AL MURAL DE REACT INSTANTÁNEAMENTE */}
                      <Link
                        to={`/mural/${area.id}`}
                        className="btn btn-light w-100 text-start d-flex justify-content-between align-items-center p-3 text-dark text-decoration-none shadow-sm carrera-btn"
                        style={{ borderRadius: "8px", fontWeight: "600" }}
                      >
                        <span className="text-wrap me-2">{area.nombre}</span>
                        <FontAwesomeIcon
                          icon={faChevronRight}
                          className="text-muted"
                        />
                      </Link>
                    </div>
                  ))
                ) : (
                  <div className="col-12 text-center">
                    <p className="text-white-50">
                      No hay carreras registradas en este nivel.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )
        )}
      </div>

      <style>{`
        .animation-fade-in { animation: fadeInUp 0.4s ease; }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        .carrera-btn { transition: all 0.2s ease; border: 1px solid transparent; }
        .carrera-btn:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.12); border-color: #88dba3; color: #005c3c !important; }
        .carrera-btn:hover svg { color: #005c3c !important; transform: translateX(3px); transition: transform 0.2s ease; }
      `}</style>
    </div>
  );
}
