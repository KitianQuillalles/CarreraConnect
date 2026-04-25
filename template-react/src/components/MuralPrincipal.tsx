// src/components/MuralPrincipal.tsx
import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowLeft } from "@fortawesome/free-solid-svg-icons";

// Importamos tus componentes
import { Alerta } from "./Alerta";
import { Banner } from "./Banner";
import { GrillaCards } from "./GrillaCards";
import { ModalDetalle } from "./ModalDetalle";

// Importamos solo la interfaz (el tipo de dato), NO los datos falsos
import type { ContenidoData } from "../data/mockData";

export function MuralPrincipal() {
  // 1. Obtenemos el ID de la carrera desde la URL (ej: /mural/5)
  const { areaId } = useParams();

  // 2. Estados para guardar la información que nos mandará Django
  const [contenidos, setContenidos] = useState<ContenidoData[]>([]);
  const [areaNombre, setAreaNombre] = useState("Cargando...");
  const [cargando, setCargando] = useState(true);

  // 3. Estados para el Modal (igual que antes)
  const [modalShow, setModalShow] = useState(false);
  const [contenidoSeleccionado, setContenidoSeleccionado] =
    useState<ContenidoData | null>(null);

  // 4. Pedir los datos a Django al cargar la pantalla
  useEffect(() => {
    // IMPORTANTE: Asegúrate de que la URL coincida con la que creamos en urls.py de Django
    fetch(`/api/contenidos/${areaId}/`)
      .then((res) => res.json())
      .then((data) => {
        setAreaNombre(data.area_nombre);
        setContenidos(data.contenidos);
        setCargando(false);
      })
      .catch((err) => {
        console.error("Error cargando el mural:", err);
        setCargando(false);
      });
  }, [areaId]);

  const handleAbrirDetalles = (contenido: ContenidoData) => {
    setContenidoSeleccionado(contenido);
    setModalShow(true);
  };

  // Pantalla de carga mientras Django responde
  if (cargando) {
    return (
      <div
        className="vh-100 d-flex justify-content-center align-items-center"
        style={{ backgroundColor: "#005c3c" }}
      >
        <div
          className="spinner-border text-light"
          role="status"
          style={{ width: "3rem", height: "3rem" }}
        ></div>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: "#f8f9fa", minHeight: "100vh" }}>
      {/* NAVBAR SUPERIOR: Reemplaza a NavMenu.tsx para poder volver atrás */}
      <nav
        className="navbar navbar-expand-lg px-4 shadow-sm py-3"
        style={{ backgroundColor: "#007b33" }}
      >
        <div className="container-fluid d-flex align-items-center">
          <Link
            to="/"
            className="btn btn-light rounded-circle d-flex justify-content-center align-items-center me-3 shadow-sm"
            style={{ width: "45px", height: "45px" }}
            title="Volver al Menú"
          >
            <FontAwesomeIcon icon={faArrowLeft} className="fs-5 text-success" />
          </Link>

          <div className="navbar-brand text-white d-flex flex-column lh-1 mb-0">
            <span className="fw-bold fs-2">Carrera Connect</span>
            <span className="fw-light mt-1" style={{ fontSize: "1.2rem" }}>
              {areaNombre}
            </span>
          </div>
        </div>
      </nav>

      {/* COMPONENTES DEL MURAL: Ahora reciben 'contenidos' como Prop */}
      <Alerta contenidos={contenidos} />

      <Banner contenidos={contenidos} onAbrirDetalles={handleAbrirDetalles} />

      <GrillaCards
        contenidos={contenidos}
        onAbrirDetalles={handleAbrirDetalles}
      />

      {/* MODAL */}
      <ModalDetalle
        show={modalShow}
        onHide={() => setModalShow(false)}
        contenido={contenidoSeleccionado}
      />
    </div>
  );
}
